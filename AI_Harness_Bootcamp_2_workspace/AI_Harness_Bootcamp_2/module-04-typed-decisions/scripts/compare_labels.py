#!/usr/bin/env python3
"""Compare your frozen labels with the model's typed answers on the ten-message sample.

Usage: compare_labels.py <workdir> <answers.json> <agreement-output.json>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: compare_labels.py <workdir> <answers.json> <agreement-output.json>", file=sys.stderr)
        return 2
    work, answers_path, target = (Path(value).expanduser().resolve() for value in argv[1:])
    try:
        state = chalk.load_json(work / "out" / "state.json")
        labels = chalk.check_labels(chalk.load_json(work / "out" / "labels.json"), state)
        answers = chalk.load_json(answers_path)["answers"]
        own = chalk.check_questions(chalk.load_json(work / "shared" / "controls" / "questions.json"))
        report = chalk.compare(labels, answers, own)
        report["answers"] = answers_path.name
        chalk.write_new(target, chalk.canonical(report))
    except FileExistsError:
        print(f"HOLD: {target.name} already exists; choose a new output name", file=sys.stderr)
        return 1
    except (OSError, chalk.Hold, KeyError, TypeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    messages = {message["id"]: message for message in state["messages"]}
    print("question      agree  disagree")
    for key, counts in report["questions"].items():
        print(f"{key:<13} {counts['agree']:>5}  {counts['disagree']:>8}")
    for item in report["disagreements"]:
        print(f"\n{item['id']} {item['question']}: you said {item['mine']}, the model said {item['model']} with declared confidence {item['declared_confidence']}")
        print(f"  {messages[item['id']]['from']}: {messages[item['id']]['text']}")
    print(f"\nYour question, {own}, on the sample:")
    for identifier, value in report["own_question"]["sample"].items():
        print(f"  {identifier}: {value['side']} (p={value['p']})  {messages[identifier]['text'][:80]}")
    highest = report["highest_confidence_among_disagreements"]
    print(f"\nAGREEMENT {len(report['questions'])} questions, {len(report['disagreements'])} disagreements, highest declared confidence among disagreements {'none' if highest is None else highest}")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
