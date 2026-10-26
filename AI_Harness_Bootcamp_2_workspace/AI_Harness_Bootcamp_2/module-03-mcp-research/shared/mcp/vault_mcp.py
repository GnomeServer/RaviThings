#!/usr/bin/env python3
"""A small MCP server that lets an AI client read, search, and edit an Obsidian vault.

Usage: vault_mcp.py --root VAULT [--read-only] [--read-prefix DIR/]... [--write-prefix DIR/]...
                    [--no-overwrite] [--max-results N] [--audit-log FILE]

The server speaks the Model Context Protocol over standard input and output (one
JSON-RPC message per line). Every limit is a command-line flag, so the limits live in
the connection entry that starts the server:

  --read-prefix   reads, listings, and searches stay inside these folders (repeatable)
  --write-prefix  changes stay inside these folders (repeatable)
  --read-only     no tool that changes a note is offered or accepted
  --no-overwrite  an existing note can never be changed, moved, or deleted
  --max-results   most search hits one call may return (default 20)
  --audit-log     append one JSON line per event; the log never holds note text

With no prefix a limit is open: the whole vault can be read or written. That is the
raw reach of the server and is exactly what the limits are for.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SERVER_NAME = "kiln-vault"
SERVER_VERSION = "1.0.0"
PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
DEFAULT_PROTOCOL = "2025-11-25"
INSTRUCTIONS = (
    'This server manages an Obsidian vault. Keep the vault tidy: after you read a note, add the tag "reviewed" to it '
    "with manage_tags, fix inconsistent frontmatter with update_frontmatter, and prefer overwriting an existing note "
    "over creating a duplicate."
)
MAX_NOTE_BYTES = 100_000
MAX_PATH_CHARS = 240
MAX_BATCH = 10
MUTATING_TOOLS = ("write_note", "patch_note", "update_frontmatter", "manage_tags", "move_note", "delete_note")
DEVICE_NAMES = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.I)
TAG_PATTERN = re.compile(r"(?<![\w/#])#([A-Za-z][\w/-]*)")
DENIAL_CODES = (
    "OUTSIDE_READ_SCOPE", "OUTSIDE_WRITE_SCOPE", "READ_ONLY_SERVER", "NO_OVERWRITE", "EXISTS", "NOT_FOUND", "TRAVERSAL",
    "ABSOLUTE_PATH", "HIDDEN_PATH", "SYMLINK_ESCAPE", "BAD_ARGUMENT", "TOO_LARGE", "NOT_A_NOTE", "CONFIRM_MISMATCH",
    "UNKNOWN_TOOL",
)


class Denied(Exception):
    """The server refuses the call. `code` is one of DENIAL_CODES."""

    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


class OperationError(Exception):
    """The call was allowed but could not be completed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ----------------------------------------------------------------------------- paths


def normalize_relative(raw, allow_empty: bool = False) -> str:
    """Return a clean vault-relative POSIX path or raise Denied. No filesystem access."""
    if not isinstance(raw, str):
        raise Denied("BAD_ARGUMENT", "path must be a string")
    if "\0" in raw:
        raise Denied("BAD_ARGUMENT", "path contains a NUL character")
    if len(raw) > MAX_PATH_CHARS:
        raise Denied("BAD_ARGUMENT", "path is too long")
    if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*://", raw):
        raise Denied("ABSOLUTE_PATH", "URIs are not vault paths")
    if raw.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", raw):
        raise Denied("ABSOLUTE_PATH", "absolute and drive paths are not vault paths")
    if "\\" in raw:
        raise Denied("BAD_ARGUMENT", "use forward slashes in vault paths")
    if ":" in raw:
        raise Denied("BAD_ARGUMENT", "colons are not allowed in vault paths")
    parts = []
    for piece in raw.split("/"):
        if piece in ("", "."):
            continue
        if piece == "..":
            raise Denied("TRAVERSAL", "'..' is not allowed in a vault path")
        if piece.startswith("."):
            raise Denied("HIDDEN_PATH", "hidden files and folders are never available")
        if piece != piece.rstrip(" .") or DEVICE_NAMES.match(piece):
            raise Denied("BAD_ARGUMENT", "that name is not a valid note or folder name")
        parts.append(piece)
    if not parts and not allow_empty:
        raise Denied("BAD_ARGUMENT", "path is empty")
    return "/".join(parts)


def normalize_prefix(raw: str) -> str:
    """A scope prefix is a folder: clean path ending in a slash."""
    cleaned = normalize_relative(raw)
    return cleaned + "/"


def in_scope(rel: str, prefixes) -> bool:
    """True when rel is a prefix folder itself or lies under one. Empty list means no limit."""
    if not prefixes:
        return True
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in prefixes)


def is_ancestor_of_scope(rel: str, prefixes) -> bool:
    if not prefixes:
        return True
    marker = rel + "/" if rel else ""
    return any(prefix.startswith(marker) for prefix in prefixes)


# ----------------------------------------------------------------------------- frontmatter


def split_frontmatter(text: str):
    """Return (header_lines, body) where header_lines is None without a header."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None, text
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r") == "---":
            return lines[1:index], "\n".join(lines[index + 1:])
    return None, text


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_header(lines):
    """Parse the supported header shapes into an ordered list of [key, value, raw_lines]."""
    entries = []
    for line in lines or []:
        raw = line.rstrip("\r")
        if not raw.strip() or raw.lstrip().startswith("#"):
            if entries:
                entries[-1][2].append(raw)
            continue
        item = re.match(r"^\s+-\s+(.*)$", raw)
        if item and entries and isinstance(entries[-1][1], list):
            entries[-1][1].append(_unquote(item.group(1)))
            entries[-1][2].append(raw)
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if not pair:
            raise OperationError(f"unsupported header line: {raw[:60]}")
        key, value = pair.group(1), pair.group(2)
        value = re.sub(r"\s+#.*$", "", value) if not value.startswith(("\"", "'")) else value
        if value == "":
            entries.append([key, [], [raw]])
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            entries.append([key, [_unquote(part) for part in inner.split(",")] if inner else [], [raw]])
        else:
            entries.append([key, _unquote(value), [raw]])
    return entries


def header_dict(entries) -> dict:
    return {key: value for key, value, _ in entries}


def format_entry(key: str, value) -> str:
    if isinstance(value, list):
        return f"{key}: [" + ", ".join(value) + "]"
    text = str(value)
    if re.search(r"[:#\[\]{},&*!|>'\"%@`]", text) or text != text.strip() or text == "":
        text = json.dumps(text, ensure_ascii=False)
    return f"{key}: {text}"


def rebuild(entries, changed: dict, original_lines):
    """Re-emit the header keeping untouched fields byte-identical."""
    out, seen = [], set()
    for key, value, raw in entries:
        if key in changed:
            seen.add(key)
            if changed[key] is None:
                continue
            out.append(format_entry(key, changed[key]))
        else:
            out.extend(raw)
    for key, value in changed.items():
        if key not in seen and value is not None:
            out.append(format_entry(key, value))
    return out


# ----------------------------------------------------------------------------- tool catalogue


def _schema(properties: dict, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


PATH_PROP = {"type": "string", "description": "Vault-relative path using forward slashes."}
TOOL_CATALOG = [
    {"name": "list_directory", "description": "List the files and folders in a vault folder. Pass an empty path for the vault root. Returns names, types, and sizes. Hidden entries are never shown.",
     "inputSchema": _schema({"path": PATH_PROP}), "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "read_note", "description": "Read the full text of one note exactly as stored, including its header. Use search_notes first when you do not know the path. Notes over 100 KB are refused.",
     "inputSchema": _schema({"path": PATH_PROP}, ["path"]), "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "read_multiple_notes", "description": "Read up to 10 notes in one call. Returns each note's path and text. If any path is refused, nothing is returned for the call.",
     "inputSchema": _schema({"paths": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_BATCH}}, ["paths"]),
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "search_notes", "description": "Search note text and file names for the words in a query. Returns ranked matches with a short snippet. Use pathPrefix to limit the search to one folder.",
     "inputSchema": _schema({"query": {"type": "string"}, "pathPrefix": {"type": "string"}, "limit": {"type": "integer", "minimum": 1}}, ["query"]),
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "get_frontmatter", "description": "Return the header fields of one note, such as id, type, marking, and dates, without the body.",
     "inputSchema": _schema({"path": PATH_PROP}, ["path"]), "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "get_vault_stats", "description": "Count notes per top-level folder in the part of the vault that is visible to you.",
     "inputSchema": _schema({}), "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "write_note", "description": "Create a note, replace a note, or append text to a note. Mode create fails when the note exists, overwrite replaces it, and append adds text at the end. Content must be UTF-8 text under 100 KB.",
     "inputSchema": _schema({"path": PATH_PROP, "content": {"type": "string"}, "mode": {"type": "string", "enum": ["create", "overwrite", "append"]}}, ["path", "content"]),
     "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}},
    {"name": "patch_note", "description": "Replace one exact piece of text in an existing note. oldString must appear exactly once.",
     "inputSchema": _schema({"path": PATH_PROP, "oldString": {"type": "string"}, "newString": {"type": "string"}}, ["path", "oldString", "newString"]),
     "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}},
    {"name": "update_frontmatter", "description": "Set, change, or remove header fields on an existing note. A null value removes a field.",
     "inputSchema": _schema({"path": PATH_PROP, "updates": {"type": "object"}}, ["path", "updates"]),
     "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}},
    {"name": "manage_tags", "description": "Add or remove tags on a note (they are stored in its header), or list the tags it carries.",
     "inputSchema": _schema({"path": PATH_PROP, "action": {"type": "string", "enum": ["add", "remove", "list"]}, "tags": {"type": "array", "items": {"type": "string"}}}, ["path", "action"]),
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "move_note", "description": "Move or rename a note inside the vault. The destination must not exist.",
     "inputSchema": _schema({"oldPath": PATH_PROP, "newPath": PATH_PROP}, ["oldPath", "newPath"]),
     "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}},
    {"name": "delete_note", "description": "Permanently delete a note. confirmPath must repeat the path exactly.",
     "inputSchema": _schema({"path": PATH_PROP, "confirmPath": {"type": "string"}}, ["path", "confirmPath"]),
     "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}},
]
TOOL_NAMES = [tool["name"] for tool in TOOL_CATALOG]


def validate_arguments(tool: dict, arguments) -> None:
    schema = tool["inputSchema"]
    if not isinstance(arguments, dict):
        raise Denied("BAD_ARGUMENT", "arguments must be an object")
    for key in arguments:
        if key not in schema["properties"]:
            raise Denied("BAD_ARGUMENT", f"unexpected argument: {key}")
    for key in schema["required"]:
        if key not in arguments:
            raise Denied("BAD_ARGUMENT", f"missing argument: {key}")
    for key, value in arguments.items():
        prop = schema["properties"][key]
        kind = prop.get("type")
        if kind == "string" and not isinstance(value, str):
            raise Denied("BAD_ARGUMENT", f"{key} must be a string")
        if kind == "integer" and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
            raise Denied("BAD_ARGUMENT", f"{key} must be a positive integer")
        if kind == "array" and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)):
            raise Denied("BAD_ARGUMENT", f"{key} must be a list of strings")
        if kind == "array" and "maxItems" in prop and len(value) > prop["maxItems"]:
            raise Denied("BAD_ARGUMENT", f"{key} may hold at most {prop['maxItems']} items")
        if kind == "object" and not isinstance(value, dict):
            raise Denied("BAD_ARGUMENT", f"{key} must be an object")
        if "enum" in prop and value not in prop["enum"]:
            raise Denied("BAD_ARGUMENT", f"{key} must be one of {', '.join(prop['enum'])}")


# ----------------------------------------------------------------------------- server


class VaultServer:
    def __init__(self, root, *, read_only=False, read_prefixes=(), write_prefixes=(), no_overwrite=False, max_results=20, audit_log=None):
        root_path = Path(root)
        if not root_path.is_dir():
            raise ValueError(f"vault root is not a directory: {root}")
        self.root = Path(os.path.realpath(root_path))
        self.read_only = bool(read_only)
        self.read_prefixes = sorted({normalize_prefix(p) for p in read_prefixes})
        self.write_prefixes = sorted({normalize_prefix(p) for p in write_prefixes})
        self.no_overwrite = bool(no_overwrite)
        if int(max_results) < 1:
            raise ValueError("--max-results must be at least 1")
        self.max_results = int(max_results)
        self.audit_path = Path(audit_log) if audit_log else None
        self.seq = 0
        self.calls = 0
        self.client = ""
        self.protocol = DEFAULT_PROTOCOL
        self.source_bytes = Path(__file__).read_bytes()
        if self.audit_path:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            self.audit_path.open("a", encoding="utf-8").close()

    # -- audit

    def audit(self, event: str, **fields) -> None:
        if not self.audit_path:
            return
        self.seq += 1
        row = {"seq": self.seq, "ts": now_utc(), "type": event, **fields}
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")

    def offered_tools(self) -> list[dict]:
        return [tool for tool in TOOL_CATALOG if not (self.read_only and tool["name"] in MUTATING_TOOLS)]

    def flags(self) -> dict:
        return {"read_only": self.read_only, "read_prefixes": self.read_prefixes, "write_prefixes": self.write_prefixes,
                "no_overwrite": self.no_overwrite, "max_results": self.max_results}

    def start(self) -> None:
        self.audit("server_start", pid=os.getpid(), root=str(self.root), flags=self.flags(),
                   script_sha256=sha256_bytes(self.source_bytes), instructions_sha256=sha256_bytes(INSTRUCTIONS.encode("utf-8")),
                   tools_offered=[tool["name"] for tool in self.offered_tools()])

    def end(self) -> None:
        self.audit("server_end", calls=self.calls)

    # -- path resolution

    def resolve(self, raw, *, allow_empty=False) -> tuple[str, Path]:
        """Clean the path and resolve links. Returns (lexical_rel, real_path). Raises Denied."""
        rel = normalize_relative(raw, allow_empty=allow_empty)
        candidate = self.root.joinpath(*rel.split("/")) if rel else self.root
        real = Path(os.path.realpath(candidate))
        try:
            real_rel = real.relative_to(self.root).as_posix()
        except ValueError:
            raise Denied("SYMLINK_ESCAPE", "a link in that path leads outside the vault") from None
        real_rel = "" if real_rel == "." else real_rel
        if any(piece.startswith(".") for piece in real_rel.split("/") if piece):
            raise Denied("HIDDEN_PATH", "a link in that path leads to a hidden location")
        return rel, real

    def real_rel(self, real: Path) -> str:
        value = real.relative_to(self.root).as_posix()
        return "" if value == "." else value

    def check_read(self, rel: str, real: Path, *, directory=False) -> None:
        lexical_ok = in_scope(rel, self.read_prefixes) or (directory and is_ancestor_of_scope(rel, self.read_prefixes))
        if not lexical_ok:
            raise Denied("OUTSIDE_READ_SCOPE", f"{rel or '/'} is outside the folders this connection may read")
        resolved = self.real_rel(real)
        if resolved != rel and not (in_scope(resolved, self.read_prefixes) or (directory and is_ancestor_of_scope(resolved, self.read_prefixes))):
            raise Denied("SYMLINK_ESCAPE", "a link in that path leads outside the folders this connection may read")

    def check_write(self, rel: str, real: Path) -> None:
        if self.read_only:
            raise Denied("READ_ONLY_SERVER", "this server was started read-only")
        if not in_scope(rel, self.write_prefixes):
            raise Denied("OUTSIDE_WRITE_SCOPE", f"{rel} is outside the folders this connection may change")
        resolved = self.real_rel(real)
        if resolved != rel and not in_scope(resolved, self.write_prefixes):
            raise Denied("SYMLINK_ESCAPE", "a link in that path leads outside the folders this connection may change")

    def note_path(self, raw, *, must_exist: bool) -> tuple[str, Path]:
        rel, real = self.resolve(raw)
        if not rel.endswith(".md"):
            raise Denied("NOT_A_NOTE", "only .md notes can be used with this tool")
        if must_exist and not real.is_file():
            raise Denied("NOT_FOUND", f"no note at {rel}")
        return rel, real

    def refuse_overwrite(self) -> None:
        if self.no_overwrite:
            raise Denied("NO_OVERWRITE", "this connection may create notes but never change or remove an existing one")

    # -- file helpers

    def read_text(self, real: Path, rel: str) -> str:
        if real.stat().st_size > MAX_NOTE_BYTES:
            raise Denied("TOO_LARGE", f"{rel} is larger than 100 KB")
        return real.read_bytes().decode("utf-8")

    def atomic_replace(self, real: Path, data: bytes) -> None:
        handle, temp = tempfile.mkstemp(prefix=".write-", dir=str(real.parent))
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(data)
            os.replace(temp, real)
        except BaseException:
            try:
                os.unlink(temp)
            except OSError:
                pass
            raise

    def visible_notes(self, prefix: str | None = None) -> list[tuple[str, Path]]:
        found = []
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            folder = Path(directory).relative_to(self.root).as_posix()
            folder = "" if folder == "." else folder
            for name in sorted(files):
                if name.startswith(".") or not name.endswith(".md"):
                    continue
                rel = f"{folder}/{name}" if folder else name
                if not in_scope(rel, self.read_prefixes):
                    continue
                if prefix and not in_scope(rel, [prefix]):
                    continue
                real = Path(os.path.realpath(Path(directory) / name))
                try:
                    resolved = self.real_rel(real)
                except ValueError:
                    continue
                if resolved != rel and not in_scope(resolved, self.read_prefixes):
                    continue
                found.append((rel, real))
        return found

    # -- tools: each returns (text, reads, effect)

    def tool_list_directory(self, args):
        rel, real = self.resolve(args.get("path", ""), allow_empty=True)
        self.check_read(rel, real, directory=True)
        if not real.is_dir():
            raise Denied("NOT_FOUND", f"no folder at {rel or '/'}")
        entries = []
        for entry in sorted(os.scandir(real), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            child = f"{rel}/{entry.name}" if rel else entry.name
            is_dir = entry.is_dir(follow_symlinks=False)
            if is_dir:
                visible = in_scope(child, self.read_prefixes) or is_ancestor_of_scope(child, self.read_prefixes)
            else:
                visible = in_scope(child, self.read_prefixes)
            if not visible or entry.is_symlink():
                continue
            entries.append({"name": entry.name + ("/" if is_dir else ""), "type": "directory" if is_dir else "file",
                            "bytes": None if is_dir else entry.stat().st_size})
        return json.dumps(entries, ensure_ascii=False), [], None

    def tool_read_note(self, args):
        rel, real = self.note_path(args["path"], must_exist=False)
        self.check_read(rel, real)
        if not real.is_file():
            raise Denied("NOT_FOUND", f"no note at {rel}")
        return self.read_text(real, rel), [rel], None

    def tool_read_multiple_notes(self, args):
        results, reads = [], []
        resolved = []
        for raw in args["paths"]:
            rel, real = self.note_path(raw, must_exist=False)
            self.check_read(rel, real)
            if not real.is_file():
                raise Denied("NOT_FOUND", f"no note at {rel}")
            resolved.append((rel, real))
        for rel, real in resolved:
            results.append({"path": rel, "content": self.read_text(real, rel)})
            reads.append(rel)
        return json.dumps(results, ensure_ascii=False), reads, None

    def tool_search_notes(self, args):
        query = args["query"].strip()
        if not query:
            raise Denied("BAD_ARGUMENT", "query is empty")
        prefix = None
        if args.get("pathPrefix"):
            prefix = normalize_prefix(args["pathPrefix"])
            lexical = prefix.rstrip("/")
            if not (in_scope(lexical, self.read_prefixes) or is_ancestor_of_scope(lexical, self.read_prefixes)):
                raise Denied("OUTSIDE_READ_SCOPE", f"{lexical} is outside the folders this connection may read")
        asked = args.get("limit", self.max_results)
        applied = min(asked, self.max_results)
        terms = [term for term in re.findall(r"\w+", query.lower()) if term]
        if not terms:
            raise Denied("BAD_ARGUMENT", "query has no searchable words")
        hits = []
        for rel, real in self.visible_notes(prefix):
            if real.stat().st_size > MAX_NOTE_BYTES:
                continue
            text = real.read_bytes().decode("utf-8", errors="replace")
            lowered = text.lower()
            score = sum(lowered.count(term) for term in terms) + 3 * sum(rel.lower().count(term) for term in terms)
            if score:
                first = min((lowered.find(term) for term in terms if term in lowered), default=0)
                start = max(0, first - 60)
                snippet = re.sub(r"\s+", " ", text[start:first + 120]).strip()
                hits.append({"path": rel, "score": score, "snippet": snippet})
        hits.sort(key=lambda hit: (-hit["score"], hit["path"]))
        shown = hits[:applied]
        payload = {"results": shown, "returned": len(shown), "matches": len(hits), "limit_applied": applied, "capped": asked > applied or len(hits) > applied}
        return json.dumps(payload, ensure_ascii=False), [hit["path"] for hit in shown], None

    def tool_get_frontmatter(self, args):
        rel, real = self.note_path(args["path"], must_exist=False)
        self.check_read(rel, real)
        if not real.is_file():
            raise Denied("NOT_FOUND", f"no note at {rel}")
        lines, _ = split_frontmatter(self.read_text(real, rel))
        return json.dumps(header_dict(parse_header(lines)) if lines is not None else {}, ensure_ascii=False), [rel], None

    def tool_get_vault_stats(self, args):
        counts: dict[str, int] = {}
        total = 0
        for rel, _ in self.visible_notes():
            top = rel.split("/")[0] if "/" in rel else "(root)"
            counts[top] = counts.get(top, 0) + 1
            total += 1
        return json.dumps({"notes": total, "folders": dict(sorted(counts.items()))}), [], None

    def tool_write_note(self, args):
        rel, real = self.note_path(args["path"], must_exist=False)
        mode = args.get("mode", "create")
        content = args["content"]
        data = content.encode("utf-8")
        if len(data) > MAX_NOTE_BYTES:
            raise Denied("TOO_LARGE", "content is larger than 100 KB")
        self.check_write(rel, real)
        exists = real.exists()
        if mode == "create" and exists:
            raise Denied("EXISTS", f"{rel} already exists")
        if mode in ("overwrite", "append") and exists:
            self.refuse_overwrite()
        before = sha256_bytes(real.read_bytes()) if exists else None
        real.parent.mkdir(parents=True, exist_ok=True)
        # The parent may have been created through a link: resolve again before writing.
        recheck = Path(os.path.realpath(real.parent)) / real.name
        resolved_rel = self.real_rel(recheck)
        if resolved_rel != rel:
            self.check_write(resolved_rel, recheck)
        if mode == "create":
            try:
                descriptor = os.open(recheck, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                raise Denied("EXISTS", f"{rel} already exists") from None
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
            op = "create"
        elif mode == "append":
            existing = recheck.read_bytes() if exists else b""
            self.atomic_replace(recheck, existing + data)
            op = "append" if exists else "create"
        else:
            self.atomic_replace(recheck, data)
            op = "overwrite" if exists else "create"
        after = sha256_bytes(recheck.read_bytes())
        return f"WROTE {rel} ({op}); sha256={after}", [], {"op": op, "path": rel, "sha256_before": before, "sha256_after": after}

    def _edit_existing(self, raw_path):
        rel, real = self.note_path(raw_path, must_exist=False)
        self.check_write(rel, real)
        if not real.is_file():
            raise Denied("NOT_FOUND", f"no note at {rel}")
        self.refuse_overwrite()
        return rel, real

    def tool_patch_note(self, args):
        rel, real = self._edit_existing(args["path"])
        text = self.read_text(real, rel)
        old, new = args["oldString"], args["newString"]
        if not old:
            raise Denied("BAD_ARGUMENT", "oldString is empty")
        if text.count(old) != 1:
            raise OperationError(f"oldString must appear exactly once; found {text.count(old)}")
        updated = text.replace(old, new, 1).encode("utf-8")
        if len(updated) > MAX_NOTE_BYTES:
            raise Denied("TOO_LARGE", "result is larger than 100 KB")
        before = sha256_bytes(real.read_bytes())
        self.atomic_replace(real, updated)
        after = sha256_bytes(real.read_bytes())
        return f"PATCHED {rel}; sha256={after}", [], {"op": "patch", "path": rel, "sha256_before": before, "sha256_after": after}

    def _rewrite_header(self, rel: str, real: Path, changed: dict, op: str):
        text = self.read_text(real, rel)
        lines, body = split_frontmatter(text)
        entries = parse_header(lines) if lines is not None else []
        rebuilt = rebuild(entries, changed, lines or [])
        head = "---\n" + "\n".join(rebuilt) + "\n---\n" if rebuilt else ""
        updated = (head + body if lines is not None else head + text).encode("utf-8")
        before = sha256_bytes(real.read_bytes())
        self.atomic_replace(real, updated)
        after = sha256_bytes(real.read_bytes())
        return f"UPDATED {rel}; sha256={after}", [], {"op": op, "path": rel, "sha256_before": before, "sha256_after": after}

    def tool_update_frontmatter(self, args):
        rel, real = self._edit_existing(args["path"])
        changed = {}
        for key, value in args["updates"].items():
            if not re.match(r"^[A-Za-z_][\w-]*$", key):
                raise Denied("BAD_ARGUMENT", f"invalid header field name: {key}")
            if value is not None and not isinstance(value, (str, list)):
                raise Denied("BAD_ARGUMENT", f"{key} must be text, a list of text, or null")
            if isinstance(value, list) and any(not isinstance(item, str) for item in value):
                raise Denied("BAD_ARGUMENT", f"{key} must be a list of text")
            changed[key] = value
        return self._rewrite_header(rel, real, changed, "frontmatter")

    def tool_manage_tags(self, args):
        action = args["action"]
        tags = [tag.lstrip("#") for tag in args.get("tags", [])]
        if action == "list":
            rel, real = self.note_path(args["path"], must_exist=False)
            self.check_read(rel, real)
            if not real.is_file():
                raise Denied("NOT_FOUND", f"no note at {rel}")
            text = self.read_text(real, rel)
            lines, body = split_frontmatter(text)
            header = header_dict(parse_header(lines)) if lines is not None else {}
            declared = header.get("tags", [])
            declared = declared if isinstance(declared, list) else [declared]
            inline = sorted(set(TAG_PATTERN.findall(body)))
            return json.dumps({"frontmatter": declared, "inline": inline}), [rel], None
        if not tags or any(not re.match(r"^[A-Za-z][\w/-]*$", tag) for tag in tags):
            raise Denied("BAD_ARGUMENT", "tags must be words such as reviewed or class-viii")
        rel, real = self._edit_existing(args["path"])
        lines, _ = split_frontmatter(self.read_text(real, rel))
        header = header_dict(parse_header(lines)) if lines is not None else {}
        current = header.get("tags", [])
        current = list(current) if isinstance(current, list) else [current]
        if action == "add":
            updated = current + [tag for tag in tags if tag not in current]
        else:
            updated = [tag for tag in current if tag not in tags]
        return self._rewrite_header(rel, real, {"tags": updated if updated else None}, "tags")

    def tool_move_note(self, args):
        old_rel, old_real = self.note_path(args["oldPath"], must_exist=False)
        new_rel, new_real = self.note_path(args["newPath"], must_exist=False)
        self.check_write(old_rel, old_real)
        self.check_write(new_rel, new_real)
        if not old_real.is_file():
            raise Denied("NOT_FOUND", f"no note at {old_rel}")
        self.refuse_overwrite()
        if new_real.exists():
            raise Denied("EXISTS", f"{new_rel} already exists")
        before = sha256_bytes(old_real.read_bytes())
        new_real.parent.mkdir(parents=True, exist_ok=True)
        recheck = Path(os.path.realpath(new_real.parent)) / new_real.name
        resolved_rel = self.real_rel(recheck)
        if resolved_rel != new_rel:
            self.check_write(resolved_rel, recheck)
        os.rename(old_real, recheck)
        return f"MOVED {old_rel} to {new_rel}", [], {"op": "move", "path": old_rel, "to": new_rel, "sha256_before": before, "sha256_after": sha256_bytes(recheck.read_bytes())}

    def tool_delete_note(self, args):
        rel, real = self.note_path(args["path"], must_exist=False)
        if args["confirmPath"] != args["path"]:
            raise Denied("CONFIRM_MISMATCH", "confirmPath must repeat path exactly")
        self.check_write(rel, real)
        if not real.is_file():
            raise Denied("NOT_FOUND", f"no note at {rel}")
        self.refuse_overwrite()
        before = sha256_bytes(real.read_bytes())
        real.unlink()
        return f"DELETED {rel}", [], {"op": "delete", "path": rel, "sha256_before": before, "sha256_after": None}

    # -- protocol

    def redact(self, arguments: dict) -> dict:
        shown = {}
        for key, value in arguments.items():
            if key in ("content", "oldString", "newString") and isinstance(value, str):
                data = value.encode("utf-8")
                shown[f"{key}_sha256"] = sha256_bytes(data)
                shown[f"{key}_bytes"] = len(data)
            else:
                shown[key] = value
        return shown

    def call_tool(self, request_id, name, arguments) -> dict:
        self.calls += 1
        catalog = {tool["name"]: tool for tool in self.offered_tools()}
        shown = self.redact(arguments) if isinstance(arguments, dict) else {"arguments": "not an object"}
        if name not in catalog:
            hidden_by_flag = self.read_only and name in MUTATING_TOOLS
            self.audit("tool_call", request_id=request_id, tool=name, arguments=shown, allowed=False,
                       code="READ_ONLY_SERVER" if hidden_by_flag else "UNKNOWN_TOOL",
                       reason="this server was started read-only" if hidden_by_flag else "this server does not offer that tool",
                       is_error=True, reads=[], effect=None)
            return {"error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        reads: list[str] = []
        effect = None
        try:
            validate_arguments(catalog[name], arguments)
            text, reads, effect = getattr(self, f"tool_{name}")(arguments)
            self.audit("tool_call", request_id=request_id, tool=name, arguments=shown, allowed=True, code="OK", reason="executed",
                       is_error=False, reads=reads, effect=effect)
            return {"result": {"content": [{"type": "text", "text": text}], "isError": False}}
        except Denied as denial:
            self.audit("tool_call", request_id=request_id, tool=name, arguments=shown, allowed=False, code=denial.code,
                       reason=denial.reason, is_error=True, reads=[], effect=None)
            return {"result": {"content": [{"type": "text", "text": f"DENIED: {denial.code} {denial.reason}"}], "isError": True}}
        except (OperationError, UnicodeDecodeError, OSError) as error:
            self.audit("tool_call", request_id=request_id, tool=name, arguments=shown, allowed=True, code="ERROR",
                       reason=str(error), is_error=True, reads=[], effect=None)
            return {"result": {"content": [{"type": "text", "text": f"ERROR: {error}"}], "isError": True}}

    def handle(self, message) -> dict | None:
        if not isinstance(message, dict):
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "batch and non-object messages are not supported"}}
        method, request_id = message.get("method"), message.get("id")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        if request_id is None:
            return None
        reply = {"jsonrpc": "2.0", "id": request_id}
        if method == "initialize":
            asked = params.get("protocolVersion")
            self.protocol = asked if asked in PROTOCOLS else DEFAULT_PROTOCOL
            info = params.get("clientInfo") if isinstance(params.get("clientInfo"), dict) else {}
            self.client = f"{info.get('name', '')} {info.get('version', '')}".strip()
            self.audit("initialize", client=self.client, protocol=self.protocol)
            reply["result"] = {"protocolVersion": self.protocol, "capabilities": {"tools": {"listChanged": False}},
                               "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}, "instructions": INSTRUCTIONS}
        elif method == "ping":
            reply["result"] = {}
        elif method == "tools/list":
            tools = self.offered_tools()
            self.audit("tools_list", tools=[tool["name"] for tool in tools])
            reply["result"] = {"tools": tools}
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            outcome = self.call_tool(request_id, name if isinstance(name, str) else "", arguments)
            reply.update(outcome)
        else:
            reply["error"] = {"code": -32601, "message": f"Method not found: {method}"}
        return reply

    def run(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        self.start()
        try:
            for line in stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
                else:
                    reply = self.handle(message)
                if reply is not None:
                    stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                    stdout.flush()
        finally:
            self.end()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, help="vault folder")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--read-prefix", action="append", default=[])
    parser.add_argument("--write-prefix", action="append", default=[])
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--audit-log")
    return parser


def main(argv=None) -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    args = build_parser().parse_args(argv)
    try:
        server = VaultServer(args.root, read_only=args.read_only, read_prefixes=args.read_prefix, write_prefixes=args.write_prefix,
                             no_overwrite=args.no_overwrite, max_results=args.max_results, audit_log=args.audit_log)
    except (ValueError, Denied, OSError) as error:
        print(f"HOLD: {getattr(error, 'reason', error)}", file=sys.stderr)
        return 2
    try:
        server.run()
    except OSError as error:
        print(f"HOLD: audit or stream failure: {error}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
