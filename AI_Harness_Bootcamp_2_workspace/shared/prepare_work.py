#!/usr/bin/env python3
"""Create an external, non-overwriting Module 02–10 exercise work folder."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REFORMATION = Path(__file__).resolve().parents[1]
SHARED = {
    "02": ("case", "controls"), "03": ("vault", "mcp", "prompts"), "05": ("case", "controls", "prompts", "agents"),
    "06": ("case", "controls"), "07": ("batch",),
    "08": ("case", "controls"), "09": ("case", "controls"),
    "10": ("case", "controls", "baseline"), "04": ("case", "controls", "prompts"),
}
SCRIPTS = {
    "02": ("second_brain.py",), "03": (), "05": ("orchestrate.py", "orchestration_evidence.py"), "06": ("blue_gauge.py",),
    "07": ("check_sheet.py",), "08": (),
    "09": (), "10": ("local_ai.py", "check_package.py", "check_readiness.py"),
    "04": ("chalk.py", "build_state.py", "check_questions.py", "label_template.py", "freeze_labels.py", "validate_answers.py", "compare_labels.py", "route.py", "compare_runs.py"),
}
MODULE_07_DOWNLOADS = (
    "shared/batch/wave1.csv",
    "shared/SHEET_RULES.md",
)
EXCLUDED = {"figures", "__pycache__", "staff", "reference", "reviews", "evidence", "tests", "facilitator", "history", "assessment", "ACCESSIBILITY.md", "PUBLIC_RUBRIC.md", "CUSTODY_CONTRACT.md"}


def excluded(name: str, module_id: str) -> bool:
    return name in EXCLUDED or name.startswith((".", "MODULE_", "graded-", "answer-key")) or name.endswith((".pyc", ".pyo")) or (module_id == "09" and name == "verify_safeguards.py")


def require_regular(path: Path, boundary: Path) -> None:
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(boundary.resolve()):
        raise ValueError(f"missing, linked, or escaped required source: {path}")


def target_path(module_id: str, relative: Path) -> Path:
    """Where a published source file lands in the work folder."""
    if module_id == "03" and relative.parts[:2] == ("shared", "vault"):
        return Path("vault", *relative.parts[2:])
    return relative


def prepare_module_03(stage: Path, dest: Path) -> None:
    """Create the vault's empty working folders and the two connection files the lab edits."""
    for folder in ("vault/Drafts", "vault/Estimate/Releasable"):
        (stage / folder).mkdir(parents=True, exist_ok=True)
    template = stage / "shared/mcp/mcp.template.json"
    inside_json = json.dumps(str(dest))[1:-1]
    (stage / "mcp.json").write_text(template.read_text(encoding="utf-8").replace("{{WORK}}", inside_json), encoding="utf-8")
    shutil.copyfile(stage / "shared/mcp/AUTHORITY.template.md", stage / "AUTHORITY.md")


MODULE_06_CONTROLS = ("PATTERNS.json", "patterns.mjs", "patterns.extension.mjs", "panels.mjs", "OMP_INSTRUCTIONS.md")


def prepare(module_id: str, destination: Path, root: Path = REFORMATION) -> Path:
    if module_id not in SHARED:
        raise ValueError("module-id must be exactly two digits, 02–10")
    requested = destination.expanduser().absolute()
    if requested.exists() or requested.is_symlink():
        raise FileExistsError(f"destination already exists: {requested}")
    dest = requested.resolve()
    repository = root.resolve().parent
    if dest.is_relative_to(repository) or repository.is_relative_to(dest):
        raise ValueError(f"destination must not overlap the repository: {dest}")
    modules = list((root / "AI_Harness_Bootcamp_2").glob(f"module-{module_id}-*"))
    if len(modules) != 1 or modules[0].is_symlink() or not modules[0].is_dir():
        raise ValueError(f"expected one real Module {module_id} directory")
    module = modules[0]
    copies: list[tuple[Path, Path]] = []
    for name in SHARED[module_id]:
        subtree = module / "shared" / name
        if not subtree.is_dir() or subtree.is_symlink():
            raise ValueError(f"missing or linked required input directory: {subtree}")
        if module_id == "07":
            continue
        for directory, dirs, files in os.walk(subtree, followlinks=False):
            parent = Path(directory)
            dirs[:] = [entry for entry in dirs if not excluded(entry, module_id)]
            for entry in dirs:
                if (parent / entry).is_symlink():
                    raise ValueError(f"linked input directory: {parent / entry}")
            for entry in files:
                if excluded(entry, module_id):
                    continue
                source = parent / entry
                require_regular(source, module)
                copies.append((source, target_path(module_id, source.relative_to(module))))
    if module_id == "07":
        for relative in MODULE_07_DOWNLOADS:
            source = module / relative
            require_regular(source, module)
            copies.append((source, Path(relative)))
    for name in SCRIPTS[module_id]:
        source = module / "scripts" / name
        require_regular(source, module)
        copies.append((source, Path("scripts") / name))
    if module_id == "06":
        for name in MODULE_06_CONTROLS:
            require_regular(module / "shared/controls" / name, module)
    if module_id == "10":
        source = module / "shared/PACKAGE.md"
        require_regular(source, module)
        copies.append((source, Path("shared/PACKAGE.md")))
    # Validation precedes every destination mutation. A staging failure never
    # leaves an apparently prepared work folder.
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".course-prepare-", dir=dest.parent) as temporary:
        stage = Path(temporary) / "work"
        (stage / "shared").mkdir(parents=True)
        (stage / "scripts").mkdir()
        (stage / "out").mkdir()
        for source, relative in copies:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if module_id == "03":
            prepare_module_03(stage, dest)
        if dest.exists() or dest.is_symlink():
            raise FileExistsError(f"destination already exists: {dest}")
        # Reserve the destination exclusively; never let POSIX rename replace an
        # empty folder that appeared after preflight.
        dest.mkdir()
        try:
            for child in stage.iterdir():
                child.rename(dest / child.name)
        except OSError:
            # Keep the incomplete attempt rather than erase an unexpected edit.
            raise ValueError(f"copy interrupted; preserve {dest} and choose a new destination")
    return dest


def next_arguments(module_id: str) -> list[str]:
    python = str(Path(sys.executable).resolve())
    if module_id == "02":
        return [python, "scripts/second_brain.py", "initialize", "--work", "."]
    if module_id == "06":
        return [python, str(REFORMATION / "AI_Harness_Bootcamp_2/module-06-decision-model/scripts/blue_gauge.py"), "start", "--work", "."]
    if module_id == "03":
        return [python, "shared/mcp/mcp_inspect.py", "--config", "mcp.json"]
    if module_id == "05":
        return [python, "scripts/orchestrate.py", "inspect", "--work", "."]
    if module_id == "07":
        return []
    if module_id == "08":
        code = 'from pathlib import Path; print(Path("shared/case/LEGEND.txt").read_text(encoding="utf-8"))'
    elif module_id == "10":
        code = 'from pathlib import Path; print(Path("shared/case/model-card.json").read_text(encoding="utf-8"))'
    else:
        folder = "shared/case"
        code = f'from pathlib import Path; print("\\n".join(p.as_posix() for p in sorted(Path("{folder}").rglob("*")) if p.is_file()))'
    return [python, "-c", code]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module_id")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        work = prepare(args.module_id, args.destination)
    except FileExistsError as error:
        print(f"HOLD: {error}")
        return 1
    except (OSError, ValueError) as error:
        print(f"HOLD: {error}; correct the prerequisite and use a new destination")
        return 2
    if args.module_id == "07":
        print(f"PASS: created {work}")
        print("Next: open your local n8n editor in the browser and follow the Module 7 lab.")
        print(f"Upload {work / 'shared/batch/wave1.csv'} through the agent workflow's current Test URL.")
        print(f"Keep {work / 'shared/SHEET_RULES.md'} open while checking the spreadsheet.")
        print("Keep both workflows unpublished. Download the spreadsheet from the tool's run.")
        print(f"Retain the unchanged download under a unique name in {work / 'out'}, then run scripts/check_sheet.py on it.")
        return 0
    command = next_arguments(args.module_id)
    ps_quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    shell_quote = lambda value: "'" + str(value).replace("'", "'\"'\"'") + "'"
    print(f"PASS: created {work}")
    print("Next (Bash/zsh, ordinary user):")
    print(f"cd {shell_quote(work)} && " + " ".join(shell_quote(part) for part in command))
    print("Next (PowerShell, ordinary user):")
    print(f"Set-Location -LiteralPath {ps_quote(work)} -ErrorAction Stop")
    if command[1] == "-c":
        print("@'\n" + command[2] + "\n'@ | & " + ps_quote(command[0]) + " -")
    else:
        print("& " + " ".join(ps_quote(part) for part in command))
    print("if ($LASTEXITCODE -ne 0) { throw 'HOLD: the next command failed; preserve this attempt.' }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
