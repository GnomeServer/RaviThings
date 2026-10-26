#!/usr/bin/env python3
"""Check readiness by confirming a successful course_write in this run.

Usage: python3 verify_tool_proof.py <work-dir> <token-file> <evidence-dir>

Resolves shared/run_omp via __file__ (parents[4] from this file to the repository root).
Requires audit_evidence clean + guard executed course_write whose resolved_path
exactly matches proof.resolve() and output_sha256 matches disk bytes.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

try:
    _here = Path(__file__).resolve()
    _root = _here.parents[4]  # case -> shared -> module00 -> AI_Harness_Bootcamp_2 -> root
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from shared.run_omp import audit_evidence
except Exception as exc:
    print(f"HOLD: prerequisite: cannot load audit_evidence ({exc})")
    sys.exit(2)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        print("HOLD: prerequisite: usage is verify_tool_proof.py <work-dir> <token-file> <evidence-dir>")
        return 2

    proof_dir = Path(args[0]).resolve()
    token_file = Path(args[1]).resolve()
    evidence = Path(args[2]).resolve()

    if not token_file.is_file():
        print(f"HOLD: prerequisite: no run token at {token_file}")
        return 2
    token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        print("HOLD: prerequisite: the run token is empty")
        return 2

    proof = proof_dir / "from-omp.txt"
    if not proof.is_file():
        print("FAIL: from-omp.txt — the tool reported success but no file exists here")
        print("READINESS CHECK HOLD")
        return 1

    observed = proof.read_text(encoding="utf-8").strip()
    want = f"omp works {token}"
    if observed != want:
        if observed == "omp works":
            print("FAIL: from-omp.txt — carries no run token, so it cannot be tied to this run")
        else:
            print(f"FAIL: from-omp.txt — content is {observed[:60]!r}; expected {want!r}")
        print("READINESS CHECK HOLD")
        return 1

    if proof.stat().st_mtime < token_file.stat().st_mtime - 1:
        print("FAIL: from-omp.txt — written before this run's token was issued")
        print("READINESS CHECK HOLD")
        return 1

    errors = audit_evidence(evidence)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        print("READINESS CHECK HOLD")
        return 1

    # Audited guard check: exact resolved_path match + hash
    try:
        guard = []
        gp = evidence / "guard.jsonl"
        if gp.is_file():
            for ln in gp.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    guard.append(json.loads(ln))
    except Exception as e:
        print(f"FAIL: guard read error: {e}")
        print("READINESS CHECK HOLD")
        return 1

    disk_sha = _sha256(proof.read_bytes())
    found = False
    for row in guard:
        if row.get("type") == "executed" and row.get("tool") == "course_write":
            rp = row.get("resolved_path", "")
            if Path(rp).resolve() == proof.resolve() and row.get("output_sha256") == disk_sha:
                found = True
                break

    if not found:
        print("FAIL: no executed course_write in guard.jsonl whose resolved_path exactly matches from-omp.txt and hash matches disk")
        print("READINESS CHECK HOLD")
        return 1

    print("PASS: from-omp.txt — correct content, this run's token, receipted by course_write (exact path + hash)")
    print("READINESS CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
