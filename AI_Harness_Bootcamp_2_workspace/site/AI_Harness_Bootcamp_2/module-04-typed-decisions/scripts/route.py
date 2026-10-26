#!/usr/bin/env python3
"""Route every message from the typed answers and your gates; write the routing table and the requirement line.

Usage: route.py <workdir> <answers.json> <attempt-number>
Writes out/routing-<n>.csv and out/requirement-<n>.json. It never overwrites an earlier attempt.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 4 or not argv[3].isdigit():
        print("usage: route.py <workdir> <answers.json> <attempt-number>", file=sys.stderr)
        return 2
    work, answers_path = (Path(value).expanduser().resolve() for value in argv[1:3])
    attempt = int(argv[3])
    try:
        state = chalk.load_json(work / "out" / "state.json")
        gates = chalk.load_gates(work / "shared" / "controls" / "gates.json")
        answers = chalk.load_json(answers_path)["answers"]
        rows, summary = chalk.route(state, answers, gates)
        summary["answers"] = answers_path.name
        csv_path = work / "out" / f"routing-{attempt}.csv"
        json_path = work / "out" / f"requirement-{attempt}.json"
        if csv_path.exists() or json_path.exists():
            raise FileExistsError
        chalk.write_routing_csv(csv_path, rows)
        chalk.write_new(json_path, chalk.canonical(summary))
    except FileExistsError:
        print(f"HOLD: attempt {attempt} already exists; use the next number", file=sys.stderr)
        return 1
    except (OSError, chalk.Hold, KeyError, TypeError, StopIteration) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print(f"gates: request {gates['request']}, authority {gates['authority']}, instructs_desk {gates['instructs_desk']}, min_confidence {gates['min_confidence']}")
    print("line   boxes  from")
    for line, value in summary["requirement"].items():
        print(f"{line}  {value['boxes']:>5}  {', '.join(value['from']) or '-'}")
    for name in ("REFER", "REVIEW", "CLARIFY"):
        ids = [row["id"] for row in rows if row["route"] == name]
        print(f"{name}: {', '.join(ids) or 'none'}")
    counts = ", ".join(f"{name} {summary['routes'][name]}" for name in chalk.ROUTES)
    print(f"ROUTED {len(rows)} messages: {counts}; requirement {summary['total_boxes']} boxes")
    print(csv_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
