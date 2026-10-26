# Module 8 verification record

## Contract alignment and learner-lab review — 2026-10-04

The Module 7 core specification now describes the shipped agent-spreadsheet exercise and uses the course map's `VERIFY:PREFLIGHT`, `VERIFY:CASE`, `VERIFY:BATCH_WORKLOAD` → `AGENT_SHEET`, `PO07_RESULT` boundary. Active schedule, authoring, and progression statements no longer require the retired fixed router. Historical router evidence remains labeled historical.

The learner-lab review corrected these findings:

- **Case isolation:** the repeated shipment names could make three independent packets look like one combined movement record. The overview and lab now retain each claim's `case_id` and prohibit mixing masses or clocks across packets.
- **Completion versus acceptance:** the final stop instruction mixed invalid execution evidence with a valid report containing content errors. The lab now records an incomplete attempt in notes, while a complete report still receives a human decision even when it contains a hold.
- **Unknowns:** nullable citations, `KEEP_UNKNOWN` versus `HOLD`, and an unidentified authority owner are explicit. No invented citation, person, or permission is needed to finish the record.
- **Resume and cost:** learners resume at the first unfinished stage instead of overwriting an existing report. Five agent sessions may make more than five provider requests.
- **Readability:** the three report fields use full-width labeled bullets, preserving readable identifiers at desktop and mobile widths. The typed-question reminder links the existing prerequisite and Jev's primary documentation without implying a Jev API call.

All 18 Bash/PowerShell command blocks are byte-identical to the previously live-exercised lab. The documented Bash preparation and freeze commands ran successfully in an isolated home folder. A missing-key review and a report without reviews both returned `HOLD`; no human-decision file was created for that incomplete attempt.

Before the concurrent Module 5/6 integration, the runtime re-audited all five original live sessions and all seven corrected claims, retaining unknown authority with no content holds. No new provider calls were made. Chromium checks exercised the revised desktop/mobile decision guidance and no-JavaScript access, with no horizontal overflow or browser errors.

`tests/test_core_standard.py` now passes the complete eleven-module supply graph. Before integration, `scripts/check_course.py` passed all 30 scoped gates, including the current spreadsheet checker, all 18 Module 8 regressions, and byte-for-byte publication checking. That complete output is retained in `course-gates.txt` under the review evidence root. The Module 7 integration HOLD recorded below is resolved.

The later merge preserves the current Module 5 orchestration and Module 6 decision-model work. It changes the shared launcher and guard hashes; the original live campaign remains evidence for its frozen runtime, not a new campaign on the merged runtime. Fresh merged-runtime smoke checks prepared Modules 5, 6, and 8, froze the seven claims, and confirmed that a missing key and an incomplete report both hold without creating a human decision. The merged desktop/mobile lab also retained readable decision fields, no horizontal overflow, and no browser errors. `integrated-preparation-smoke.json` and `integrated-publication-review.json` retain those observations. Obsolete generated publication files and a retired Module 6 test-cache directory were preserved outside the worktree.

The first merged course run passed 29 of 30 gates; Module 2's mutation gate hit the unchanged 600-second limit. A profile attributed 209.572 of 215.219 seconds to its existing `safe()` path guard, including 65,330,040 sibling `Path` constructions. The guard now compares `os.listdir()` names and folds the requested name once per ancestor, retaining its exact-case/collision predicate and all link, junction, and traversal checks. No cache, timeout increase, or mutation reduction was introduced. A real-filesystem smoke preserved exact file contents and rejected incorrect case, traversal, a file symlink, and a linked parent. The initial gate log, profile, diagnosis, and smoke results remain under the review evidence root.

The final merged `scripts/check_course.py` run passed all 30 scoped gates, including all eight Module 2 mutation kills, the eleven-module supply graph, all 18 Module 8 regressions, and byte-for-byte publication checking. The build published 35 instructional pages, 419 raw downloads, and 40 UI/generated assets. Complete output is retained in `integrated-course-gates-final.txt`.

After that full run, `main` gained Copper Span's exact-stage-brief receipt fix (`026225e`). The final integration retained it and passed all 12 Module 5 Python tests, all eight orchestration-guard tests, the eleven-module supply graph, and a fresh byte-for-byte publication check. `post-course-receipt-check.json` records this incremental verification; the full 30-gate result above precedes that final Module 5 integration.

Concurrent commits `9704eef` and `4a84550` supplied matching Module 7 contract corrections and made Module 6's exact-check/semantic-judgment split an explicit Module 8 prerequisite. Those corrections were retained. The subsequent checks passed the supply graph, all 18 Module 8 regressions, eight publication tests, 34 builder tests, and regenerated publication byte equality. `post-progression-checks.json` retains the commands and results. The final mobile overview rendered the prerequisite reminder without overflow or browser errors; final-tab screenshot helpers timed out, recorded in `post-progression-browser.json`. Earlier screenshots retain the visual evidence for the unchanged learner-lab decision guidance.

**Review evidence:** `$HOME/course-evidence/module08-hallucination-20261004T195428Z-62c876a8/followup-review-1791154694549/`. This review does not measure learner comprehension, completion time, or native Windows execution.

## Hallucination-control rewrite — 2026-10-04

The current exercise replaces variation comparison with structured source checks, two blind reviewer roles, an evidence-bound correction, and two fresh reviews of the complete correction.

**Live evidence:** `$HOME/course-evidence/module08-hallucination-20261004T195428Z-62c876a8/`. Raw receipts remain outside the checkout. `commands.json` records invocation boundaries, exit codes, and output. `attempt/report.json` binds all five audited runs to their inputs, instructions, source reads, and original responses.

| Check | Observed result |
|---|---|
| Pinned runtime | OMP 18.3.5; `openrouter/anthropic/claude-sonnet-4.6`; macOS arm64 |
| Prepare and freeze | Seven claims and three original source packets frozen successfully |
| Missing credential | `HOLD` before a model attempt was created |
| Live ensemble | Before/source, before/skeptic, corrector, after/source, and after/skeptic all passed receipt audits |
| Complete recheck | All seven corrected claims rechecked; zero remaining exact-check issues, reviewer disagreements, or correction regressions |
| Missing authority | C07 remained `unknown`, with null value and locator; operational dispatch stayed `HOLD` |
| Offline regressions | `tests/test_module_08.py`: 14 passed; `tests/test_adequacy.py`: 4 passed |
| Pre-integration course gates | `scripts/check_course.py`: all 29 scoped gates passed before the concurrent Module 7 rewrite was integrated; complete output retained in `worktree-course-gates.txt` |
| Published interface | Overview-to-lab navigation, eight steps, PowerShell tab and native command copy, desktop/mobile layouts, mobile course menu, and readable commands without JavaScript exercised in Chromium |
| Combined-course checks | All 18 Module 8 regressions, 9 publication tests, 34 builder tests, and byte-for-byte publication checking passed after integration. `tests/test_core_standard.py` reported `HOLD: course map and module supply boundaries disagree: 07-fixed-workflow.md`; the incoming Module 7 map names `AGENT_SHEET` while its unchanged core specification still names the retired fixed-workflow products. That unrelated contract was not rewritten here. |

Report SHA-256: `f46b4e768e84ed2f833dfb6124900f54a8cbfddd251b31a8862359412d4ea747`.
Command-log SHA-256: `0c320b30de8d68973b25b2e47d6dc1c6b7dfbf7f0860886938da87f7c25ac8be`.

`publication-proof.json` and four screenshots retain the interface observations.

**Limits:** This is one real five-session campaign, not a measured hallucination rate, independent-model-family comparison, learner-time study, or human acceptance decision. All agents used the same model in separate sessions. The seeded claims are authored defects and controls, not observations of spontaneous model failures. Jev supplies the typed state/question design reference; this exercise does not invoke Jev or measure calibrated confidence. Browser checks do not establish Windows execution. No instructor or classmate grade is required.

## Historical package review — 2026-08-23

The record below concerns the retired variation-comparison exercise. Its script names, reference snapshot, and review results do not verify the current rewrite.

**Date:** 2026-08-23
**Standard:** `reference/REFERENCE.md`, SHA-256 recorded in `reference/REFERENCE.sha256`
**Amendments:** none. Reference frozen 2026-08-23.

### Executable evidence

| Evidence | Command | Result file |
|---|---|---|
| Acceptance oracle | `python3 tests/test_module_07.py` | `evidence/oracle-final.txt` |
| Oracle adequacy | `python3 tests/test_adequacy.py` | `evidence/adequacy-final.txt` |
| Restore | `python3 scripts/restore_baseline.py` | `RESTORE OK`; work copies pass |

### Prose panel

Language-model seats. **Class F / human panel is UNMEASURED.**

| File | Seat | Total |
|---|---|---|
| `reviews/round-1-technical.md` | Technical | 32/40 REJECT |
| `reviews/round-1-curriculum.md` | Curriculum | 30/40 REJECT |
| `reviews/round-1-adversarial.md` | Adversarial | 31/40 REJECT |
| `reviews/round-1-voice.md` | Voice | 90/100 human craft, 6/100 AI mannerisms REJECT |

### Decision

**Accepted as a reviewed implementation package, ready for a controlled pilot with a facilitator present.** Not accepted as a measured learner experience.
