"""Read a setup guide into the ordered boxes a learner pastes.

Each box keeps the heading it sits under, the **Terminal:** label above it,
its language, its exact text, and the Expected/Stop/Recovery notes after it,
so a run can be reported against what the page promised.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Box:
    line: int  # 1-based line of the opening fence
    lang: str
    code: str
    heading: str
    label: str
    notes: dict[str, str] = field(default_factory=dict)

    @property
    def first(self) -> str:
        return next((part.strip() for part in self.code.splitlines() if part.strip()), "")


NOTE = re.compile(r"\*\*(Expected|Stop|Recovery):\*\*\s*(.*?)(?=\s*\*\*(?:Expected|Stop|Recovery):\*\*|$)", re.S)


def read_boxes(path: str | Path) -> list[Box]:
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    boxes: list[Box] = []
    heading = label = ""
    index = 0
    while index < len(lines):
        text = lines[index]
        if text.startswith("#"):
            heading, label = text.lstrip("#").strip(), ""
        elif text.startswith("**Terminal:"):
            label = text.strip("*").strip()
        elif text.startswith("```"):
            lang = text[3:].strip()
            end = index + 1
            while end < len(lines) and not lines[end].startswith("```"):
                end += 1
            box = Box(index + 1, lang, "\n".join(lines[index + 1:end]), heading, label)
            after = end + 1
            notes: list[str] = []
            while after < len(lines) and not lines[after].startswith(("```", "#", "**Terminal:")):
                notes.append(lines[after])
                after += 1
            for kind, body in NOTE.findall("\n".join(notes)):
                box.notes[kind] = " ".join(body.split())
            boxes.append(box)
            index = end
        index += 1
    return boxes


def box_at(boxes: list[Box], line: int) -> Box:
    for box in boxes:
        if box.line == line:
            return box
    raise KeyError(f"no box opens at line {line}")
