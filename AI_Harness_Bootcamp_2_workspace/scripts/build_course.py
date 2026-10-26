#!/usr/bin/env python3
"""Publish the allowlisted Reformation course; --check never writes."""
from __future__ import annotations

import argparse
import html
import json
import os
import posixpath
import re
import sys
import zlib
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import markdown

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PARTS = {"staff", "facilitator", "reference", "reviews", "review", "history", "evidence", "tests", "work", "__pycache__", ".git", "graded", "answer-keys", "answers"}
SAFE_TAGS = set("a p h1 h2 h3 h4 h5 h6 ul ol li em strong code pre blockquote table caption thead tbody tr th td details summary img hr br div span dl dt dd sup sub del input".split())
VOID_TAGS = {"img", "hr", "br", "input", "meta", "link"}
COMMAND_LANGUAGES = {"bash", "sh", "zsh", "powershell"}
PAGE_KINDS = {"home", "overview", "lab", "setup", "reference"}
UI_SUFFIXES = {".css", ".js", ".woff2", ".txt", ".svg", ".webp"}
SEARCH_PATH = PurePosixPath("assets/search-index.json")
CALLOUT_KINDS = {"Expected:": "expected", "Stop:": "stop", "Recovery:": "recovery"}
SHELL_FAMILY = {"bash": "bash", "sh": "bash", "zsh": "bash", "powershell": "powershell"}
SHELL_NAMES = {"bash": "Bash or zsh", "powershell": "PowerShell"}
STEP_NUMBER = re.compile(r"^\s*(\d+)\.\s+")


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Node | str] = field(default_factory=list)

    def text(self) -> str:
        return "".join(child.text() if isinstance(child, Node) else child for child in self.children)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def render(self) -> str:
        if not self.tag:
            return "".join(child.render() if isinstance(child, Node) else html.escape(child, quote=False) for child in self.children)
        attrs = "".join(f' {key}="{html.escape(value, quote=True)}"' for key, value in self.attrs.items())
        if self.tag in VOID_TAGS:
            return f"<{self.tag}{attrs}>"
        inner = "".join(child.render() if isinstance(child, Node) else html.escape(child, quote=False) for child in self.children)
        return f"<{self.tag}{attrs}>{inner}</{self.tag}>"


class TreeParser(HTMLParser):
    def __init__(self, safe_fragment: bool = False):
        super().__init__(convert_charrefs=True)
        self.root = Node("")
        self.stack = [self.root]
        self.safe_fragment = safe_fragment

    def handle_starttag(self, tag, attrs):
        if self.safe_fragment and tag not in SAFE_TAGS:
            raise ValueError(f"active or unsupported HTML element: {tag}")
        attributes = dict((key, value or "") for key, value in attrs)
        if len(attributes) != len(attrs):
            raise ValueError("duplicate HTML attribute")
        for key, value in attributes.items():
            if key.lower().startswith("on") or key in {"srcdoc", "formaction", "style"}:
                raise ValueError(f"active HTML attribute: {key}")
            if key in {"href", "src"} and urlsplit(value).scheme.lower() not in {"", "https", "http", "mailto"}:
                raise ValueError(f"unsafe link scheme: {value}")
        node = Node(tag, attributes)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise ValueError(f"unbalanced HTML closing tag: {tag}")
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def finish(self) -> Node:
        self.close()
        if len(self.stack) != 1:
            raise ValueError(f"unclosed HTML element: {self.stack[-1].tag}")
        return self.root


def parse_html(text: str, safe_fragment=False) -> Node:
    parser = TreeParser(safe_fragment)
    parser.feed(text)
    return parser.finish()


def safe_relative(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value or ":" in value:
        raise ValueError(f"invalid manifest path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"..", "."} for part in value.split("/")):
        raise ValueError(f"escaping manifest path: {value}")
    return path


def source_path(base: Path, rel: str) -> Path:
    path = base / safe_relative(rel)
    if any(part.lower() in BLOCKED_PARTS or part.startswith(".") for part in Path(rel).parts):
        raise ValueError(f"staff or hidden source cannot be published: {rel}")
    if path.name in {"CUSTODY_CONTRACT.md", "spec.json"} or path.name.lower().startswith(("answer-key", "graded-")):
        raise ValueError(f"staff source cannot be published: {rel}")
    current = path
    while current != base:
        if current.is_symlink():
            raise ValueError(f"symlink source cannot be published: {path}")
        current = current.parent
    if not path.is_file():
        raise ValueError(f"missing publication source: {path}")
    return path


def inventory(root: Path) -> tuple[dict, dict[PurePosixPath, Path], dict[Path, PurePosixPath], set[Path]]:
    course = json.loads((root / "course.json").read_text(encoding="utf-8"))
    modules = course.get("modules", [])
    if [module.get("id") for module in modules] != [f"{i:02d}" for i in range(11)]:
        raise ValueError("manifest must enumerate exactly the eleven modules 00–10 in order")
    if course.get("schema_version") != 1 or course.get("site_dir") != "site" or course.get("course_id") != "AI_Harness_Bootcamp_2":
        raise ValueError("unsupported course manifest identity")
    boot = root / safe_relative(course["source_root"])
    if boot.resolve() != root.resolve() / "AI_Harness_Bootcamp_2" or boot.is_symlink():
        raise ValueError("source_root must be the Reformation module tree")
    destinations: dict[PurePosixPath, Path] = {}
    sources: dict[Path, PurePosixPath] = {}
    pages: set[Path] = set()

    def add(base: Path, src: str, dest: str, page: bool = False):
        source = source_path(base, src)
        target = safe_relative(dest)
        if any(part.lower() in BLOCKED_PARTS for part in target.parts):
            raise ValueError(f"staff destination: {target}")
        if target == SEARCH_PATH:
            raise ValueError("search index is a reserved generated destination")
        if target in destinations:
            raise ValueError(f"duplicate publication destination: {target}")
        if source in sources:
            raise ValueError(f"duplicate publication source: {source}")
        if not page and source.suffix.lower() in {".html", ".htm", ".pyc"}:
            raise ValueError(f"untrusted or generated raw artifact cannot be published: {source}")
        destinations[target] = source
        sources[source] = target
        if page:
            if source.suffix != ".md" or target.suffix != ".html":
                raise ValueError(f"instructional page must map Markdown to HTML: {source}")
            pages.add(source)

    if course["index"].get("kind") != "home":
        raise ValueError("index must be the home page")
    if "guide" in course["index"]:
        raise ValueError("home cannot define a guide")
    add(boot, course["index"]["source"], course["index"]["dest"], True)
    for module in modules:
        directory = module["directory"]
        if any(not isinstance(module.get(key), str) or not module[key].strip() for key in ("title", "case_name", "summary", "nav_summary")):
            raise ValueError("module display fields must be nonempty strings")
        outcomes = module.get("outcomes", {})
        if not isinstance(outcomes, dict) or not set(outcomes) <= {"can", "will"}:
            raise ValueError(f"module {module['id']}: outcomes may contain only 'can' and 'will'")
        if not isinstance(outcomes.get("can", ""), str):
            raise ValueError(f"module {module['id']}: outcomes.can must be a string")
        will = outcomes.get("will", [])
        if not isinstance(will, list) or any(not isinstance(item, str) or not item.strip() for item in will):
            raise ValueError(f"module {module['id']}: outcomes.will must be a list of nonempty strings")
        kinds = [page.get("kind") for page in module["pages"]]
        if any(kind not in PAGE_KINDS - {"home"} for kind in kinds):
            raise ValueError("unrecognized instructional page kind")
        if any(kinds.count(kind) != 1 for kind in ("overview", "lab")):
            raise ValueError("each module needs one overview and lab page")
        safe_relative(directory)
        if not re.fullmatch(rf"module-{module['id']}-[a-z0-9-]+", directory):
            raise ValueError(f"module ID/directory mismatch: {directory}")
        base = boot / directory
        prefix = PurePosixPath(course["course_id"]) / directory
        for page in module["pages"]:
            if "guide" in page:
                guide = page["guide"]
                if not isinstance(guide, dict) or not set(guide) <= {"context_sections", "optional_sections"}:
                    raise ValueError(f"{directory}/{page['source']}: guide may declare only context_sections and optional_sections")
                anchors = []
                for values in guide.values():
                    if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
                        raise ValueError("guide sections must be lists of nonempty anchors")
                    anchors.extend(values)
                if len(anchors) != len(set(anchors)):
                    raise ValueError("guide anchors must be unique and disjoint")
            add(base, page["source"], str(prefix / page["dest"]), True)
        for kind in ("figures", "scripts"):
            for entry in module.get(kind, []):
                add(base, entry["source"], str(prefix / entry["dest"]))
        for relative in module.get("raw_downloads", []):
            add(base, relative, str(prefix / relative))
        for relative in module.get("download_dirs", []):
            folder = base / safe_relative(relative)
            if not folder.is_dir() or folder.is_symlink():
                raise ValueError(f"missing or linked exercise directory: {folder}")
            for source in sorted(folder.rglob("*")):
                if source.is_symlink():
                    raise ValueError(f"linked exercise source: {source}")
                if source.is_file():
                    rel = source.relative_to(base).as_posix()
                    if any(part == "__pycache__" for part in source.parts) or source.suffix == ".pyc":
                        continue
                    add(base, rel, str(prefix / rel))
        verifier = module.get("verifier_download")
        if verifier and (base / verifier) not in sources:
            add(base, verifier, str(prefix / verifier))
    for entry in course.get("shared_downloads", []):
        add(root, entry["source"], entry["dest"])
    ui_assets = course.get("ui_assets", [])
    for entry in ui_assets:
        if PurePosixPath(entry["source"]).suffix not in UI_SUFFIXES or PurePosixPath(entry["dest"]).suffix not in UI_SUFFIXES:
            raise ValueError("unsupported UI asset type")
        add(root, entry["source"], entry["dest"])
    if not {"assets/course.css", "assets/course.js", "assets/theme-init.js"}.issubset(entry["dest"] for entry in ui_assets):
        raise ValueError("course.css, course.js and theme-init.js must be declared")
    bands = course.get("home_bands", {})
    if not isinstance(bands, dict):
        raise ValueError("home_bands must be an object")
    ui_destinations = {entry["dest"] for entry in ui_assets}
    hero = next((entry["dest"] for entry in ui_assets if PurePosixPath(entry["dest"]).suffix == ".webp"), None)
    band_destinations = set()
    for band_id, target in bands.items():
        if not isinstance(band_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", band_id):
            raise ValueError(f"invalid home band id: {band_id!r}")
        if not isinstance(target, str) or not target.endswith(".webp") or target not in ui_destinations:
            raise ValueError(f"home band must reference a declared WebP UI asset: {target!r}")
        if target == hero:
            raise ValueError(f"home band cannot use the hero image: {target}")
        if target in band_destinations:
            raise ValueError(f"home bands must use distinct images: {target}")
        band_destinations.add(target)
    return course, destinations, sources, pages


def rewrite_link(value: str, source: Path, dest: PurePosixPath, mapping: dict[Path, PurePosixPath], course: dict, root: Path) -> str:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return value
    if parsed.path.startswith("/"):
        raise ValueError(f"source link must be relative: {source}: {value}")
    target = Path(os.path.normpath(source.parent / unquote(parsed.path)))
    if target not in mapping:
        raise ValueError(f"unlisted local link: {source.relative_to(root)} -> {value}")
    path = posixpath.relpath(str(mapping[target]), str(dest.parent))
    return urlunsplit(("", "", quote(path, safe="/-._~"), parsed.query, parsed.fragment))


def _annotate_commands(tree: Node) -> None:
    """Mark each fence explicitly labelled with a shell language; every other fence stays ordinary copyable text."""
    for node in tree.walk():
        if node.tag != "pre":
            continue
        codes = [child for child in node.children if isinstance(child, Node) and child.tag == "code"]
        language = codes[0].attrs.get("class", "") if len(codes) == 1 else ""
        if language.startswith("language-") and language.removeprefix("language-") in COMMAND_LANGUAGES:
            node.attrs["data-command"] = language.removeprefix("language-")


def _identify_stretch(node: Node, label: str) -> None:
    """An optional stretch disclosure needs a stable anchor and exactly one summary, guided or not."""
    node.attrs.setdefault("id", "rf-stretch")
    if len([child for child in node.children if isinstance(child, Node) and child.tag == "summary"]) != 1:
        raise ValueError(f"{label}: optional stretch requires one summary")


def _procedure_cards(tree: Node) -> None:
    """Wrap terminal labels with their command, pair the two shells into panels, and wrap Expected/Stop/Recovery. Authored text is unchanged.

    A Bash card followed by its PowerShell twin becomes one ``rf-shell-pair`` of two ``rf-shell-panel`` blocks. When each shell
    carries its own Expected/Stop/Recovery paragraphs, those callouts stay inside that shell's panel; shared callouts after the twin stay outside."""
    def lead(node) -> str:
        if not isinstance(node, Node) or node.tag != "p" or not node.children:
            return ""
        first = node.children[0]
        return first.text().strip() if isinstance(first, Node) and first.tag == "strong" else ""

    def blank(node) -> bool:
        return isinstance(node, str) and not node.strip()

    def rebuild(parent: Node) -> None:
        for child in parent.children:
            if isinstance(child, Node):
                rebuild(child)
        children, cards, index = parent.children, [], 0
        while index < len(children):
            node = children[index]
            head = lead(node)
            after = index + 1
            while after < len(children) and blank(children[after]):
                after += 1
            following = children[after] if after < len(children) else None
            if head.startswith("Terminal:") and isinstance(following, Node) and following.tag == "pre" and "data-command" in following.attrs:
                family = SHELL_FAMILY[following.attrs["data-command"]]
                node.attrs["class"] = "rf-command-head"
                cards.append(Node("div", {"class": "rf-command", "data-shell": family, "data-shell-name": SHELL_NAMES[family]}, [node, *children[index + 1:after], following]))
                index = after + 1
                continue
            kind = next((kind for prefix, kind in CALLOUT_KINDS.items() if head.startswith(prefix)), None)
            cards.append(Node("div", {"class": f"rf-callout rf-callout--{kind}"}, [node]) if kind else node)
            index += 1
        def callout(node) -> bool:
            return isinstance(node, Node) and node.attrs.get("class", "").startswith("rf-callout ")

        def panel_end(start: int, own_callouts: bool) -> int:
            end = start + 1
            if own_callouts:
                while end < len(cards) and (blank(cards[end]) or callout(cards[end])):
                    end += 1
                while end > start + 1 and blank(cards[end - 1]):
                    end -= 1
            return end

        def panel(start: int, end: int) -> Node:
            card = cards[start]
            return Node("div", {"class": "rf-shell-panel", "data-shell": card.attrs["data-shell"], "data-shell-name": card.attrs["data-shell-name"]}, cards[start:end])

        paired, index = [], 0
        while index < len(cards):
            node = cards[index]
            if isinstance(node, Node) and node.attrs.get("data-shell") == "bash":
                after = index + 1
                while after < len(cards) and (blank(cards[after]) or callout(cards[after])):
                    after += 1
                partner = cards[after] if after < len(cards) else None
                if isinstance(partner, Node) and partner.attrs.get("data-shell") == "powershell":
                    own = any(callout(item) for item in cards[index + 1:after])
                    bash_end = panel_end(index, own)
                    partner_end = panel_end(after, own)
                    paired.append(Node("div", {"class": "rf-shell-pair"}, [panel(index, bash_end), panel(after, partner_end)]))
                    index = partner_end
                    continue
            paired.append(node)
            index += 1
        parent.children = paired

    rebuild(tree)


def _page_records(course: dict) -> list[dict]:
    records = [{**course["index"], "path": course["index"]["dest"], "moduleId": None}]
    for module in course["modules"]:
        prefix = PurePosixPath(course["course_id"]) / module["directory"]
        records.extend({**page, "path": str(prefix / page["dest"]), "moduleId": module["id"]} for page in module["pages"])
    return records


def _guide_tree(tree: Node, guide: dict, label: str) -> tuple[list[dict], list[dict]]:
    """Group only top-level boundaries; retain the original nodes and their order."""
    contexts = set(guide.get("context_sections", []))
    optional = set(guide.get("optional_sections", []))
    headings = [node.attrs.get("id") for node in tree.children if isinstance(node, Node) and node.tag == "h2"]
    if any(headings.count(anchor) != 1 for anchor in contexts | optional):
        raise ValueError(f"{label}: missing or duplicate configured guide anchor")
    original_text = tree.text()
    original_ids = [node.attrs["id"] for node in tree.walk() if "id" in node.attrs]
    original_commands = [node.text() for node in tree.walk() if "data-command" in node.attrs]
    children, result, steps, outline = tree.children, [], [], []

    def stretch(node):
        return isinstance(node, Node) and node.tag == "details" and "rf-stretch" in node.attrs.get("class", "").split()

    def identify_stretch(node):
        _identify_stretch(node, label)
        outline.append({"id": node.attrs["id"], "title": "Optional stretch"})

    index = 0
    while index < len(children):
        node = children[index]
        if isinstance(node, Node) and node.tag == "h2":
            anchor = node.attrs["id"]
            end = index + 1
            while end < len(children) and not (isinstance(children[end], Node) and children[end].tag == "h2") and not stretch(children[end]):
                end += 1
            if anchor in optional:
                if end == len(children) or not stretch(children[end]):
                    raise ValueError(f"{label}: optional heading must precede its stretch disclosure")
                identify_stretch(children[end])
                group = children[index:end + 1]
                result.append(Node("section", {"class": "rf-optional"}, group))
                index = end + 1
                continue
            group = children[index:end]
            context = anchor in contexts
            name = "context" if context else "step"
            body = Node("div", {"class": f"rf-{name}-body", "id": f"rf-body-{anchor}"}, group[1:])
            attrs = {"class": f"rf-{name}", f"data-{name}-id": anchor}
            item = {"id": anchor, "title": node.text()}
            if not context:
                attrs["data-step-index"] = str(len(steps) + 1)
                authored = STEP_NUMBER.match(item["title"])
                if authored and isinstance(node.children[0], str):
                    item["title"] = STEP_NUMBER.sub("", item["title"], count=1)
                    item["number"] = authored.group(1)
            result.append(Node("section", attrs, [node, body]))
            outline.append(item)
            if not context:
                steps.append(item)
            index = end
        elif stretch(node):
            identify_stretch(node)
            result.append(node)
            index += 1
        else:
            result.append(node)
            index += 1
    tree.children = result
    if tree.text() != original_text or [node.text() for node in tree.walk() if "data-command" in node.attrs] != original_commands:
        raise ValueError(f"{label}: procedure transformation changed authored text")
    final_ids = [node.attrs["id"] for node in tree.walk() if "id" in node.attrs]
    if any(anchor not in final_ids for anchor in original_ids) or len(final_ids) != len(set(final_ids)):
        raise ValueError(f"{label}: procedure transformation changed or duplicated an anchor")
    return steps, outline


def _section_records(tree: Node, title: str) -> list[dict]:
    """Attribute prose once, to its nearest heading; never index fenced bytes."""
    sections = []

    def new_section(anchor: str, text: str, optional: bool, level: int = 0):
        record = {"id": anchor, "title": text, "text": [], "optional": optional, "level": level}
        sections.append(record)
        return record

    current = new_section("", title, False)

    def visit(node: Node | str, optional: bool = False):
        nonlocal current
        if isinstance(node, str):
            current["text"].append(node)
            return
        if node.tag in {"pre", "h1"} or "data-course-map" in node.attrs or "data-photo-band" in node.attrs:
            return
        classes = node.attrs.get("class", "").split()
        if "rf-optional" in classes or "rf-stretch" in classes:
            previous = current
            if "rf-stretch" in classes:
                summary = next(child for child in node.children if isinstance(child, Node) and child.tag == "summary")
                current = new_section(node.attrs["id"], summary.text(), True, 2)
            for child in node.children:
                if not isinstance(child, Node) or child.tag != "summary":
                    visit(child, True)
            current = previous
            return
        if node.tag in {"h2", "h3"}:
            current = new_section(node.attrs["id"], node.text(), optional, int(node.tag[1]))
            return
        for child in node.children:
            visit(child, optional)
        if node.tag in {"p", "li", "td", "th", "summary", "blockquote"}:
            current["text"].append(" ")

    visit(tree)
    for section in sections:
        section["text"] = " ".join("".join(section["text"]).split())
    return sections


def _prepare_page(source: Path, dest: PurePosixPath, mapping: dict[Path, PurePosixPath], course: dict, root: Path, record: dict) -> dict:
    fragment = markdown.markdown(source.read_text(encoding="utf-8"), extensions=["fenced_code", "tables", "toc", "md_in_html"], extension_configs={"tables": {"use_align_attribute": True}}, output_format="html")
    try:
        tree = parse_html(fragment, True)
    except ValueError as error:
        raise ValueError(f"{source.relative_to(root)}: {error}") from error
    label = source.relative_to(root).as_posix()
    if sum(node.tag == "h1" for node in tree.walk()) != 1:
        raise ValueError(f"{label}: expected one h1")
    _annotate_commands(tree)
    placeholders = [node for node in tree.walk() if "data-course-map" in node.attrs]
    if len(placeholders) != (1 if record["kind"] == "home" else 0):
        raise ValueError("exactly one course map placeholder is required, on home only")
    bands = course.get("home_bands", {})
    band_placeholders = [node for node in tree.walk() if "data-photo-band" in node.attrs]
    if band_placeholders and record["kind"] != "home":
        raise ValueError(f"photo band placeholders are allowed on home only: {source}")
    seen_bands = set()
    for node in band_placeholders:
        band_id = node.attrs["data-photo-band"]
        if node.tag != "div" or any(isinstance(child, Node) or child.strip() for child in node.children):
            raise ValueError(f"photo band placeholder must be an empty div: {source}: {band_id}")
        if band_id not in bands:
            raise ValueError(f"unknown photo band id: {source}: {band_id}")
        if band_id in seen_bands:
            raise ValueError(f"duplicate photo band placeholder: {source}: {band_id}")
        seen_bands.add(band_id)
    if record["kind"] == "home" and set(bands) != seen_bands:
        raise ValueError("home bands lack placeholders: " + ", ".join(sorted(set(bands) - seen_bands)))
    if any(node.attrs.get("id", "").startswith("rf-") for node in tree.walk()):
        raise ValueError("rf- anchors are reserved for the publisher")
    title = next(node.text() for node in tree.walk() if node.tag == "h1")
    steps = []
    outline = [{"id": node.attrs["id"], "title": node.text()} for node in tree.children if isinstance(node, Node) and node.tag == "h2"]
    if "guide" in record:
        steps, outline = _guide_tree(tree, record["guide"], label)
    for node in tree.walk():
        if node.tag == "details" and "rf-stretch" in node.attrs.get("class", "").split():
            _identify_stretch(node, label)
    _procedure_cards(tree)
    sections = _section_records(tree, title)
    heading = "Course data"
    for node in list(tree.walk()):
        if node.tag.startswith("h") and node.tag[1:].isdigit():
            heading = node.text()
        if node.tag == "table":
            node.children.insert(0, Node("caption", {}, [heading]))
        if node.tag == "th":
            node.attrs["scope"] = "col"
        if node.tag == "img" and not node.attrs.get("alt", "").strip():
            raise ValueError(f"{source}: image needs alternative text")
        for attr in ("href", "src"):
            if attr in node.attrs:
                node.attrs[attr] = rewrite_link(node.attrs[attr], source, dest, mapping, course, root)
    def wrap_tables(parent: Node):
        for i, child in enumerate(parent.children):
            if isinstance(child, Node):
                wrap_tables(child)
                if child.tag == "table":
                    parent.children[i] = Node("div", {"class": "table-scroll", "tabindex": "0", "role": "region", "aria-label": child.children[0].text()}, [child])
    wrap_tables(tree)
    return {"tree": tree, "title": title, "record": record, "sections": sections, "outline": outline, "steps": steps}


def _relative(dest: PurePosixPath, target: str) -> str:
    return quote(posixpath.relpath(target, str(dest.parent)), safe="/-._~")


def _outcomes(module: dict) -> tuple[str, list[str]]:
    """Displayed outcome text; a blank capability or an empty activity list is simply absent."""
    outcomes = module.get("outcomes", {})
    can = outcomes.get("can", "")
    return (can if can.strip() else ""), outcomes.get("will", [])


def _course_map(course: dict, dest: PurePosixPath) -> Node:
    rows = []
    for module in course["modules"]:
        overview = next(page for page in module["pages"] if page["kind"] == "overview")
        path = str(PurePosixPath(course["course_id"]) / module["directory"] / overview["dest"])
        can, _ = _outcomes(module)
        parts = [
            Node("span", {"class": "rf-map-number"}, [module["id"]]),
            Node("span", {"class": "rf-map-name"}, [module["case_name"]]),
            Node("span", {"class": "rf-map-title"}, [module["title"].split("·", 1)[-1].strip()]),
            Node("span", {"class": "rf-map-summary"}, [module["summary"]]),
        ]
        if can:
            parts.append(Node("span", {"class": "rf-map-outcome"}, [can]))
        parts.append(Node("span", {"class": "rf-map-progress", "data-module-progress": module["id"]}, []))
        rows.append(Node("li", {}, [Node("a", {"href": _relative(dest, path)}, parts)]))
    return Node("ol", {"class": "rf-course-map"}, rows)


def _module_routes(course: dict, module: dict) -> dict[str, str]:
    prefix = PurePosixPath(course["course_id"]) / module["directory"]
    return {page["kind"]: str(prefix / page["dest"]) for page in module["pages"] if page["kind"] in {"overview", "lab"}}


def _png_dimensions(data: bytes, path: PurePosixPath) -> tuple[str, str]:
    """Read a complete PNG IHDR; image data decoding is left to the browser."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid PNG signature: {path}")
    if len(data) < 33:
        raise ValueError(f"truncated PNG IHDR: {path}")
    if int.from_bytes(data[8:12], "big") != 13 or data[12:16] != b"IHDR":
        raise ValueError(f"invalid PNG IHDR length or first chunk: {path}")
    if zlib.crc32(data[12:29]) != int.from_bytes(data[29:33], "big"):
        raise ValueError(f"invalid PNG IHDR checksum: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if not (0 < width <= 0x7fffffff and 0 < height <= 0x7fffffff):
        raise ValueError(f"invalid PNG intrinsic dimensions: {path}")
    depth, color, compression, filtering, interlace = data[24:29]
    depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
    if depth not in depths.get(color, ()) or compression != 0 or filtering != 0 or interlace not in (0, 1):
        raise ValueError(f"invalid PNG IHDR fields: {path}")
    return str(width), str(height)


def _webp_dimensions(data: bytes, path: PurePosixPath) -> tuple[str, str]:
    """Read WebP intrinsic dimensions; image data decoding is left to the browser."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"invalid WebP signature: {path}")
    if int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise ValueError(f"invalid WebP RIFF size: {path}")
    if len(data) < 20 or data[12:16] not in {b"VP8 ", b"VP8L", b"VP8X"}:
        raise ValueError(f"invalid WebP first chunk: {path}")
    offset = 12
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError(f"truncated WebP chunk header: {path}")
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        offset += 8 + size + (size & 1)
        if offset > len(data):
            raise ValueError(f"truncated WebP chunk: {path}")
    size = int.from_bytes(data[16:20], "little")
    chunk = data[20:20 + size]
    kind = data[12:16]
    if kind == b"VP8 ":
        if len(chunk) < 10 or chunk[0] & 1 or chunk[3:6] != b"\x9d\x01\x2a":
            raise ValueError(f"invalid WebP VP8 keyframe: {path}")
        width = int.from_bytes(chunk[6:8], "little") & 0x3fff
        height = int.from_bytes(chunk[8:10], "little") & 0x3fff
    elif kind == b"VP8L":
        if len(chunk) < 5 or chunk[0] != 0x2f:
            raise ValueError(f"invalid WebP VP8L header: {path}")
        bits = int.from_bytes(chunk[1:5], "little")
        width = (bits & 0x3fff) + 1
        height = ((bits >> 14) & 0x3fff) + 1
    else:
        if len(chunk) != 10:
            raise ValueError(f"invalid WebP VP8X header: {path}")
        width = int.from_bytes(chunk[4:7], "little") + 1
        height = int.from_bytes(chunk[7:10], "little") + 1
    if not width or not height:
        raise ValueError(f"invalid WebP intrinsic dimensions: {path}")
    return str(width), str(height)


def _asset_context(course: dict, outputs: dict[PurePosixPath, bytes]) -> dict:
    declared = [PurePosixPath(entry["dest"]) for entry in course["ui_assets"]]
    fonts = []
    for path in declared:
        if path.suffix != ".css":
            continue
        for face in re.findall(r"@font-face\s*\{([^}]+)\}", outputs[path].decode(), re.S):
            if "U+0000-00FF" not in face or not re.search(r"font-family:\s*['\"](?:Inter|Space Grotesk)['\"]", face):
                continue
            source = re.search(r"""url\(['"]([^'"]+)['"]\)""", face)
            if source:
                fonts.append(posixpath.normpath(str(path.parent / source[1])))
    dimensions = {}
    for path, data in outputs.items():
        if path.suffix == ".svg" and "figures" in path.parts:
            image = ET.fromstring(data)
            viewbox = image.get("viewBox", "").split()
            width, height = image.get("width", ""), image.get("height", "")
            if not width.isdigit() or not height.isdigit():
                if len(viewbox) != 4:
                    raise ValueError(f"figure lacks intrinsic dimensions: {path}")
                width, height = viewbox[2:]
            dimensions[str(path)] = (width, height)
        elif path.suffix.lower() == ".png" and "figures" in path.parts:
            dimensions[str(path)] = _png_dimensions(data, path)
    for path in declared:
        if path.suffix == ".webp":
            dimensions[str(path)] = _webp_dimensions(outputs[path], path)
    hero = next((str(path) for path in declared if path.suffix == ".webp"), None)
    return {"styles": [str(path) for path in declared if path.suffix == ".css"],
            "fonts": fonts, "hero": hero,
            "dimensions": dimensions}


def _appearance(extra_class: str = "") -> str:
    return f'''<label class="rf-appearance {extra_class}" hidden>Appearance
<select class="sc-select" data-theme><option value="system">System</option><option value="dark">Dark</option><option value="sand">Sand</option></select></label>'''


def _reset_place() -> str:
    return '<button type="button" class="sc-btn rf-btn sc-btn--secondary rf-reset" data-reset-place hidden>Reset progress on this device</button>'


def _course_navigation(modules: list[dict], dest: PurePosixPath, current_module: str | None, rail: bool = False) -> str:
    links = []
    for module in modules:
        attrs = ' aria-current="page"' if module["overview"] == str(dest) else ""
        if module["id"] == current_module:
            attrs += f' data-current-module="{module["id"]}"'
        label = html.escape(f'{module["id"]} · {module["caseName"]}')
        summary = html.escape(module["navSummary"])
        css = ' class="sc-rail__item"' if rail else ""
        links.append(f'<a{css} href="{_relative(dest, module["overview"])}"{attrs}><span class="sc-rail__label"><span class="rf-nav-name">{label}</span><span class="rf-nav-summary">{summary}</span></span></a>')
    return f'<nav class="rf-nav{" sc-rail" if rail else ""}" aria-label="Course assignments">{"".join(links)}</nav>'


def _step_labels(steps: list[dict]) -> dict[str, str]:
    """Authored numbers win when any step carries one; unnumbered preparation steps then show a neutral marker."""
    if any("number" in item for item in steps):
        return {item["id"]: item.get("number", "·") for item in steps}
    return {item["id"]: str(index + 1) for index, item in enumerate(steps)}


def _outline(items: list[dict], *, compact: bool = False, steps: list[dict] | None = None) -> str:
    labels = _step_labels(steps or [])
    grouped: list[tuple[dict, list[dict]]] = []
    for item in items:
        if item["level"] == 3 and grouped:
            grouped[-1][1].append(item)
        else:
            grouped.append((item, []))

    def row(item: dict, children: list[dict]) -> str:
        anchor = html.escape(item["id"], quote=True)
        title = html.escape(item["title"])
        if compact:
            number = labels.get(item["id"], "")
            prefix = f"Step {number} · " if number.isdigit() else ""
            opening = '<li class="rf-outline-item">'
            content = f'<a href="#{anchor}">{prefix}{title}</a>'
        elif item["id"] in labels:
            number = labels[item["id"]]
            done = f"Step {number} done: {title}" if number.isdigit() else f"Done: {title}"
            opening = f'<li class="rf-stepper-item" data-step-ref="{anchor}">'
            content = (f'<input class="rf-stepper-check" type="checkbox" id="rf-done-{anchor}" data-step-done="{anchor}" aria-label="{done}">'
                       f'<a href="#{anchor}"><span class="rf-stepper-number" aria-hidden="true">{number}</span><span class="rf-stepper-title">{title}</span></a>')
        elif steps is not None:
            opening = '<li class="rf-stepper-item rf-stepper-item--aside">'
            content = f'<a href="#{anchor}"><span class="rf-stepper-title">{title}</span></a>'
        else:
            opening = '<li class="rf-outline-item">'
            content = f'<a href="#{anchor}">{title}</a>'
        nested = f'<ol class="rf-outline-children">{"".join(row(child, []) for child in children)}</ol>' if children else ""
        return opening + content + nested + "</li>"

    rows = "".join(row(item, children) for item, children in grouped)
    if compact:
        return (f'<details class="rf-inline-outline"><summary><span class="rf-outline-label">On this page</span>'
                f'<span class="rf-outline-current" hidden></span></summary>'
                f'<nav aria-label="On this page"><ol>{rows}</ol></nav></details>')
    label = "Steps" if steps is not None else "On this page"
    css = ' class="rf-stepper-nav"' if steps is not None else ""
    return f'<nav id="rf-outline"{css} aria-label="{label}"><h2 class="sc-label">{label}</h2><ol class="rf-stepper">{rows}</ol></nav>'


def _decorate_reading(tree: Node, dest: PurePosixPath, assets: dict, kind: str):
    entry = False
    for child in tree.children:
        if not isinstance(child, Node):
            continue
        if child.tag == "h2":
            entry = child.attrs.get("id") == "start-here"
        if entry and child.tag in {"ol", "ul"} and kind == "overview":
            child.attrs["class"] = "rf-entry-sequence"
            first = next((node for node in child.walk() if node.tag == "a"), None)
            if first:
                first.attrs["class"] = "sc-btn rf-btn sc-btn--primary"

    def decorate(parent: Node):
        for index, child in enumerate(parent.children):
            if not isinstance(child, Node):
                continue
            decorate(child)
            if child.tag == "pre":
                language = child.attrs.get("data-command", "Source")
                child.attrs.update({"tabindex": "0", "role": "region", "aria-label": f"{language} code"})
            if child.tag == "table" and kind == "overview" and any("/platforms/" in n.attrs.get("href", "") or n.attrs.get("href", "").startswith("platforms/") for n in child.walk()):
                child.attrs["class"] = "rf-platform-table"
            if child.tag == "img":
                target = posixpath.normpath(str(dest.parent / unquote(urlsplit(child.attrs["src"]).path)))
                if target in assets["dimensions"]:
                    width, height = assets["dimensions"][target]
                    child.attrs.update({"width": width, "height": height, "loading": "lazy", "class": "rf-figure-image"})
                    link = Node("a", {"href": child.attrs["src"], "class": "rf-figure-link", "data-figure-open": ""}, ["Open full-size figure"])
                    parent.children[index] = Node("span", {"class": "rf-figure"}, [child, link])
    decorate(tree)


def _dialogs(navigation: str, home: str) -> str:
    close = '<button type="button" class="sc-btn rf-btn sc-btn--secondary" data-dialog-close>Close</button>'
    return f'''<dialog id="rf-course-dialog" class="sc-drawer rf-dialog" aria-labelledby="rf-course-title" hidden>
<div class="rf-dialog-head"><h2 id="rf-course-title">Course</h2>{close}</div>{navigation}
<div class="rf-menu-tools">{_appearance()}{_reset_place()}</div></dialog>
<dialog id="rf-search-dialog" class="sc-palette rf-dialog" aria-labelledby="rf-search-title" hidden>
<div class="rf-dialog-head"><h2 id="rf-search-title">Search course</h2>{close}</div>
<label for="rf-search-input">Search the lessons</label><input id="rf-search-input" class="sc-input" type="search" autocomplete="off">
<label for="rf-search-scope">Search scope</label><select id="rf-search-scope" class="sc-select">
<option value="all">Whole course</option><option value="module">This module</option><option value="page">This page</option></select>
<p id="rf-search-status" role="status"></p><ol id="rf-search-results" class="rf-search-results"></ol>
<div class="rf-search-recovery" hidden><button type="button" class="sc-btn rf-btn sc-btn--secondary" data-search-retry>Retry</button>
<a class="sc-btn rf-btn sc-btn--secondary" href="{home}#work-through-the-assignments">Course map</a></div></dialog>
<dialog id="rf-figure-dialog" class="sc-drawer rf-dialog" aria-labelledby="rf-figure-title" hidden>
<div class="rf-dialog-head"><h2 id="rf-figure-title">Full-size figure</h2>{close}</div>
<div class="rf-figure-scroll" tabindex="0" role="region" aria-label="Full-size figure"></div></dialog>'''


def render_page(source: Path, dest: PurePosixPath, mapping: dict[Path, PurePosixPath], course: dict, root: Path, prepared: dict) -> bytes:
    tree, title, record, common = prepared["tree"], prepared["title"], prepared["record"], prepared["common"]
    kind, module_id = record["kind"], record["moduleId"]
    home = _relative(dest, course["index"]["dest"])
    assets = common["assets"]
    module = next((item for item in course["modules"] if item["id"] == module_id), None)
    can, will = _outcomes(module) if module else ("", [])
    outcomes_title = "After this assignment you can" if can else "You will"
    routes = _module_routes(course, module) if module else {}
    navigation = _course_navigation(common["modules"], dest, module_id)
    _decorate_reading(tree, dest, assets, kind)
    for node in list(tree.walk()):
        if "data-course-map" in node.attrs:
            node.children = [_course_map(course, dest)]
        if "data-photo-band" in node.attrs:
            target = course["home_bands"][node.attrs["data-photo-band"]]
            width, height = assets["dimensions"][target]
            node.tag = "figure"
            node.attrs = {"class": "rf-band sc-photo", "data-sc-theme": "dark"}
            node.children = [Node("img", {"class": "rf-band-image", "src": _relative(dest, target),
                                          "width": width, "height": height, "alt": "", "loading": "lazy", "decoding": "async"})]
    h1 = next(node for node in tree.children if isinstance(node, Node) and node.tag == "h1")
    tree.children.remove(h1)
    page_data = {"version": 2, "page": str(dest), "kind": kind, "moduleId": module_id,
                 "root": posixpath.relpath(".", str(dest.parent)).rstrip("/") + "/",
                 "modules": common["modules"], "pages": common["pages"], "steps": prepared["steps"], "resume": common["resume"]}
    module_steps = sum(len(page["steps"]) for page in common["pages"] if page["moduleId"] == module_id)
    labels = _step_labels(prepared["steps"])
    for section in list(tree.walk()):
        if section.tag == "section" and "data-step-index" in section.attrs:
            heading = next(child for child in section.children if isinstance(child, Node) and child.tag == "h2")
            if isinstance(heading.children[0], str) and STEP_NUMBER.match(heading.children[0]):
                heading.children[0] = STEP_NUMBER.sub("", heading.children[0], count=1)
            heading.children.insert(0, Node("span", {"class": "rf-step-number", "aria-hidden": "true"}, [labels[section.attrs["data-step-id"]]]))
    nav_items = [{"id": section["id"], "title": section["title"], "level": section["level"]}
                 for section in prepared["sections"] if section["level"] in {2, 3}]
    if kind == "overview" and (can or will):
        nav_items.insert(0, {"id": "rf-outcomes-title", "title": outcomes_title, "level": 2})
    step_titles = {item["id"]: item["title"] for item in prepared["steps"]}
    for item in nav_items:
        if item["id"] in step_titles:
            item["title"] = step_titles[item["id"]]
    inline_outline = _outline(nav_items, compact=True, steps=prepared["steps"] or None)
    if kind == "home":
        lead = next(node for node in tree.children if isinstance(node, Node) and node.tag == "p")
        tree.children.remove(lead)
        lead.attrs["class"] = "rf-lead"
        setup = _relative(dest, common["modules"][0]["overview"])
        image = ""
        if assets["hero"]:
            width, height = assets["dimensions"][assets["hero"]]
            image = f'<img class="rf-hero-image" src="{_relative(dest, assets["hero"])}" width="{width}" height="{height}" alt="" fetchpriority="high">'
        main = f'''<main id="main" class="rf-home-main" tabindex="-1"><section class="rf-hero sc-photo" data-sc-theme="dark">{image}
<div class="rf-hero-content">{h1.render()}{lead.render()}
<div class="rf-hero-actions"><a id="rf-home-primary" class="sc-btn rf-btn sc-btn--primary" href="{setup}">Start with setup</a>
<a class="sc-btn rf-btn sc-btn--secondary" href="#work-through-the-assignments">Explore the course</a></div>
<p id="rf-resume-note" hidden></p><a id="rf-home-setup" href="{setup}" hidden>Start with setup</a></div></section>
<div class="rf-home-content">{inline_outline}{tree.render()}</div></main>'''
    else:
        role = {"overview": "Overview", "lab": "Lab", "setup": "Setup", "reference": "Reference"}[kind]
        breadcrumb = f'<nav class="rf-breadcrumb" aria-label="Breadcrumb"><a href="{home}">Course</a><span aria-hidden="true"> / </span><a href="{_relative(dest, routes["overview"])}">{module_id} · {html.escape(module["case_name"])}</a><span aria-hidden="true"> / </span><span>{role}</span></nav>'
        links = []
        for page_kind, label in (("overview", "Overview"), ("lab", "Lab")):
            current = ' aria-current="page"' if str(dest) == routes[page_kind] else ""
            links.append(f'<a href="{_relative(dest, routes[page_kind])}"{current}>{label}</a>')
        local = f'<nav class="rf-local-links" aria-label="Assignment documents">{"".join(links)}</nav>'
        intro = []
        while tree.children:
            node = tree.children[0]
            if isinstance(node, Node) and (node.tag in {"h2", "section"} or "rf-stretch" in node.attrs.get("class", "").split()):
                break
            intro.append(tree.children.pop(0))
        controls = ""
        if prepared["steps"]:
            controls = '''<fieldset id="rf-reader-controls" hidden><legend>Reading mode</legend>
<button type="button" class="sc-btn rf-btn sc-btn--secondary" data-view-choice="guided">Guided</button>
<button type="button" class="sc-btn rf-btn sc-btn--secondary" data-view-choice="read">Read full page</button>
<p class="rf-reader-hint">Use Read full page to find text across every section.</p></fieldset>'''
        panel = ""
        if kind == "overview":
            if can or will:
                body = f'<p class="rf-outcomes-can">{html.escape(can)}</p>' if can else ""
                if will:
                    items = "".join(f"<li>{html.escape(item)}</li>" for item in will)
                    body += ('<p class="rf-outcomes-sub">You will</p>' if can else "") + f'<ul class="rf-outcomes-list">{items}</ul>'
                panel += (f'<section class="rf-outcomes" aria-labelledby="rf-outcomes-title"><h2 id="rf-outcomes-title" class="rf-outcomes-title">{outcomes_title}</h2>{body}</section>')
            if module_steps:
                panel += (f'<section class="rf-module-progress" data-module-progress="{module_id}" data-step-total="{module_steps}" aria-labelledby="rf-module-progress-title">'
                          f'<h2 id="rf-module-progress-title" class="rf-module-progress-title">Your progress</h2><p class="rf-module-progress-text">{module_steps} steps. Mark each one done as you finish it; progress is saved on this device.</p>'
                          f'<div class="rf-progress-track" aria-hidden="true"><div class="rf-progress-fill"></div></div></section>')
        progress = ""
        if kind in {"lab", "setup"} and can:
            progress += f'<p class="rf-outcome-line"><span class="rf-outcome-label">After this assignment you can</span> {html.escape(can)}</p>'
        if prepared["steps"]:
            total = len(prepared["steps"])
            progress += (f'<div class="rf-progress" data-progress data-step-total="{total}"><div class="rf-progress-track" aria-hidden="true"><div class="rf-progress-fill"></div></div>'
                         f'<p class="rf-progress-text">{total} steps. Mark each step done as you finish it; progress is saved on this device.</p></div>')
        if prepared["steps"]:
            last = next(node for node in tree.walk() if node.attrs.get("data-step-id") == prepared["steps"][-1]["id"])
            actions = []
            stretch = next((node for node in tree.walk() if "rf-stretch" in node.attrs.get("class", "").split()), None)
            if stretch:
                actions.append(Node("a", {"href": "#" + stretch.attrs["id"], "class": "sc-btn rf-btn sc-btn--secondary"}, ["Optional stretch"]))
            if kind == "setup":
                next_href, next_label = _relative(dest, routes["lab"]), "Open the lab"
            else:
                position = next(index for index, item in enumerate(common["modules"]) if item["id"] == module_id)
                if position + 1 < len(common["modules"]):
                    next_href, next_label = _relative(dest, common["modules"][position + 1]["overview"]), "Next assignment"
                else:
                    next_href, next_label = home + "#work-through-the-assignments", "Course map"
            actions.append(Node("a", {"href": next_href, "class": "sc-btn rf-btn sc-btn--secondary"}, [next_label]))
            last.children[-1].children.append(Node("nav", {"class": "rf-end-actions", "aria-label": "Continue reading"}, actions))
        back = f'<p class="rf-back-to-lab"><a class="sc-btn rf-btn sc-btn--secondary" href="{_relative(dest, routes["lab"])}">Back to lab</a></p>' if kind == "reference" else ""
        rail_outline = _outline(nav_items, steps=prepared["steps"] or None)
        main = f'''<div class="rf-layout"><aside class="rf-course-rail">{_course_navigation(common["modules"], dest, module_id, True)}</aside>
<main id="main" class="rf-reading" tabindex="-1"><header class="rf-page-header sc-grid">{breadcrumb}{h1.render()}</header>{local}{progress}
<div class="rf-intro">{Node("", {}, intro).render()}</div>{panel}<div class="rf-reader-mobile-slot">{controls}</div>{inline_outline}{tree.render()}{back}</main>
<aside class="rf-section-rail"><div class="rf-reader-desktop-slot"></div>{rail_outline}</aside></div>'''
    styles = "".join(f'<link rel="stylesheet" href="{_relative(dest, path)}">' for path in assets["styles"])
    preloads = "".join(f'<link rel="preload" href="{_relative(dest, path)}" as="font" type="font/woff2" crossorigin>' for path in assets["fonts"])
    data = json.dumps(page_data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><script src="{_relative(dest, "assets/theme-init.js")}"></script>{preloads}{styles}
<script src="{_relative(dest, "assets/course.js")}" defer></script></head>
<body class="{"rf-home" if kind == "home" else "rf-interior"}" data-page-kind="{kind}">
<a class="sc-skip-link" href="#main">Skip to content</a>
<header class="rf-masthead sc-grain"><div class="rf-masthead-inner">
<a class="sc-brand rf-brand" href="{home}" aria-label="Starzl Enterprises AI Harness Bootcamp — home"><span class="sc-brand__dot" aria-hidden="true"></span>
<span class="sc-brand__name">Starzl Enterprises</span><span class="sc-brand__divider" aria-hidden="true"></span><span class="sc-brand__product">AI Harness Bootcamp</span></a>
<div class="rf-header-actions"><button type="button" class="sc-btn rf-btn sc-btn--secondary" data-search-open hidden>Search course</button>
<button type="button" class="sc-btn rf-btn sc-btn--secondary rf-course-trigger" data-course-open hidden>Course</button>{_appearance("rf-desktop-appearance")}</div></div>
<details class="rf-course-fallback"><summary>Course</summary>{navigation}</details></header>{main}
<div class="rf-status"><p id="copy-status" role="status" aria-live="polite"></p><p id="rf-state-status" role="status"></p></div>
<footer class="rf-footer"><p class="rf-caveat">Fictional cases, for class use only. A passing check does not authorize any real-world action.</p>
<div class="rf-footer-tools">{_appearance()}{_reset_place()}</div>
<p class="rf-print-note">Expand optional work and figure-text disclosures before printing if your browser does not expand them automatically.</p></footer>
{_dialogs(navigation, home)}<script type="application/json" id="rf-page-data">{data}</script></body></html>
'''
    return document.encode("utf-8")


def validate_links(outputs: dict[PurePosixPath, bytes]) -> None:
    parsed = {path: parse_html(data.decode("utf-8")) for path, data in outputs.items() if path.suffix == ".html"}
    anchors = {}
    for path, tree in parsed.items():
        ids = [node.attrs["id"] for node in tree.walk() if "id" in node.attrs]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate HTML anchor: {path}")
        anchors[path] = set(ids)
    for path, tree in parsed.items():
        for node in tree.walk():
            for attr in ("href", "src"):
                value = node.attrs.get(attr)
                if value is None:
                    continue
                url = urlsplit(value)
                if url.scheme or url.netloc:
                    continue
                target = PurePosixPath(posixpath.normpath(str(path.parent / unquote(url.path)))) if url.path else path
                if target not in outputs:
                    raise ValueError(f"broken published link: {path} -> {value}")
                if url.fragment and target in anchors and unquote(url.fragment) not in anchors[target]:
                    raise ValueError(f"missing published anchor: {path} -> {value}")
    for path, data in outputs.items():
        if path.suffix != ".css":
            continue
        css = re.sub(r"/\*.*?\*/", "", data.decode("utf-8"), flags=re.S)
        references = [next(value for value in match if value) for match in re.findall(r"""url\(\s*(?:'([^']*)'|"([^"]*)"|([^)\s]+))\s*\)""", css, re.I)]
        references.extend(re.findall(r"""@import\s+['"]([^'"]+)['"]""", css, re.I))
        for value in references:
            url = urlsplit(value)
            if url.scheme == "data":
                continue
            if url.scheme or url.netloc or url.path.startswith("/") or "\\" in value:
                raise ValueError(f"nonlocal CSS dependency: {path} -> {value}")
            target = PurePosixPath(posixpath.normpath(str(path.parent / unquote(url.path)))) if url.path else path
            if target not in outputs:
                raise ValueError(f"missing CSS dependency: {path} -> {value}")
    if SEARCH_PATH in outputs:
        search = json.loads(outputs[SEARCH_PATH])
        if {page["path"] for page in search["pages"]} != {str(path) for path in parsed}:
            raise ValueError("search must contain exactly the instructional destinations")
        targets = [(page["path"], section["id"]) for page in search["pages"] for section in page["sections"]]
        for tree in parsed.values():
            for node in tree.walk():
                if node.attrs.get("id") == "rf-page-data":
                    page_data = json.loads(node.text())
                    targets.extend((path, section["id"]) for path, sections in page_data.get("resume", {}).items() for section in sections)
        for path, anchor in targets:
            if PurePosixPath(path) not in anchors or (anchor and anchor not in anchors[PurePosixPath(path)]):
                raise ValueError(f"dangling search/resume target: {path}#{anchor}")


def build(root: Path = ROOT, check: bool = False) -> int:
    course, destinations, mapping, pages = inventory(root)
    records = {PurePosixPath(record["path"]): record for record in _page_records(course)}
    prepared = {dest: _prepare_page(source, dest, mapping, course, root, records[dest]) for dest, source in destinations.items() if source in pages}
    outputs = {dest: source.read_bytes() for dest, source in destinations.items() if source not in pages}
    common = {
        "assets": _asset_context(course, outputs),
        "modules": [{"id": module["id"], "caseName": module["case_name"], "navSummary": module["nav_summary"], "title": module["title"].split("·", 1)[-1].strip(),
                     **_module_routes(course, module)} for module in course["modules"]],
        "pages": [{"path": str(dest), "title": page["title"], "kind": page["record"]["kind"], "moduleId": page["record"]["moduleId"], "steps": [step["id"] for step in page["steps"]]} for dest, page in prepared.items()],
        "resume": {str(dest): [{**step, "optional": False} for step in page["steps"]] + [
            {key: section[key] for key in ("id", "title", "optional")} for section in page["sections"] if section["optional"]
        ] for dest, page in prepared.items() if page["steps"]},
    }
    for dest, page in prepared.items():
        page["common"] = common
        outputs[dest] = render_page(destinations[dest], dest, mapping, course, root, page)
    outputs[SEARCH_PATH] = (json.dumps({"version": 1, "pages": [
        {"path": str(dest), "moduleId": page["record"]["moduleId"], "kind": page["record"]["kind"], "title": page["title"], "sections": page["sections"]}
        for dest, page in prepared.items()
    ]}, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    validate_links(outputs)
    site = root / "site"
    if site.is_symlink():
        raise ValueError("site must not be a symlink")
    existing = set()
    if site.exists():
        for path in site.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"linked public output: {path}")
            if path.is_file():
                existing.add(PurePosixPath(path.relative_to(site).as_posix()))
    extras = existing - outputs.keys()
    if extras:
        raise ValueError("unlisted public output (preserved): " + ", ".join(map(str, sorted(extras))))
    if check:
        mismatches = [str(dest) for dest, data in outputs.items() if dest not in existing or (site / dest).read_bytes() != data]
        if mismatches:
            raise ValueError("missing or stale published bytes: " + ", ".join(mismatches))
        # Read the actual published documents, not only regenerated fragments.
        validate_links({dest: (site / dest).read_bytes() for dest in outputs})
    else:
        for dest, data in outputs.items():
            target = site / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    ui_count = len(course["ui_assets"]) + 1
    print(f"PASS: {len(pages)} instructional pages, {len(outputs) - len(pages) - ui_count} raw downloads, {ui_count} UI/generated assets {'checked byte-for-byte' if check else 'published'}; public links and page structure checked")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        return build(check=args.check)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
