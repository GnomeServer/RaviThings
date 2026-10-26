# Round 1 — curriculum review (2026-10-02)

Reviewer: read-only curriculum reviewer agent on the Module 10 worktree. Findings are reproduced verbatim; the closing list records what changed in revision 2.

## 1. Match the PO-10 decomposition claim to work the learner actually does

LEARNING_OBJECTIVES.md:37

Major. PO-10 (LEARNING_OBJECTIVES.md:37) and enabling objective 1 (modules/core/10-typed-decisions.md:25) both put "decomposes a desk decision into atomic questions with fixed answer sets" at the head of the mastery claim. The lab never asks for it. The question set is a supplied input (`Consumes: VERIFY:QUESTION_SET`), and the only instruction is "Read the seven questions" (MODULE_10_LAB.md:180). No artifact records which judgment each question isolates, and the handoff has no section for it. This fails the capability-delta and evidence tests: the headline capability is claimed but never practised or evidenced. Smallest fix: reword PO-10 and EO1 to "uses a supplied atomic question set with fixed answer sets and states which judgment each question isolates". Then add one line to the handoff's Agreement and gates section that names, for each of the four labelled questions, the judgment it isolates. The other option is a short step in which the learner splits one broad question into typed ones.

## 2. Fix the recovery path for a held first reply: the verifier hard-codes answers-1.json

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/verify/verify_decisions.py:115

Major. If `decide-1` is held, the lab tells the learner to validate `decide-2` into `out/answers-2.json` and to "use answers-2.json wherever the rest of this page says answers-1.json" (MODULE_10_LAB.md:287). The verifier's `agreement()` does three things. It reads `agreement-1.json`, indexes `shared["answers"]["answers-1.json"]`, and compares the labels only against that file (verify_decisions.py:116-119). With no answers-1.json, `report` catches a KeyError and prints `HOLD agreement: missing field 'answers-1.json'`, so the final check can never reach PASS. The runbook calls a held first reply "an observation, not a failure of the learner" (RUNBOOK coaching boundary). Smallest fix: have `agreement()` pick the agreement file that matches the answers file named in the final `requirement-N.json` (or the lowest-numbered answers file present), not the literal answers-1. The other option is to change the lab's recovery to keep the `-1` output names.

## 3. Move the Chalk Line break to where the route says it falls

AI_Harness_Bootcamp_2/module-10-typed-decisions/facilitator/RUNBOOK.md:21

Major. RUNBOOK.md:21 puts the break "at minute 80, after the first run has been validated and before the comparison is read". The route itself has validation ending at minute 60 and the comparison starting at minute 70 (rows at lines 28-30). At minute 80 the learner is ten minutes into compare and adjudicate, so the break cuts through adjudication. COURSE_MAP.md:67 and the public homepage (AI_Harness_Bootcamp_2/README.md:87) repeat the same false placement, while the clock table puts the break after 80 facilitated minutes (15:20–16:40). Smallest fix: keep the 80/70 clock and describe the break truthfully as "mid-adjudication, after the comparison has been printed" in all three places. The other option is to move it to minute 60: 15:20–16:20, break, 16:30–18:00, with the timetable updated in COURSE_MAP and the homepage.

## 4. Resolve the overlap with PO-03 and the pre-emption of PO-05 and PO-07 created by placing Module 10 in session 5

LEARNING_OBJECTIVES.md:35

Major (progression test). Module 10 now runs as session 5, before Modules 04–09 (COURSE_MAP.md schedule rows). Its claim makes the learner freeze labels before seeing outcomes and measure model answers against them (LEARNING_OBJECTIVES.md:37). PO-05 ("freezes an outcome-blind sample") and PO-07 ("freezes cases, configurations and hard gates before outcomes") still count outcome-blind freezing as new learning, so later modules would re-claim a capability the learner already used in session 5. Separately, PO-03 already owns "judges the assistant's handling classifications against stated rules", which overlaps PO-10's label comparison and adjudication against desk rules. Smallest fix: narrow PO-10's new capability to typed answer sets, mechanical validation, and gates set from measured confidence. Then mark freeze-before-outcome in PO-10 as a stated quality bar and remove it from the new-capability wording of PO-05 and PO-07 (or state it there as assumed knowledge). The other option is to schedule Module 10 after Module 07.

## 5. Define "decision function" at first use

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:16

Minor. The lab's eight bold-defined orientation terms are state, typed question, quantity candidate, yes-or-no, choice, declared confidence, score, and gate. That meets the eight-term target. The module's central term, "decision function", is used from the step list (MODULE_10_LAB.md:16) and as a step heading (line 243), but neither the lab nor the README (line 11) defines it. Only the model-facing CONTRACT.md explains it. Smallest fix: at line 16, or at the opening of the "Run the decision function once" step, add "A **decision function** is a model run that reads given inputs and returns only typed answers, with no prose and no side effects." If that pushes past the eight-term target, fold yes-or-no/choice/score under typed question.

## 6. Remove the calibration and product claim and the assignment frame from the overview

AI_Harness_Bootcamp_2/module-10-typed-decisions/README.md:19

Minor. README.md:19 says "A dedicated decision model returns typed answers with calibrated probabilities as its only output... which is what this assignment does". There are two problems. First, it is an unsupported product-category claim (calibration is asserted, not shown), and it contradicts the module's own scope boundary that it "does not calibrate declared confidence" (core spec). Second, "this assignment" is course framing that would not survive outside the course. Smallest fix: replace the first two sentences with "A general model run through a harness can be held to a typed-answer contract, with one difference you must respect: the confidence it declares is a claim about itself."

## 7. Give the stretch's second run a folder that cannot collide with the recovery run

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:418

Minor. When `decide-1` is held, recovery already writes `E/decide-2` and `answers-2.json` (MODULE_10_LAB.md:287). The optional stretch then tells the learner to run into `E/decide-2` again (line 418 and the following command). The launcher refuses an existing evidence folder with `EXIT=2`, and `compare_runs.py answers-1.json answers-2.json` has no answers-1 to compare. Smallest fix: in the stretch, say "into the next unused `decide-N` folder, and compare your two validated answers files".

## 8. Rebalance the practice rows: setup is under-allocated and the queue/handoff row has slack

AI_Harness_Bootcamp_2/module-10-typed-decisions/facilitator/RUNBOOK.md:26

Minor. Row 10–25 (RUNBOOK.md:26) gives 15 minutes to two preparation blocks, reading DESK_RULES, building the state, reading all seven questions and three answer formats, and tracing candidates for CL-007/014/037. The lab also puts hidden key entry in this section (MODULE_10_LAB.md:104), but the runbook schedules it at 45–60 (line 28). Row 45–60 has no slack for the held-reply path the coaching section expects (a second paid run of 2–4 minutes plus validation). Row 105–140 gives 35 minutes to the queues, which the staff key puts at three messages (2 REFER, 1 CLARIFY), plus the handoff and verifier. Smallest fix: move key entry to row 10–25, or move the lab's key block to just before the run step. Then shift about 5 minutes from 105–140 into 45–60 for a possible decide-2.

## 9. Have the learner inspect the receipt that EO2 claims they read

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/MODULE_10_LAB.md:259

Minor (evidence test). Enabling objective 2 promises "receipts that show what it read and that it wrote nothing", and Check the work says to confirm read-only status from the receipt. After the run, though, the lab only lists the receipt files (MODULE_10_LAB.md:259) and opens `response.md` (line 265). The learner never opens `policy.json` or `events.jsonl` to confirm read-only policy, reads of both files, and no writes. Only the verifier checks this. Smallest fix: after line 265, add one sentence telling the learner to open `policy.json` and `events.jsonl`, confirm write tools are denied and both `out/state.json` and `shared/controls/questions.json` were read, and record that in the handoff's Limits.

## Reviewer summary

Module 10 does not depend on another module's evidence or name another module's case (it links only Module 00 setup), the lab defines eight orientation terms, and no grading language was found. It does have problems. The headline \"decompose\" capability is never practised. The documented held-reply recovery can never pass the verifier, which hard-codes answers-1.json. The break placement contradicts the route in the runbook, the course map, and the homepage. And scheduling the module in session 5 overlaps PO-03 and pre-empts the freeze-before-outcome objectives of PO-05 and PO-07.

## Closed in revision 2

- Decomposition claimed but not practised: the learner adds one yes-or-no question of their own, checked by `check_questions.py` before the paid call, reported by `compare_labels.py`, and named in the handoff; PO-10, enabling objective 1, and the manifest outcomes reworded.
- Recovery path with no `answers-1.json`: agreement and routing follow the named answers file; the recovery variant is tested.
- Break placement: described as after the printed comparison and before adjudication in the runbook, the course map, and the homepage.
- Overlap with PO-03/05/07: PO-10 names rule-based judgment as practiced earlier; PO-05 and PO-07 state the freeze-before-outcome discipline as assumed.
- `decision function` defined at first use.
- Calibration claim removed from the overview.
- Stretch collision: next unused `decide-N` folder.
- Runbook rows rebalanced; key entry moved to the setup row.
- Receipt inspection sentence added after the run.
