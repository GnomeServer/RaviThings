#!/usr/bin/env python3
"""Compare two validated runs of the same questions: where did the typed answers change?

Usage: compare_runs.py <answers-a.json> <answers-b.json>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402

def side(key: str, answer: dict):
    if "p" in answer:
        return chalk.yes_no_side(answer["p"])
    return answer.get("choice", answer.get("score"))


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: compare_runs.py <answers-a.json> <answers-b.json>", file=sys.stderr)
        return 2
    try:
        first = {row["id"]: row for row in chalk.load_json(Path(argv[1]))["answers"]}
        second = {row["id"]: row for row in chalk.load_json(Path(argv[2]))["answers"]}
        if list(first) != list(second):
            raise chalk.Hold("the two runs do not cover the same messages")
    except (OSError, chalk.Hold, KeyError, TypeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    total = 0
    questions = [key for key in next(iter(first.values())) if key != "id"]
    print("question       flips  messages")
    for key in questions:
        flipped = [identifier for identifier in first if side(key, first[identifier][key]) != side(key, second[identifier][key])]
        total += len(flipped)
        print(f"{key:<14} {len(flipped):>5}  {', '.join(flipped) or '-'}")
    print(f"STABILITY {len(first)} messages, {len(questions)} questions, {total} flipped answers out of {len(first) * len(questions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
