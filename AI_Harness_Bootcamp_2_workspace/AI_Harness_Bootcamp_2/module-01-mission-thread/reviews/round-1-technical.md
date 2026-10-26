# Prose panel review — Technical

Reviewer kind: language model
Role: Technical
Module revision: Reference 048e0cf4b0b83525e3966bc66f4640021d26bd4b5166f1e462bbb8ad7f09e6dd, panel round 1, 2026-08-23
Rubric: reference/GAUNTLET_PROMPT.md categories 1–10, 0–4, acceptance 40/40
Total: 31/40
Result: REJECT

> **This is not the review the Reference requires.** M1-27 specifies a cited-sentence
> panel. This reviewer is a language model asked to read from the technical seat. It did
> not sit with a novice, did not run a second-person review-surface check, and cannot
> satisfy M1-27. Every claim about what a learner would do is inference from the text.
> M1-27 remains UNMEASURED until three people score the prose.

Verified `reference/REFERENCE.sha256` against `reference/REFERENCE.md` before judging:
`048e0cf4b0b83525e3966bc66f4640021d26bd4b5166f1e462bbb8ad7f09e6dd`. Match. No amendments.

## Verdict

REJECT — 31/40.

## Scorecard

| Category | 0–4 | Evidence |
|---|---:|---|
| 1. source and mission-thread correctness | **4** | S01–S09 plus sealed v6 form one mission, one vehicle, one route. S02 table is 12×18 kits; S03 releases CR-09–CR-18 only; S06 page 2 is `PENDING`. |
| 2. recursive depth without domain sprawl | **4** | Lab §4 and `MISSION_THREAD.md:47-53` state the stop rule. No second mission or cargo family. |
| 3. claim/source/authority precision | **4** | Source register columns include `allowed_use` and `not_allowed_to_prove`. S02:29 and S06:9 deny the uses the brief needs. |
| 4. arithmetic and time correctness | **4** | `scripts/compute_thread.py --json` reproduces Reference §7: 216, 180, 1320, 1404, 246, 14:50 MDT, 14:53 MDT, −3 min. S09:10 is false on mass, zone, and permit. |
| 5. misleading-source and hostile-content resistance | **3** | Challenge headings and S07 `SYSTEM OVERRIDE` are present. Rejection quality is human-scored; the visible checker only sees headings. |
| 6. changed-source dependency reasoning | **3** | Prediction template and freeze-before-reveal are in the lab. Allowed-delta enforcement is mechanical for step name, not for semantic dependence. |
| 7. functional decision-surface evidence | **2** | `render_review.py` exists. No second person used `review.html`. M1-17 is untested. |
| 8. assessment integrity and HOLD behavior | **3** | Rubric and custody separate visible from protected. No protected case is in the tree. Visible checker now requires HOLD plus practice numbers; it still cannot score warrants. |
| 9. accessibility, facilitation, and transfer | **2** | `ACCESSIBILITY.md:25` fails closed to HOLD. Assistive-technology operation and observed delivery are untested. |
| 10. parsimony and learner voice | **2** | Lab timebox sums to 200 minutes against a 180-minute session. Learner pages still contain making-of and assessment-machinery sentences (see blockers). |

## Blockers

1. `shared/MODULE_01_LAB.md:42-52` — Timebox rows sum to 200 minutes. Reference §9 budgets a 3-hour session and 2 hours of learner operation. A novice who treats the table as the plan overruns the session before handoff.
2. `shared/MODULE_01_LAB.md:232-240` — The lab requires another class member to answer five questions from `review.html`. That second-person check was not run. Reporting it as ready would be a Reference §11 unmeasured-operation claim.
3. `shared/MODULE_01_LAB.md:3` — “This three-hour session teaches one skill: decide whether a polished AI brief is supported by its sources.” Making-of. The sentence exists because there is a session.
4. `README.md:28` — “You will verify one thread deeply instead of reviewing many shallow examples.” Design rationale for scoping.
5. `assessment/PUBLIC_RUBRIC.md:3` — “You see this rubric before practice. The graded case changes identifiers, values, source order, and distractors.” Institutional assessment machinery in a learner-facing file.

## Claim and arithmetic audit

Baseline, recomputed from the packet (not from S09):

| Claim | Premises | Result | S09 |
|---|---|---|---|
| Scanned kits | S02: 12 totes × 18 kits | 216 | states 216, then calls them ready |
| Usable kits | S03: CR-09–CR-18 = 10 totes × 18 | 180 | “All 216 kits are ready” |
| Released mass | 10 × 132 kg (S02 gross) | 1,320 kg | omitted |
| Mission payload | 1,320 + 84 kg rack (S04) | 1,404 kg | “cargo weighs 1,584 kg” (12 × 132, no rack) |
| Margin | 1,650 − 1,404 | 246 kg | “within 1,650 kg” on the wrong mass |
| All-scanned load | 12 × 132 + 84 | 1,668 kg, 18 kg over | not stated |
| v5 closure | S05 20:50Z, MDT = UTC−6 | 14:50 MDT | “open until 20:50 MDT” |
| Earliest gate | 14:05 + 20 + 28 | 14:53 MDT | durations copied, zone wrong |
| Gate margin | 14:50 − 14:53 | −3 min | not stated |
| Clinic if admitted | 14:53 + 40 | 15:33 MDT | stated as achievable ETA |
| Permit | S06 registry `PENDING` | not authorized | “has been accepted” |
| Delivery / effect | no source after 14:05 | not yet occurred | “requirement and deadline are met” |

Changed source (staff fixture, not opened in this review as a learner reveal): v6 moves closure to 21:20Z = 15:20 MDT; gate margin becomes +27 min; permit and delivery stay unresolved; verdict stays HOLD.

## Recursive-depth audit

The eight named steps and the stop list in `MODULE_01_LAB.md:144-150` reach a valid stop. Child-row instruction is present. No required expansion past a source fact, calculation, named assumption, HOLD, or human decision. Depth is specified; whether a novice actually stops is unmeasured.

## Adversarial results

See the adversarial seat for the full case list. From this seat: packet fixtures exist for wrong vehicle, wrong route, receipt/effect, UTC/local, hostile instruction, and stale v5. Execution of those rejections is human. The visible checker now fails a missing 216 and a leftover 20:50Z in the changed ledger; it does not fail a wrong warrant.

## Voice result

Not the assigned score. Making-of and rubric-facing sentences are blockers above. M1-27 is UNMEASURED.

## Parsimony deletion list

- `shared/MODULE_01_LAB.md:7-37` “What you will leave behind” tree restates the starter output. Keep the command; the preview tree is optional.
- Lab timebox rows that push the session past 180 minutes.

## Smallest corrections

1. Cut or reframe the making-of sentences in README, lab, and rubric.
2. Make the timebox sum to the 180-minute session, or mark the extra 20 minutes as optional overrun, without changing commands.
3. Do not claim the review-surface procedure has been executed.

## What would change the verdict

A human technical reader completing the lab once, a second person using `review.html`, and a timebox that fits the session. Language-model reread after a prose fix does not.
