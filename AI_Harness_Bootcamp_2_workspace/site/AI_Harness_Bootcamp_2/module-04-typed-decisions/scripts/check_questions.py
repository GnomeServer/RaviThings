#!/usr/bin/env python3
"""Check the question file before the model runs: the seven supplied questions intact, plus exactly one yes-or-no question of your own.

Usage: check_questions.py <workdir>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_questions.py <workdir>", file=sys.stderr)
        return 2
    work = Path(argv[1]).expanduser().resolve()
    try:
        questions = chalk.load_json(work / "shared" / "controls" / "questions.json")
        own = chalk.check_questions(questions)
    except (OSError, chalk.Hold) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(questions['questions'])} questions; your question is {own}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
