#!/usr/bin/env python3
"""Scoped maintainer checks for Module 0; setup execution remains separate evidence.

Governing principle: a check that has never failed proves nothing. Every check here
has at least one killing mutation in mutations.py, and test_module_00.py asserts that
the mutation actually kills it. A check with no killing mutation fails C6.

Import surface:
    run(module_root) -> list[Result]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------------------
# Result model

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass(frozen=True)
class Result:
    cid: str
    state: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.state}] {self.cid}: {self.detail}"


class Recorder:
    def __init__(self) -> None:
        self.results: list[Result] = []

    def record(self, cid: str, ok: bool, detail: str, warn_only: bool = False) -> None:
        state = PASS if ok else (WARN if warn_only else FAIL)
        self.results.append(Result(cid, state, detail))

    def check(self, cid: str, ok: bool, ok_detail: str, fail_detail: str) -> None:
        self.record(cid, ok, ok_detail if ok else fail_detail)


# --------------------------------------------------------------------------------------
# File discovery (C1: glob-derived, never a hand-maintained list)

PLATFORM_GLOB = "platforms/*.md"
# Files a learner is told to open, copy, or execute. Maintainer material is excluded by
# directory, so a new learner file is picked up automatically and a new maintainer file
# is not silently scanned as learner prose.
MAINTAINER_DIRS = {"reference", "evidence", "facilitator", "assessment", "tests", "reviews",
                   # Checker test data. Deliberately corrupted drafts, not learner prose --
                   # scanning them as prose reads every planted error as a writing defect.
                   "fixtures", "pass", "fail", "v1-superseded", "v2"}


def module_files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in MAINTAINER_DIRS for part in p.relative_to(root).parts[:-1]):
            continue
        if p.suffix in {".md", ".py", ".sh", ".ps1"}:
            out.append(p)
    return out


def learner_docs(root: Path) -> list[Path]:
    return [p for p in module_files(root) if p.suffix == ".md"]


def learner_scripts(root: Path) -> list[Path]:
    return [p for p in module_files(root) if p.suffix in {".py", ".sh", ".ps1"}]


# --------------------------------------------------------------------------------------
# Fence parsing (C2: every fence, regardless of info string)

FENCE_RE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.M | re.S)


@dataclass(frozen=True)
class Fence:
    path: Path
    line: int
    info: str
    body: str

    @property
    def lang(self) -> str:
        return self.info.strip().lower().split()[0] if self.info.strip() else ""

    @property
    def statements(self) -> list[str]:
        return [ln for ln in self.body.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def fences(paths: list[Path]) -> list[Fence]:
    out = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        for m in FENCE_RE.finditer(text):
            out.append(Fence(p, text[: m.start()].count("\n") + 1, m.group(1), m.group(2)))
    return out


SHELL_LANGS = {"bash", "sh", "zsh"}
PS_LANGS = {"powershell", "pwsh"}
# A fence is "executable" if a learner is meant to run it. `text` blocks count: the
# v1 oracle exempted them and shipped runnable `codex login` inside one.
EXEC_LANGS = SHELL_LANGS | PS_LANGS | {"text", "console"}


# --------------------------------------------------------------------------------------
# Helpers

def section_of(path: Path, line: int) -> str:
    """The nearest '## ' heading above a line."""
    heading = ""
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if i > line:
            break
        if ln.startswith("## "):
            heading = ln[3:].strip()
    return heading


# --------------------------------------------------------------------------------------
# Class A — reachable, runnable, cannot strand the learner

PATH_ASSIGN_RE = re.compile(r"""PATH=["']?([^"'\n]*)["']?""")


def class_a(r: Recorder, root: Path) -> None:
    docs, plats = learner_docs(root), sorted(root.glob(PLATFORM_GLOB))
    fs = fences(docs)

    # A7 — no block can persist an empty PATH element
    empties = []
    for f in fs + [Fence(p, 1, p.suffix[1:], p.read_text(encoding="utf-8")) for p in learner_scripts(root)]:
        for val in PATH_ASSIGN_RE.findall(f.body):
            if "::" in val or val.startswith(":") or val.endswith(":"):
                empties.append(f"{f.path.name}:{f.line}")
    r.check("A7", not empties, "no PATH assignment can contain an empty element",
            f"PATH assignments that can yield '.' on PATH: {sorted(set(empties))[:5]}")

    # A8 — credential entry is alone in its fence, and the read is its last statement
    unsafe = []
    for f in fs:
        if not re.search(r"read\s+-r\s+-s|Read-Host[^\n]*-AsSecureString", f.body):
            continue
        st = f.statements
        if not st or not re.search(r"read\s+-r\s+-s|Read-Host[^\n]*-AsSecureString", st[-1]):
            unsafe.append(f"{f.path.name}:{f.line}")
    r.check("A8", not unsafe, "hidden-input reads end their fence; no pasted line can be captured",
            f"credential reads with following lines in the same paste: {unsafe}")


    # A10 — installer inspection completes before the installer runs.
    # Keyed on the file the download actually produced, not on a list of known installer
    # names: a guide could otherwise suppress this check by renaming the file.
    def token(raw: str) -> str:
        raw = raw.strip().strip("\"'")
        raw = re.sub(r"^\$\{?\w+\}?/", "", raw)          # "$tmp/x.sh" -> "x.sh"
        return raw.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

    DOWNLOAD = re.compile(
        r"(?:curl|wget)\s[^\n]*?(?:-o|--output)\s+(\S+)"          # curl -o FILE
        r"|Invoke-WebRequest\s[^\n]*?-OutFile\s+(\S+)"             # PowerShell
        r"|(?:curl|wget)\s[^\n]*?(?:-O|--remote-name)\b[^\n]*?(\S+/([\w.-]+\.(?:sh|ps1)))"  # -O keeps the remote name
    )
    EXEC = re.compile(r"(?:^|\|\s*|;\s*|&&\s*|\b[A-Z_]+=\S+\s+)(?:bash|sh|zsh|&)\s+(\S+)", re.M)
    # The pager's target may be a variable ($installer) rather than a filename, so match
    # any token on the line rather than requiring a .sh/.ps1 suffix.
    PAGER = re.compile(r"(?:less|more|Get-Content|bat)\b([^\n]*)")

    late = []
    for p in plats:
        text = p.read_text(encoding="utf-8")
        downloaded = {token(next(g for g in m.groups() if g)): m.start()
                      for m in DOWNLOAD.finditer(text)}
        for m in EXEC.finditer(text):
            name = token(m.group(1))
            # Only files this guide downloaded need inspecting. A script the learner got
            # by cloning the repository was reviewed when the repository was reviewed.
            if name not in downloaded:
                continue
            before = text[: m.start()]
            line_no = before.count("\n") + 1
            paged = any(token(t) == name
                        for line in PAGER.findall(before) for t in line.split())
            if not paged:
                late.append(f"{p.name}:{line_no} runs {name} without paging it first")
                continue
    r.check("A10", not late, "downloaded installers are inspected before they run",
            f"execute-before-inspect: {sorted(set(late))[:6]}")

    # A11 — every shell box parses. A box that leaves the shell waiting for more input
    # (a lost closing brace or quote) looks to a learner like a terminal that hangs.
    broken = []
    for f in fs:
        if f.lang not in SHELL_LANGS:
            continue
        done = subprocess.run(["bash", "-n"], input=f.body, capture_output=True, text=True)
        if done.returncode != 0:
            broken.append(f"{f.path.name}:{f.line}: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else 'syntax error'}")
    r.check("A11", not broken, "every shell box parses", f"boxes that don't parse: {broken[:5]}")

    # A12 — PowerShell scripts a learner runs are plain ASCII. Windows PowerShell 5.1 reads a
    # file without a byte-order mark in the ANSI code page, so one curly quote or dash can end
    # a string early and stop the whole script from parsing.
    non_ascii = [str(p.relative_to(root)) for p in learner_scripts(root)
                 if p.suffix == ".ps1" and any(b > 0x7F for b in p.read_bytes())]
    r.check("A12", not non_ascii, "PowerShell scripts are ASCII, so Windows PowerShell 5.1 parses them",
            f"non-ASCII PowerShell scripts: {non_ascii}")


# --------------------------------------------------------------------------------------
# Class B — the acceptance machinery discriminates

def class_b(r: Recorder, root: Path) -> None:
    # B1-B6 — the practice checker's own adequacy test carries these
    adequacy = subprocess.run([sys.executable, str(root / "tests/test_checker.py")],
                              capture_output=True, text=True)
    tail = (adequacy.stdout.strip().splitlines() or ["no output"])[-1]
    r.check("B1-B6", adequacy.returncode == 0,
            f"practice checker adequacy: {tail}",
            f"practice checker adequacy failed: {adequacy.stdout.strip()[-300:]}")

    # B8 — readiness check rejects bad receipts via exit status.
    verifier = root / "shared/case/verify_tool_proof.py"
    with tempfile.TemporaryDirectory() as td:
        pdir = Path(td)
        evidence = pdir / "evidence"
        evidence.mkdir()
        tokf = pdir / "tok.txt"
        tokf.write_text("deadbeef\n")
        proof = pdir / "from-omp.txt"
        # missing
        res = subprocess.run([sys.executable, str(verifier), str(pdir), str(tokf), str(evidence)], capture_output=True, text=True)
        r.check("B8", res.returncode != 0, "rejects missing result", "accepted missing")
        # wrong content
        proof.write_text("some prose about the token\n")
        res = subprocess.run([sys.executable, str(verifier), str(pdir), str(tokf), str(evidence)], capture_output=True, text=True)
        r.check("B8", res.returncode != 0, "rejects wrong content", "accepted wrong content")
        # correct bytes no receipt
        proof.write_text("omp works deadbeef\n")
        now = time.time()
        os.utime(proof, (now, now))
        os.utime(tokf, (now, now))
        res = subprocess.run([sys.executable, str(verifier), str(pdir), str(tokf), str(evidence)], capture_output=True, text=True)
        r.check("B8", res.returncode != 0, "rejects no receipt", "accepted no receipt")
        # stale
        os.utime(proof, (now-10, now-10))
        os.utime(tokf, (now, now))
        res = subprocess.run([sys.executable, str(verifier), str(pdir), str(tokf), str(evidence)], capture_output=True, text=True)
        r.check("B8", res.returncode != 0, "rejects stale", "accepted stale")

# --------------------------------------------------------------------------------------
# Class C — the oracle cannot be defeated by editing a file it does not read

DANGEROUS = {
    r"sudo\s+npm\s+(?:install|i)\b[^\n]*\s-g\b": "sudo global npm",
    r"npm\s+(?:install|i)\b[^\n]*\s-g\b[^\n]*sudo": "sudo global npm",
    r"curl\s[^\n]*(?:--insecure|\s-k\b)": "insecure curl",
    r"chmod\s+-R\s+0?777": "world-writable recursive chmod",
    r"rm\s+-rf\s+(?:~|/\s|\$HOME|[^\n]*(?:AIHB_OCT_2026|AI_Harness_Bootcamp))": "destructive recursive delete",
    r"Set-ExecutionPolicy\s+(?:Unrestricted|Bypass)\s+-Scope\s+(?:LocalMachine|CurrentUser)": "policy bypass",
    r"(?:echo|printf|Write-Output|Write-Host)\s[^\n]*(?:\$\{?(?:XAI|OPENAI|OPENROUTER)_API_KEY|\$env:(?:XAI|OPENAI|OPENROUTER)_API_KEY)": "secret echo",
    r"pacman\s+-Sy(?!u)": "Arch partial upgrade",
    r"(?:cd|clone|--prefix)\s+[^\n]*/mnt/c": "WSL work on the Windows filesystem",
}


def class_c(r: Recorder, root: Path) -> None:
    docs, scripts = learner_docs(root), learner_scripts(root)
    all_files = docs + scripts

    # Local learner files must be scanned. Cross-module navigation is owned by
    # the manifest-driven publication gate and each destination's module gate.
    scanned = {p.resolve() for p in all_files}
    course = json.loads((Path(__file__).resolve().parents[3] / "course.json").read_text(encoding="utf-8"))
    module_entries = {(root.parent / module["directory"] / "README.md").resolve() for module in course["modules"]}
    escaped = []
    for p in docs:
        for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)#]+)\)", p.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            linked = (p.parent / target).resolve()
            if linked in module_entries:
                continue
            if not linked.exists() or linked.is_dir():
                continue
            if linked.suffix in {".md", ".py", ".sh", ".ps1"} and linked not in scanned:
                escaped.append(f"{p.name} -> {linked.name}")
    r.check("C1", not escaped,
            f"scan set derived by glob: {len(all_files)} files, and every linked file is inside it",
            f"files a learner is sent to read that no scan reads: {sorted(set(escaped))[:5]}")

    # C2 — safety scan reads every fence, whatever the info string
    hits = []
    scanned = 0
    for f in fences(docs):
        scanned += 1
        for pat, label in DANGEROUS.items():
            if re.search(pat, f.body, re.I):
                hits.append(f"{label} at {f.path.name}:{f.line}")
    for p in scripts:
        for pat, label in DANGEROUS.items():
            if re.search(pat, p.read_text(encoding="utf-8"), re.I):
                hits.append(f"{label} in {p.name}")
    r.check("C2", not hits, f"{scanned} fences and {len(scripts)} scripts scanned, no dangerous form",
            f"dangerous forms: {hits[:6]}")


# --------------------------------------------------------------------------------------
# Class D — claims match artifacts

def class_d(r: Recorder, root: Path) -> None:
    # REF — the Reference is frozen and the hash matches
    href = root / "reference/REFERENCE.sha256"
    want_hash = href.read_text(encoding="utf-8").split()[0] if href.exists() else ""
    got = hashlib.sha256((root / "reference/REFERENCE.md").read_bytes()).hexdigest()
    r.check("REF", bool(want_hash) and want_hash == got, f"Reference frozen at {got[:12]}",
            f"Reference hash {got[:12]} does not match recorded {want_hash[:12]}")


# --------------------------------------------------------------------------------------


def run(root: Path) -> list[Result]:
    r = Recorder()
    class_a(r, root)
    class_b(r, root)
    class_c(r, root)
    class_d(r, root)
    return r.results


if __name__ == "__main__":
    module = Path(__file__).resolve().parents[1]
    results = run(module)
    for res in results:
        print(res)
    bad = [x for x in results if x.state == FAIL]
    print(f"\n{len(results) - len(bad)} PASS / {len(bad)} FAIL")
    sys.exit(1 if bad else 0)
