# Module 4 facilitator runbook

## What the harness changes

Unaided, in two hours, a clerk reading forty messages totals the gloves by hand, counts a corrected requisition twice because the correction and the confirmation both restate it, takes "2 cases" for two boxes or twenty, and either obeys or quietly drops the note that calls itself approved. With the supplied controls, the model answers seven fixed questions per message and nothing else; the validator refuses any reply that strays from the answer sets; the router applies supersession, the instruction gate, the request gate, usability, authority, and declared confidence in code the learner can read; and the hostile note and the authority change land in a queue only a person may close. The requirement line rests on picked messages the learner can name, and the model's declared confidence is measured against labels the learner wrote before the run.

## Session result

The learner builds the state, writes and freezes labels for ten messages, runs the model once as a read-only decision function, validates 320 typed answers or preserves a held reply, measures agreement on the four labeled questions, adjudicates every disagreement against the desk rules, sets `min_confidence` from the highest declared confidence a wrong answer carried, routes the pile, decides the `REFER`, `REVIEW`, and `CLARIFY` queues, and hands the desk lead a requirement line with the authority change recorded as the lead's decision. The verifier confirms order and consistency; the learner's labels and reading judge the answers.

## Before class

1. Run `python tests/test_module_04.py` and `python tests/test_adequacy.py` from this module's folder and confirm every criterion passes and every mutation is killed.
2. Run `python tests/test_runtime_launcher.py` and `python tests/test_runtime_guard.py` from the repository's `tests` folder and confirm both pass.
3. Run the lab once on your own machine with a live key. Keep the `decide-1` receipt: its `response.md` shows what the pinned model actually returned, and `compare_labels.py` against your own labels shows which questions it got wrong and with what declared confidence. Those are the examples you will use at minute 60.
4. Confirm each learner's process-local OpenRouter key is set, with its per-key ceiling, before the first live run. One run costs well under a dollar; the optional second run doubles it.
5. Confirm `tests/answer_key.json` is not in any learner download: run `python shared/prepare_work.py 04 <tmp>` from the repository and list the folder.

## Tuesday delivery route

Module 4 is the third Tuesday block, about two and a half hours. Pacing marks below count minutes from the start of the block, exclude breaks, and are approximate planning guides: follow the learners' progress, not the clock. The break falls after the comparison has been printed and before adjudication, roughly 80 minutes in; learners save `agreement-1.json` and step away.

| Roughly (minutes in) | Action and result |
|---|---|
| 0–10 | A chat answer versus a typed answer: show one message, ask the room for a route, then ask the seven questions one at a time. Learner can say why the broad question hides five judgments and why code combines them. |
| 10–30 | Prepare the work copy and enter the key, read `DESK_RULES.md`, build the state, read the question file, add one question of your own, and check the file. `state.json` holds forty messages and 68 candidates; `check_questions.py` passes. |
| 30–50 | Label the ten sample messages and freeze them. `labels.sha256` exists before any run. |
| 50–65 | Run the decision function once and validate; if the reply is held, run again into `decide-2`. A validated `answers-N.json` exists, or both receipts are held with their causes recorded. |
| 65–75 | Read an agreement table live with your own receipt: a disagreement where the model was right, one where it was wrong, and the declared confidence on each. Learner can state the rule for setting `min_confidence` from a measurement. |
| 75–110 | Compare, break about 80 minutes in with the comparison printed, adjudicate every disagreement in `adjudication.md`, set the gates, route, and read the routing table. A routing attempt exists whose gates match the measurement. |
| 110–140 | Decide the three queues, write the handoff, run the verifier. Six `PASS` lines or a documented `HOLD`, and a handoff with all six sections. |
| 140–150 | What the requirement line proves and what it does not: the picked messages, the authority change that only the lead may decide, the delegated requisitions waiting on it, and the ten-message sample's limits. Learner can name what a second run would add. |

## Coaching boundary

- Do not give the routes, the requirement line, or the key's totals. Point to the desk rule that decides a disagreement and let the learner apply it.
- When a learner's labels disagree with the model and the learner was wrong, the frozen file stays as it is; the correction goes in `adjudication.md`. A learner who edits `labels.json` after the freeze will see the verifier hold `labels`; explain why that hold is the point.
- When `CL-020` reaches a learner, the question is not whether Okafor's signature counts but who decides that it does. The two requisitions Okafor signed under it, `CL-021` and `CL-037`, route to `REFER` because the authority question counts only the administrative officer's own messages; the handoff must record all three as the desk lead's decision, with the boxes the line gains if the lead ratifies the delegation. The clerk and the router do not change who may approve.
- A held first reply (prose around the document, a candidate the message does not have) is an observation, not a failure of the learner. The second run goes into `decide-2`; the first stays.
- A learner who wants to raise the request gate or lower `min_confidence` must point at the disagreement that justifies it. The default gates are a starting point, not a rule.

## Common problems

- `EXIT=2` with an OMP prerequisite error: the verified latest-release installation is missing, unusable, or reporting an invalid version. Restore setup and record the actual `omp --version` output before starting a fresh attempt.
- `HOLD: ... keys differ from the question set`: the model added or dropped a key. Keep the receipt; run again into `decide-2`.
- The validator reports a candidate the message does not have: the model typed a quantity instead of choosing one. This is the behavior the candidate design exists to catch; show the class the held line.
- `HOLD routing: ... route again after changing gates`: the learner edited `gates.json` after the last routing. Route as the next attempt number.
- The handoff holds on a queued message: the learner left a `CLARIFY` row out. `routing-N.csv` lists them.
- Agreement is high and no disagreement carried high confidence: the learner may keep `min_confidence` at `0.7` and must say in the handoff that ten messages cannot establish a rate. That is a correct result, not a missing one.
- `HOLD state: ... differs from the supplied copy`: the learner edited a case file, the contract, the prompt, or a supplied question. Only `gates.json` and the learner's own question are theirs to change; restore the file from the checkout.
- `HOLD answers: ... labels written after a run do not count`: the labels on disk when the run started differ from the frozen ones. The launcher's input snapshot is the evidence; start a fresh attempt.

## Operational readiness notes

See Module 00 facilitator runbook for shared staff operational procedures, T-relative schedule, privacy-safe register, platform matrix, and evidence collection. This module: labels frozen before model answers/adjudication; ten-message sample limits stated in handoff.

Record machine, source hashes, outcomes, and HOLDs for the published controls. No blind provider retry.
