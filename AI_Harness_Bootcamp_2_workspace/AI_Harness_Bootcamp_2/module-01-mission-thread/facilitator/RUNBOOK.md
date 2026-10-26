# Module 1 facilitator runbook

## Session result

The learner independently verifies one end-to-end claim. They identify what each source can establish, trace a material claim, recompute deterministic consequences, reject attractive wrong evidence, apply one source change, and leave a bounded verdict and handoff.

Misleading claims to watch for: warehouse receipt offered as usable inventory; accepted-for-processing offered as permit approval; archived bulletin offered as current; R-17 community page offered for R-71; VX-240 note offered for VX-204; instruction embedded inside a source; producer confidence and self-review.

Logistics knowledge outside the packet is not tested. If learners need facts that are not in the packet or orientation, the case is defective.

## Before class
1. Run `python3 scripts/verify_content.py` from the Module 1 directory.
2. The producer rebuttal for practice uses `--fixture` and the sealed fixture (prints exact PRACTICE warning and provenance sidecar); live uses the shared launcher with write-only target. A failed child exit never becomes success.
3. Run the staff reference calculator and visible checker against staff passing and failing specimens. The ledger check prints the baseline arithmetic it scores, one function at a time. Do not hand learners the calculator's full output before they freeze; that output also includes the sealed-change clock.
4. Confirm the sealed practice change is in the facilitator fixtures; prepare decisive checks.
5. Confirm the learner's Module 0 setup; do not reuse Module 0 answers.
6. Keep `SEALED_CHANGE.md` closed until each baseline ledger, prediction, and verdict hash is recorded.
7. Prepare a domain-novice observer to flag any instruction that requires unstated logistics knowledge.
8. Inspect the generated `review.html` at a 390px viewport and 200% zoom. Long identifiers in notes must wrap without widening the page; ledgers may scroll inside their own containers. Check the keyboard decision link and the revealed-source link with JavaScript disabled.

## Route

Clock marks are approximate planning guides: follow the learners' progress, not the clock.

| Roughly | Facilitator action | Learner result |
|---|---|---|
| 0:00–0:15 | Introduce the question, class-only boundary, and eight-step thread | Learner can explain receipt versus release and delivery versus usable effect |
| 0:15–0:35 | Learner confirms packet and source identities | Manifest passes; source register begins |
| 0:35–1:20 | Learner builds and reopens the thread ledger | All eight steps and child claims exist |
| 1:20–1:45 | Learner recomputes and challenges the brief | Calculations and six rejection reasons |
| 1:45–2:05 | Learner writes and inspects corrected brief | Review surface answers five decision questions |
| 2:05–2:20 | Learner freezes baseline verdict and source-change prediction | Hashes and timestamps precede reveal |
| 2:20–2:40 | Release v6; learner updates dependent claims | Preserved baseline and exact changed-source delta |
| 2:40–3:00 | Learner runs two fresh sessions with their own AI: one writes the handoff, the next tests that handoff against the sources only | Receipted handoff, a separate scrutiny session, and the learner's own reading of that scrutiny |

## Coaching boundary

You may:

- define a term already stated in the orientation;
- point to the current step or source file;
- help open a file or run a supplied script;
- ask the learner to state the exact entity, source, or next handoff;
- remind them to preserve baseline work.

You may not supply:

- source authority for a material claim;
- an arithmetic premise, operator, converted time, result, or the distinction between a calculated and feasible arrival;
- the reason a distractor fails;
- the child claim needed to repair a broken thread;
- the fields affected by v6;
- the baseline or changed verdict; or
- wording for the standing rule.

Do not sit in as the second reader of the handoff, and do not ask a classmate to do it. The learner's new session does that check.
If you cross that line, mark the work as guided practice.

## After the two sessions

Do not choose a handoff or a claim for the learner to defend out loud. Step 12 is their model writing `handoff.md` from the files they saved. Step 13 is a new session that sees only that handoff and the source files. You may help them run the supplied commands. You do not supply the scrutiny, and you do not treat either model's text as the verdict.

## Domain-overload check

Stop and inspect the case—not the learner—when:

- more than two learners ask for the same unstated logistics fact;
- domain explanation exceeds 15 minutes;
- arithmetic consumes more than 20 minutes;
- learners cannot explain a source mismatch in ordinary language;
- a logistics expert passes through outside knowledge while a novice cannot locate it in the packet; or
- reviewers cannot attribute a miss to verification rather than domain knowledge.

Record the issue and revise the adapter before the next cohort.

## `HOLD` conditions

Use `HOLD` when a decisive source, accessible view, practice fixture, or review surface is missing or compromised; source identity cannot be stabilized; a material claim lacks support; baseline order is broken; or the learner attempts consequential use.

A well-documented `HOLD` can complete practice. It does not satisfy the module requirements.

## Collect

- source register;
- original and changed thread ledgers;
- challenge matrix;
- corrected brief and review-surface check;
- baseline and changed verdicts;
- baseline hashes and change-release order;
- handoff;
- visible checker output; and
- result or reason for `HOLD`.

Do not collect credentials, private local files, outside operational details, or model chat history unrelated to the case.

## Operational readiness notes

See Module 00 facilitator runbook for shared staff operational procedures, T-relative schedule, privacy-safe register, platform matrix, and evidence collection. This module: baseline/prediction before sealed change; thread walk and claim defense on unseen selection.

Record machine, source hashes, outcomes, and HOLDs for the published controls. No blind provider retry.
