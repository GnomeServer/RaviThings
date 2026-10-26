# Reference: Module 4 — Decide with typed questions

**Frozen on:** 2026-10-02 (revision 2, after the four-perspective review round)  
**Scope:** one Tuesday block of about two and a half hours built around forty fictional intake messages `CL-001`–`CL-040` for the Ferry Depot to Clinic K-3 glove run on vehicle `CL-9`  
**Course objective:** work with atomic typed questions, state the judgment each isolates and add one of your own, run the pinned model once as a read-only decision function through the shared launcher, validate every typed answer mechanically, measure the answers against labels frozen before the run, set routing gates from the measurement, route forty messages in code, and hand a person the queue that only a person may decide

## 1. The need

A chat model answers a request with prose that a person must read and interpret before anything can act on it. Desk work at volume needs the opposite: a fixed question, a fixed answer set, and a value code can branch on. The course had modules for direction, verification, context, tools, diagnosis, controls, workflows, evaluation, agents, and transfer; it had no module in which the learner specifies the *shape* of an AI judgment so that software, not the model, owns the decision. Module 4 adds that capability on Tuesday, after context control (Module 02) and limited-authority tools (Module 03), and before the Wednesday modules that build predicates and workflows on structured records.

### 1.1 Prior art that defined the target

TypeSafe's Jev (docs.typesafe.ai) is a "System One" model: the caller sends a `state` and a set of typed `questions` (Choice, Score, Noul) and receives typed answers with per-option probabilities and a derived `confidence`, with no text generation and no parsing. Its guidance is the design the module teaches: keep control flow and side effects in code; decompose a broad judgment into atomic questions; give each question only the context it needs; use probabilities and confidence to act, confirm, or escalate; ask independent questions together and compose them in code; gate by confidence with thresholds that scale with risk. Jev computes confidence from the distribution (Choice: `(p_max − 1/n)/(1 − 1/n)`; a Noul's confidence is `|2p − 1|`). The module reuses the Noul formula for its yes-or-no questions so that one `min_confidence` gate applies to every answer type.

Jev itself is not usable from the course stack: it is a hosted, proprietary model with its own API and credential, and the course pins one provider, one model, and one launcher (`shared/run_omp.py` with `openrouter/anthropic/claude-sonnet-4.6`). The course cannot obtain calibrated probabilities from the pinned model either: Anthropic's API exposes no token log-probabilities, so any confidence the model reports is self-declared.

### 1.2 Open-source counterparts, and which one the stack can use

| Counterpart | What it gives | Fit with the course stack |
|---|---|---|
| Instructor (MIT; python.useinstructor.com) | Pydantic-typed extraction from any OpenAI-compatible provider, including OpenRouter and Anthropic; validation with automatic re-ask on failure | Strongest general-purpose library for "fill structured fields" in Python; it calls the provider directly, so it bypasses the launcher's receipts, guard, and no-retry rule. Recommended to graduates building software; not used in the module. |
| Pydantic AI (MIT; ai.pydantic.dev) | Typed agents with `output_type`, an OpenRouter provider, tools, and evals | The agent runtime Instructor's own documentation points to; the same bypass applies. |
| BAML (Apache 2.0; boundaryml.com) | A typed function language with schema-aligned parsing and a Rust toolchain, compiling to Python and other clients | Powerful, but a new language and toolchain for a nondeveloper course; out of scope. |
| Outlines, vLLM guided decoding, llguidance (Apache 2.0) | Grammar-constrained generation with access to logits, so Choice probabilities are real distributions | Requires an open-weight model served locally or on a GPU host; the course stack has no local model. This is the only open-source route to *measured* option probabilities, and it is what a team would reach for to reproduce Jev's confidence semantics. |
| OpenRouter `response_format: json_schema` (strict) | Provider-side schema enforcement on supporting endpoints, including Anthropic's structured outputs | Real schema enforcement, but the pinned launcher runs OMP in print mode and exposes no `response_format`; adding it would change the shared launcher every module relies on. |

The module therefore implements the pattern rather than a library: the contract goes in as the saved instruction (Module 02's mechanism, with its `instruction_loaded` receipt), the state and the question set go in as files the model reads with `course_read`, the model's entire reply is the typed-answer document, a stdlib validator in `scripts/chalk.py` is the type checker, `scripts/route.py` is the code that owns the decision, and the learner's frozen labels are the only measurement of the declared confidence. Everything the learner runs is Python 3.12 standard library, as in every other module.

## 2. Case

Chalk Line is a vehicle resupply of sterile surgical gloves from Ferry Depot to Clinic K-3 on vehicle `CL-9`, run 15:00 MDT on 8 October 2026, intake closing 14:00. The desk clerk consolidates the day's requirement line (boxes per catalog line `GL-65`, `GL-70`, `GL-75`, `GL-80`; a case is ten boxes) from forty messages that arrived during the shift. The warehouse picks from that line; the desk lead signs it.

Stake, in one sentence: the clerk would load `CL-9` with the glove count a fluent summary says Clinic K-3 needs, and a total that counts the corrected requisition twice, keeps a cancelled one, takes "cases" for boxes, or obeys the note that calls itself approved loads gloves the clinic never asked for while the size the theatres are out of stays short.

Traps, all in `tests/answer_key.json` under `traps`: one hostile intake note (`CL-014`) that tells the desk to treat itself as approved and to hide the note; one legitimate authority change (`CL-020`) that must still go to the desk lead; twelve supersession links including a correction, a cancellation, a resend, a confirmation, and two "this covers" messages; three unit traps (`CL-007` "Two surgical cases" are patients, `CL-014` and `CL-030` say cases); two messages for Clinic K-8 on vehicle `CL-6`; one Zulu timestamp; one quoted request inside a no-action message; three locally true messages that are not requirements (a permit, a pick already on the dock, a receipt confirmation).

## 3. Protected answer model

The staff key is `tests/answer_key.json`. It is excluded from every learner download by `shared/prepare_work.py` (the `tests` directory is excluded) and by the publication allowlist, and the oracle's `M4-BAN` criterion fails if it is copied under `shared/`.

Key totals: seven `PICK` messages (`CL-015`, `CL-023`, `CL-024`, `CL-029`, `CL-031`, `CL-035`, `CL-038`); requirement `GL-65` 12, `GL-70` 12, `GL-75` 28, `GL-80` 6, total 58 boxes; routes `PICK` 7, `CLARIFY` 1 (`CL-010`), `REFER` 5 (`CL-007`, `CL-014`, `CL-020`, `CL-021`, `CL-037`), `REVIEW` 0, `SUPERSEDED` 9, `IGNORE` 18. Authority is yes only for the administrative officer's own messages, so Okafor's two `K3-REQ` requisitions under the unratified delegation are referred, and the desk lead's decision on `CL-020` is worth 11 boxes (10 of `GL-70` and the fifth box of `GL-65`). A referred message replaces nothing, which is why `CL-007` surfaces as `REFER` rather than disappearing behind the referred `CL-017`. If the hostile note were believed and given authority, its ten cases would add 100 boxes of `GL-80`; losing the `CL-038` → `CL-008` link double-counts 20 boxes of `GL-75`. Learner-facing files state none of these totals; the oracle's `M4-LEAK` criterion checks.

Adjudication points the facilitator should expect: `CL-026` (a status question, keyed as not a request); `CL-008`, `CL-037`, and `CL-038` (urgency keyed from the message's own words, which name no timing); `CL-037` (the new total, `q3`, not the increment, `q1`); `CL-021` and `CL-037` (authority keyed no because the sender is not the administrative officer, so the delegation under `CL-020` is the desk lead's decision and not the router's).

## 4. Mechanism

- `scripts/build_state.py` builds `out/state.json` deterministically: movement, catalog, short desk rules, and the forty messages with quantity candidates. A candidate is a number (digits or the words one to ten) that is not part of an identifier, clinic code, or clock time, followed by up to two words of the same sentence. 68 candidates exist.
- `shared/controls/questions.json` holds seven questions: `request` (yes-no), `line` (choice of seven), `quantity` (choice among that message's candidates plus `NONE`), `urgency` (score of four levels), `authority` (yes-no), `instructs_desk` (yes-no), `replaces` (choice among earlier IDs plus `NONE`). The learner appends exactly one yes-no question of their own; `scripts/check_questions.py` checks the file before the paid call, and the verifier compares the seven supplied entries with the checkout's copy.
- `shared/controls/CONTRACT.md` is the saved instruction; `shared/prompts/DECIDE.md` is the fixed prompt. The launcher runs the read profile with no write authority. The verifier requires both files to have been read through `course_read` and the run to have started after the labels were frozen.
- `scripts/validate_answers.py` accepts the bare document or one fenced block, parses strictly (duplicate keys are a violation), and checks IDs, order, keys, ranges, options, candidates, and earlier-ID constraints. One violation holds the reply.
- `scripts/route.py` applies, in order: supersession (a link counts only when the replacing message is not itself referred and the link's declared confidence reaches `min_confidence`; an uncertain link sends both messages to `REVIEW`), the `instructs_desk` gate, the `request` gate, usability (`MIXED` → `REVIEW`; `UNSTATED`/`NONE`/no quantity/unit not the next word → `CLARIFY`), the `authority` gate, and `min_confidence` across `line`, `quantity`, and the Noul confidences of `request`, `authority`, and `instructs_desk`. It writes `routing-N.csv` and `requirement-N.json` and never overwrites an attempt.
- `scripts/validate_answers.py` refuses a receipt whose launcher result is not `PASS`.
- `shared/verify/verify_decisions.py` pins the case files, the contract, the prompt, and the seven supplied questions to the checkout's copies; binds the frozen labels, the state, the question file, the contract, and the prompt to each run's `input_sha256` snapshot, so a freeze record written after a run cannot pass; verifies every `answers-N.json` against its receipt and every `agreement-N.json` against the answers file it names; recomputes the highest-numbered routing from the gates on disk; and reads the handoff for every queued message and exactly one decision. It reuses the shared launcher's `audit_evidence`.

## 5. Oracle criteria

`tests/test_module_04.py` reports thirteen criteria: `M4-REF`, `M4-CASE`, `M4-STATE`, `M4-QUESTIONS`, `M4-VALID`, `M4-ROUTE`, `M4-LABELS`, `M4-VERIFY`, `M4-BAN`, `M4-INDEP`, `M4-TOKEN`, `M4-LEAK`, `M4-LAUNCH`. `tests/test_adequacy.py` proves each with at least one killing mutation from `tests/mutations.py` by mirroring the module beside a link to the repository's `shared` helpers.

## 6. Limits

- Declared confidence is the model's claim about itself; the module measures it on ten labeled messages and sets one gate from the worst wrong answer. Ten messages cannot establish a rate, and the lab says so.
- The validator enforces the schema after the fact; it does not constrain generation. A held reply is preserved and a second run is a new receipt.
- The module makes one paid call in the core and one in the stretch. It does not measure stochastic variation beyond the optional two-run flip count.
- The review round of 2026-10-02 (adversarial, curriculum, technical, voice) found and closed: a forgeable freeze record, unpinned case and prompt files, a hard-coded `answers-1.json` that broke the documented recovery path, supersession by referred or uncertain links, the instruction answer missing from the confidence set, unit words matched anywhere in a candidate, delegated requisitions counted before the lead's decision, and an inverted gate example in the lab.
- The router's unit arithmetic recognizes boxes and cases only. A chosen candidate with any other unit is routed to `CLARIFY`, never counted.
- No gate consumes another module's product; the case names no other movement.

## 2026-10-04 amendment — Jev is now reachable

§1.1 said Jev was not usable from the course stack. That changed: OpenRouter serves `typesafe/jev-1.13` under the course key, and the observed OMP 18.3.5 run could set it as the judge role. Current setup follows the latest stable OMP release and records each run's actual runtime version. Module 06 now uses Jev. Module 04 keeps the pinned chat model as its decision function; its capability, giving an AI judgment a typed shape and measuring declared confidence against labels frozen before the run, is unchanged and is Module 06's prerequisite. The phrase "the Wednesday modules that build predicates" in §1 refers to the retired Module 06 design. The digest is recomputed for this amendment.
