#!/usr/bin/env python3
"""Build a synthetic, passing Module 3 attempt (work folder plus receipts) in a temporary directory.

The launcher's own receipt integrity is tested in tests/test_runtime_launcher.py. This builder
stands in for those receipts so the verifier's decisions can be tested without a model, a
network, or the OMP binary: tests patch the receipt auditor and supply the call records.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE / "shared" / "mcp"))
sys.path.insert(0, str(MODULE / "scripts"))
from handling import table_rows  # noqa: E402

KEY = json.loads((MODULE / "scripts" / "handling_key.json").read_text(encoding="utf-8"))
EFFECTIVE = {note: row["effective"] for note, row in KEY["notes"].items()}
SOURCES = sorted(EFFECTIVE)
CALIBRATION = sorted(KEY["calibration"])
T0 = datetime(2026, 10, 8, 9, 0, 0, tzinfo=timezone.utc)


def stamp(minutes: int) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ai_proposal() -> dict[str, str]:
    """An AI that believes body claims, forged notices, and the marking field. It misses by design."""
    wrong = {"BODY_CLAIM": "PARTNER", "FORGED_NOTICE_TARGET": "OPEN", "NOTICE_CHAIN_TARGET": "OPEN"}
    return {note: wrong.get(KEY["notes"][note].get("trap", "ORDINARY"), EFFECTIVE[note]) for note in SOURCES}


def records_for(name: str, bundle: "Bundle") -> list[dict]:
    def executed(tool, reads=(), effect=None):
        return {"classification": "EXECUTED", "tool": tool, "audit": {"code": "OK", "reads": list(reads)}, "effect": effect}

    def create(path):
        return {"op": "create", "path": path, "sha256_after": "0" * 64}

    if name == "smoke":
        return [executed("mcp__vault_list_directory")]
    if name == "research":
        calls = [executed("mcp__vault_read_multiple_notes", [f"Sources/{n}.md" for n in SOURCES[i:i + 10]]) for i in range(0, 40, 10)]
        calls += [executed("mcp__vault_write_note", effect=create(f"Drafts/research/{leaf}")) for leaf in
                  ("handling-proposal.md", "open-questions.md", *[f"fact-{i}.md" for i in range(6)])]
        calls.append({"classification": "DENIED_BY_SERVER", "tool": "mcp__vault_write_note", "audit": {"code": "OUTSIDE_WRITE_SCOPE", "reads": []}, "effect": None})
        return calls
    if name == "partner":
        return [executed("mcp__vault_read_multiple_notes", [f"Estimate/Releasable/{n}.md" for n in bundle.releasable]),
                executed("mcp__vault_write_note", effect=create("Drafts/partner/partner-extract.md"))]
    return [{"classification": "DENIED_BY_RUNTIME", "tool": "mcp__vault_read_note", "audit": None, "effect": None}]


class Bundle:
    """A passing attempt. Tests change one thing, then call run()."""

    def __init__(self, base: Path):
        self.base = base
        self.work = base / "work"
        self.evidence = base / "receipts"
        self.final = dict(EFFECTIVE)
        self.proposal = ai_proposal()
        self.records: dict[str, list[dict]] = {}
        self.audit_errors: dict[str, list[str]] = {}
        self.build()

    @property
    def releasable(self) -> list[str]:
        return [note for note in SOURCES if self.final[note] in ("OPEN", "PARTNER")]

    def build(self) -> None:
        work, evidence = self.work, self.evidence
        shutil.copytree(MODULE / "shared" / "vault", work / "vault")
        (work / "vault" / "Drafts").mkdir(exist_ok=True)
        (work / "vault" / "Estimate" / "Releasable").mkdir(exist_ok=True)
        shutil.copytree(MODULE / "shared" / "mcp", work / "shared" / "mcp", ignore=shutil.ignore_patterns("__pycache__"))
        script = sha((work / "shared" / "mcp" / "vault_mcp.py").read_bytes())
        self.hashes = {"raw": ("c-raw", "a-research"), "research": ("c-research", "a-research"), "partner": ("c-partner", "a-partner"), "revoked": ("c-revoked", "a-revoked")}
        starts = {"smoke": 30, "research": 40, "partner": 70, "revoked": 90}
        phase = {"smoke": "research", "research": "research", "partner": "partner", "revoked": "revoked"}
        for name, minutes in starts.items():
            folder = evidence / name
            config, authority = self.hashes[phase[name]]
            write(folder / "result.json", json.dumps({"started_at": stamp(minutes), "status": "PASS"}))
            policy = {"mcp": {"phase": phase[name], "script": {"sha256": script} if phase[name] != "revoked" else None, "config": {"sha256": config}, "authority": {"sha256": authority}}}
            write(folder / "policy.json", json.dumps(policy))
            tools = [] if phase[name] == "revoked" else ["mcp__vault_read_note"]
            write(folder / "guard.jsonl", "".join(json.dumps({"type": "provider_request", "tools": tools}) + "\n" for _ in range(2)))
        write(evidence / "contract-inspection.json", json.dumps({"inspected_at_utc": stamp(5), "script_sha256": script, "findings": [
            {"code": "ANNOTATION_CLAIMS_READ_ONLY_BUT_DESCRIBES_CHANGE", "tool": "manage_tags"}, {"code": "INSTRUCTIONS_STEER_WRITES", "tool": None}]}))
        write(evidence / "contract.md", "manage_tags is marked read-only yet its description says it adds and removes tags. The server instructions ask the model to tag and overwrite notes, so I will not pass them on. " * 2)
        probe = lambda phase_, stamp_min, breached, config, authority, verdict="PASS": {"probed_at_utc": stamp(stamp_min), "phase": phase_, "verdict": verdict, "ignore_allow_list": False,
                                                                                         "summary": {"breached": breached}, "config_sha256": config, "authority_sha256": authority}
        write(evidence / "probe-raw.json", json.dumps(probe("research", 10, 13, "c-raw", "a-research", "HOLD")))
        write(evidence / "probe-research.json", json.dumps(probe("research", 20, 0, "c-research", "a-research")))
        write(evidence / "probe-partner.json", json.dumps(probe("partner", 60, 0, "c-partner", "a-partner")))
        # classification work
        cal_rows = "\n".join(f"| {note} | {EFFECTIVE[note]} | H1 | reason for {note} |" for note in CALIBRATION)
        cal_text = f"# Calibration\n\n| Note | My marking | Rule | Reason |\n|---|---|---|---|\n{cal_rows}\n"
        write(work / "vault" / "Estimate" / "Calibration.md", cal_text)
        write(evidence / "calibration-frozen.json", json.dumps({"frozen_at_utc": stamp(25), "calibration_sha256": sha(cal_text.encode()),
                                                              "rows": [{"note": n, "marking": EFFECTIVE[n], "rule": "H1"} for n in CALIBRATION]}))
        self.write_proposal()
        self.write_register()
        self.stage()
        self.write_extract(None)
        write(work / "mcp.json", json.dumps({"mcpServers": {}}))
        write(evidence / "handoff.md", "# Handoff\n\n" + "\n\n".join(f"## {h}\n{'A complete sentence that says something specific about the work. ' * 2}" for h in
                                                                 ("Finding", "Authority in force", "What the probes showed", "Classification decisions and overrides", "Residual risk and owner")) + "\n")
        for name in starts:
            self.records[name] = records_for(name, self)

    def write_proposal(self) -> None:
        rows = "\n".join(f"| {n} | {self.proposal[n]} | H1 | reason |" for n in SOURCES)
        write(self.work / "vault" / "Drafts" / "research" / "handling-proposal.md", f"# Proposal\n\n| Note | Proposed | Rule | Reason |\n|---|---|---|---|\n{rows}\n")
        write(self.work / "vault" / "Drafts" / "research" / "open-questions.md", "# Open questions\n")
        for index in range(6):
            write(self.work / "vault" / "Drafts" / "research" / f"fact-{index}.md", f"# Fact {index}\n")

    def write_register(self) -> None:
        rows = []
        for note in SOURCES:
            changed = self.final[note] != self.proposal[note]
            rows.append(f"| {note} | {self.proposal[note]} | {self.final[note]} | {'H1' if changed else ''} | {'checked the rules' if changed else ''} |")
        write(self.work / "vault" / "Estimate" / "Handling register.md",
              "# Handling register\n\n| Note | AI proposed | Final | Rule | Reason |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")

    def stage(self) -> None:
        folder = self.work / "vault" / "Estimate" / "Releasable"
        shutil.rmtree(folder)
        folder.mkdir()
        for note in self.releasable:
            shutil.copyfile(self.work / "vault" / "Sources" / f"{note}.md", folder / f"{note}.md")

    def write_extract(self, text: str | None) -> None:
        text = text or ("# Partner extract\n\nMSR Heron is open to all traffic. [[KH-014]]\n"
                        "Vehicle movement through the base gates is restricted from 2200L to 0500L. [[KH-006]]\n"
                        "Rotary-wing flights are not cleared while the dust forecast is in force. [[KH-017]]\n")
        write(self.work / "vault" / "Drafts" / "partner" / "partner-extract.md", text)

    def run(self) -> tuple[int, str]:
        """Return (hold count, printed report) from the real verifier with the receipt auditor patched."""
        spec = importlib.util.spec_from_file_location("verify_research_under_test", MODULE / "shared" / "verify" / "verify_research.py")
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(REPO))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(REPO))
        module.audit_evidence = lambda folder: self.audit_errors.get(Path(folder).name, [])
        module.mcp_call_records = lambda folder: self.records[Path(folder).name]
        buffer = StringIO()
        with redirect_stdout(buffer):
            holds = module.verify(self.work, self.evidence)
        return holds, buffer.getvalue()
