#!/usr/bin/env python3
"""Run every scoped maintainer gate in separate processes; never call a provider."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path) -> bool:
    print(f"+ {command!r} (cwd={cwd})", flush=True)
    environment = dict(os.environ)
    environment.pop("OPENROUTER_API_KEY", None)
    try:
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"HOLD: required gate could not execute: {error}")
        return False
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    return result.returncode == 0


def main() -> int:
    try:
        course = json.loads((ROOT / "course.json").read_text(encoding="utf-8"))
        modules = course["modules"]
        if [module["id"] for module in modules] != [f"{i:02d}" for i in range(11)]:
            raise ValueError("manifest must enumerate all eleven module IDs in order")
        commands: list[tuple[list[str], Path]] = [
            ([sys.executable, str(ROOT / "tests/test_command_syntax.py")], ROOT),
            ([sys.executable, str(ROOT / "scripts/check_command_syntax.py")], ROOT),
        ]
        for module in modules:
            directory = (ROOT / "AI_Harness_Bootcamp_2" / module["directory"]).resolve()
            if not directory.is_relative_to(ROOT / "AI_Harness_Bootcamp_2") or not directory.is_dir():
                raise ValueError(f"missing or escaped module directory: {directory}")
            module_id = module["id"]
            required = {f"tests/test_module_{module_id}.py"}
            if module_id == "07":
                required = {"tests/test_controls.mjs"}
            elif module_id == "00":
                required.update({"tests/test_checker.py", "tests/test_n8n_local.py"})
            elif module_id == "01":
                required.update({"tests/test_workflow.py", "tests/test_adequacy.py"})
            elif module_id == "05":
                required.add("tests/test_orchestration_guard.mjs")
            elif module_id != "09":
                required.add("tests/test_adequacy.py")
            if module_id == "10":
                required.add("tests/test_readiness.py")
            listed = module["tests"]
            if len(listed) != len(set(listed)) or not required.issubset(listed):
                raise ValueError(f"Module {module_id} manifest omits or duplicates required tests")
            for relative in listed + (["scripts/verify_content.py"] if module_id == "01" else []):
                script = (directory / relative).resolve()
                if not script.is_relative_to(directory):
                    raise ValueError(f"escaped test path: {relative}")
                runner = ["node", "--test"] if script.suffix == ".mjs" else [sys.executable]
                commands.append((runner + [str(script)], directory))
        for relative in ("tests/test_core_standard.py", "tests/test_publication.py", "tests/test_build_course.py", "tests/test_runtime_launcher.py", "tests/test_runtime_guard.py", "AI_Harness_Bootcamp_2/tests/test_module_figures.py"):
            commands.append(([sys.executable, str(ROOT / relative)], ROOT))
        commands.append(([sys.executable, str(ROOT / "scripts/build_course.py"), "--check"], ROOT))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"HOLD: invalid gate manifest: {error}", file=sys.stderr)
        return 1
    failures = sum(not run(command, cwd) for command, cwd in commands)
    if failures:
        print(f"HOLD: {failures} of {len(commands)} required gates failed")
        return 1
    print(f"PASS: all {len(commands)} scoped gates; live/human/platform lanes remain separately evidenced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
