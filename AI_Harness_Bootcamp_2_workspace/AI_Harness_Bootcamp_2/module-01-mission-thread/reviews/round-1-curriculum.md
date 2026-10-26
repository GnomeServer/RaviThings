# Prose panel review — Curriculum

Reviewer kind: language model
Role: Curriculum
Module revision: Reference 048e0cf4b0b83525e3966bc66f4640021d26bd4b5166f1e462bbb8ad7f09e6dd, panel round 1, 2026-08-23
Rubric: reference/GAUNTLET_PROMPT.md categories 1–10, 0–4, acceptance 40/40
Total: 28/40
Result: REJECT

> **This is not the review the Reference requires.** M1-27 specifies a cited-sentence
> panel. This reviewer is a language model asked to read from the curriculum seat. It did
> not sit with a novice, did not run a second-person review-surface check, and cannot
> satisfy M1-27. Every claim about what a learner would not know is inference from the
> text. M1-27 remains UNMEASURED until three people score the prose.

Verified `reference/REFERENCE.sha256` before judging. Hash matches
`048e0cf4b0b83525e3966bc66f4640021d26bd4b5166f1e462bbb8ad7f09e6dd`. Reference frozen
2026-08-14. No amendments.

## Verdict

REJECT — 28/40.

## Scorecard

| Category | 0–4 | Evidence |
|---|---:|---|
| 1. source and mission-thread correctness | **4** | One fictional thread. Orientation defines the eight steps before the lab uses them. |
| 2. recursive depth without domain sprawl | **3** | Stop rule is written. Lab §3–4 still asks a novice to invent child rows without a worked example of one split. |
| 3. claim/source/authority precision | **3** | Authority is taught. Terms `warrant`, `locator`, `SUPERSEDED`, `HOSTILE_TEXT` appear as labels before a first-use gloss in the lab. |
| 4. arithmetic and time correctness | **3** | Six required calculations are named. Lab §5 says use a machine calculator and keep feasibility separate from arithmetic — craft. No worked numeric example, which is correct for M1-ANSWER, and hard on a novice. |
| 5. misleading-source and hostile-content resistance | **3** | Challenge matrix supplies the six attractive errors. “Noticing is insufficient” is in the Reference, not in those words in the lab; the lab does ask for mismatch and needed owner. |
| 6. changed-source dependency reasoning | **3** | Prediction-before-reveal is sequenced. The prediction template names the exact v6 closure (`21:20Z`) before reveal — the change identity is taught, the numeric answer is not. |
| 7. functional decision-surface evidence | **2** | Five questions are the right test. The lab treats a classmate’s use of `review.html` as a gate no one has run. |
| 8. assessment integrity and HOLD behavior | **3** | Practice/protected split is stated. Several sentences explain the course’s grading scheme instead of the craft (`PUBLIC_RUBRIC.md:3`, `MODULE_01_LAB.md:39`, `:66`, `:325`). |
| 9. accessibility, facilitation, and transfer | **2** | Equivalent-path HOLD is written. M1-04 (novice-packet audit), M1-25, M1-26 observed delivery, and M1-28 transfer are unmeasured. |
| 10. parsimony and learner voice | **2** | Opening pages preview the artifact and the assessment. Timebox overruns the session. Completion check is a rubric restatement. |

## Blockers

1. `shared/MODULE_01_LAB.md:3` — “This three-hour session teaches one skill: decide whether a polished AI brief is supported by its sources. The logistics case gives that skill a real shape, but every fact you need is in the supplied packet.” Session-machinery plus marketing cadence (“gives that skill a real shape”).
2. `shared/MODULE_01_LAB.md:7` — “## What you will leave behind” followed by the work-folder tree. Artifact table of contents.
3. `shared/MODULE_01_LAB.md:39` — “It is practice only. Your graded attempt uses a different case and protected checks.” The craft (“this checker is not the grade”) is buried inside course policy.
4. `shared/MODULE_01_LAB.md:42-52` — Timebox sums to 200 minutes. A mentor on the job would give a duration; they would not allocate eight institutional slices that exceed the stated session.
5. `README.md:5` — “This is not a logistics-planning lesson; every domain rule is supplied.” Scoping rationale.
6. `README.md:15-28` — “What you will verify” plus “You will verify one thread deeply instead of reviewing many shallow examples.” Preview and design rationale.
7. `shared/MISSION_THREAD.md:20` — “This module asks whether the supplied evidence supports a `GO` brief at step 6.” The document talking about the module.
8. `assessment/PUBLIC_RUBRIC.md:43-45` — Reassessment policy. Does not survive outside the institution.
9. `shared/NEXT_MODULE.md:9` — “In Module 2, you will decide where that rule belongs…” Companion-handoff lecture.

## Claim and arithmetic audit

Curriculum seat does not re-derive the payload. The six named calculations in `MODULE_01_LAB.md:158-165` match Reference §7. S09 is the wrong-answer brief. No learner-facing file contains `246 kg`, `1,404 kg`, or `3 minutes late`.

## Recursive-depth audit

Stop conditions are listed twice (orientation and lab). Missing: one concrete split of a compound sentence into two ledger rows using only labels, not Cold Lantern answers. Without that, a novice can stall at §3.

## Adversarial results

Handled as curriculum design: similar IDs, receipt/effect, hostile text, producer self-review. Partial: novice without logistics background (M1-04 unmeasured); facilitator leak (runbook forbids it; no observed delivery). Unhandled as a taught recovery: a learner who cannot find a classmate for `MODULE_01_LAB.md:240`.

## Voice result

See voice seat. From this seat the blocking pattern is institutional evaluation jargon and making-of, not fake warmth.

## Parsimony deletion list

- Lab “What you will leave behind” heading and tree (keep the starter command).
- Rubric Reassessment section.
- NEXT_MODULE preview of Module 2’s internal taxonomy (“temporary task direction, reusable instruction…”).
- Completion-check bullets that restate the rubric (`MODULE_01_LAB.md:401-417`).

## Smallest corrections

Reframe lab:3 as purpose for the reader (“You decide whether this brief is supported”). Cut design-rationale lines. Collapse the timebox to 180 minutes or mark overflow. Keep every command block byte-for-byte.

## What would change the verdict

A novice completing the packet without logistics coaching, and a human curriculum reader scoring the prose after the making-of cut. Not a second language-model pass.
