#!/usr/bin/env python3
"""Module 3 oracle: server limits, connection checks, probe verdicts, corpus key, handling checks, and publication hygiene.

Every criterion prints PASS or FAIL with its id. tests/test_adequacy.py mutates a copy of this
module and requires each id to fail for at least one mutation, so a green oracle means the
checks can actually go red. No network, no model, no OMP binary.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "shared" / "mcp"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
PASS: list[str] = []
FAIL: list[str] = []

import authority  # noqa: E402
import authority_probe  # noqa: E402
import corpus_rules  # noqa: E402
import freeze_calibration  # noqa: E402
import handling  # noqa: E402
import mcp_inspect  # noqa: E402
import scan_extract  # noqa: E402
import seed_register  # noqa: E402
import stage_releasable  # noqa: E402
import synthetic_bundle as sb  # noqa: E402
import vault_mcp  # noqa: E402

KEY = json.loads((ROOT / "scripts" / "handling_key.json").read_text(encoding="utf-8"))
EFFECTIVE = {note: row["effective"] for note, row in KEY["notes"].items()}


def check(cid: str, condition: bool, detail: str) -> None:
    (PASS if condition else FAIL).append(f"{cid}: {detail}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_work(base: Path) -> Path:
    """What preparing the work copy produces, built from this module's own files."""
    work = base / "work"
    shutil.copytree(ROOT / "shared" / "vault", work / "vault")
    shutil.copytree(ROOT / "shared" / "mcp", work / "shared" / "mcp", ignore=shutil.ignore_patterns("__pycache__"))
    for folder in ("vault/Drafts", "vault/Estimate/Releasable"):
        (work / folder).mkdir(parents=True, exist_ok=True)
    template = (work / "shared" / "mcp" / "mcp.template.json").read_text(encoding="utf-8")
    (work / "mcp.json").write_text(template.replace("{{WORK}}", json.dumps(str(work))[1:-1]), encoding="utf-8")
    return work


RESEARCH = {"schema_version": 1, "phase": "research", "allow_tools": ["list_directory", "read_multiple_notes", "read_note", "search_notes", "write_note"],
            "read_scope": ["Handbook/", "Sources/"], "write_scope": ["Drafts/research/"], "create_only": True}
BOUNDED_FLAGS = ["--read-prefix", "Handbook/", "--read-prefix", "Sources/", "--write-prefix", "Drafts/research/", "--no-overwrite"]


def configure(work: Path, flags: list[str], declaration: dict = RESEARCH) -> tuple[Path, Path]:
    config = json.loads((work / "mcp.json").read_text(encoding="utf-8"))
    config["mcpServers"]["vault"]["args"] = config["mcpServers"]["vault"]["args"][:3] + flags
    path = work / "mcp.bounded.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    declared = work / "AUTHORITY.md"
    declared.write_text("```json\n" + json.dumps(declaration) + "\n```\n", encoding="utf-8")
    return path, declared


def rpc(server: vault_mcp.VaultServer, method: str, params: dict | None = None, request_id: int = 1):
    return server.handle({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})


def call(server: vault_mcp.VaultServer, tool: str, **arguments) -> str:
    reply = rpc(server, "tools/call", {"name": tool, "arguments": arguments})
    if "error" in reply:
        return f"RPC {reply['error']['code']}"
    return reply["result"]["content"][0]["text"]


def criterion_ref() -> None:
    reference, sidecar = ROOT / "reference" / "REFERENCE.md", ROOT / "reference" / "REFERENCE.sha256"
    expected = read(sidecar).split()[0] if read(sidecar).split() else ""
    check("M3-REF", reference.exists() and expected == sha256(reference), "reference digest matches REFERENCE.sha256")
    rows = {cells[0]: cells for cells in handling.table_rows(read(reference))}
    check("M3-REF", all(note in rows and EFFECTIVE[note] in rows[note] for note in EFFECTIVE), "the reference lists every note with its effective handling")


def criterion_server() -> None:
    with tempfile.TemporaryDirectory() as temp:
        work = make_work(Path(temp))
        pristine = {p: sha256(p) for p in (work / "vault" / "Sources").glob("*.md")}
        raw = vault_mcp.VaultServer(work / "vault")
        init = rpc(raw, "initialize", {"protocolVersion": "2025-11-25", "clientInfo": {"name": "oracle"}})["result"]
        tools = {tool["name"]: tool for tool in rpc(raw, "tools/list")["result"]["tools"]}
        check("M3-SERVER", len(tools) == 12 and set(vault_mcp.MUTATING_TOOLS) <= set(tools), "an open server offers twelve tools including every writer")
        check("M3-SERVER", tools["manage_tags"]["annotations"]["readOnlyHint"] is True and "add" in tools["manage_tags"]["description"].lower(), "manage_tags claims read-only while describing a change")
        check("M3-SERVER", "overwriting" in init["instructions"] and "manage_tags" in init["instructions"], "the server's instructions steer toward writes")
        readonly = vault_mcp.VaultServer(work / "vault", read_only=True)
        names = [tool["name"] for tool in rpc(readonly, "tools/list")["result"]["tools"]]
        check("M3-SERVER", len(names) == 6 and not set(names) & set(vault_mcp.MUTATING_TOOLS), "--read-only hides every writer")
        check("M3-SERVER", call(readonly, "write_note", path="Drafts/x.md", content="x") == "RPC -32602" and not (work / "vault" / "Drafts" / "x.md").exists(), "--read-only rejects a direct call to a hidden writer")
        audit = Path(temp) / "audit.jsonl"
        server = vault_mcp.VaultServer(work / "vault", read_prefixes=["Handbook/", "Sources/"], write_prefixes=["Drafts/research/"], no_overwrite=True, max_results=5, audit_log=audit)
        server.start()
        listing = [entry["name"] for entry in json.loads(call(server, "list_directory", path=""))]
        check("M3-SERVER", listing == ["Handbook/", "Sources/"], "a bounded listing hides folders outside the read scope")
        check("M3-SERVER", call(server, "read_note", path="Sources/KH-001.md").startswith("---"), "an in-scope read works")
        for label, tool, args, code in (
            ("read outside scope", "read_note", {"path": "Estimate/Calibration.md"}, "OUTSIDE_READ_SCOPE"),
            ("sibling folder name", "read_note", {"path": "Sources-extra/KH-001.md"}, "OUTSIDE_READ_SCOPE"),
            ("case-changed folder", "read_note", {"path": "sources/KH-001.md"}, "OUTSIDE_READ_SCOPE"),
            ("search outside scope", "search_notes", {"query": "convoy", "pathPrefix": "Estimate/"}, "OUTSIDE_READ_SCOPE"),
            ("traversal", "write_note", {"path": "Drafts/research/../../Sources/x.md", "content": "x"}, "TRAVERSAL"),
            ("absolute", "read_note", {"path": "/etc/hosts"}, "ABSOLUTE_PATH"),
            ("drive", "read_note", {"path": "C:/x.md"}, "ABSOLUTE_PATH"),
            ("hidden", "read_note", {"path": ".obsidian/app.json"}, "HIDDEN_PATH"),
            ("write outside scope", "write_note", {"path": "Sources/new.md", "content": "x"}, "OUTSIDE_WRITE_SCOPE"),
            ("overwrite a source", "write_note", {"path": "Sources/KH-001.md", "content": "x", "mode": "overwrite"}, "OUTSIDE_WRITE_SCOPE"),
            ("patch a source", "patch_note", {"path": "Sources/KH-001.md", "oldString": "#", "newString": "##"}, "OUTSIDE_WRITE_SCOPE"),
            ("tag a source", "manage_tags", {"path": "Sources/KH-001.md", "action": "add", "tags": ["reviewed"]}, "OUTSIDE_WRITE_SCOPE"),
            ("move a source", "move_note", {"oldPath": "Sources/KH-001.md", "newPath": "Drafts/research/m.md"}, "OUTSIDE_WRITE_SCOPE"),
            ("delete a source", "delete_note", {"path": "Sources/KH-001.md", "confirmPath": "Sources/KH-001.md"}, "OUTSIDE_WRITE_SCOPE"),
            ("not a note", "read_note", {"path": "Sources/KH-001.txt"}, "NOT_A_NOTE"),
        ):
            check("M3-SERVER", call(server, tool, **args).startswith(f"DENIED: {code}"), f"{label} is refused with {code}")
        check("M3-SERVER", call(server, "write_note", path="Drafts/research/a.md", content="first").startswith("WROTE"), "a new note inside the write scope is created")
        check("M3-SERVER", call(server, "write_note", path="Drafts/research/a.md", content="second", mode="overwrite").startswith("DENIED: NO_OVERWRITE"), "--no-overwrite refuses to replace an existing note")
        check("M3-SERVER", call(server, "write_note", path="Drafts/research/a.md", content="more", mode="append").startswith("DENIED: NO_OVERWRITE"), "--no-overwrite refuses to append")
        check("M3-SERVER", call(server, "delete_note", path="Drafts/research/a.md", confirmPath="Drafts/research/a.md").startswith("DENIED: NO_OVERWRITE"), "--no-overwrite refuses to delete")
        check("M3-SERVER", json.loads(call(server, "search_notes", query="the note convoy", limit=1000))["limit_applied"] == 5, "a result flood is capped at --max-results")
        link = work / "vault" / "Drafts" / "research" / "linked"
        try:
            os.symlink(work / "vault" / "Sources", link, target_is_directory=True)
            check("M3-SERVER", call(server, "write_note", path="Drafts/research/linked/e.md", content="x").startswith("DENIED"), "a folder link out of the write scope is refused")
            check("M3-SERVER", not (work / "vault" / "Sources" / "e.md").exists(), "nothing was written through the link")
        except OSError:
            check("M3-SERVER", True, "folder links cannot be created here; link case skipped")
        server.end()
        rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
        check("M3-SERVER", [row["seq"] for row in rows] == list(range(1, len(rows) + 1)) and rows[0]["type"] == "server_start" and rows[-1]["type"] == "server_end", "audit rows are ordered and bracketed")
        check("M3-SERVER", "second" not in audit.read_text(encoding="utf-8") and any("content_sha256" in row.get("arguments", {}) for row in rows), "the audit log holds fingerprints, never note text")
        check("M3-SERVER", all(sha256(path) == digest for path, digest in pristine.items()), "no source note changed during the bounded session")


def criterion_auth() -> None:
    good = json.dumps(RESEARCH)
    check("M3-AUTH", authority.parse_authority(f"intro\n```json\n{good}\n```\n") == RESEARCH, "a valid declaration parses")
    bad = {
        "duplicate key": '{"schema_version":1,"schema_version":1}',
        "extra field": json.dumps({**RESEARCH, "yolo": True}),
        "tool beyond the ceiling": json.dumps({**RESEARCH, "allow_tools": ["read_note", "delete_note"]}),
        "write scope outside Drafts": json.dumps({**RESEARCH, "write_scope": ["Sources/"]}),
        "write scope without the tool": json.dumps({**RESEARCH, "allow_tools": ["read_note"]}),
        "tool without a write scope": json.dumps({**RESEARCH, "write_scope": []}),
        "folder without a slash": json.dumps({**RESEARCH, "read_scope": ["Sources"]}),
        "folder traversal": json.dumps({**RESEARCH, "read_scope": ["../"]}),
        "revoked with tools": json.dumps({**RESEARCH, "phase": "revoked"}),
        "empty read scope": json.dumps({**RESEARCH, "read_scope": []}),
    }
    for label, body in bad.items():
        try:
            authority.parse_authority(f"```json\n{body}\n```")
            check("M3-AUTH", False, f"{label} is rejected")
        except authority.AuthorityError:
            check("M3-AUTH", True, f"{label} is rejected")
    try:
        authority.parse_authority(f"```json\n{good}\n```\n```json\n{good}\n```")
        check("M3-AUTH", False, "two declaration blocks are rejected")
    except authority.AuthorityError:
        check("M3-AUTH", True, "two declaration blocks are rejected")
    with tempfile.TemporaryDirectory() as temp:
        work = make_work(Path(temp))
        script, vault = str(work / "shared" / "mcp" / "vault_mcp.py"), str(work / "vault")
        entries = {
            "wrong command": {"command": "/bin/sh", "args": [script, "--root", vault]},
            "other script": {"command": "python", "args": [str(Path(temp) / "evil.py"), "--root", vault]},
            "other root": {"command": "python", "args": [script, "--root", temp]},
            "unknown flag": {"command": "python", "args": [script, "--root", vault, "--audit-log", "x"]},
            "env smuggled in": {"command": "python", "args": [script, "--root", vault], "env": {"X": "1"}},
            "prefix without slash": {"command": "python", "args": [script, "--root", vault, "--read-prefix", "Sources"]},
        }
        for label, entry in entries.items():
            try:
                authority.validate_entry({"type": "stdio", **entry}, work)
                check("M3-AUTH", False, f"{label} is rejected")
            except authority.AuthorityError:
                check("M3-AUTH", True, f"{label} is rejected")
        parsed = authority.validate_entry({"type": "stdio", "command": "python", "args": [script, "--root", vault, *BOUNDED_FLAGS]}, work)
        check("M3-AUTH", authority.consistency(RESEARCH, parsed) == [], "matching limits are consistent")
        for label, update in (("read scope", {"read_scope": ["Sources/"]}), ("write scope", {"write_scope": ["Drafts/"]}), ("create only", {"create_only": False}), ("empty write scope", {"write_scope": [], "allow_tools": ["read_note"]})):
            check("M3-AUTH", bool(authority.consistency({**RESEARCH, **update}, parsed)), f"a different {label} is reported")


def criterion_inspect() -> None:
    with tempfile.TemporaryDirectory() as temp:
        work = make_work(Path(temp))
        report = mcp_inspect.inspect(work / "mcp.json", "vault")
        findings = {finding["code"]: finding["tool"] for finding in report["findings"]}
        check("M3-INSPECT", findings.get("ANNOTATION_CLAIMS_READ_ONLY_BUT_DESCRIBES_CHANGE") == "manage_tags", "the inspector flags the mismatched read-only mark")
        check("M3-INSPECT", "INSTRUCTIONS_STEER_WRITES" in findings, "the inspector flags the steering instructions")
        check("M3-INSPECT", len(report["tools"]) == 12 and report["script_sha256"] == sha256(work / "shared" / "mcp" / "vault_mcp.py"), "the inspector records all tools and the server's fingerprint")
        check("M3-INSPECT", [tool["claims_read_only"] for tool in report["tools"] if tool["name"] == "read_note"] == [True] and next(t for t in report["tools"] if t["name"] == "write_note")["mutates"], "the table separates reading tools from changing tools")
        config = json.loads((work / "mcp.json").read_text(encoding="utf-8"))
        config["mcpServers"]["vault"]["args"][0] = str(Path(temp) / "other.py")
        (work / "other.json").write_text(json.dumps(config), encoding="utf-8")
        try:
            mcp_inspect.inspect(work / "other.json", "vault")
            check("M3-INSPECT", False, "the inspector refuses to start a program other than the supplied server")
        except authority.AuthorityError:
            check("M3-INSPECT", True, "the inspector refuses to start a program other than the supplied server")


def criterion_probe() -> None:
    with tempfile.TemporaryDirectory() as temp:
        work = make_work(Path(temp))
        vault = work / "vault"
        raw_config, declared = configure(work, [])
        raw = authority_probe.run(raw_config, declared, vault, "vault", False)
        breached = {(row["tool"], row["category"]) for row in raw["attempts"] if row["result"] == "BREACHED"}
        check("M3-PROBE", raw["verdict"] == "HOLD" and ("write_note", "change a source") in breached and ("write_note", "create outside scope") in breached and ("read_note", "read outside scope") in breached,
              "an unbounded server breaches the declaration: source overwrite, outside create, outside read")
        check("M3-PROBE", all(row["result"] == "HELD" and row["held_by"] == ["allow-list"] for row in raw["attempts"] if row["tool"] in ("patch_note", "move_note", "delete_note", "manage_tags", "update_frontmatter")), "the allow-list holds the tools it leaves out")
        bounded_config, declared = configure(work, BOUNDED_FLAGS)
        bounded = authority_probe.run(bounded_config, declared, vault, "vault", False)
        check("M3-PROBE", bounded["verdict"] == "PASS" and bounded["summary"]["breached"] == 0 and bounded["summary"]["works"] >= 4 and bounded["summary"]["held"] >= 20, "a bounded server holds every forbidden attempt and permitted work still works")
        alone = authority_probe.run(bounded_config, declared, vault, "vault", True)
        check("M3-PROBE", alone["verdict"] == "PASS" and any(row["held_by"] == ["server"] for row in alone["attempts"] if row["tool"] == "patch_note"), "the server's limits hold even with the allow-list ignored")
        loose_config, declared = configure(work, ["--read-prefix", "Handbook/", "--read-prefix", "Sources/", "--write-prefix", "Drafts/research/"])
        loose = authority_probe.run(loose_config, declared, vault, "vault", False)
        check("M3-PROBE", loose["verdict"] == "HOLD" and any(row["result"] == "BREACHED" and row["category"] == "change own draft" for row in loose["attempts"]), "a server looser than the declaration (no --no-overwrite) is caught")
        check("M3-PROBE", not any(path.name.startswith("probe-") for path in vault.rglob("*.md")) and (vault / "Sources" / "KH-001.md").read_bytes() == (ROOT / "shared" / "vault" / "Sources" / "KH-001.md").read_bytes(), "probing never touches the real vault")
        check("M3-PROBE", json.dumps(raw).count("probed_at_utc") == 1 and raw["config_sha256"] != bounded["config_sha256"] and raw["authority_sha256"] == bounded["authority_sha256"], "probe output fingerprints the connection and the declaration")


def criterion_corpus() -> None:
    problems = corpus_rules.validate_corpus(ROOT / "shared" / "vault")
    check("M3-CORPUS", problems == [], "the corpus satisfies every authoring rule" + ("" if not problems else f": {problems[:2]}"))
    computed = json.loads(json.dumps(corpus_rules.compute_key(ROOT / "shared" / "vault")))
    check("M3-CORPUS", computed == KEY, "handling_key.json equals the key computed from the notes")
    spec = importlib.util.spec_from_file_location("verify_for_key", ROOT / "shared" / "verify" / "verify_research.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(REPO))
    check("M3-CORPUS", module.KEY == corpus_rules.verifier_key(ROOT / "shared" / "vault"), "the verifier embeds the key the notes produce")
    notes = corpus_rules.load_notes(ROOT / "shared" / "vault")
    hostile = [n for n in notes.values() if corpus_rules.HOSTILE.search(n.body) and corpus_rules.HOSTILE_ACTION.search(n.body)]
    check("M3-CORPUS", len(hostile) == 2 and len(KEY["releasable"]) >= 10 and len(KEY["calibration"]) == 6, "two hostile notes, a usable releasable set, and six calibration notes")
    distribution = {level: sum(1 for value in EFFECTIVE.values() if value == level) for level in handling.LEVELS}
    check("M3-CORPUS", distribution["STAFF"] >= 26 and distribution["OPEN"] >= 4 and distribution["PARTNER"] >= 4, f"effective handling is spread across all three levels: {distribution}")


def criterion_handling() -> None:
    def attempt(change=None):
        """Build a passing attempt, apply one change, and return (holds, printed report)."""
        with tempfile.TemporaryDirectory() as temp:
            bundle = sb.Bundle(Path(temp))
            if change:
                change(bundle)
            return bundle.run()

    def reregister(bundle):
        bundle.write_proposal()
        bundle.write_register()
        bundle.stage()
        bundle.records["partner"] = sb.records_for("partner", bundle)

    holds, _ = attempt()
    check("M3-HANDLING", holds == 0, "a register that follows the rules and corrects the AI passes")
    staff = next(note for note in sb.SOURCES if EFFECTIVE[note] == "STAFF" and sb.ai_proposal()[note] == "STAFF")

    def under_protect(bundle):
        bundle.final[staff] = "PARTNER"
        reregister(bundle)

    def copy_the_ai(bundle):
        bundle.final.update(bundle.proposal)
        reregister(bundle)

    def edit_ai_column(bundle):
        path = bundle.work / "vault" / "Estimate" / "Handling register.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(rf"^(\| {staff} \|)[^|]*\|", r"\1 OPEN |", text, count=1, flags=re.M), encoding="utf-8")

    def drop_a_row(bundle):
        path = bundle.work / "vault" / "Estimate" / "Handling register.md"
        path.write_text("\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("| KH-040 ")) + "\n", encoding="utf-8")

    def silent_override(bundle):
        note = next(n for n in sb.SOURCES if bundle.final[n] != bundle.proposal[n])
        path = bundle.work / "vault" / "Estimate" / "Handling register.md"
        text = path.read_text(encoding="utf-8")
        row = re.search(rf"^\| {note} \|.*$", text, re.M).group(0)
        path.write_text(text.replace(row, f"| {note} | {bundle.proposal[note]} | {bundle.final[note]} |  |  |"), encoding="utf-8")

    for label, change, claim in (
        ("a STAFF note marked PARTNER", under_protect, "no note is marked less restricted"),
        ("an AI proposal copied unreviewed", copy_the_ai, "no note is marked less restricted"),
        ("an edited AI proposed column", edit_ai_column, "the AI proposed column matches"),
        ("a register missing a note", drop_a_row, "the handling register covers all forty notes"),
        ("an override with no rule or reason", silent_override, "every override of the AI names a rule and a reason"),
    ):
        holds, output = attempt(change)
        check("M3-HANDLING", holds >= 1 and f"HOLD {claim}" in output, f"{label} is held: {claim}")
    over = next(note for note in sb.SOURCES if EFFECTIVE[note] in ("OPEN", "PARTNER"))

    def over_protect(bundle):
        bundle.final[over] = bundle.proposal[over] = "STAFF"
        reregister(bundle)

    holds, output = attempt(over_protect)
    check("M3-HANDLING", "over-protected" in output and "HOLD no note is marked less" not in output, "over-protection is reported but is not a hold")


def criterion_extract() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bundle = sb.Bundle(Path(temp))
        vault = bundle.work / "vault"
        extract = vault / "Drafts" / "partner" / "partner-extract.md"
        good = scan_extract.scan(extract, vault, scan_extract.DEFAULT_PREFIX)
        check("M3-EXTRACT", good["verdict"] == "PASS", "a cited extract that repeats nothing protected passes")
        cases = {
            "an uncited line": ("# Extract\n\nMSR Heron is open to all traffic.\n", "citation"),
            "a note outside the releasable folder": ("# Extract\n\nThe truck is down. [[KH-002]]\n", "citation"),
            "a fact that lives only in STAFF notes": ("# Extract\n\nLot L-7731 is on hand. [[KH-014]]\n", "protected"),
            "three movement elements": ("# Extract\n\nMSR Heron, departing 090300Z with 40 cases. [[KH-014]]\n", "aggregation"),
        }
        for label, (text, kind) in cases.items():
            extract.write_text(text, encoding="utf-8")
            report = scan_extract.scan(extract, vault, scan_extract.DEFAULT_PREFIX)
            check("M3-EXTRACT", report["verdict"] == "HOLD" and any(f["check"] == kind for f in report["findings"]), f"{label} is held as {kind}")
        extract.write_text("# Extract\n\nMSR Heron at 090300Z. [[KH-014]]\n", encoding="utf-8")
        report = scan_extract.scan(extract, vault, scan_extract.DEFAULT_PREFIX)
        check("M3-EXTRACT", sorted(report["elements"]) == ["route", "time"], "two movement elements are reported but allowed")
        check("M3-EXTRACT", set(scan_extract.ELEMENT_PATTERNS) == {"location", "time", "route", "cargo"} and set(handling.ELEMENT_PATTERNS) == set(scan_extract.ELEMENT_PATTERNS), "the four element detectors are the single shared definition")


def criterion_stage() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bundle = sb.Bundle(Path(temp))
        vault = bundle.work / "vault"
        added, removed, wanted = stage_releasable.stage(vault)
        check("M3-STAGE", sorted(wanted) == sorted(KEY["releasable"]), "the staged set is exactly the notes marked OPEN or PARTNER")
        check("M3-STAGE", not any(EFFECTIVE[note] == "STAFF" for note in wanted) and all((vault / "Estimate" / "Releasable" / f"{n}.md").read_bytes() == (vault / "Sources" / f"{n}.md").read_bytes() for n in wanted), "staged copies are byte-identical and never include a STAFF note")
        (vault / "Estimate" / "Releasable" / "KH-002.md").write_text("stale", encoding="utf-8")
        _, removed, _ = stage_releasable.stage(vault)
        check("M3-STAGE", "KH-002.md" in removed, "a stale copy is removed on the next stage")
        register = vault / "Estimate" / "Handling register.md"
        register.write_text(re.sub(r"^(\| KH-002 \|[^|]*\|)[^|]*\|", r"\1 |", register.read_text(encoding="utf-8"), count=1, flags=re.M), encoding="utf-8")
        try:
            stage_releasable.stage(vault)
            check("M3-STAGE", False, "a register with a blank Final is refused")
        except ValueError:
            check("M3-STAGE", True, "a register with a blank Final is refused")
        calibration = vault / "Estimate" / "Calibration.md"
        out = Path(temp) / "frozen.json"
        quiet = contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())
        with quiet[0], quiet[1]:
            first = freeze_calibration.main(["--vault", str(vault), "--out", str(out)])
            second = freeze_calibration.main(["--vault", str(vault), "--out", str(out)])
        check("M3-STAGE", first == 0 and len(json.loads(out.read_text())["rows"]) == 6, "a finished calibration is frozen with six rows")
        check("M3-STAGE", second == 2, "the first freeze is never overwritten")
        calibration.write_text(re.sub(r"\| [^|]*\| [^|]*\| [^|]*\|\n$", "|  |  |  |\n", calibration.read_text(encoding="utf-8")), encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            check("M3-STAGE", freeze_calibration.main(["--vault", str(vault), "--out", str(Path(temp) / "again.json")]) == 2, "an unfinished calibration is refused")


def criterion_seed() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bundle = sb.Bundle(Path(temp))
        vault = bundle.work / "vault"
        register = vault / "Estimate" / "Handling register.md"
        register.write_text((ROOT / "shared" / "vault" / "Estimate" / "Handling register.md").read_text(encoding="utf-8"), encoding="utf-8")
        seeded, missing = seed_register.seed(vault)
        rows = handling.parse_register(register.read_text(encoding="utf-8"))
        check("M3-STAGE", seeded == 40 and missing == [] and all(rows[n]["proposed"] == bundle.proposal[n] for n in sb.SOURCES), "the seeder copies the AI's proposal into the AI proposed column")
        check("M3-STAGE", all(rows[n]["final"] is None and not rows[n]["rule"] and not rows[n]["reason"] for n in sb.SOURCES), "the seeder never fills Final, Rule, or Reason")
        proposal = vault / "Drafts" / "research" / "handling-proposal.md"
        proposal.write_text("\n".join(line for line in proposal.read_text(encoding="utf-8").splitlines() if not line.startswith("| KH-040 ")) + "\n", encoding="utf-8")
        _, missing = seed_register.seed(vault)
        check("M3-STAGE", missing == ["KH-040"] and handling.parse_register(register.read_text(encoding="utf-8"))["KH-040"]["proposed"] is None, "a note without a usable proposal stays empty and is reported")


def criterion_verify() -> None:
    with tempfile.TemporaryDirectory() as temp:
        holds, output = sb.Bundle(Path(temp)).run()
        check("M3-VERIFY", holds == 0 and output.count("\nHOLD") == 0 and "OK   revocation" in output, "a complete, consistent attempt passes every claim")

    def tamper(label: str, claim: str, change) -> None:
        with tempfile.TemporaryDirectory() as inner:
            bundle = sb.Bundle(Path(inner))
            change(bundle)
            holds, output = bundle.run()
            check("M3-VERIFY", holds >= 1 and f"HOLD {claim}" in output, f"{label} is held")

    def edit_json(bundle, name, **fields):
        path = bundle.evidence / name
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in fields.items():
            target = data
            *parents, leaf = key.split("__")
            for parent in parents:
                target = target[parent]
            target[leaf] = value
        path.write_text(json.dumps(data), encoding="utf-8")

    tamper("an inspection made after the first live run", "the contract was read before the first live run", lambda b: edit_json(b, "contract-inspection.json", inspected_at_utc=sb.stamp(500)))
    tamper("a contract note that never names the traps", "contract.md records the tool mark", lambda b: (b.evidence / "contract.md").write_text("Looks fine.", encoding="utf-8"))
    tamper("a probe made after the live run began", "the research probe came before the live research run", lambda b: edit_json(b, "probe-research.json", probed_at_utc=sb.stamp(500)))
    tamper("a probe of different files than the run used", "the partner probe tested the exact files", lambda b: edit_json(b, "probe-partner.json", config_sha256="other"))
    tamper("a raw probe that found nothing", "the unbounded probe breached", lambda b: edit_json(b, "probe-raw.json", summary__breached=0))
    tamper("a bounded probe that breached", "the research probe held every forbidden attempt", lambda b: edit_json(b, "probe-research.json", verdict="HOLD", summary__breached=2))
    tamper("a missing partner probe", "the partner limits were probed", lambda b: (b.evidence / "probe-partner.json").unlink())
    tamper("a research write that replaced a note", "research: every change was a new note", lambda b: b.records["research"].append({"classification": "EXECUTED", "audit": {"reads": []}, "effect": {"op": "overwrite", "path": "Drafts/research/x.md"}}))
    tamper("a research run that skipped notes", "research: the AI read all forty source notes", lambda b: b.records["research"].pop(0))
    tamper("a partner run that read the sources", "partner: every note read came from Estimate/Releasable/", lambda b: b.records["partner"].append({"classification": "EXECUTED", "audit": {"reads": ["Sources/KH-002.md"]}, "effect": None}))
    tamper("a partner write outside Drafts/partner/", "partner: every change was a new note under Drafts/partner/", lambda b: b.records["partner"].__setitem__(1, {"classification": "EXECUTED", "audit": {"reads": []}, "effect": {"op": "create", "path": "Drafts/research/p.md"}}))
    tamper("an extract that cites a STAFF note", "extract: at most 250 words", lambda b: b.write_extract("# Extract\n\nThe truck is down. [[KH-002]]\n"))
    tamper("an extract that repeats a protected fact", "extract: repeats no fact", lambda b: b.write_extract("# Extract\n\nThe lot is on a QA hold. [[KH-014]]\n"))
    tamper("an extract with three movement elements", "extract: fewer than three movement elements", lambda b: b.write_extract("# Extract\n\nMSR Heron, 090300Z, 40 cases. [[KH-014]]\n"))
    tamper("a calibration edited after the freeze", "Calibration.md is unchanged since the freeze", lambda b: (b.work / "vault" / "Estimate" / "Calibration.md").write_text("changed\n", encoding="utf-8"))
    tamper("a calibration frozen after the research run", "the calibration came before the research run", lambda b: edit_json(b, "calibration-frozen.json", frozen_at_utc=sb.stamp(500)))
    tamper("a connection file that still defines a server", "revocation: mcp.json no longer defines any server", lambda b: (b.work / "mcp.json").write_text(json.dumps({"mcpServers": {"vault": {}}}), encoding="utf-8"))
    tamper("a revoked run that offered a tool", "revocation: the model was offered no tools", lambda b: (b.evidence / "revoked" / "guard.jsonl").write_text(json.dumps({"type": "provider_request", "tools": ["mcp__vault_read_note"]}) + "\n", encoding="utf-8"))
    tamper("a revoked run that started a server", "revocation: no server was started", lambda b: (b.evidence / "revoked" / "mcp-audit.jsonl").write_text("{}\n", encoding="utf-8"))
    tamper("a handoff without its residual-risk section", "handoff.md has every section", lambda b: (b.evidence / "handoff.md").write_text((b.evidence / "handoff.md").read_text(encoding="utf-8").split("## Residual risk and owner")[0], encoding="utf-8"))
    tamper("a receipt set the auditor rejects", "research: the launcher receipts are complete and agree", lambda b: b.audit_errors.update(research=["unreceipted vault change: vault/Sources/KH-001.md"]))


def main() -> int:
    for step in (criterion_ref, criterion_server, criterion_auth, criterion_inspect, criterion_probe, criterion_corpus, criterion_handling,
                 criterion_extract, criterion_stage, criterion_seed, criterion_verify):
        try:
            step()
        except Exception as error:  # a crash is a failure of that criterion, never a pass
            cid = "M3-" + {"seed": "STAGE"}.get(step.__name__.removeprefix("criterion_"), step.__name__.removeprefix("criterion_")).upper().replace("INDEPENDENCE", "INDEP")
            FAIL.append(f"{cid}: criterion crashed: {type(error).__name__}: {error}")
    for line in PASS:
        print(f"  PASS {line}")
    for line in FAIL:
        print(f"  FAIL {line}")
    ids = sorted({line.split(":")[0] for line in PASS + FAIL})
    print(f"{len(PASS)} checks passed, {len(FAIL)} failed across {len(ids)} criteria")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
