#!/usr/bin/env python3
"""Practice checker for the North Shelf status brief from Harbor Depot to Field Clinic S-3.

What it checks: the brief's shape (a title line, 5 or 6 sections, 500 to 900 words),
the facts the sources confirm, and promises the sources don't make. For each fact, it
finds the sentences about that fact and decides whether the brief states it, denies it,
or says nothing. A number counts only when it's attached to the thing it counts: 27
must be the on-hand count, and 40 the request.

What it can't check: whether the brief answers the clinic's questions, whether a
sentence hints at a pickup or a delivery without the words it looks for, whether the
writing is clear, or whether anyone should send the brief. Those are yours.

It reads wording, not meaning. It can miss a wrong statement phrased in words it
doesn't recognize, and it can flag a correct sentence whose wording it doesn't expect.
Treat each FAIL as a finding to check against the sources, not as a verdict.

Usage:  python3 check_artifact.py draft-v1.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ABBREVIATIONS = {"p.m.": "p<DOT>m<DOT>", "a.m.": "a<DOT>m<DOT>"}


LIST_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
NEGATING_LEAD_IN = re.compile(r"\b(must not|do not|don't|should not|shouldn't)\s*:\s*$", re.I)


def carry_lead_ins(text: str) -> str:
    """Read each list item under 'the clinic must not:' as 'must not ...'.

    A list item on its own ('- treat the window as a time the kits will arrive') would
    otherwise read as a promise, because its negation sits on the line above.
    """
    out, negation = [], ""
    for line in text.splitlines():
        if negation and LIST_ITEM.match(line):
            out.append(LIST_ITEM.sub(f"- {negation} ", line, count=1))
            continue
        if line.strip():
            lead_in = NEGATING_LEAD_IN.search(line)
            negation = lead_in.group(1) if lead_in else ""
        out.append(line)
    return "\n".join(out)


def sentences(text: str) -> list[str]:
    text = carry_lead_ins(text)
    for real, safe in ABBREVIATIONS.items():
        text = text.replace(real, safe)
    parts = re.split(r"(?<=[.!?])\s+|\s*;\s*|\n{2,}", text)
    out = []
    for part in parts:
        for safe, real in ((v, k) for k, v in ABBREVIATIONS.items()):
            part = part.replace(safe, real)
        if part.strip():
            out.append(" ".join(part.split()))
    return out


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w’'-]+\b", text)


AFFIRMED, DENIED, SILENT = "affirms", "denies", "is silent about"


def stance(text: str, topic: str, affirm: str, deny: str) -> tuple[str, str]:
    affirming = ""
    for sentence in sentences(text):
        if not re.search(topic, sentence, re.I):
            continue
        affirmations = list(re.finditer(affirm, sentence, re.I))
        if deny and any(
            not any(a.start() <= d.start() and d.end() <= a.end() for a in affirmations)
            for d in re.finditer(deny, sentence, re.I)
        ):
            return DENIED, sentence
        if affirmations:
            affirming = affirming or sentence
    return (AFFIRMED, affirming) if affirming else (SILENT, "")


def attached(text: str, subject: str, patterns: tuple[str, ...]) -> set[int]:
    found: set[int] = set()
    for sentence in sentences(text):
        if not re.search(subject, sentence, re.I):
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, sentence, re.I):
                found.add(int(match.group(1)))
    return found


PROHIBITED_SENTENCE = (
    "you can expect the kits during the thursday and friday documentation window."
)

CONFIRMED = [
    ("commodity", r"water-treatment kits", r"water-treatment kits", None),
    ("origin", r"harbor depot", r"harbor depot", None),
    ("destination", r"field clinic s-3", r"field clinic s-3", None),
    ("thursday", r"thursday", r"thursday", r"thursday[^.]*(?:cancell?ed|closed|not open)"),
    ("friday", r"friday", r"friday", r"friday[^.]*(?:cancell?ed|closed|not open)"),
    ("documentation hours", r"9:00\s*a\.?m\.?|5:00\s*p\.?m\.?|documentation window",
     r"9:00\s*a\.?m\.?[\s\S]{0,40}5:00\s*p\.?m\.?",
     r"\b(?:8:00|10:00|11:00|12:00|1:00|2:00|3:00|4:00|6:00|7:00)\s*[ap]\.?m\.?"),
    ("contact line", r"call|contact|phone|reach|555-0194", r"555-0194", None),
    ("pen 4", r"pen\s*4", r"pen\s*4", r"pen\s*(?!4\b)\d+"),
    ("custody not release", r"release|custody|staged|counted",
     r"custody(?:\s+is|,)?\s+not a release|custody is not a release|not a release|no lot (?:is |has been )?released|"
     r"releases no lot|not released|is not a release|not yet released|not been released|"
     r"n't (?:been |yet )?released|none (?:is|are|has been|have been) released|nothing (?:is|has been) released",
     r"is a release|are released|has been released|is released|counts as a release"),
    ("release owner", r"ivo marsh", r"ivo marsh", None),
    ("no vehicle", r"vehicle",
     r"(?:no vehicle (?:is|has been) assigned|assigns no vehicle|"
     r"a vehicle (?:is not|has not been) assigned)",
     r"vehicle (?:is|has been) assigned|(?:has|have) assigned (?:a |the )?vehicle|assigned (?:HS-3|the vehicle)|HS-3 (?:is|has been) assigned"),
    ("no permit", r"permit",
     r"(?:no permit (?:is|has been) approved|approves no permit|"
     r"a permit (?:is not|has not been) approved)",
     r"permit (?:is|has been) approved|approved (?:a |the )?permit"),
    ("no receipt", r"receipt",
     r"(?:no receipt (?:is|has been) confirmed|confirms no receipt|"
     r"a receipt (?:is not|has not been) confirmed)",
     r"receipt (?:is|has been) confirmed|confirmed (?:a |the )?receipt"),
    ("supportability unknown", r"supportab|supportability|movement is supportable",
     r"whether (?:the )?(?:movement|it) is supportable is (?:unknown|not known)|supportability (?:is )?(?:unknown|not known)|unknown|not known",
     r"(?:is confirmed|can go|is supportable and ready|supportability is known|movement is supportable)"),
]

REQUEST_SUBJECT = r"request"
REQUEST_PATTERNS = (
    r"asks for (\d+)", r"requested(?: quantity)?[: ]+(\d+)",
    r"request(?:ed)? (?:is )?for (\d+)",
    r"(\d+)\s+water-treatment kits were requested",
    r"request[^.;]{0,40}? for (\d+) water-treatment kits", r"\b(\d+) requested\b",
)
ON_HAND_SUBJECT = r"on[ -]hand|counted and staged|kits (?:on hand|counted)|harbor depot (?:holds|has)"
ON_HAND_PATTERNS = (
    r"(\d+)\s+(?:water-treatment )?kits (?:are )?on hand",
    r"on[ -]hand(?: count)?(?: is| of|:)?\s*(\d+)",
    r"(\d+)\s+water-treatment kits, counted and staged",
    r"(\d+)\s+water-treatment kits (?:counted and staged|are counted and staged)",
    r"has (\d+) water-treatment kits (?:counted and staged|on hand)",
    r"holds (\d+) water-treatment kits",
    r"(\d+) kits are counted and staged",
    r"(\d+) (?:water-treatment )?kits on hand",
)

UNSUPPORTED_CLOCKS = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:a\.?m\.?|p\.?m\.?)", re.I)
ALLOWED_CLOCKS = {"9:00", "5:00"}

DELIVERY_PROMISE = (
    r"expect|pickup|deliver|ship|coming|stage|arrive",
    r"expect the kits|expect receipt|will deliver|will ship|will arrive|"
    r"arrive on thursday|arrive during|ready for pickup|stage the kits|"
    r"treatment water is coming|pickup appointment|delivery promise",
    r"not a pickup|not a delivery|not a dispatch|do not tell|do not stage|"
    r"do not schedule|must not|no delivery promise|carries no delivery|"
    r"\bdo not\b|\bdon't\b|\bmust not\b|\bnever\b|\bshould not\b|\bshouldn't\b|"
    r"\bis not\b|\bisn't\b|\bare not\b|\baren't\b|\bdoes not\b|\bdoesn't\b|"
    r"\bcannot\b|\bcan't\b",
)

PROHIBITED_DISTRIBUTION = (
    r"\bforward (?:this|it)\b|\bpost (?:it|this)\b|\bpass (?:this|it) (?:along|on)\b|"
    r"\bshare (?:this|it)\b|\bsend (?:this|it) to (?:every|all|your)\b|\btell everyone\b|"
    r"radio station|press release|public bulletin|social media|neighborhood list|"
    r"every household|door to door|noticeboard|notice board|operations list"
)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def run(text: str) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    title = re.search(r"(?m)^# ", text) is not None
    checks.append(("title line", title, "present" if title else "no # title line"))
    sections = len(re.findall(r"(?m)^## ", text))
    checks.append(("section count", sections in (5, 6), f"the brief has {sections} sections"))
    n = len(words(text))
    checks.append(("word count 500-900", 500 <= n <= 900, f"the brief has {n} words"))

    for name, topic, affirm, deny in CONFIRMED:
        if affirm is None:
            ok = re.search(topic, text) is not None
            checks.append((name, ok, "present" if ok else "not found in the draft"))
            continue
        verdict, sentence = stance(text, topic, affirm, deny or r"(?!x)x")
        checks.append((name, verdict == AFFIRMED,
                       "stated" if verdict == AFFIRMED
                       else f"the draft {verdict} it: {sentence[:90] or '(no sentence mentions it)'}"))

    requested = attached(text, REQUEST_SUBJECT, REQUEST_PATTERNS)
    checks.append(("requested 40", requested == {40},
                   "40 kits requested" if requested == {40}
                   else f"the draft attaches {sorted(requested) or 'no number'} to the request, not 40"))

    on_hand = attached(text, ON_HAND_SUBJECT, ON_HAND_PATTERNS)
    checks.append(("on-hand 27", on_hand == {27},
                   "27 kits on hand" if on_hand == {27}
                   else f"the draft attaches {sorted(on_hand) or 'no number'} to on-hand, not 27"))

    prohibited = PROHIBITED_SENTENCE in _normalized(text)
    checks.append(("prohibited sentence", not prohibited,
                   "absent" if not prohibited
                   else "the draft contains the sentence that turns the window into a promise"))

    hs3_assigned = False
    hs3_sentence = ""
    for sentence in sentences(text):
        if not re.search(r"HS-3", sentence):
            continue
        if re.search(r"not assigned|n't assigned|not been assigned|n't been assigned|unassigned|no vehicle|does not assign|doesn't assign|assigns no", sentence, re.I):
            continue
        if re.search(r"assign", sentence, re.I):
            hs3_assigned = True
            hs3_sentence = sentence
            break
    checks.append(("HS-3", not hs3_assigned,
                   "not assigned" if not hs3_assigned
                   else f"the draft assigns HS-3: {hs3_sentence[:80]}"))

    topic, affirm, deny = DELIVERY_PROMISE
    promised = ""
    for sentence in sentences(text):
        if not re.search(topic, sentence, re.I):
            continue
        if re.search(affirm, sentence, re.I) and not re.search(deny, sentence, re.I):
            promised = sentence
            break
    checks.append(("no delivery promise", not promised,
                   "not promised" if not promised
                   else f"the draft promises movement: {promised[:80]}"))

    go = re.search(r"\bGO\b", text)
    checks.append(("no GO", go is None,
                   "absent" if go is None else "the draft calls the movement a GO"))

    invented = [m.group(1) for m in UNSUPPORTED_CLOCKS.finditer(text)
                if m.group(1) not in ALLOWED_CLOCKS]
    checks.append(("no invented clock time", not invented,
                   "none" if not invented
                   else f"the source packet does not contain a clock time of {sorted(set(invented))}"))

    distributed = re.search(PROHIBITED_DISTRIBUTION, text, re.I)
    checks.append(("no prohibited distribution", distributed is None,
                   "stays with the clinic supply team" if distributed is None
                   else f"the brief directs wider distribution: {distributed.group(0)!r}"))

    return checks


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("draft-v1.md")
    if not path.exists():
        print(f"HOLD: there is no file at {path}")
        return 1
    checks = run(path.read_text(encoding="utf-8"))
    for name, ok, why in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {name} — {why}")
    failed = [name for name, ok, _ in checks if not ok]
    if failed:
        print(f"\nHOLD: {len(failed)} mechanical requirement(s) failed; this is practice only")
        return 1
    print("\nPASS: mechanical requirements passed; this is practice only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
