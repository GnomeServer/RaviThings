#!/usr/bin/env python3
"""Parse every maintained shell fence, without executing its commands.

The publisher's allowlist supplies pages and raw instructional Markdown. Active
facilitator runbooks and root maintainer procedures are added explicitly. Frozen
evidence, reviews, raster prompts, archives and generated HTML are not inputs.
Bash fences are offered to Bash/zsh and must parse in both. Missing parsers HOLD.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from build_course import inventory

ROOT = Path(__file__).resolve().parents[1]
ROOT_PROCEDURES = ("README.md", "COURSE_MAP.md", "AUTHORING_GUIDE.md", "LEARNING_OBJECTIVES.md", "CASE_FAMILY.md", "MISSION_THREAD_SCENARIOS.md")
LANGUAGES = {"bash": ("bash", "zsh"), "zsh": ("zsh",), "sh": ("sh",), "powershell": ("powershell",)}
OPEN_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})([^\r\n]*)[\r\n]*$")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class Fence:
    file: str
    heading: str
    number: int
    language: str
    opening_line: int
    source_line: int
    body: str


def extract_fences(text: str, filename: str) -> list[Fence]:
    """Lex all fenced payloads, including non-shell fences, before reading headings."""
    lines = text.splitlines(keepends=True)
    headings: dict[int, str] = {}
    result = []
    index = number = 0
    while index < len(lines):
        opening = OPEN_FENCE.match(lines[index])
        if not opening:
            heading = HEADING.match(lines[index])
            if heading:
                level = len(heading[1])
                headings = {key: value for key, value in headings.items() if key < level}
                headings[level] = heading[2]
            index += 1
            continue
        indent, delimiter, info = opening.groups()
        if delimiter[0] == "`" and "`" in info:
            index += 1
            continue
        number += 1
        start = index
        index += 1
        closing = re.compile(r"^ {0,3}" + re.escape(delimiter[0]) + "{" + str(len(delimiter)) + r",}[ \t]*(?:\r?\n)?$")
        while index < len(lines) and not closing.match(lines[index]):
            index += 1
        if index == len(lines):
            raise ValueError(f"{filename}:{start + 1}: unclosed fence #{number}")
        language = info.strip().split(maxsplit=1)[0].lower() if info.strip() else ""
        if language in LANGUAGES:
            body = "".join(line[min(len(indent), len(line) - len(line.lstrip(' '))):] for line in lines[start + 1:index])
            result.append(Fence(filename, " / ".join(headings.values()) or "(top of file)", number, language, start + 1, start + 2, body))
        index += 1
    return result


def maintained_sources(root: Path) -> list[Path]:
    course, _, sources, _ = inventory(root)
    paths = {path for path in sources if path.suffix.lower() == ".md"}
    boot = root / course["source_root"]
    paths.update(boot / module["directory"] / "facilitator/RUNBOOK.md" for module in course["modules"])
    paths.update(root / name for name in ROOT_PROCEDURES)
    for path in paths:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"missing, linked or escaped maintained source: {path}")
    return sorted(paths)


def parser_environment(home: Path) -> dict[str, str]:
    # No provider credentials, imported functions, startup files or user profiles.
    names = ("PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR")
    env = {name: os.environ[name] for name in names if name in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), ZDOTDIR=str(home), LC_ALL="C", POWERSHELL_TELEMETRY_OPTOUT="1", POWERSHELL_UPDATECHECK="Off")
    return env


def run(command: list[str], env: dict[str, str], *, text: str | None = None) -> subprocess.CompletedProcess:
    # Binary stdin preserves LF/heredoc bytes on native Windows too.
    result = subprocess.run(command, input=text.encode("utf-8") if text is not None else None, capture_output=True, env=env, timeout=90)
    return subprocess.CompletedProcess(result.args, result.returncode, result.stdout.decode("utf-8", errors="replace"), result.stderr.decode("utf-8", errors="replace"))


def shell_version(name: str, executable: str, env: dict[str, str]) -> str:
    resolved = Path(executable).resolve()
    if name == "sh" and resolved.name == "dash":
        query = shutil.which("dpkg-query", path=env.get("PATH"))
        if not query:
            raise ValueError("cannot identify dash package version")
        observed = run([query, "-W", "-f=${Version}", "dash"], env)
        version = "dash " + observed.stdout.strip()
    else:
        observed = run([executable, "--version"], env)
        version = observed.stdout.strip().splitlines()[0] if observed.stdout.strip() else ""
    if observed.returncode or not version:
        raise ValueError(f"cannot identify {name} version: {observed.stderr.strip()}")
    return version


def parse_shell(name: str, executable: str, body: str, env: dict[str, str]) -> list[dict]:
    options = ["-f", "-n"] if name == "zsh" else ["-n"]
    result = run([executable, *options], env, text=body)
    if result.returncode == 0:
        return []
    diagnostic = (result.stderr or result.stdout).strip() or f"parser exit {result.returncode}"
    match = re.search(r"(?:line\s+|:\s*)(\d+)(?::|\s|$)", diagnostic)
    return [{"line": int(match[1]) if match else 1, "message": diagnostic}]


# ParseInput has this signature in both Windows PowerShell 5.1 and PowerShell 7.
# Bodies arrive as UTF-8 JSON data; none is passed to Invoke-Expression or &.
POWERSHELL_DRIVER = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$inputRows = ConvertFrom-Json ([IO.File]::ReadAllText($env:COURSE_SYNTAX_INPUT, [Text.Encoding]::UTF8))
$results = @()
foreach ($row in $inputRows) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseInput([string]$row.body, [string]$row.file, [ref]$tokens, [ref]$errors)
    $diagnostics = @()
    foreach ($errorItem in $errors) {
        $diagnostics += @{line=$errorItem.Extent.StartLineNumber; column=$errorItem.Extent.StartColumnNumber; message=$errorItem.Message; error_id=$errorItem.ErrorId}
    }
    $results += @{errors=$diagnostics}
}
ConvertTo-Json -Depth 8 -Compress -InputObject @{version=$PSVersionTable.PSVersion.ToString(); edition=$PSVersionTable.PSEdition; results=$results}
"""


def parse_powershell(executable: str, fences: list[Fence], env: dict[str, str], directory: Path) -> dict:
    source = directory / "powershell-input.json"
    source.write_text(json.dumps([{"body": fence.body, "file": fence.file} for fence in fences], ensure_ascii=False), encoding="utf-8")
    encoded = base64.b64encode(POWERSHELL_DRIVER.encode("utf-16-le")).decode("ascii")
    result = run([executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], {**env, "COURSE_SYNTAX_INPUT": str(source)})
    if result.returncode:
        raise ValueError(f"PowerShell parser invocation failed: {(result.stderr or result.stdout).strip()}")
    parsed = json.loads(result.stdout.lstrip("\ufeff"))
    if len(parsed["results"]) != len(fences) or not parsed["version"]:
        raise ValueError("incomplete PowerShell parser response")
    return parsed


def diagnostic(fence: Fence, parser: str, error: dict) -> dict:
    return {"file": fence.file, "heading": fence.heading, "fence": fence.number, "language": fence.language, "parser": parser,
            "line": fence.source_line + max(1, error["line"]) - 1, "column": error.get("column"), "message": error["message"]}


def check(root: Path, overrides: dict[str, str] | None = None) -> dict:
    overrides = overrides or {}
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "publication allowlist Markdown + active runbooks + root maintainer procedures", "files": [], "parsers": {}, "fence_totals": {}, "parser_totals": {}, "diagnostics": [], "status": "HOLD"}
    fences = []
    for path in maintained_sources(root):
        raw = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        blocks = extract_fences(raw.decode("utf-8"), relative)
        report["files"].append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "fences": len(blocks)})
        fences.extend(blocks)
    report["fence_totals"] = dict(Counter(fence.language for fence in fences))
    counts = Counter()
    with tempfile.TemporaryDirectory(prefix="course-syntax-") as temp:
        directory = Path(temp)
        env = parser_environment(directory)
        for name in ("bash", "zsh", "sh", "powershell"):
            default = ("powershell.exe" if os.name == "nt" else "pwsh") if name == "powershell" else name
            executable = shutil.which(overrides.get(name, default))
            parser = report["parsers"][name] = {"path": str(Path(executable).absolute()) if executable else None, "version": None, "self_check": "HOLD"}
            selected = [fence for fence in fences if name in LANGUAGES[fence.language]]
            counts[name] = 0
            if not executable:
                parser["error"] = f"required parser missing: {overrides.get(name, default)}"
                continue
            try:
                if name == "powershell":
                    probes = [Fence("(parser self-check)", "", 0, "powershell", 1, 1, value) for value in ("Write-Output 'syntax only'", "function broken {")]
                    parsed = parse_powershell(executable, probes + selected, env, directory)
                    parser.update(version=parsed["version"], edition=parsed["edition"])
                    results = [row["errors"] for row in parsed["results"]]
                    if results[0] or not results[1]:
                        raise ValueError("parser did not accept valid and reject invalid self-checks")
                    errors_by_fence = results[2:]
                else:
                    parser["version"] = shell_version(name, executable, env)
                    if parse_shell(name, executable, "true\n", env) or not parse_shell(name, executable, "broken() {\n", env):
                        raise ValueError("parser did not accept valid and reject invalid self-checks")
                    errors_by_fence = [parse_shell(name, executable, fence.body, env) for fence in selected]
                parser["self_check"] = "PASS"
                counts[name] = len(selected)
                for fence, errors in zip(selected, errors_by_fence, strict=True):
                    report["diagnostics"].extend(diagnostic(fence, name, error) for error in errors)
            except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
                parser["error"] = str(error)
    report["parser_totals"] = dict(counts)
    if not report["diagnostics"] and all(parser["self_check"] == "PASS" for parser in report["parsers"].values()):
        report["status"] = "PASS"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path, help="write source-hash-bound JSON receipt to a new external file")
    for name in ("bash", "zsh", "sh", "powershell"):
        parser.add_argument("--" + name, help="explicit parser executable (otherwise resolve from PATH)")
    args = parser.parse_args(argv)
    try:
        report = check(args.root.resolve(), {name: getattr(args, name) for name in ("bash", "zsh", "sh", "powershell") if getattr(args, name)})
        for item in report["files"]:
            print(f"SOURCE {item['path']} sha256={item['sha256']} runnable_fences={item['fences']}")
        for name, item in report["parsers"].items():
            print(f"PARSER {name}: {json.dumps(item, ensure_ascii=False)}")
        for item in report["diagnostics"]:
            print(f"HOLD: {item['file']}:{item['line']} [{item['heading']}] fence#{item['fence']} {item['parser']}: {item['message']}")
        print(f"FENCE TOTALS {report['fence_totals']}; PARSER TOTALS {report['parser_totals']}")
        print(f"{report['status']}: command syntax only; native runtime and Windows PowerShell 5.1 proof remain separately required")
        if args.report:
            with args.report.open("x", encoding="utf-8") as output:
                json.dump(report, output, indent=2, ensure_ascii=False)
                output.write("\n")
        return 0 if report["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"HOLD: command syntax inventory: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
