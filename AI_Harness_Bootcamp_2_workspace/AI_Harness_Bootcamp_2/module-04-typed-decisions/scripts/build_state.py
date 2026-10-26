#!/usr/bin/env python3
"""Build out/state.json from the supplied case: catalog, desk rules, forty messages, and the quantity candidates software found.

Usage: build_state.py <workdir>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: build_state.py <workdir>", file=sys.stderr)
        return 2
    work = Path(argv[1]).expanduser().resolve()
    try:
        state = chalk.build_state(work / "shared" / "case")
        target = work / "out" / "state.json"
        chalk.write_new(target, chalk.canonical(state))
    except (OSError, chalk.Hold) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    candidates = sum(len(message["candidates"]) for message in state["messages"])
    print(f"PASS: state.json holds {len(state['messages'])} messages and {candidates} quantity candidates")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
