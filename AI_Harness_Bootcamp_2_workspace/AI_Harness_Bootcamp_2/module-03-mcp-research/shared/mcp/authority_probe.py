#!/usr/bin/env python3
"""Try to break the limits on a connection, without a model.

Usage: authority_probe.py --config mcp.json --authority AUTHORITY.md --vault VAULT --out FILE
                          [--server vault] [--ignore-allow-list]

A model might never attempt a forbidden action, so a clean model run proves little.
The probe attempts each forbidden action itself, directly against the server entry
exactly as configured, on a throwaway COPY of the vault. Your vault is never touched.

For every attempt it records what the declared authority intends (PERMITTED or
FORBIDDEN) and what actually happened:

  WORKS                a permitted action worked
  HELD                 a forbidden action was stopped (by the allow-list, the server, or both)
  BREACHED             a forbidden action had an effect: a changed file, or content returned
  UNAVAILABLE          a permitted action is not offered: its tool is off the allow-list, or the server refused it
  SKIPPED              the attempt could not be set up on this machine

--ignore-allow-list sends every attempt to the server even when allow_tools would have
stopped it, so the server's own limits are tested alone.

Exit 0: PASS (no forbidden attempt had an effect, and permitted work works).
Exit 1: HOLD. Exit 2: the inputs cannot be used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authority import AuthorityError, READ_TOOLS, parse_authority, parse_config, server_entry, validate_entry  # noqa: E402
from mcp_client import McpClient, McpClientError  # noqa: E402
from vault_mcp import in_scope, is_ancestor_of_scope  # noqa: E402

PROBE_TEXT = "probe text\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(*roots: Path) -> dict:
    state = {}
    for root in roots:
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs:
                path = Path(directory) / name
                state[str(path) + "/"] = "link" if path.is_symlink() else None
            for name in files:
                path = Path(directory) / name
                state[str(path)] = "link" if path.is_symlink() else sha256_bytes(path.read_bytes())
    return state


class Context:
    """The throwaway copy and the facts attempts need."""

    def __init__(self, vault: Path, declaration: dict, tmp: Path):
        self.tmp = tmp
        self.vault = tmp / "vault"
        self.pristine = tmp / "pristine"
        self.outside = tmp / "outside-area"
        self.sentinel = tmp / "outside.md"
        self.declaration = declaration
        self.reads = declaration["read_scope"]
        self.writes = declaration["write_scope"]
        shutil.copytree(vault, self.pristine, symlinks=True, ignore=shutil.ignore_patterns(".obsidian", "__pycache__"))
        self.outside.mkdir()
        self.sentinel.write_text("outside sentinel\n", encoding="utf-8")
        self.restore()
        notes = sorted(p.relative_to(self.pristine).as_posix() for p in self.pristine.rglob("*.md"))
        self.notes = notes
        self.in_scope_notes = [n for n in notes if in_scope(n, self.reads)]
        self.source_note = next((n for n in notes if n.startswith("Sources/")), notes[0] if notes else None)
        self.outside_folder = next((f for f in ("Estimate", "Sources", "Handbook", "Drafts")
                                    if (self.pristine / f).is_dir() and not in_scope(f, self.reads) and not is_ancestor_of_scope(f, self.reads)), None)
        self.outside_note = next((n for n in notes if self.outside_folder and n.startswith(self.outside_folder + "/")), None)
        self.write_dir = self.writes[0] if self.writes else None

    def restore(self) -> None:
        if self.vault.exists() or self.vault.is_symlink():
            shutil.rmtree(self.vault)
        shutil.copytree(self.pristine, self.vault, symlinks=True)
        (self.vault / "Drafts").mkdir(exist_ok=True)
        hidden = self.vault / ".obsidian"
        hidden.mkdir(exist_ok=True)
        (hidden / "app.json").write_text("{}\n", encoding="utf-8")
        for leftover in self.outside.iterdir():
            shutil.rmtree(leftover) if leftover.is_dir() else leftover.unlink()


def attempts(ctx: Context) -> list[dict]:
    """The fixed battery. `setup` runs on the throwaway copy before the attempt."""
    d = ctx.declaration
    first, second = (ctx.in_scope_notes + [None, None])[:2]
    reads_ok = [n for n in (first, second) if n]
    src = ctx.source_note
    outside = ctx.outside_note
    folder = ctx.outside_folder
    wdir = ctx.write_dir
    created = f"{wdir}probe-created.md" if wdir else None
    items: list[dict] = []

    def add(category, tool, args, intended, target, **extra):
        items.append({"category": category, "tool": tool, "args": args, "intended": intended, "target": target, **extra})

    def make_draft():
        path = ctx.vault / created
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(PROBE_TEXT, encoding="utf-8")

    def leak_search(outcome):
        if not outcome["sent"] or outcome["is_error"]:
            return False
        try:
            hits = json.loads(outcome["text"])["results"]
        except (ValueError, KeyError, TypeError):
            return False
        return any(not in_scope(hit["path"], ctx.reads) for hit in hits)

    def leak_listing(outcome):
        if not outcome["sent"] or outcome["is_error"]:
            return False
        try:
            names = [e["name"].rstrip("/") for e in json.loads(outcome["text"])]
        except (ValueError, KeyError, TypeError):
            return False
        return any(not (in_scope(n, ctx.reads) or is_ancestor_of_scope(n, ctx.reads)) for n in names)

    def flood(outcome):
        if not outcome["sent"] or outcome["is_error"]:
            return False
        try:
            return json.loads(outcome["text"])["returned"] > 20
        except (ValueError, KeyError, TypeError):
            return False

    if first:
        add("read in scope", "read_note", {"path": first}, "PERMITTED", first)
    if len(reads_ok) == 2:
        add("read in scope", "read_multiple_notes", {"paths": reads_ok}, "PERMITTED", ", ".join(reads_ok))
    add("read in scope", "search_notes", {"query": "the"}, "PERMITTED", "query 'the' (no folder given)", breach=leak_search)
    add("read in scope", "list_directory", {"path": ""}, "PERMITTED", "vault root", breach=leak_listing)
    if outside:
        add("read outside scope", "read_note", {"path": outside}, "FORBIDDEN", outside)
        if first:
            add("read outside scope", "read_multiple_notes", {"paths": [first, outside]}, "FORBIDDEN", f"{first}, {outside}")
        add("read outside scope", "search_notes", {"query": "the", "pathPrefix": folder + "/"}, "FORBIDDEN", f"pathPrefix={folder}/")
        add("read outside scope", "list_directory", {"path": folder}, "FORBIDDEN", folder + "/")
        add("read outside scope", "get_frontmatter", {"path": outside}, "FORBIDDEN", outside)
    if wdir:
        add("create in scope", "write_note", {"path": f"{wdir}probe-new.md", "content": PROBE_TEXT, "mode": "create"}, "PERMITTED", f"{wdir}probe-new.md")
        overwrite_ok = "PERMITTED" if not d["create_only"] else "FORBIDDEN"
        add("change own draft", "write_note", {"path": created, "content": "replaced\n", "mode": "overwrite"}, overwrite_ok, f"overwrite {created}", setup=make_draft)
        add("change own draft", "write_note", {"path": created, "content": "more\n", "mode": "append"}, overwrite_ok, f"append {created}", setup=make_draft)
    add("create outside scope", "write_note", {"path": "Estimate/probe-outside.md", "content": PROBE_TEXT, "mode": "create"}, "FORBIDDEN", "Estimate/probe-outside.md")
    add("create outside scope", "write_note", {"path": "Sources/probe-new.md", "content": PROBE_TEXT, "mode": "create"}, "FORBIDDEN", "Sources/probe-new.md")
    add("create outside scope", "write_note", {"path": "probe-root.md", "content": PROBE_TEXT, "mode": "create"}, "FORBIDDEN", "probe-root.md (vault root)")
    if src:
        add("change a source", "write_note", {"path": src, "content": "replaced\n", "mode": "overwrite"}, "FORBIDDEN", f"overwrite {src}")
        add("change a source", "write_note", {"path": src, "content": "more\n", "mode": "append"}, "FORBIDDEN", f"append {src}")
        add("change a source", "patch_note", {"path": src, "oldString": "#", "newString": "##"}, "FORBIDDEN", src)
        add("change a source", "update_frontmatter", {"path": src, "updates": {"marking": "OPEN"}}, "FORBIDDEN", f"{src} marking -> OPEN")
        add("change a source", "manage_tags", {"path": src, "action": "add", "tags": ["reviewed"]}, "FORBIDDEN", f"{src} add tag")
        add("remove or move", "move_note", {"oldPath": src, "newPath": "Drafts/probe-moved.md"}, "FORBIDDEN", f"{src} -> Drafts/probe-moved.md")
        add("remove or move", "delete_note", {"path": src, "confirmPath": src}, "FORBIDDEN", f"delete {src}")
    if created:
        add("remove or move", "delete_note", {"path": created, "confirmPath": created}, "FORBIDDEN", f"delete {created}", setup=make_draft)
    add("path trick", "read_note", {"path": "../outside.md"}, "FORBIDDEN", "../outside.md")
    add("path trick", "write_note", {"path": "Drafts/../Sources/probe-trick.md", "content": PROBE_TEXT, "mode": "create"}, "FORBIDDEN", "Drafts/../Sources/probe-trick.md")
    add("path trick", "read_note", {"path": str(ctx.sentinel)}, "FORBIDDEN", "absolute path to a file outside the vault")
    add("path trick", "read_note", {"path": ".obsidian/app.json"}, "FORBIDDEN", ".obsidian/app.json (hidden)")
    if wdir:
        def make_link():
            link = ctx.vault / wdir / "probe-link"
            link.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(ctx.outside, link, target_is_directory=True)
        add("path trick", "write_note", {"path": f"{wdir}probe-link/escape.md", "content": PROBE_TEXT, "mode": "create"}, "FORBIDDEN", f"{wdir}probe-link/escape.md (folder link to outside)", setup=make_link, needs_symlink=True)
    add("flood", "search_notes", {"query": "the", "limit": 1000}, "FORBIDDEN", "limit=1000 (more than 20 hits)", breach=flood)
    for index, item in enumerate(items, 1):
        item["id"] = f"A{index:02d}"
    return items


def classify(text: str, rpc_error):
    if rpc_error:
        return "DENIED", "UNKNOWN_TOOL"
    match = re.match(r"DENIED: (\w+)", text)
    if match:
        return "DENIED", match.group(1)
    return "ERROR", "ERROR"


def run(config_path: Path, authority_path: Path, vault: Path, server: str, ignore_allow_list: bool) -> dict:
    config_bytes, authority_bytes = config_path.read_bytes(), authority_path.read_bytes()
    declaration = parse_authority(authority_bytes.decode("utf-8"))
    if declaration["phase"] == "revoked":
        raise AuthorityError("a revoked connection has nothing to probe")
    config = parse_config(config_bytes.decode("utf-8"))
    entry = server_entry(config, server)
    work = config_path.resolve().parent
    parsed = validate_entry(entry, work)
    if not vault.is_dir():
        raise AuthorityError(f"vault folder not found: {vault}")
    flags = []
    rest = entry["args"][1:]
    index = 0
    while index < len(rest):
        if rest[index] == "--root":
            index += 2
            continue
        flags.append(rest[index])
        index += 1
    with tempfile.TemporaryDirectory(prefix="course-probe-") as temp:
        ctx = Context(vault, declaration, Path(temp))
        argv = [sys.executable, str(parsed["script"]), "--root", str(ctx.vault), *flags, "--audit-log", str(ctx.tmp / "probe-audit.jsonl")]
        client = McpClient(argv, cwd=str(work))
        results = []
        try:
            info = client.initialize("course-authority-probe")
            client.list_tools()
            for spec in attempts(ctx):
                results.append(run_attempt(client, ctx, spec, declaration, ignore_allow_list))
        finally:
            client.close()
    summary = {"works": 0, "held": 0, "breached": 0, "unavailable": 0, "skipped": 0}
    key = {"WORKS": "works", "HELD": "held", "BREACHED": "breached", "UNAVAILABLE": "unavailable", "SKIPPED": "skipped"}
    for row in results:
        summary[key[row["result"]]] += 1
    reasons = [f"{row['id']} {row['tool']} {row['target']}: {row['note']}" for row in results if row["result"] == "BREACHED"]
    read_ok = any(row["result"] == "WORKS" and row["tool"] in READ_TOOLS for row in results)
    if not read_ok:
        reasons.append("no permitted read worked: the limits may be tighter than the work needs, or no readable note is in scope")
    if "write_note" in declaration["allow_tools"]:
        created = [row for row in results if row["category"] == "create in scope"]
        if not created or created[0]["result"] != "WORKS":
            reasons.append("creating a new note inside write_scope did not work")
    return {
        "schema_version": 1,
        "probed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "config_sha256": sha256_bytes(config_bytes),
        "authority_sha256": sha256_bytes(authority_bytes),
        "phase": declaration["phase"],
        "ignore_allow_list": ignore_allow_list,
        "server": {"name": info.get("serverInfo", {}).get("name"), "version": info.get("serverInfo", {}).get("version")},
        "flags": {"read_prefixes": parsed["read_prefixes"], "write_prefixes": parsed["write_prefixes"], "read_only": parsed["read_only"],
                  "no_overwrite": parsed["no_overwrite"], "max_results": parsed["max_results"]},
        "attempts": results,
        "summary": summary,
        "verdict": "PASS" if not reasons else "HOLD",
        "reasons": reasons,
    }


def run_attempt(client: McpClient, ctx: Context, spec: dict, declaration: dict, ignore_allow_list: bool) -> dict:
    base = {"id": spec["id"], "category": spec["category"], "tool": spec["tool"], "arguments": spec["args"], "target": spec["target"], "intended": spec["intended"]}
    harness_allows = True if ignore_allow_list else spec["tool"] in declaration["allow_tools"]
    base["harness_allows"] = harness_allows
    ctx.restore()
    if spec.get("needs_symlink"):
        try:
            os.symlink(ctx.outside, ctx.tmp / "symlink-capability-test", target_is_directory=True)
            (ctx.tmp / "symlink-capability-test").unlink()
        except (OSError, NotImplementedError):
            return {**base, "server": {"outcome": "NOT_SENT", "code": None, "effect": False}, "result": "SKIPPED", "held_by": [], "note": "this machine cannot create folder links"}
    if spec.get("setup"):
        spec["setup"]()
    before = {**snapshot(ctx.vault, ctx.outside), "sentinel": sha256_bytes(ctx.sentinel.read_bytes())}
    if harness_allows:
        outcome = {"sent": True, **client.call(spec["tool"], spec["args"])}
    else:
        outcome = {"sent": False, "is_error": True, "text": "", "rpc_error": None}
    after = {**snapshot(ctx.vault, ctx.outside), "sentinel": sha256_bytes(ctx.sentinel.read_bytes())}
    effect = before != after
    if not outcome["sent"]:
        server = {"outcome": "NOT_SENT", "code": None, "effect": effect}
    elif outcome["is_error"]:
        kind, code = classify(outcome["text"], outcome["rpc_error"])
        server = {"outcome": kind, "code": code, "effect": effect}
    else:
        server = {"outcome": "ALLOWED", "code": "OK", "effect": effect}
    breach_check = spec.get("breach")
    returned_content = outcome["sent"] and not outcome["is_error"]
    leaked = breach_check(outcome) if breach_check else False
    if spec["intended"] == "FORBIDDEN":
        breached = effect or (leaked if breach_check else returned_content)
        if breached:
            return {**base, "server": server, "result": "BREACHED", "held_by": [], "note": "the action had an effect" if effect else "the server returned what it should have refused"}
        held_by = ["allow-list"] if not outcome["sent"] else ["server"]
        return {**base, "server": server, "result": "HELD", "held_by": held_by, "note": ""}
    if leaked:
        return {**base, "server": server, "result": "BREACHED", "held_by": [], "note": "a permitted action returned something outside the declared read scope"}
    if returned_content:
        return {**base, "server": server, "result": "WORKS", "held_by": [], "note": ""}
    reason = "its tool is not in allow_tools" if not outcome["sent"] else f"the server refused it: {server['code']}"
    return {**base, "server": server, "result": "UNAVAILABLE", "held_by": [], "note": reason}


def render(report: dict) -> str:
    lines = []
    for row in report["attempts"]:
        detail = ""
        if row["result"] == "HELD":
            detail = " (allow-list)" if row["held_by"] == ["allow-list"] else (" (server capped the result)" if row["server"]["code"] == "OK" else f" (server: {row['server']['code']})")
        elif row["result"] == "BREACHED":
            detail = f" ({row['note']})"
        elif row["result"] in ("UNAVAILABLE", "SKIPPED"):
            detail = f" ({row['note']})"
        lines.append(f"{row['id']} {row['tool']:<20} {row['target'][:44]:<44} {row['intended'].lower():<9} -> {row['result']}{detail}")
    s = report["summary"]
    lines += ["", f"works {s['works']}  held {s['held']}  breached {s['breached']}  unavailable {s['unavailable']}  skipped {s['skipped']}"]
    for reason in report["reasons"]:
        lines.append(f"  - {reason}")
    lines.append("PASS: no forbidden attempt had an effect" if report["verdict"] == "PASS" else f"HOLD: {len(report['reasons'])} problem(s) listed above")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--authority", required=True, type=Path)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--server", default="vault")
    parser.add_argument("--ignore-allow-list", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.out.exists() or args.out.is_symlink():
            raise AuthorityError(f"{args.out} already exists; choose a new file so earlier probes are kept")
        report = run(args.config, args.authority, args.vault, args.server, args.ignore_allow_list)
    except (AuthorityError, McpClientError, OSError, UnicodeDecodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(render(report))
    print(f"\nSaved {args.out}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
