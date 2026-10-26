# Reference: Module 6 — Use Jev inside Oh My Pi

**Frozen on:** 2026-10-07 (revision 9; learner close measures chat-token use. Revision 8 native four-pattern implementation retained)
**Scope:** one Wednesday block of about three hours. Learners open ordinary Oh My Pi, install the TypeSafe skill, and have it write code that calls `jev-1.13` through OpenRouter with `OPENROUTER_API_KEY`. Jev is not the chat model. They do not create a TypeSafe key, set an Oh My Pi judge role, or start `scripts/blue_gauge.py`. The launcher, guard, and extension notes below are historical staff mechanics, not the learner path.
**Course objective:** Using Jev inside Oh My Pi, configure and compare four decision-model patterns: ask several questions about the same state in one request and inspect which answers matter; send uncertain messages to review and measure the effect of different gates; combine normalized scores and change priorities without another Jev call; route requests to record lookup, deterministic record comparison, or human queue and verify what actually ran. The close measures that those closed decisions stay out of the chat model. One mastery capability with at most three enabling objectives. Earlier capabilities (typed questions, labeled measurement, source checks, bounded native agent work) are prerequisites.

## 1. The need

Module 04 taught typed questions answered by the chat model and routing on its declared confidence. A decision model returns typed answers with model-derived probabilities rather than free-text drafts. Using one well inside a harness is a distinct capability: configure supplied pattern controls through plain prompts, observe the actual calls, routes, and handler executions, change one architectural setting, and compare the observed effect on the same saved answers. Cost and latency advantages require measurements on the current inputs and build; they are not guaranteed.

Capability delta: before, the learner could decompose a decision into typed questions answered by the chat model and gate on its declared confidence. After, the learner can choose and operate a decision-model architecture inside the native harness and explain its observed call, routing, priority, and handler consequences.

## 2. Sources

TypeSafe documentation, read 2026-10-04 (rechecked for pattern definitions):

- [How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one): code owns control flow; decompose the state and the questions; atomic questions; structure in questions; ask many questions in one request; combine answers in code; route on uncertainty.
- [Patterns](https://docs.typesafe.ai/patterns): speculative fan-out, confidence-gated routing, composite scoring, intent routing (authoritative source order).
- [Primitives](https://docs.typesafe.ai/primitives), [Noul](https://docs.typesafe.ai/primitives/noul), [Confidence](https://docs.typesafe.ai/confidence): Choice, Score, and Noul; phrase a Noul so a high value means yes; one condition per Noul; thresholds by error cost with a middle band to a person; Choice confidence `(p_max − 1/n)/(1 − 1/n)`; Score confidence by distance from the peak level. TypeSafe Choice confidence is derived from the probability distribution and is not the top-option probability.
- [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) (reviewed 2026-10-02): literal reading; math and counting; date and time comparison; indirection; large irrelevant state; adversarial content; contradictory instructions and criteria; Choice option order (leans to the first option); no generation.
- Cookbooks and integration notes: self-consistency for Nouls and Choices (illustrative bands); citation check; guardrails; date extraction in code; parallel questions batched in one request.
- OpenRouter: Jev hub, Decisions API, no separate TypeSafe account required; input billed, output free.
- TypeSafe's [coding-agent integration guidance](https://docs.typesafe.ai/introduction/coding-agents): keeps the coding/chat agent separate from Jev's structured decisions. The supplied controls call OMP's native judge helpers; OMP's conversational model explains the resulting work.

Historical Oh My Pi observations at tag `v18.3.5` and the v18.6.1 upstream source were read for API shapes only. The classroom runtime version is recorded at launch rather than pinned. Native `judgeBatch(states, questions, {intent, concurrency, retries})`, `.drain({timeout})`, `.status()`, `.close()`, and `completion(prompt, {model, system, schema})` returning a handle with `.wait()` are the verified shapes. Direct `judge()` discards the served model in its cell-facing return; batch items are used when build evidence is required. Native judgment caching is per state/model/question name/instructions/criteria; unique run-scoped question-ID namespaces are required to prevent cross-arm cache reuse on comparison experiments.

## 3. Case

Desk rules: `shared/case/DESK_RULES.md`. Three cargo families (generator spares, medical-equipment battery kits, water-system repair parts). One origin, one destination, one flight (BG-F17), one fixed snapshot. Stock states: `HELD`, `RECEIVED`, `INSPECTED`, `RELEASED`. Flight acceptance states: `ACCEPTED`, `PENDING`, `WITHDRAWN`. Release and acceptance are separate authorities. `PASS`, `RETURN`, `REVIEW` are message routes only. The duty logistics officer owns the review queue and proposed handoff. The cargo release officer owns stock release. The air movement controller owns exact-flight acceptance and dispatch.

Eighty messages (BG-001–BG-080) and sixteen requests (BGR-001–BGR-016). Each message/request state exposes only the raw text to Jev. Source records (scans.json, flight_acceptances.json, MISSION.json) stay in the supplied engine. Eight visible near-miss identities and three locally true broken handoffs (receipt/release gap, release/flight-acceptance gap, wrong-flight acceptance) are present. BG-006 supplies the hostile paperwork instruction. BG-019 and BG-052 supply the supersession trap. Only BG-001–BG-020 may appear as worked examples before the freeze. Held-out answers and labels remain unavailable until after the frozen unseen measurement.

The state sent to the model is the message or request text alone. All source checks, time selection against the snapshot, authority comparison, and handler dispatch remain in supplied Python.

## 4. Mechanics

- `scripts/blue_gauge.py start [--work PATH]`: prepares the external attempt (or validates an existing one), records absolute shared-helper paths and the copied analysis adapter, prints OMP version and model pins, and supervises the real interactive OMP TUI with inherited stdio, `--extension`, `--config`, `--append-system-prompt` (the supplied OMP_INSTRUCTIONS.md), `--tools` limited to blue_gauge+eval, and session-dir under the attempt. It records native session IDs after exit. No JSON wrapper or custom prompt console.
- `resume`: lists ordinary and registered externally prepared attempts, requires explicit attempt/session selection, verifies frozen controls, and resumes the native session without issuing a paid plan. Copied controls resolve shared helpers from the recorded policy, not ancestor-directory guesses.
- Inside OMP the `blue_gauge` tool (registered by `patterns.extension.mjs`) exposes the finite protocol: `inspect` (controls, source by known ID, or run), `configure` (pattern + changes → new immutable revision), `prepare` (pattern + revision + mode → one exact frozen eval cell), `replay` (confidence/scoring/intent only, saved answers, compatible revisions → zero Jev/handler calls), `show`, `verify`.
- The Python adapter (`control_action`) and runner (`patterns.mjs`) own branching, source resolution (`resolve_flight_acceptance`), routing (`screen_step`), normalization, weight application, handler dispatch (record_lookup reads authoritative facts; record_comparison compares exact cargo/flight/time records; human_review writes an officer queue item), and evidence writes. All three handlers are deterministic code with saved disk effects. The learner prompt never supplies executable code or paths; the runner never calls a completion helper.
- Native guard: one prepare-issued cell admitted once; altered cell, write to case, or arbitrary path fails before execution. 240-second bound per operation; outstanding handles cancelled on deadline or interrupt; partial results preserved; operation held.
- Replays change only gates/weights/handler mapping. Questions, source hashes, and answer content are checked for compatibility; a changed question definition is refused. Urgency reuse additionally requires identical state/question content and served Jev build. A handler failure does not invalidate otherwise complete typed intent answers for a nonexecuting preview; missing or malformed typed answers do. Native usage and main-chat overhead are separate from Jev requests. Missing provenance is labeled "not recorded". `max_comparison_complexity` has a supplied maximum of 1.
- `verify --work PATH --evidence PATH`: staff/noninteractive audit that recomputes comparisons and joins native tool calls, guard decisions, raw results, model identities, and disk effects. Reports technical `PASS`/`HOLD`, never a learner score.
- Supplied controls live in `shared/controls/`. `PATTERNS.json` holds the public question groups, gates, weights, handlers, and ceiling. `patterns.mjs`, `patterns.extension.mjs`, and `panels.mjs` implement the runner, native tool/guard, and evidence-derived renderer. `OMP_INSTRUCTIONS.md` is the append-system instruction. No learner-editable templates or selection forms remain in the active path.

## 5. Observed staff runs and rehearsal checks (explicitly historical)

Pinned OMP 18.3.5 and later 18.6.x compatibility smoke observations from earlier oxygen-cylinder corpus are retired from active use. They are retained here only as historical context for the one-shot launcher mechanics that this redesign replaced. They are not evidence for the airlift case, the four-pattern controls, or current native behavior.

The earlier airlift rehearsal (build 20260917, same 20 practice messages) is retained below as engineering history. It is not a performance guarantee, learner result, or promised output:

- Serial arm: 56 Jev requests, 8852 ms wall, reported $0.001011906.
- Fan-out arm: 18 requests, 2871 ms wall, reported $0.000711018.
- Three confidence-gate replays: 0 additional Jev requests.
- 60 unseen completed with 55 Jev requests, 13 reviews, 1 critical error → HOLD on that rehearsal sample.
- 80 scores obtained, but the original audit falsely counted three concurrent calls at an adjacent request boundary. Exact datetime/timedelta comparisons now treat endpoints as exclusive; a regression distinguishes that boundary from a genuine one-millisecond third overlap. The original held receipt remains unchanged.
- Native completion API 18.6 provides text and handle IDs; usage/served identity may be partial; print-not-recorded and HOLD benefit claims were applied where provenance was absent.

Any live learner run records its own served build, request counts joined to native usage, and actual outcomes. The original rehearsal receipts are not rewritten by later fixes.

Latest-runtime compatibility smoke (2026-10-05 UTC) on checksum-verified `omp/18.6.1` listed the unchanged `openrouter/typesafe/jev-1.13` and exercised one guarded batch with bool/choice/score shapes. Served model `openrouter/typesafe/jev-1.13-20260917`. This remains a native macOS arm64 boundary check only.

### Native airlift attempt, 2026-10-07 UTC

Recorded runtime: macOS arm64, OMP 18.6.0, Python 3.12.13, Node 22.23.2; served Jev build 20260917. Attempt `20261007T045231Z-e604be`, evidence under its external work folder's `out/native`. No automatic retry or model substitution.

- Cold serial `r_30eb710ab626`: 56 joined Jev requests, 8940 ms arm wall, reported USD 0.001011906. Cold fan-out `r_bb4072e5d694`: 18 requests, 2670 ms, reported USD 0.000711018. Both have 3/20 reviews and two critical label disagreements. Fan-out is not more accurate on this observed pair.
- Pass-gate replays at 0.4, 0.6 and 0.8, with return confidence 0.4, make zero additional Jev calls. Review load is 3/20, 4/20 and 6/20; the two wrong automatic routes remain.
- Frozen unseen `r_83f45a237edc`: all 60 rows complete; 55 Jev requests and five code-only rows; 8013 ms; reported USD 0.002160606; 13 reviews and one critical miss on BG-052. Decision `HOLD`; no label-guided retune or repeat.
- Scoring `r_3a9ac2b94193`: all 80 rows complete; 73 compatible urgency answers reused; 80 Jev requests for missing dimensions; 9172 ms; reported USD 0.001615152. At weights 0.5/0.3/0.2, BG-012 ranks 3 and BG-014 ranks 11. The zero-call 0.2/0.6/0.2 replay ranks them 24 and 1. The zero-call 0.1/0.2/0.7 replay moves BG-006 from 19 to 1. Raw answers and source facts remain unchanged.
- Intent baseline `r_3fc4b0811722`: 16 actual completion attempts, seven completed and nine `content_filter` failures. Routed `r_ce1fbec60d09`: 16 joined Jev requests; two code lookups, 13 human queue entries, one selected drafting completion that failed with `content_filter`. Reconciliation requests were deferred because returned complexity exceeded the unchanged maximum of 1. No specialist lane completed, so the required four-handler live proof remains `HOLD`. Completed age verification did not remove these observed refusals.
- Intent preview `r_aa53e8c93a42` uses the valid saved typed answers despite the failed handler. At intent confidence 0.9, it predicts 15 human routes but creates zero queue entries and makes zero Jev/completion calls. Completion cost and served identity are not recorded by this native API path; no cost-saving claim is established.

Main-model prose is not an execution receipt. In this attempt some chat tables displayed success checkmarks for failed handlers; the saved raw errors, executed flags, native panels and verifier remain authoritative.

### Explicit intent-only recovery

The separately authorized comparison retained the same model pins, source packet, handler map, 0.6 live intent gate, 0.5 complexity-confidence gate and maximum complexity 1. Revision `v_fb8d5319cf68` clarified that applying one stated desk rule to one cargo is a standard procedure. Score levels and the level-two authority boundary did not change. The prior 0.9 preview, all earlier receipts and the frozen unseen result were retained.

- Baseline `r_32dc6c4f8982`: 16 general-assistant completion attempts, seven completed and the same nine `incomplete: content_filter` errors; 50706 ms wall. Completion cost and served identity remain not recorded.
- Routed `r_34f5efc6f236`: 16 joined Jev requests, 3678 ms wall, reported Jev USD 0.000460068. Two code lookups and twelve human queue entries completed. Both selected reconciliation completions were actually attempted and returned `incomplete: content_filter`; neither completed.
- BGR-005 qualified at complexity 0.98, confidence 0.73; BGR-006 qualified at 0.69, confidence 0.50. Those failures were provider errors after dispatch, not complexity-gate deferrals. BGR-009 and BGR-010 were genuinely deferred because scores 1.04 and 1.03 exceeded maximum 1; their confidences 0.91 and 0.90 exceeded the 0.5 confidence gate. One intent-label mismatch on BGR-012 was retained.
- Recovery consumption: 16 Jev invocations and 18 native completion attempts, within the authorized maxima of 16 and 32. No other pattern or unseen measurement was repeated. The required completed reconciliation and drafting lanes remain `HOLD`; no further paid operation is implicit.

Native chat also misclassified these reconciliation errors as safety deferrals. Raw completion errors and native invocation counts established the correction. Attempted, completed, deferred and preview-only work must remain distinct in the handoff.

## 6. Limits

- The screen routes messages; it releases nothing and accepts nothing for a flight. The duty logistics officer owns the review queue; the cargo release officer owns stock release; the air movement controller owns exact-flight acceptance and dispatch.
- All probabilities, scores, and handler selections are observations on this sample and the build that answered. A later build may answer differently. Drift of a few hundredths between runs of identical inputs is expected. Thresholds and weights belong in gaps wider than observed drift.
- Message and request text travel to OpenRouter and to TypeSafe (for Jev) or the conversational provider (for main chat). Practice data only.
- Native batch items are not provider requests. One `judgeBatch` call may produce multiple provider round-trips depending on the bridge. Reported cost (USD) is the value returned by the native API; it is not independently verified billing.
- Replays and shows make zero additional Jev or native completion calls. The conversational turn that requests or explains them can still incur main-chat usage. Report these separately; a replay is not a newly measured live arm. Missing cost or served identity is labeled "not recorded", never zero.
- The 30-minute decision window is scenario time. It is not a learner processing deadline or an observed runtime measurement.
- The supplied extension renders deterministic panels from saved numeric evidence. No browser, separate dashboard, or additional package is part of the exercise.

## 7. Revision note

Revision 6 replaced the oxygen-cylinder one-shot selection/repair/tuning/freeze/measure workflow and its CLI, templates, and forms with native four-pattern controls, source-bound airlift records and sixteen differentiated requests. It added frozen copied-adapter identity, exact datetime concurrency checks, and nonexecuting previews from complete typed answers when a handler failed. At that revision, the specialist live-proof requirement remained held. Those receipts remain historical; they are not joined to different sources or rewritten as successful execution.

Revision 7 clarifies request-work complexity without changing score levels or authority gates, adds the observed intent-only recovery above, and gives the learner the distinction between applying a desk rule and deciding whether to waive it. The recovery does not establish completed specialist lanes or a cost-saving claim.

Revision 8 replaces specialist completions and the general-assistant baseline with record lookup, deterministic record comparison, and the human officer queue. Drafts, approvals, uncertain requests, and ambiguous identities remain human-owned. `max_comparison_complexity` retains a maximum of 1. Intent mode is routed-only; the issued cell is `run({judgeBatch,plan})`. A fresh intent-only check can use practice-visible single-source requests and queue ambiguous requests without disclosing held-out worked records. A single held-out request source still requires the frozen unseen measurement. Source visibility is saved in the immutable plan and retained during replay.

Revision 9 replaces the learner-facing review-packet close with a measured comparison of chat-model tokens and Jev tokens on BG-001 through BG-005. Closed decisions stay out of the chat. A gate change adds no call. A missing cost is "not recorded", not zero. Published OpenRouter comparisons are cited as other inputs, not as this desk's result. `OMP_INSTRUCTIONS.md` still describes the historical launcher handoff; learners do not start that launcher. Historical receipts are unchanged.

## 8. Latest-runtime compatibility smoke, 2026-10-05 UTC (historical boundary check)

The checksum-verified latest `omp/18.6.1` binary listed 14 live judge candidates, including the unchanged `openrouter/typesafe/jev-1.13` selection. A separate guarded batch judged one practice state with bool, choice and score questions. The served model was `openrouter/typesafe/jev-1.13-20260917`; the receipt and output audit passed, with reported judge cost USD 0.000016548. Run ID: `07428752-46d3-400b-9a3c-2899235c01b3`.

This is a native macOS arm64 compatibility check of the underlying primitives, not a rerun of the full four-pattern workflow or a new accuracy claim. Runtime versions are recorded observations rather than course pins; the selected and served judge-model constraints remain unchanged.

## 9. Revision 8 native intent verification, 2026-10-07 UTC

The installed runtime was updated through `omp update` from 18.6.0 to the offered stable 18.8.0 before any paid intent operation. The bounded smoke used `openrouter/anthropic/claude-sonnet-4.6` for conversation and `openrouter/typesafe/jev-1.13` for classification; the served Jev build was `openrouter/typesafe/jev-1.13-20260917`.

Attempt: `20261007T094437Z-927e53`. Native session: `01a115c0-38f8-743b-a8b6-2283303694d1`. Evidence lives in the external attempt's `work/out/native/`, not in the publication allowlist.

| Operation | Receipt | Observed result |
|---|---|---|
| Intent, gate 0.6 | `r_443336865127` | `PASS`; all 16 typed decisions and all 16 saved handler effects complete; 2 lookups, 1 deterministic comparison, 13 officer queue entries; 16 native judge invocations joined to 16 Jev requests; reported Jev USD 0.000460068; observed arm wall time 2,969 ms; zero assistant completions; zero intent or unsafe-handler mismatches |
| Gate 0.9 preview | `r_7c623ac031fe` | `PASS`; all 16 predicted routes are human review; BGR-001, BGR-002 and BGR-006 move from their original automatic handlers; zero new Jev requests, zero handler executions and zero new handler files |

BGR-006's executed comparison kept BG-AC2019 for BG-F17 current and excluded the newer BG-AC3019 for BG-F71. BGR-005 was queued: its observed complexity score was 1.02, above the unchanged ceiling of 1, despite complexity confidence 0.71. Its source still showed released stock and pending flight acceptance. No threshold was relaxed to obtain another comparison. Drafts and authorization requests produced officer queue entries, not assistant text or approval.

BGR-007 preserved both referenced identities in its officer queue item while withholding BG-071's worked source before an unseen measurement in the new attempt. The new attempt's unseen state remained empty; no substitute or fabricated unseen result was installed.

The source/guard/native-usage/disk-effect audit returned no errors. All 23 files belonging to the original intent receipt remained byte-identical after replay. All 232 previously snapshotted files in the earlier attempt's runs, revisions and copied source/control trees remained unchanged. Its frozen unseen receipt `r_83f45a237edc` remains the recorded `HOLD`; the first three paid patterns and the unseen check were not rerun.

The actual generated-page copy controls supplied both native prompts. The published exercise was inspected in Dark and Sand at 1,440 and 390 pixels; both text fences wrapped without page or fence overflow at 390 pixels. Native results were observed at 120 and 80 terminal columns. A main-chat summary incorrectly called BG-C104 “fully-cleared”; an explicit correction acknowledged that error and restored the distinction between confirmed source records and clearance, loading or dispatch. The saved handlers never granted that authority.

All 35 local scoped course gates passed. Module 6's nine behavior groups passed, and its nine deliberate regressions were killed with zero survivors. This is bounded intent verification plus preserved historical evidence, not a new four-pattern measurement or a cargo-clearance claim. Conversational usage remains separate from the reported Jev and completion counts.
