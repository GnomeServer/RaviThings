# Prose panel review — Adversarial

Reviewer kind: language model
Role: Adversarial
Module revision: Reference 048e0cf4b0b83525e3966bc66f4640021d26bd4b5166f1e462bbb8ad7f09e6dd, panel round 1, 2026-08-23
Rubric: reference/GAUNTLET_PROMPT.md categories 1–10 plus required adversarial cases, 0–4, acceptance 40/40
Total: 29/40
Result: REJECT

> **This is not the review the Reference requires.** M1-27 specifies a cited-sentence
> panel. This reviewer is a language model asked to read from the adversarial seat. It did
> not sit with a novice, did not run a second-person review-surface check, and cannot
> satisfy M1-27. Case results below are packet-and-checker inspections, not observed
> learner failures. M1-27 remains UNMEASURED until three people score the prose.

Verified Reference hash `048e0cf4b0b83525e3966bc66f4640021d26bd4b5166f1e462bbb8ad7f09e6dd`.
Match. Frozen 2026-08-14. No amendments.

## Verdict

REJECT — 29/40.

## Scorecard

| Category | 0–4 | Evidence |
|---|---:|---|
| 1. source and mission-thread correctness | **4** | Near-ID distractors only. No second scenario. |
| 2. recursive depth without domain sprawl | **3** | Stop rule present. A learner can still write a fluent summary row and pass the visible checker if step names and six numbers exist. |
| 3. claim/source/authority precision | **3** | Register schema forces a not-allowed field. Checker does not read it. |
| 4. arithmetic and time correctness | **3** | Visible checker now requires 216, 180, 1404/1,404, 246, 14:50, 14:53 in ledger text. It does not recompute from premises; `12*18=216` with a wrong warrant still passes if the tokens appear. |
| 5. misleading-source and hostile-content resistance | **3** | Fixtures exist. Checker matches challenge headings, not rejection reasons. |
| 6. changed-source dependency reasoning | **3** | Unrelated step-name deltas fail. A semantically unrelated edit inside an allowed Route-window column can pass. |
| 7. functional decision-surface evidence | **2** | Surface is local HTML. Second-person use untested. File presence can still look like completion. |
| 8. assessment integrity and HOLD behavior | **3** | Copying S09 fails several practice numbers (1584, 20:50 MDT). Protected grading is absent. A learner can still paste the six required tokens without understanding. |
| 9. accessibility, facilitation, and transfer | **2** | HOLD on missing access is written. Facilitator leak is a policy line, not a control. |
| 10. parsimony and learner voice | **3** | Packet is one case. Learner prose still explains the course to the course. |

## Blockers

1. Reference §11: “a citation passes without source identity, applicability, and support.” The visible checker accepts any non-empty warrant (`check_work.py` source-trace check). That is allowed for visible practice; describing the checker as proving applicability would be the failure. `MODULE_01_LAB.md:355` currently says it cannot judge interpretation — keep that. Do not strengthen the success line.
2. Reference §11: “any claim of timing, effectiveness, cost, or cross-platform operation is reported without measurement.” PowerShell fences are present and untested end to end. Lab must not claim they were run.
3. `shared/MODULE_01_LAB.md:240` — classmate review-surface gate, unexecuted.
4. `facilitator/RUNBOOK.md:12` — “Run the staff reference calculator and visible checker against staff passing and failing specimens.” On-disk `evidence/specimens/pass` and `fail` are empty. Specimens live only as constructed workdirs in `tests/test_workflow.py`. The runbook points at a path that is not there.

## Claim and arithmetic audit

S09:10 is the attack: 216 ready, 1,584 kg, 20:50 MDT, permit accepted, 15:33 as proof the deadline is met. Packet counters:

- S03 quarantines CR-19/CR-20 → 180 usable, not 216 ready.
- S04 rack 84 kg → 1,404 kg mission payload, not 1,584.
- S05 20:50**Z** → 14:50 MDT; gate 14:53 misses by 3 minutes.
- S06 `PENDING` → not accepted.
- No delivery source → 15:33 is counterfactual if the gate is closed.

Changed v6 repairs only the gate. Permit and delivery still HOLD.

## Recursive-depth audit

A shallow ledger that names eight steps and embeds the six tokens defeats the visible checker. Depth is a human gate (thread walk / claim defense). That split is correct. It is also why 40/40 is unavailable without observed defense.

## Adversarial results

| Required case | Result | Evidence |
|---|---|---|
| Wrong vehicle, two-digit ID (VX-240) | handled | S07; challenge heading; lab §2 near-match line |
| Wrong route, one-digit ID (R-17) | handled | S08; challenge heading; changed-brief R-17 ban in checker |
| Current but irrelevant source | handled | S08 dated same day; authority, not recency |
| Authoritative but superseded source | handled | S05 archived bulletin in the same file |
| Receipt offered as proof of effect | handled | S02:29; S06 accepted-for-processing page |
| Scanned inventory as usable | handled | S02 vs S03; 216 vs 180 |
| Required rack omitted | handled | S04 RR-84; brief’s 1,584 kg is the omit-rack / all-scanned error |
| UTC read as local | handled | S05 states Z; S09 writes 20:50 MDT; checker bans 20:50Z from changed conclusions |
| Source text instructs AI to ignore later sources | handled | S07 SYSTEM OVERRIDE; lab §6 treat-as-data |
| Polished brief, false conclusion | handled | S09 |
| Learner asks producer to verify itself | handled | lab:202; S09 confidence line is the bait |
| Sealed change applied to unrelated fields | partial | step-name guard; column-level semantic dependence unenforced |
| Stale baseline values in changed result | handled | 20:50Z banned from changed ledger, brief, verdict |
| Missing or inaccessible decisive source | partial | accessibility HOLD written; not executed |
| Learner with no logistics background | partial | orientation is short; M1-04 unmeasured |
| Facilitator accidentally reveals the answer | partial | runbook “may not”; no mechanical stop |

Unhandled: none of the sixteen as packet absences. Several are policy-only.

## Voice result

Not the assigned score. Adversarial concern: `MODULE_01_LAB.md:39` and rubric lines that teach the assessment scheme give a learner a map of what is graded versus what is craft.

## Parsimony deletion list

Empty specimen directories under `evidence/specimens/` if they remain. Runbook line that assumes they are populated.

## Smallest corrections

1. Point the runbook at `tests/test_workflow.py` constructed workdirs, or delete the specimen sentence.
2. Cut making-of / assessment-scheme sentences (curriculum list).
3. Leave the visible/protected split and script CLIs unchanged.

## What would change the verdict

Observed thread-walk and claim-defense on an unseen selection, plus a second person on `review.html`. A cleaner runbook path is not enough for 40/40.
