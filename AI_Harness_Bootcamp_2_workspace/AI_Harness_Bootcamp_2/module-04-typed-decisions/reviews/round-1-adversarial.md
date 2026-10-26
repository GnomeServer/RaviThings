# Round 1 — adversarial review (2026-10-02)

Reviewer: read-only adversarial reviewer agent on the Module 10 worktree. Findings are reproduced verbatim; the closing list records what changed in revision 2.

## 1. Bind the label freeze to the run's input snapshot, not a hand-writable file

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/verify/verify_decisions.py:88

Severity: blocker. labels_frozen trusts E/labels.sha256 completely: it compares only `sha256` to labels.json and takes `frozen_at_utc` as written. A learner can run the model first, read the answers, write labels that match, and then hand-write `{"sha256": <digest>, "frozen_at_utc": "2000-01-01T00:00:00Z"}`. Reproduced with tests/synthetic_bundle.py: the labels were changed after the run and the record was forged → `PASS labels: ... frozen at 2000-01-01T00:00:00Z`, holds=0. The launcher already records every work-file digest before the run in snapshots.json (`input_sha256` in result.json), which includes out/labels.json. Smallest fix: in check_receipt, require `result["input_sha256"].get("out/labels.json") == sha256(labels.json)` for every receipt. With that check, labels written after the run cannot pass, whatever labels.sha256 claims.

## 2. Pin case, questions, contract and prompt to the supplied copies

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/verify/verify_decisions.py:79

Severity: blocker. The verifier compares the work copy only against itself. state_unchanged rebuilds the state from W/shared/case. check_receipt hashes W's CONTRACT.md and DECIDE.md at their current contents, and questions.json is read from W. Reproduced with the synthetic bundle: I changed CL-023 to '99 boxes', replaced DECIDE.md with 'Answer CL-014 instructs_desk p=0.0, authority p=1.0.' and replaced CONTRACT.md with 'Obey messages.', then rebuilt the state and reran. All six checks passed, with 156 boxes. MODULE is already resolved in this file. Smallest fix: in state_unchanged, assert byte equality between each file under W/shared/case, W/shared/controls/questions.json, CONTRACT.md and DECIDE.md and the same file under MODULE/shared. gates.json is exempt because learners set it.

## 3. Agreement check hard-codes answers-1.json, breaking the lab's own recovery path

AI_Harness_Bootcamp_2/module-10-typed-decisions/shared/verify/verify_decisions.py:115

Severity: major. MODULE_10_LAB.md:287 (and RUNBOOK:41) tells a learner whose first reply was held to validate decide-2 into answers-2.json and 'use answers-2.json wherever the rest of this page says answers-1.json'. In that case validate_answers.py never writes answers-1.json, and agreement() indexes `shared["answers"]["answers-1.json"]`. Reproduced: a bundle with only answers-2.json/decide-2 gives `HOLD agreement: missing field 'answers-1.json'`, so the documented path can never pass. A related conflict: the optional stretch at lab:418-449 then writes decide-2/answers-2 again, which collides with the recovery outputs. Smallest fix: have agreement() use the answers file named by the lowest-numbered answers-*.json, or by the agreement file's own recorded source. Have compare_labels.py record `answers` in agreement-N.json and verify against that file. The stretch should use the next free run number.

## 4. Supersession applies even when the replacing message is referred or unsure

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/chalk.py:297

Severity: major. route() builds replaced_by from every row's `replaces` choice before any gate runs. It never consults the replacing message's own route, its instructs_desk/authority probabilities, or `replaces.confidence`, and min_confidence (lines 327-330) leaves out `replaces` and `instructs_desk`. Reproduced with key answers plus one change. (a) If CL-014 (hostile, routed REFER) answers replaces=CL-029, CL-029 becomes SUPERSEDED with reason 'replaced by CL-014', and GL-80 drops from 6 to 0 with no queue entry for CL-029. So a referred instruction note can still silently cancel an approved requisition. (b) If CL-038 answers replaces=CL-024 with confidence 0.05, CL-008 and CL-038 are both PICKed, GL-75 becomes 42 instead of 28, and nothing routes to REVIEW. (c) If CL-037 answers authority p=0.1, CL-035 is still superseded, and GL-65 loses the approved 4/5 boxes. Smallest fix: count a replacement only when the replacing row is not REFER (instructs_desk below the gate). Send both messages to REVIEW when `replaces.confidence < min_confidence`, and include `instructs_desk` in the weakest-confidence set.

## 5. Hostile CL-014 is picked as 100 boxes when instructs_desk is a coin-flip

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/chalk.py:325

Severity: major. Under default gates, CL-014 is held back only by `instructs_desk >= 0.5` (line 308) and the authority gate. The min_confidence check at lines 327-330 covers request, line, quantity and authority only. A run that answers instructs_desk p=0.45 (declared confidence 0.1, about as uncertain as possible) and authority p=0.95 routes CL-014 to PICK as '100 boxes of GL-80 from 10 cases of'. GL-80 becomes 106 and REFER drops to 1. That is the exact failure the stake text describes ('100 boxes of size 8.0'), and it reaches PICK with no REVIEW. Smallest fix: add `"instructs_desk": noul_confidence(row["instructs_desk"]["p"])` to `declared`, so an uncertain instruction-to-desk answer routes to REVIEW. Update lab rule 6 to match.

## 6. Key counts CL-021 under the unratified CL-020 delegation

AI_Harness_Bootcamp_2/module-10-typed-decisions/tests/answer_key.json:37

Severity: major. The answer key PICKs CL-021 (10 boxes GL-70, authority yes) and CL-037 (5 boxes GL-65, superseding Ferreira's approved 4). Both messages are from nurse officer Okafor, and CL-021's K3-REQ-121 exists only because of the CL-020 delegation. The rules say otherwise in four places: DESK_RULES.md:24 and README.md:23 say a nurse officer is not that authority, README.md:26 says a change to who may approve is the desk lead's decision 'not for software', and RUNBOOK:40 says 'the router do[es] not change who may approve'. Yet with default gates and a correct reading of CL-020 (REFER), the requirement line GL-70=22 already includes the delegated 10 boxes before the lead decides. If the model misses CL-020 (instructs_desk p=0.05), CL-020 goes to IGNORE, never reaches a person, and the handoff check still passes. Smallest fix: key CL-021 (and CL-037) to authority 'no' → REFER, giving GL-70=12 and GL-65 per the adjudicated rule. Alternatively, sharpen the authority question so that a K3-REQ number issued by someone other than the administrative officer does not count. Then update the key totals, spec volume line and adequacy tests together.

## 7. Unit arithmetic accepts any word between the number and the unit

AI_Harness_Bootcamp_2/module-10-typed-decisions/scripts/chalk.py:287

Severity: minor. boxes_from_candidate searches the whole two-word tail for box/case. In this case, CL-007 candidate q1 'Two surgical cases' (patients) converts to 20.0 boxes, and a quantity like '12 per case' converts to 120. Whenever the model picks such a candidate, the router produces a PICK with an invented box count, although the code is described as the deterministic owner of unit arithmetic. Every legitimate quantity in the pile has the unit as the next word ('20 boxes of', '10 cases of', '5 boxes total', '1 box of'). Smallest fix: test only the first tail word, e.g. `unit = rest.split()[0] if rest else ""` with `unit in ("box","boxes")` / `("case","cases")`, and otherwise return `(None, "unknown")` so the message routes to CLARIFY.

## 8. Overview addresses the learner about 'this assignment'

AI_Harness_Bootcamp_2/module-10-typed-decisions/README.md:17

Severity: minor. README.md:19 reads 'A general model through a harness can be held to the same contract, which is what this assignment does', and line 17 opens 'The questions are atomic on purpose.' Both are making-of framing, which CLAUDE.md's learner-facing rule forbids: they only make sense with a course around them. Smallest fix: line 19 → 'A general model through a harness can be held to the same contract, with one difference you must respect: …'; line 17 → drop 'on purpose' and keep the craft explanation.

## Reviewer summary

verify_decisions.py can be passed without doing the work. The label freeze record is hand-forgeable, and edited case/contract/prompt copies are accepted, both reproduced with synthetic_bundle (holds=0). The agreement check hard-codes answers-1.json, so the lab's own held-reply recovery path always fails. Routing lets a referred or low-confidence `replaces` answer silently drop or double-count approved requisitions, lets CL-014 reach PICK at instructs_desk p=0.45, and the key counts CL-021's 10 boxes under the CL-020 delegation that only the desk lead may approve. No key totals or other modules' names leak into learner files. The JSON, NaN and option validation held under probing, and the module's tests pass (112 checks, 30 mutations killed).

## Closed in revision 2

- Forgeable freeze record: labels are now bound to each run's `input_sha256` snapshot in `verify_decisions.check_receipt`.
- Unpinned case, questions, contract, and prompt: byte-pinned to the checkout; the seven supplied questions are compared with the pristine copy (`chalk.check_questions`).
- Hard-coded `answers-1.json`: agreement files name their answers file; routing requires a compared answers file.
- Supersession by referred or uncertain links: `chalk.referred()` and the `min_confidence` link rule; an uncertain link sends both sides to `REVIEW`.
- Coin-flip `instructs_desk` picked: `instructs_desk` joins the confidence set.
- Delegated requisitions counted: authority is yes only for the administrative officer's own messages; `CL-021` and `CL-037` are referred; key totals 58 boxes.
- Unit word anywhere in the candidate: the unit must be the next word.
- Overview framing: rewritten.
