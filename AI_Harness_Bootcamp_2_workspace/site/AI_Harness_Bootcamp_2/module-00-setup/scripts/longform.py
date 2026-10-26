#!/usr/bin/env python3
"""Plan, draft, check, and revise a long document with OMP, one limited job per session.

Every model step is one run of the shared course launcher (shared/run_omp.py) with the
pinned model and only the files that step may write. A missing key, a failed run, or a
receipt that doesn't match the file on disk is a HOLD. Nothing here retries a paid call or
writes model text itself.

  outline  W E                      OMP proposes outline-proposed.md; a copy becomes outline.md
  freeze   W E                      check brief.md, tests.md, outline.md and record their hashes
  draft    W E --section N | --rest one session per section, then draft-v1.md
  ledger   W FILE                   every number and code in FILE, and which sources contain it
  critique W E --draft vN --round R separate review sessions, saved in review/rR/
  revise   W E --from vA --to vB --fixes FILE
                                    rewrite only the sections named under Accepted in FILE
  reveal   W E                      copy CHANGED_INPUT.md into the work folder
  compare  W vA vB                  which sections changed between two versions
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORDS = (600, 900)
SECTIONS = (5, 6)
TITLE_RE = re.compile(r"^#\s+(\S.*?)\s*$")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(\S.*?)\s*$")
VERSION_RE = re.compile(r"^v\d+$")
BRIEF_LABELS = (
    "Reader:",
    "What the reader must know:",
    "What the reader must do, and must not do yet:",
    "Sources it may use:",
    "Length and shape:",
    "What it can't authorize:",
    "Sensitive data:",
    "Disclosure:",
    "Who decides whether it goes out:",
)
TEST_HEADINGS = ("Must say", "Must never say or imply", "A reader must be able to answer")
TOKEN_RE = re.compile(r"\b\d{3}-\d{4}\b|\b\d{1,2}:\d{2}\b|\b[A-Z]{1,3}-\d+\b|\b\d+\b")
WORD_RE = re.compile(r"\b[\w’'-]+\b")


# --------------------------------------------------------------------------------------
# Locations and receipts


def module_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "shared/case/prompts/section.txt").is_file():
            return parent
    raise FileNotFoundError("Module 0 case prompts are missing from the checkout")


def shared_launcher() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "shared/run_omp.py"
        if candidate.is_file() and (parent / "shared/course_guard.mjs").is_file():
            return candidate
    raise FileNotFoundError("shared OMP launcher is missing from the checkout")


def pinned() -> tuple[str, str]:
    shared = str(shared_launcher().parent)
    if shared not in sys.path:
        sys.path.insert(0, shared)
    from run_omp import MODEL, PROVIDER

    return PROVIDER, MODEL


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def hold(message: str, code: int = 1) -> int:
    print(f"HOLD: {message}", file=sys.stderr)
    return code


def plain_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def folders(work: Path, evidence: Path) -> str | None:
    if not work.is_dir() or work.is_symlink():
        return f"work folder does not exist: {work}"
    if not evidence.is_dir() or evidence.is_symlink():
        return f"evidence folder does not exist: {evidence}"
    if work == evidence or work in evidence.parents or evidence in work.parents:
        return "work and evidence folders must not contain each other"
    return None


def ready_to_launch() -> str | None:
    if not os.environ.get("OPENROUTER_API_KEY"):
        return "OPENROUTER_API_KEY unavailable; enter and export the key in this terminal"
    if not shutil.which("omp"):
        return "omp is not on PATH; open a terminal where setup's omp check passes"
    try:
        shared_launcher()
        module_root()
    except FileNotFoundError as error:
        return str(error)
    return None


def render(evidence: Path, label: str, template: str, **values: str) -> Path:
    text = (module_root() / "shared/case/prompts" / template).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        raise ValueError(f"prompt {template} has an unfilled field")
    folder = evidence / "prompts"
    folder.mkdir(exist_ok=True)
    path = folder / f"{label}-{stamp()}.txt"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
    return path


def run_session(workdir: Path, prompt: Path, evidence: Path, label: str, outputs: list[str]) -> tuple[Path, list[str]]:
    """One launcher run. Returns the receipt folder and any reasons to hold."""
    receipts = evidence / "receipts" / f"{label}-{stamp()}"
    receipts.parent.mkdir(exist_ok=True)
    command = [sys.executable, str(shared_launcher()), "--workdir", str(workdir), "--prompt", str(prompt), "--evidence", str(receipts)]
    for output in outputs:
        command += ["--allow-write", output]
    print(f"RUNNING {label}: writes {', '.join(outputs)}", flush=True)
    completed = subprocess.run(command)
    if completed.returncode == 2:
        return receipts, ["the launcher stopped before the run; read its HOLD line above"]
    if completed.returncode != 0:
        return receipts, [f"the run held (exit {completed.returncode}); read its HOLD line above"]
    return receipts, confirm(workdir, receipts, outputs)


def confirm(workdir: Path, receipts: Path, outputs: list[str]) -> list[str]:
    """The run passed, used the pinned model, and wrote each output through course_write."""
    try:
        result = json.loads((receipts / "result.json").read_text(encoding="utf-8"))
        guard = [json.loads(line) for line in (receipts / "guard.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        provider, model = pinned()
    except (OSError, ValueError, ImportError) as error:
        return [f"receipts are incomplete: {error}"]
    errors = []
    if result.get("status") != "PASS" or result.get("exit_code") != 0:
        errors.append("the run is not a completed live run")
    if result.get("provider") != provider or result.get("model") != model:
        errors.append("the run did not use the pinned model")
    written = {row.get("output_sha256") for row in guard if row.get("type") == "executed" and row.get("tool") == "course_write"}
    for output in outputs:
        target = workdir / output
        if not plain_file(target):
            errors.append(f"{output} was not written")
            continue
        value = digest(target)
        if (result.get("output_sha256") or {}).get(output) != value or value not in written:
            errors.append(f"{output} does not match its course_write receipt")
    return errors


def report(receipts: Path, errors: list[str]) -> int:
    for error in errors:
        print(f"HOLD: {error}", file=sys.stderr)
    print(f"Receipts: {receipts}", file=sys.stderr if errors else sys.stdout)
    return 1 if errors else 0


# --------------------------------------------------------------------------------------
# The plan


def label_re(label: str) -> str:
    """A label at the start of a line, tolerating list marks and bold: '- **Claim:** text'."""
    return rf"^[ \t>*_-]*{re.escape(label)}[*_]*[ \t]*"


def labelled(text: str, label: str) -> str:
    match = re.search(label_re(label) + r"(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def outline_field(body: str, label: str) -> str:
    """The text after an outline label, including list lines under it, up to the next label."""
    lines, taking = [], False
    for line in body.splitlines():
        if re.match(r"^[ \t>*_-]*(?:Job|Facts|Words):", line):
            taking = bool(re.match(label_re(label), line))
            if taking:
                lines.append(re.sub(label_re(label), "", line).strip())
            continue
        if taking and line.strip():
            lines.append(line.strip().lstrip("-* ").strip())
    return "; ".join(part for part in lines if part)


def brief_errors(work: Path) -> list[str]:
    path = work / "brief.md"
    if not plain_file(path):
        return ["brief.md is missing"]
    text = path.read_text(encoding="utf-8")
    return [f"brief.md: fill in {label!r}" for label in BRIEF_LABELS if not labelled(text, label)]


def tests_errors(work: Path) -> list[str]:
    path = work / "tests.md"
    if not plain_file(path):
        return ["tests.md is missing"]
    text = path.read_text(encoding="utf-8")
    errors = []
    for heading in TEST_HEADINGS:
        match = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.M)
        bullets = [line for line in (match.group(1).splitlines() if match else []) if re.match(r"^\s*-\s+\S", line)]
        if not bullets:
            errors.append(f"tests.md: add at least one test under '## {heading}'")
    return errors


def read_outline(work: Path) -> tuple[str, list[dict], list[str]]:
    path = work / "outline.md"
    if not plain_file(path):
        return "", [], ["outline.md is missing"]
    lines = path.read_text(encoding="utf-8").splitlines()
    title, sections, errors = "", [], []
    for line in lines:
        if not title and TITLE_RE.match(line) and not line.startswith("##"):
            title = TITLE_RE.match(line).group(1)
        heading = SECTION_RE.match(line)
        if heading:
            sections.append({"n": int(heading.group(1)), "title": heading.group(2), "heading": line.strip(), "body": []})
        elif sections:
            sections[-1]["body"].append(line)
    if not title:
        errors.append("outline.md needs a title line that starts with '# '")
    if not SECTIONS[0] <= len(sections) <= SECTIONS[1]:
        errors.append(f"outline.md has {len(sections)} sections; plan {SECTIONS[0]} or {SECTIONS[1]}")
    for index, section in enumerate(sections, start=1):
        body = "\n".join(section.pop("body"))
        if section["n"] != index:
            errors.append(f"number the sections 1, 2, 3 in order; found {section['n']} in place of {index}")
        section["job"], section["facts"] = outline_field(body, "Job:"), outline_field(body, "Facts:")
        words = re.search(r"\d+", outline_field(body, "Words:"))
        section["words"] = int(words.group()) if words else 0
        for field in ("job", "facts"):
            if not section[field]:
                errors.append(f"section {section['n']}: fill in its {field.capitalize()}: line")
        if not section["words"]:
            errors.append(f"section {section['n']}: Words: must be a whole number")
    total = sum(section["words"] for section in sections)
    if sections and not WORDS[0] <= total <= WORDS[1]:
        errors.append(f"the sections' Words add up to {total}; plan {WORDS[0]} to {WORDS[1]}")
    return title, sections, errors


def plan_errors(work: Path, evidence: Path) -> list[str]:
    path = evidence / "plan.json"
    if not plain_file(path):
        return ["the plan isn't frozen; run the freeze step first"]
    plan = json.loads(path.read_text(encoding="utf-8"))
    changed = [name for name in ("brief.md", "tests.md", "outline.md") if not plain_file(work / name) or digest(work / name) != plan["files"].get(name)]
    if changed:
        return [f"{', '.join(changed)} changed after you froze the plan; start a new attempt to change the plan"]
    return []


def section_file(version: str, n: int) -> str:
    return f"draft/{version}/{n:02d}.md"


def words(text: str) -> int:
    return len(WORD_RE.findall(text))


def assemble(work: Path, version: str) -> int:
    title, sections, errors = read_outline(work)
    if errors:
        return hold("; ".join(errors))
    target = work / f"draft-{version}.md"
    if target.exists() or target.is_symlink():
        return hold(f"draft-{version}.md already exists; keep it")
    parts = []
    for section in sections:
        path = work / section_file(version, section["n"])
        if not plain_file(path):
            return hold(f"{section_file(version, section['n'])} is missing")
        prose = path.read_text(encoding="utf-8").strip()
        first, _, rest = prose.partition("\n")
        if re.match(r"^#{1,6}\s", first):
            # Headings come from outline.md. A heading the session wrote anyway is left out.
            print(f"NOTE: {section_file(version, section['n'])} starts with its own heading; draft-{version}.md uses the heading from outline.md")
            prose = rest.strip()
        parts.append(prose)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\n" + "\n\n".join(f"{s['heading']}\n\n{part}" for s, part in zip(sections, parts)) + "\n")
    print(f"ASSEMBLED draft-{version}.md")
    print(f"{'Section':<8}{'Budget':>8}{'Words':>8}  Title")
    for section, part in zip(sections, parts):
        print(f"{section['n']:<8}{section['words']:>8}{words(part):>8}  {section['title']}")
    print(f"{'Total':<8}{sum(s['words'] for s in sections):>8}{words(target.read_text(encoding='utf-8')):>8}")
    return 0


# --------------------------------------------------------------------------------------
# Actions


def outline(work: Path, evidence: Path) -> int:
    errors = brief_errors(work) + tests_errors(work)
    if errors:
        return hold("; ".join(errors))
    if (work / "outline-proposed.md").exists():
        return hold("outline-proposed.md already exists; keep it, and correct outline.md instead")
    blocked = ready_to_launch()
    if blocked:
        return hold(blocked, 2)
    prompt = render(evidence, "outline", "outline.txt")
    receipts, errors = run_session(work, prompt, evidence, "outline", ["outline-proposed.md"])
    if errors:
        return report(receipts, errors)
    if not (work / "outline.md").exists():
        shutil.copyfile(work / "outline-proposed.md", work / "outline.md")
        print("PASS: OMP wrote outline-proposed.md; your copy to correct is outline.md")
    else:
        print("PASS: OMP wrote outline-proposed.md; outline.md already existed and was kept")
    return report(receipts, [])


def freeze(work: Path, evidence: Path) -> int:
    title, sections, errors = read_outline(work)
    errors = brief_errors(work) + tests_errors(work) + errors
    if errors:
        for error in errors:
            print(f"HOLD: {error}", file=sys.stderr)
        return 1
    path = evidence / "plan.json"
    if path.exists():
        if any((work / "draft").glob("v1/*.md")):
            return hold("the plan is frozen and drafting has started; start a new attempt to change the plan")
        path.replace(evidence / f"plan-{stamp()}.json")
    plan = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "files": {name: digest(work / name) for name in ("brief.md", "tests.md", "outline.md")},
        "title": title,
        "sections": sections,
    }
    with path.open("x", encoding="utf-8") as handle:
        json.dump(plan, handle, indent=2)
        handle.write("\n")
    print(f"PLAN FROZEN: {title}")
    print(f"{'Section':<8}{'Words':>6}  Title / Facts")
    for section in sections:
        print(f"{section['n']:<8}{section['words']:>6}  {section['title']}")
        print(f"{'':<14}Facts: {section['facts']}")
    print(f"{'Total':<8}{sum(s['words'] for s in sections):>6}")
    return 0


def draft_one(work: Path, evidence: Path, sections: list[dict], n: int) -> tuple[int, Path | None]:
    output = section_file("v1", n)
    if (work / output).exists():
        return hold(f"{output} already exists; keep it"), None
    earlier = [section_file("v1", s["n"]) for s in sections if s["n"] < n and plain_file(work / section_file("v1", s["n"]))]
    note = f" Also read the sections already written: {', '.join(earlier)}." if earlier else ""
    prompt = render(evidence, f"section-{n:02d}", "section.txt", N=str(n), OUTPUT=output, EARLIER=note)
    receipts, errors = run_session(work, prompt, evidence, f"section-{n:02d}", [output])
    if errors:
        return report(receipts, errors), receipts
    print(f"PASS: OMP wrote {output}")
    return report(receipts, []), receipts


def session_text(receipts: Path) -> str:
    """Every text block the session's assistant wrote, in order, from the saved event stream."""
    texts = []
    try:
        for line in (receipts / "events.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line) if line.strip() else {}
            message = row.get("message", {}) if row.get("type") == "message_end" else {}
            if message.get("role") == "assistant":
                texts += [block["text"].strip() for block in message.get("content", []) if block.get("type") == "text" and block.get("text", "").strip()]
    except (OSError, ValueError):
        return ""
    return "\n\n".join(texts)


def draft(work: Path, evidence: Path, section: int | None, rest: bool) -> int:
    title, sections, errors = read_outline(work)
    errors = errors + plan_errors(work, evidence)
    if errors:
        return hold("; ".join(errors))
    blocked = ready_to_launch()
    if blocked:
        return hold(blocked, 2)
    numbers = [s["n"] for s in sections]
    if section is not None:
        if section not in numbers:
            return hold(f"outline.md has no section {section}", 2)
        code, receipts = draft_one(work, evidence, sections, section)
        if code == 0 and receipts is not None:
            print("\nWhat the session wrote besides the file, including the source lines it quoted:\n")
            print(session_text(receipts) or "(no reply text)")
        if code:
            return code
    else:
        for n in numbers:
            if (work / section_file("v1", n)).exists():
                continue
            code, _ = draft_one(work, evidence, sections, n)
            if code:
                return code
    missing = [n for n in numbers if not plain_file(work / section_file("v1", n))]
    if missing:
        print(f"Sections still to draft: {', '.join(map(str, missing))}")
        return 0
    return assemble(work, "v1") if not (work / "draft-v1.md").exists() else 0


def source_texts(work: Path) -> dict[str, str]:
    texts = {}
    for path in sorted((work / "sources").glob("*.md")):
        texts[path.name.split("-", 1)[0]] = path.read_text(encoding="utf-8")
    if plain_file(work / "CHANGED_INPUT.md"):
        texts["CHANGED_INPUT"] = (work / "CHANGED_INPUT.md").read_text(encoding="utf-8")
    # A numbered list item ("4. Whom do we call") is not a source fact about 4.
    return {label: re.sub(r"(?m)^\s*\d+[.)]\s", "", text) for label, text in texts.items()}


def ledger(work: Path, name: str) -> int:
    path = (work / name).resolve()
    if not plain_file(path) or work.resolve() not in path.parents:
        return hold(f"{name} is not a file in the work folder", 2)
    sources = source_texts(work)
    if not sources:
        return hold("sources/ is missing from the work folder", 2)
    found: dict[str, list[str]] = {}
    section = "title"
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        heading = SECTION_RE.match(line)
        if heading:
            section = heading.group(1)
            line = heading.group(2)
        for token in TOKEN_RE.findall(line):
            found.setdefault(token, []).append(f"{section}:{number}")
    missing = 0
    print(f"NUMBERS AND CODES IN {name}")
    print(f"{'Token':<12}{'Where (section:line)':<34}In sources")
    for token in sorted(found, key=lambda t: (found[t][0], t)):
        holders = [label for label, text in sources.items() if re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", text)]
        where = ", ".join(found[token][:6]) + (" ..." if len(found[token]) > 6 else "")
        if not holders:
            missing += 1
        print(f"{token:<12}{where:<34}{', '.join(holders) if holders else 'NOT IN SOURCES  <- check it'}")
    print(f"{len(found)} numbers and codes; {missing} not in the sources")
    return 0


PASSES = ("tests", "facts", "reader", "style")


def packet(evidence: Path, label: str, files: dict[str, Path]) -> Path:
    folder = evidence / "packets" / f"{label}-{stamp()}"
    folder.mkdir(parents=True)
    for name, source in files.items():
        target = folder / name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copyfile(source, target)
    return folder


def isolated(work: Path, evidence: Path, label: str, template: str, files: dict[str, Path], output: str, saved: Path, **fields: str) -> int:
    folder = packet(evidence, label, files)
    prompt = render(evidence, label, template, **fields)
    receipts, errors = run_session(folder, prompt, evidence, label, [output])
    if errors:
        return report(receipts, errors)
    shutil.copyfile(folder / output, saved)
    if digest(saved) != digest(folder / output):
        return report(receipts, [f"the saved copy of {output} differs from the receipted file"])
    print(f"PASS: a new session wrote {saved.relative_to(work)}")
    return report(receipts, [])


Q_START = r"[ \t>#*_-]*Q(\d+)\b"


def blocks(text: str) -> list[tuple[str, str]]:
    """Split a review file into (number, block) pairs at lines such as 'Q3' or '**Q3**'."""
    parts = re.split(rf"(?m)^(?={Q_START})", text)
    return [(re.match(Q_START, part).group(1), part) for part in parts if re.match(Q_START, part)]


def merge_facts(questions: Path, answers: Path, target: Path, round_name: str) -> None:
    answered = {number: (labelled(block, "Answer:") or "(no answer returned)", labelled(block, "Source:") or "none")
                for number, block in blocks(answers.read_text(encoding="utf-8"))}
    lines = [f"# Facts pass, round {round_name}", "",
             "Each claim from the draft, beside the answer a separate session gave from the sources alone, without seeing the draft.", ""]
    for number, block in blocks(questions.read_text(encoding="utf-8")):
        answer, source = answered.get(number, ("(no answer returned)", "none"))
        lines += [f"## Q{number} · Section {labelled(block, 'Section:') or '?'}",
                  f"Claim in the draft: {labelled(block, 'Claim:')}",
                  f"Question: {labelled(block, 'Question:')}",
                  f"Answer from the sources: {answer}",
                  f"Source: {source}", ""]
    with target.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def questions_only(source: Path, target: Path) -> None:
    """Keep the questions; drop the draft's claims, so the answering session can't copy them."""
    claim = re.compile(f"(?:{label_re('Claim:')})|(?:{label_re('Section:')})")
    kept = [line for line in source.read_text(encoding="utf-8").splitlines() if not claim.match(line)]
    target.write_text("\n".join(kept) + "\n", encoding="utf-8")


def count(text: str, label: str, value: str = "") -> int:
    return len(re.findall(label_re(label) + value, text, re.M))


def critique(work: Path, evidence: Path, version: str, round_name: str) -> int:
    draft_path = work / f"draft-{version}.md"
    if not plain_file(draft_path):
        return hold(f"draft-{version}.md is missing", 2)
    if not plain_file(work / "tests.md") or not plain_file(work / "STYLE.md") or not (work / "sources").is_dir():
        return hold("tests.md, STYLE.md, or sources/ is missing from the work folder", 2)
    blocked = ready_to_launch()
    if blocked:
        return hold(blocked, 2)
    out = work / "review" / f"r{round_name}"
    record = out / "round.json"
    reviewed = {"draft": draft_path.name, "sha256": digest(draft_path)}
    if record.is_file() and json.loads(record.read_text(encoding="utf-8")) != reviewed:
        return hold(f"review/r{round_name} already holds a review of another draft; use the next round number", 2)
    if out.exists() and not record.is_file():
        return hold(f"review/r{round_name} already exists without a record of its draft; use the next round number", 2)
    out.mkdir(parents=True, exist_ok=True)
    if not record.is_file():
        record.write_text(json.dumps(reviewed, indent=2) + "\n", encoding="utf-8")
    label = f"r{round_name}"
    if not (out / "tests-pass.md").exists():
        code = isolated(work, evidence, f"{label}-tests", "tests-pass.txt", {"draft.md": draft_path, "tests.md": work / "tests.md"}, "tests-pass.md", out / "tests-pass.md")
        if code:
            return code
    if not (out / "facts-pass.md").exists():
        if not (out / "fact-questions.md").exists():
            code = isolated(work, evidence, f"{label}-fact-questions", "fact-questions.txt", {"draft.md": draft_path}, "fact-questions.md", out / "fact-questions.md")
            if code:
                return code
        if not (out / "fact-answers.md").exists():
            stripped = evidence / "packets" / f"{label}-questions-only-{stamp()}.md"
            stripped.parent.mkdir(parents=True, exist_ok=True)
            questions_only(out / "fact-questions.md", stripped)
            sources = {"questions.md": stripped, "sources": work / "sources"}
            change = ""
            if plain_file(work / "CHANGED_INPUT.md"):
                sources["CHANGED_INPUT.md"] = work / "CHANGED_INPUT.md"
                change = " Also read CHANGED_INPUT.md. Where it changes a fact, its new value replaces the old one."
            code = isolated(work, evidence, f"{label}-fact-answers", "fact-answers.txt", sources, "fact-answers.md", out / "fact-answers.md", CHANGE=change)
            if code:
                return code
        merge_facts(out / "fact-questions.md", out / "fact-answers.md", out / "facts-pass.md", round_name)
        print(f"MERGED review/{label}/facts-pass.md")
    if not (out / "reader-pass.md").exists():
        code = isolated(work, evidence, f"{label}-reader", "reader.txt", {"draft.md": draft_path}, "reader-pass.md", out / "reader-pass.md")
        if code:
            return code
    if not (out / "style-pass.md").exists():
        code = isolated(work, evidence, f"{label}-style", "style.txt", {"draft.md": draft_path, "STYLE.md": work / "STYLE.md"}, "style-pass.md", out / "style-pass.md")
        if code:
            return code
    tests_text = (out / "tests-pass.md").read_text(encoding="utf-8")
    facts_text = (out / "facts-pass.md").read_text(encoding="utf-8")
    print(f"CRITIQUE ROUND {round_name} COMPLETE for draft-{version}.md")
    print(f"  tests-pass.md   {count(tests_text, 'Result:', r'(?:NOT MET|UNCLEAR)')} tests not met or unclear")
    print(f"  facts-pass.md   {len(re.findall(r'(?m)^## Q', facts_text))} claims, {facts_text.count('NOT IN SOURCES')} answered NOT IN SOURCES")
    print(f"  reader-pass.md  {count((out / 'reader-pass.md').read_text(encoding='utf-8'), 'Action:')} actions a reader would take")
    print(f"  style-pass.md   {count((out / 'style-pass.md').read_text(encoding='utf-8'), 'Rule:')} style findings")
    return 0


def accepted_sections(text: str) -> list[int] | None:
    """Section numbers named under '## Accepted'; None when the heading is missing."""
    match = re.search(r"^##\s+Accepted\b[^\n]*\n([\s\S]*?)(?=^##\s|\Z)", text, re.M)
    if not match:
        return None
    return sorted({int(n) for n in re.findall(label_re("Section:") + r"(\d+)\b", match.group(1), re.M)})


def compare(work: Path, first: str, second: str, quiet: bool = False) -> int:
    title, sections, errors = read_outline(work)
    if errors:
        return hold("; ".join(errors))
    changed = 0
    for section in sections:
        a, b = work / section_file(first, section["n"]), work / section_file(second, section["n"])
        if not plain_file(a) or not plain_file(b):
            return hold(f"{section_file(first, section['n'])} or {section_file(second, section['n'])} is missing")
        if a.read_bytes() == b.read_bytes():
            print(f"SAME     section {section['n']}: {section['title']}")
            continue
        changed += 1
        print(f"CHANGED  section {section['n']}: {section['title']}")
        if not quiet:
            diff = difflib.unified_diff(a.read_text(encoding="utf-8").splitlines(), b.read_text(encoding="utf-8").splitlines(),
                                        fromfile=section_file(first, section["n"]), tofile=section_file(second, section["n"]), lineterm="")
            print("\n".join(diff))
    print(f"{changed} of {len(sections)} sections changed between {first} and {second}")
    return 0


def revise(work: Path, evidence: Path, first: str, second: str, fixes: str) -> int:
    title, sections, errors = read_outline(work)
    errors = errors + plan_errors(work, evidence)
    if errors:
        return hold("; ".join(errors))
    fixes_path = (work / fixes).resolve()
    if not plain_file(fixes_path) or work.resolve() not in fixes_path.parents:
        return hold(f"{fixes} is not a file in the work folder", 2)
    numbers = {s["n"] for s in sections}
    flagged = accepted_sections(fixes_path.read_text(encoding="utf-8"))
    if flagged is None:
        return hold(f"{fixes} has no '## Accepted' heading")
    if not flagged:
        return hold(f"{fixes} names no section under '## Accepted' (write a line such as 'Section: 2'); with nothing accepted there is nothing to revise")
    unknown = [n for n in flagged if n not in numbers]
    if unknown:
        return hold(f"{fixes} names sections the outline doesn't have: {unknown}")
    for n in numbers:
        if not plain_file(work / section_file(first, n)):
            return hold(f"{section_file(first, n)} is missing")
    target_dir = work / "draft" / second
    if target_dir.exists() or (work / f"draft-{second}.md").exists():
        return hold(f"draft/{second} or draft-{second}.md already exists; choose a new version name")
    blocked = ready_to_launch()
    if blocked:
        return hold(blocked, 2)
    target_dir.mkdir(parents=True)
    for n in sorted(numbers - set(flagged)):
        shutil.copyfile(work / section_file(first, n), work / section_file(second, n))
    targets = [section_file(second, n) for n in flagged]
    change = plain_file(work / "CHANGED_INPUT.md")
    prompt = render(evidence, f"revise-{second}", "revise.txt",
                    FIXES=fixes_path.relative_to(work.resolve()).as_posix(),
                    FROM_FILES=", ".join(section_file(first, n) for n in flagged),
                    TARGETS="\n".join(f"- {target} (section {n})" for target, n in zip(targets, flagged)),
                    CHANGE_FILE=", CHANGED_INPUT.md" if change else "",
                    CHANGE_RULE="\n- Where CHANGED_INPUT.md changes a fact, use its new value in place of the old one." if change else "")
    receipts, errors = run_session(work, prompt, evidence, f"revise-{second}", targets)
    if errors:
        failed = evidence / "failed" / f"{second}-{stamp()}"
        failed.parent.mkdir(exist_ok=True)
        target_dir.replace(failed)
        print(f"Kept the incomplete draft/{second} at {failed}", file=sys.stderr)
        return report(receipts, errors)
    print(f"PASS: OMP rewrote section(s) {', '.join(map(str, flagged))}; the others were copied unchanged")
    report(receipts, [])
    code = assemble(work, second)
    if code:
        return code
    print()
    return compare(work, first, second)


def reveal(work: Path, evidence: Path) -> int:
    source = module_root() / "shared/case/CHANGED_INPUT.md"
    target = work / "CHANGED_INPUT.md"
    if target.exists() or target.is_symlink():
        return hold("CHANGED_INPUT.md is already in the work folder; keep it")
    shutil.copyfile(source, target)
    record = {"revealed_at": datetime.now(timezone.utc).isoformat(), "sha256": digest(target)}
    with (evidence / "change.json").open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(target.read_text(encoding="utf-8").strip())
    print(f"\nREVEALED CHANGED_INPUT.md at {record['revealed_at']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("outline", "freeze", "reveal"):
        sub = actions.add_parser(name)
        sub.add_argument("work", type=Path)
        sub.add_argument("evidence", type=Path)
    sub = actions.add_parser("draft")
    sub.add_argument("work", type=Path)
    sub.add_argument("evidence", type=Path)
    which = sub.add_mutually_exclusive_group(required=True)
    which.add_argument("--section", type=int)
    which.add_argument("--rest", action="store_true")
    sub = actions.add_parser("ledger")
    sub.add_argument("work", type=Path)
    sub.add_argument("file")
    sub = actions.add_parser("critique")
    sub.add_argument("work", type=Path)
    sub.add_argument("evidence", type=Path)
    sub.add_argument("--draft", required=True)
    sub.add_argument("--round", required=True)
    sub = actions.add_parser("revise")
    sub.add_argument("work", type=Path)
    sub.add_argument("evidence", type=Path)
    sub.add_argument("--from", dest="first", required=True)
    sub.add_argument("--to", dest="second", required=True)
    sub.add_argument("--fixes", required=True)
    sub = actions.add_parser("compare")
    sub.add_argument("work", type=Path)
    sub.add_argument("first")
    sub.add_argument("second")
    args = parser.parse_args(argv)
    work = args.work.expanduser().resolve()
    for value in (getattr(args, "first", None), getattr(args, "second", None), getattr(args, "draft", None)):
        if value is not None and not VERSION_RE.match(value):
            return hold(f"version names look like v1, v2, v3; got {value!r}", 2)
    if getattr(args, "round", None) is not None and not str(args.round).isdigit():
        return hold("the round is a whole number, such as 1", 2)
    if args.action in ("ledger", "compare"):
        if not work.is_dir():
            return hold(f"work folder does not exist: {work}", 2)
        return ledger(work, args.file) if args.action == "ledger" else compare(work, args.first, args.second)
    evidence = args.evidence.expanduser().resolve()
    problem = folders(work, evidence)
    if problem:
        return hold(problem, 2)
    try:
        if args.action == "outline":
            return outline(work, evidence)
        if args.action == "freeze":
            return freeze(work, evidence)
        if args.action == "draft":
            return draft(work, evidence, args.section, args.rest)
        if args.action == "critique":
            return critique(work, evidence, args.draft, args.round)
        if args.action == "revise":
            return revise(work, evidence, args.first, args.second, args.fixes)
        return reveal(work, evidence)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return hold(str(error), 2)


if __name__ == "__main__":
    raise SystemExit(main())
