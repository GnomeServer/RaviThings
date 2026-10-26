#!/usr/bin/env python3
"""Oracle: module figure specs render and every Markdown image resolves."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILDER = REPO_ROOT / "scripts" / "render_figures.mjs"


def test_module_figures_check() -> None:
    result = subprocess.run(
        ["node", str(BUILDER), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


if __name__ == "__main__":
    try:
        test_module_figures_check()
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("PASS: module figures --check")
