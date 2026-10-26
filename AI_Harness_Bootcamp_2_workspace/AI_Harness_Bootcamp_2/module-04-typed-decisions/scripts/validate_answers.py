#!/usr/bin/env python3
"""Check the model's reply against the question set, message by message, and save the typed answers.

Usage: validate_answers.py <workdir> <receipt-dir> <answers-output.json>
The receipt directory is one launcher attempt; its response.md is the reply.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: validate_answers.py <workdir> <receipt-dir> <answers-output.json>", file=sys.stderr)
        return 2
    work, receipt, target = (Path(value).expanduser().resolve() for value in argv[1:])
    try:
        state = chalk.load_json(work / "out" / "state.json")
        questions = chalk.load_json(work / "shared" / "controls" / "questions.json")
        result = chalk.load_json(receipt / "result.json")
        if result.get("status") != "PASS":
            raise chalk.Hold(f"{receipt.name} is a held launcher run ({result.get('reason', 'no reason recorded')}); keep it and validate the next passing receipt")
        reply = (receipt / "response.md").read_text(encoding="utf-8")
        document, fenced = chalk.parse_reply(reply)
        answers = chalk.validate_answers(document, state, questions)
        chalk.write_new(target, chalk.canonical({"schema": chalk.ANSWER_SCHEMA, "receipt": receipt.name, "answers": answers}))
    except FileExistsError:
        print(f"HOLD: {target.name} already exists; choose a new output name", file=sys.stderr)
        return 1
    except (OSError, chalk.Hold) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    if fenced:
        print("note: the reply was wrapped in a code fence; the document inside it was accepted")
    print(f"PASS: {len(answers)} messages, {len(answers) * (len(questions['questions']))} typed answers, 0 violations")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
