# Reference: Module 8 — Control hallucinations

**Revision:** 4  
**Frozen on:** 2026-10-08  
**Scope:** three typed Jev checks, then structured claim checks and a fixed review-and-correction ensemble, on fictional Slope Brief evidence  
**Supersedes:** the 40-pair change-evaluation exercise and 38-call variation/restore stretch; their historical evidence remains historical

## Mastery and progression

Using source verification, typed questions, deterministic predicates, and fixed-flow operation, the learner controls unsupported assertions through a source-bound review-and-correction loop. The learner can handle reviewer error, unanimous unsupported approval, correction regressions, and absent authority without converting any of them into release permission.

The enabling capabilities are composing three typed Jev checks over the whole brief with the questions and gates in one readable file; assigning the appropriate evidence check to each material claim; directing blind review and source-constrained correction while retaining coverage; and adjudicating disagreements and regressions against original evidence. Files and receipts prove the work; creating them is not the mastery claim.

## Source basis

[Jev's introduction](https://docs.typesafe.ai/introduction) describes state plus atomic typed questions and directly structured results. Its [confidence documentation](https://docs.typesafe.ai/confidence) distinguishes returned distributions and derived confidence. The [citation check](https://docs.typesafe.ai/cookbooks/citation_check), [Noul primitive](https://docs.typesafe.ai/primitives/noul), [line-by-line search](https://docs.typesafe.ai/cookbooks/semantic_find), and [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade) pages, with OpenRouter's [verified cascade](https://openrouter.ai/docs/cookbook/evaluate-and-optimize/jev-verified-cascade), supply the three check shapes, checked on 2026-10-08. Those checks run live through OpenRouter as `jev-1.13` with `OPENROUTER_API_KEY`, from code the coordinator writes under `W/checks`. No run here measures their calibration; the gates (0.8 and 0.6 for support confidence, 0.7 and 0.5 for wrongness, 0.7 and 0.35 for existence) are starting values taken from the cookbooks for comparison, not validated thresholds.

The runtime is the existing shared launcher with the latest stable OMP release and `openrouter/anthropic/claude-sonnet-4.6`, using only `OPENROUTER_API_KEY`. Each attempt records its actual OMP version. It generates JSON, which the supplied Python checker validates. Neither provider-enforced structured output nor Jev probability semantics is claimed.

## Independent supplied case

The movement is heater-fuel cans from Ridge Depot to Clinic T-8 on SB-4. Source packets PC-01, PC-02, and PC-03 preserve the original source bytes. The seven-claim draft is authored practice data, not a recorded provider output.

| Claim | Case and kind | Starting condition |
|---|---|---|
| C01 | PC-03 mass | `2040 kg` without a source locator; the authoritative payload record states `2233 kg`. |
| C02 | PC-01 time | `13:05` without its zone. |
| C03 | PC-01 time | `13:05 UTC`, confusing the local clock with UTC. |
| C04 | PC-03 citation | An SB-5 assertion attached to the SB-4 payload record. |
| C05 | PC-01 gate | Supported full gate passage with its authoritative locator. |
| C06 | PC-02 mass | Supported `2222 kg` with its authoritative locator. |
| C07 | PC-03 authority | An assertion of dispatch release that the packet does not establish. |

The corrector must preserve C05 and C06. Gate and citation fields are extractive complete-source passages, not free paraphrases. Mass and clock fields require exact sourced values and labels with the correct locator. A missing authorization becomes an explicit null value and null locator, not a denial or an invented approval. The PC-01 `2255 kg` near-miss versus `2211 kg` payload example is a separate worked counterexample, not another registered claim.

No other module's files, verdicts, or scenario facts are consumed. This fictional exercise authorizes no movement.

## Typed checks before freeze

Step 1 finds each claim's value in its own packet in code, after whitespace normalization, and records every containing locator, its authoritative flag, and whether it equals the claim's locator; no model is called. Step 2 sends each found claim with the full cited record (or the authoritative record of that kind when no locator is cited) to Jev with one choice question, supports, contradicts, or says nothing, and compares two gates on saved answers. Steps 3 and 4 send each of the seven claims with every packet record and four Noul questions phrased so that yes means wrong, keep the highest, and compare two gates without a call. Step 5 sends only the flagged claims to the pinned chat model through chat completions for a proposed value or null with a packet locator, records usage, and saves the result as a proposal. Steps 6 and 7 send each claim's question with every packet record as choice options plus one Noul existence question, then join the files into `summary.md` headed as checks. Nothing under `W/checks` is a frozen input, a child input, or a disposition; the freeze and audit code do not read it.

## Execution contract

Invoke `AI_Harness_Bootcamp_2/module-08-change-eval/scripts/hallucination.py` from the repository. The shared preparation helper supplies only the case and controls in a fresh external W. E is separate and must not exist before freeze.

1. `freeze --work W --out E` checks supplied input identities and creates frozen original claims, sources, controls, manifest, and `initial-checks.json`. It makes no provider call. The manifest covers the adapter, shared launcher, and guard as well as the input/control bytes.
2. `review --attempt E --reviewer source --phase before` and the separate skeptic invocation each run a fresh read-only agent. Each sees only the original claims, original source packets, and schema. Neither sees another verdict or the exact checker findings.
3. `correct --attempt E` first audits both prior reviews. A fresh correcting agent receives the original claims and sources, schema, deterministic findings, and both completed reviews as data. It returns the complete registered set, preserving IDs, cases, and kinds.
4. The source and skeptic review invocations with `--phase after` each receive only the complete correction, original sources, and schema. They do not receive prior reviews or the correction discussion.
5. `report --attempt E` audits all five distinct live runs again, compares saved parsed documents with their actual model responses, rechecks every corrected claim, and writes `report.json`, `report.md`, and `human-decision.json` without replacing prior outputs.

Persistent `inputs/<stage>` folders make the blind boundaries inspectable; `runs/<stage>` holds real launcher receipts; `reviews/<phase>-<role>.json` and `correction.json` preserve parsed outputs. Each audit binds the phase's exact read root, read-only authority, prompt, saved role instruction, all input bytes, successful reads of every required file, and completed pinned-model execution. Frozen input/control drift or edited parsed results holds the next operation.

There are five human-started model turns, not five provider requests: a turn may make several tool/provider exchanges. There are no implicit retries, fallback models, autonomous agent conversations, or multi-agent writes. Missing prerequisites hold the live lane; no fixture substitutes for execution.

## Structured checks and acceptance

A review contains `schema: m08-review-v1` and seven unique answers with exactly `id`, `verdict`, `locator`, `quote`, and `reason`. Verdicts are `supported`, `contradicted`, or `unknown`. Supported and contradicted judgments need a nonempty exact quotation from a real record in the claim's own case. Unknown may cite a real passage showing the limitation or leave both locator and quote null. A genuine quote can still fail to support the judgment; schema acceptance is not semantic truth.

A correction contains `schema: m08-correction-v1` and all seven claims with exactly `id`, `case_id`, `kind`, `value`, and `locator`. Value is nonempty text or null. A null value has a null locator. Invented locators, missing or duplicate IDs, changed case/kind identities, and malformed JSON stop the stage. A well-formed but incorrect value is retained for fresh review and final reporting.

Deterministic checks use complete values, units, clock labels, same-case authoritative locators, and extractive source text. They are not a list of special-cased bad numbers. Corrected clocks can pass. A right number with a wrong-case citation cannot pass. A model vote cannot override these checks.

The final report separates `technical_complete` from `content_holds`. It exposes every original/corrected claim, exact finding, reviewer quotation and reason, disagreement, and initially supported claim changed by correction. Properly retaining an unknown authority does not by itself block an internal summary, but `operational_dispatch` always remains `HOLD`.

Human dispositions are `USE`, `KEEP_UNKNOWN`, or `HOLD`, each with a source-backed reason. `internal_summary_decision` and `unresolved_evidence_and_owner` state the overall limit. These human judgments are recorded, not automatically verified. A successful report command is not a learner score or a dispatch decision.

## Failure and evidence boundaries

Preserve incomplete receipts, malformed responses, wrong judgments, and failed attempts. Never remove a difficult claim, overwrite a response, or combine favorable rows from different attempts. Existing attempts and reports are refused. Five same-model sessions do not establish independent model-family agreement, calibrated confidence, a general hallucination rate, or superiority. Local records are inspectable audit evidence, not tamper-proof proof against an operator who can rewrite the entire evidence directory.

The roughly 130-minute session allocation is a design budget, unmeasured with learners. Actual provider, browser, platform, and technical checks must be recorded separately from editorial review.

## 2026-10-04 amendment — inspectable handoff without grading

No classmate or instructor grades a learner's work, and no peer sign-off is required. The handoff itself contains the original failure, frozen evidence, independent reviews, correction, full recheck, human disposition, and unresolved boundary. Technical `PASS` and `HOLD` describe work checks and decisions, never learner qualification.

## 2026-10-04 amendment — Module 6 prerequisite

Module 6 no longer has the learner configure a literal predicate in a supplied control. It now has the learner pin a decision model as the harness judge, keep exact checks in code beside that model's typed judgments, and freeze thresholds before one held-out measurement. Where "Mastery and progression" lists deterministic predicates as a prerequisite, read exact checks kept in code beside decision-model judgments. This module's own capability and evidence are unchanged. The digest is recomputed for this amendment.

## 2026-10-04 amendment — inherited skills and two enabling capabilities

Module 05 now teaches bounded agent handoffs, Module 06 teaches the split between exact checks kept in code, model judgments, and decisions reserved for a person, and Module 07 connects one agent to one spreadsheet-writing tool. "Mastery and progression" therefore takes as prerequisites source verification, typed questions, exact checks kept in code beside decision-model judgments, bounded agent handoffs, and bounded model-and-tool operation. Giving each material claim its exact check, support judgment, or held authority applies the Module 06 split and is a quality bar, not an enabling capability. The two enabling capabilities are directing blind review and source-constrained correction while retaining coverage, and adjudicating disagreements and regressions against the original evidence. The exercise, evidence, and checks are unchanged. The digest is recomputed for this amendment.
