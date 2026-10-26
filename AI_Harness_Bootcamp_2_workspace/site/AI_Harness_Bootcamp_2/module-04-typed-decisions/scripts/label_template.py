#!/usr/bin/env python3
"""Write out/labels.json: the ten sample messages with blank answers for you to fill in before the model runs.

Usage: label_template.py <workdir>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: label_template.py <workdir>", file=sys.stderr)
        return 2
    work = Path(argv[1]).expanduser().resolve()
    try:
        state = chalk.load_json(work / "out" / "state.json")
        messages = {message["id"]: message for message in state["messages"]}
        rows = []
        for identifier in chalk.SAMPLE_IDS:
            message = messages[identifier]
            rows.append({"id": identifier, "from": message["from"], "text": message["text"],
                         "candidates": [f"{item['id']}: {item['text']}" for item in message["candidates"]],
                         "request": "?", "line": "?", "quantity": "?", "authority": "?"})
        target = work / "out" / "labels.json"
        chalk.write_new(target, chalk.canonical({"schema": chalk.LABEL_SCHEMA, "how": "request and authority: yes or no. line: GL-65, GL-70, GL-75, GL-80, UNSTATED, MIXED, or NONE. quantity: a candidate id such as q1, or NONE.", "labels": rows}))
    except (OSError, chalk.Hold, KeyError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print(f"wrote {len(rows)} sample entries")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
