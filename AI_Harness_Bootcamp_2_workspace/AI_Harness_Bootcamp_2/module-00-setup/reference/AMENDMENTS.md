# Reference amendments

Every change from the frozen Reference v1 (2026-08-12) to v2 (2026-08-14), with the reason and the evidence that forced it. Required by §6 D4: a deviation that is not recorded reads as conformance.

## Contradictions inside v1, now resolved

| # | v1 | Problem | v2 |
|---|---|---|---|
| 1 | §5.D required Ubuntu to provide "a command-line-only alternative when a desktop session is not present"; the next sentence required a desktop-capable machine for Obsidian. | Two clauses of the same section demanded opposite things. The build silently resolved it toward refusal and recorded nothing. | §4.2 resolves it explicitly: no desktop session means a named stop with the limitation recorded. The CLI-only-alternative clause is withdrawn. |
| 2 | §8 set 3 facilitated hours including 2 hours of learner work. The shipped lab timebox summed to 180 minutes and the facilitator schedule to 150. | Three numbers, no arbiter, and no check. Both shipped schedules exceeded the frozen budget. | §4.6 names 180/120 as the single source of truth, sourced to `COURSE_MAP.md`. §6 D3 asserts the arithmetic. |
| 3 | §6 closed with "Qualification evidence must remain in evaluator custody," which the build read as licence to invent a second, unseen graded case scored in the session's last 20 minutes. | No such case exists anywhere in the course skeleton. `COURSE_MAP.md:58` and `modules/core/00-direct-bounded-work.md:6,12` specify one supplied case with a supplied **protected acceptance control** (`VERIFY:PROTECTED_ACCEPTANCE`). | §6 E6 requires the skeleton model: one supplied case, one protected control confirmed before work and run by the evaluator. The unseen-second-case architecture is withdrawn. |
| 4 | §3 said installing n8n and Obsidian "does not become Module 0's learning objective," while the shipped rubric made Setup a hard gate of the module result. | A learner with broken n8n failed PO-00 regardless of their work. | §6 E4 forbids a setup gate in the rubric. §7 restates setup as an entry condition. |

## Criteria v1 required but never checked

| # | Source | v1 | v2 |
|---|---|---|---|
| 5 | `LEARNING_OBJECTIVES.md` PO-00 evidence; `00-direct-bounded-work.md:13,24` | The **capability-limit statement** — model output vs product surface vs harness control vs human decision, plus one observed capability and one limitation — appeared in no lab step, no work file, and no rubric row. | §6 E1 makes it a required record with a rubric gate. |
| 6 | `00-direct-bounded-work.md:30` Gate: "the falsifier fails visibly" | The lab asked the learner only to *state* a falsifier. Nothing ran it. | §6 E2 requires the learner to run it and record the observed failure. |

## The oracle, rebuilt

v1 §9 enumerated 21 criteria checked almost entirely by substring presence. The suite reported 171 PASS / 0 FAIL — a true count — while the module simultaneously contained three of v1 §10's own absolute failures and two learner files that no scan read.

| # | v1 mechanism | Why it failed | v2 |
|---|---|---|---|
| 7 | Hand-maintained file dictionaries. | `shared/case/REQUEST.md` and `CHANGED_INPUT.md` — both opened and copied by the learner — were in no scan set. Arbitrary unsafe content in them passed. | §6 C1: glob-derived scan set with an asserted count. |
| 8 | Safety scan restricted to ```bash|powershell|sh|zsh fences. | Seventeen ```text and ```markdown blocks were unscanned, and shipped content already puts executable commands in ```text. | §6 C2: every fence, regardless of info string. |
| 9 | Pins matched against a concatenation of all files. | One correct pin masked any number of wrong ones. | §6 C3: parsed from `VERSIONS.md`, asserted per file. |
| 10 | One `**Terminal:` and one stop-condition pair per *file* satisfied "every command block" and "every install step". | Structural conformance was measured per file, not per unit. | §6 C5: per-unit counts. |
| 11 | No check had a negative fixture. | Nothing proved any check could fail. | §6 C6 and the governing principle: every criterion names an input it must reject; `tests/mutations/` asserts it. |
| 12 | Nothing checked that the module was reachable, that blocks were paste-safe, or that a guide could not strand the learner. | The two most severe defects found in review — an unpublished module and a clone the guide itself dirtied — were invisible to every check. | §6 Class A, entirely new. |

## New material with no v1 counterpart

| # | Section | Why |
|---|---|---|
| 13 | §1.1 — a setup path is a program; an unexecuted program is broken. | Docable: 0 of 40 hand-annotated tutorials reached a working setup. v1 treated non-execution as a caveat; v2 treats it as a prediction of failure. |
| 14 | §1.2 — no time budget in this document is authored. | Nathan & Petrosino: experts underestimate novice completion time and cannot correct for it when told. v1's budgets were authored. |
| 15 | §2 — field survey, fourteen exemplars with citations. | v1 had none. Its standards were asserted rather than derived. |
| 16 | §4.3 — the adversary is named: an AI on the learner's machine optimising for green, and an honest learner under time pressure. | METR measured 30.4% vs 0.7% reward hacking on oracle visibility. v1 had no threat model. |
| 17 | §4.4 — three-state verdict. | v1 was binary, so any pin drift produced a hard HOLD. `brew doctor` is the standing evidence that a noisy binary gate gets ignored. |
| 18 | §5 — off-axis frontier. | v1 had none, so the conventional design was defaulted into rather than chosen. |
| 19 | §6 B7–B9, X8 — the deciding control must not exist on the learner's machine, and the tool-proof and n8n checks must verify provenance. | okpy keyed its HMAC on a public string; v1's tool proof was satisfiable by three `printf` calls; v1's n8n check passed against any listener on port 5678. |
| 20 | §6 A8, A9, B10 — credential entry alone; duration annotations; bounded retries. | Bracketed-paste capture of the following line; Salerno's progress-feedback category (9/24 sessions); ImpossibleBench's finding that extra submissions raise gaming 33%→38%. |
| 21 | §8 — obsolescence with named signals. | v1 §12 listed empirical limits but no expiry conditions. |

## Carried forward unchanged

v1's shared environment rules (§4, now §3 invariants 1–8), its absolute-failure list, its parsimony rule, its 32/32 panel standard, and its refusal to accept an AI-detector score as evidence. The last is now cited: RAID (ACL 2024) and Liang et al. (2023).

## Re-freezing

`REFERENCE.sha256` records the SHA-256 of the amended `REFERENCE.md`, followed by `reference/REFERENCE.md`. Change the digest only for an explicit contract amendment; retain the reason and behavioral evidence here. Historical v1/v2 findings above remain historical.

## v3 amendment — one harness, one provider, honest evidence

| # | Previous requirement or defect | Current contract and reason |
|---|---|---|
| 22 | Multiple participant agent/tool chains, unaudited proof files, mixed provider pins and clean-tree gating | Git/Python/OMP 18.3.5 plus OpenRouter only; exact `openrouter/anthropic/claude-sonnet-4.6`; verified-first official binary; three-argument token-and-receipt proof. Preserve unrelated checkout changes and use external work. |
| 23 | Protected-control claims described a public practice checker as inaccessible; technical or agent results could be read as qualification | Public practice is inspectable. Qualification requires actual independent evaluator custody and original evidence; otherwise HOLD. No fabricated control, human result, or hidden second case. |
| 24 | Old timeboxes and perfect review scores implied measured performance | Session allocations and the 60-minute first-result goal are design targets. Keep platform, live, accessibility, peer and human outcomes separate; no unobserved pass. |
| 25 | Frozen reference still contained retired services, multi-agent setup checks, source-wording gates and thin-case examples after the setup cutover | Replace active §§3–8 with the implemented single-runtime and North Shelf contract; retain the research survey and historical evidence. Preserve all supplied case facts and the count-only changed input. |
| 26 | The public checker rejected “No vehicle is assigned,” “No permit is approved” and “No receipt is confirmed” by matching a shorter positive substring | An affirmative span shields only the nested substring; a separate contradictory occurrence still wins. Actual before/after counterexamples are retained in the staff QA record; nine polarity boundaries are permanent regression coverage. |
| 27 | macOS's reopened-terminal block repaired PATH while claiming persistent availability | Persist the non-secret user-bin setting idempotently in the selected login profile, then verify in a new shell without a PATH repair. The isolated cold-shell before-run selected the other installation and failed the intended-path check. |
| 28 | OMP `--no-rules` did not stop ancestor context discovery outside the isolated runtime cwd | Place cwd beneath isolated HOME. The real pinned-OMP before/after smoke observed the external synthetic context marker before the fix and its absence after it, with zero provider requests. |

The digest is re-frozen for this explicit v3 replacement, not to hide a failed gate. Per-run evidence and unresolved external dependencies are recorded in `reformation/evidence/exercise-runs.json`.

## v4 amendment — remove grading and qualification lane from active reference contract

| # | Previous requirement or defect | Current contract and reason |
|---|---|---|
| 29 | §5 and §6 described independent assessment, real evaluator custody, qualification remains HOLD, and an Assessment gate requiring CUSTODY_CONTRACT and named evaluator/evidence | Public practice and technical acceptance use the visible practice checker and human decision record. No separate hidden case or qualification lane is supplied. A documented HOLD is valid technical evidence. The Assessment row is replaced by Decision record requiring named owner and source evidence. References to deleted grading documents removed from active sections. |

The digest will be re-frozen for this explicit amendment. Historical evidence and prior amendments remain unchanged.

## Standalone repository path amendment

The course now lives at `~/Documents/AIHB_OCT_2026`, with `shared/` and `AI_Harness_Bootcamp_2/` directly under its root. The active launcher path in `REFERENCE.md` is updated to match, and `REFERENCE.sha256` records those bytes. Research, supplied case facts, runtime pins, and historical evidence remain unchanged. Current run summaries are at `evidence/exercise-runs.json`; earlier paths above describe the original repository.

## v5 amendment — native local n8n readiness, 2026-10-02

The native Module 7 cutover requires the full official n8n 2.41.5 stack. The prior named-shell rule did not describe the n8n-only WSL bridge on the PowerShell route. Active §3 now preserves native PowerShell for OMP/Python/Git/credentials/course work while bounding that bridge to n8n. Local n8n readiness remains a prerequisite, not a Module 0 mastery objective or an alternate AI harness.

The readiness contract now names owner approval for Docker/licensing/privileged runners, preserved installations and engine context, loopback binding, a collision-checked recorded Compose project, explicit lifecycle inputs, refusal of inherited overrides, and saved-workflow persistence. Native Apple Silicon evidence used the six-service stack; host-shell parser/boundary checks cover the five authored procedures without claiming five native platform runs. Current evidence is in `../evidence/REVIEW_VERDICT.md` and Module 7's `evidence/native/runtime-proof.json`.

The obsolete A1/A4 source scans misread `printf '%s/get-n8n.sh'` as an executed relative path. A3 banned every `exit`, including safe subshell refusals and the intentional WSL-to-PowerShell return. Those incidental-source assertions and their mutations were removed rather than re-pinned. Real syntax, collision/preservation/refusal boundaries and native runtime behavior are recorded separately; the remaining oracle is explicitly scoped, not proof that every platform procedure was executed. The digest is re-frozen for this explicit contract amendment; historical v1–v4 records remain unchanged.

## v6 amendment — remove the nonexistent per-key spending ceiling, 2026-10-02

There is no per-key spending limit. Reference §4 called a provider-side US$40 ceiling "a limit, not a promised cost," and the setup guides, credentials page, troubleshooting table, facilitator runbooks, and Module 08 and 09 instructions told learners to set and confirm a per-key spending cap before paid work and to stop if they could not. None of that describes a control that exists, so it is removed rather than reworded.

The reference now states only the paid-work controls that do exist: the fixed provider and model, process-local key handling, and no automatic paid retries. Module 08's stretch runner no longer records a provider-ceiling prerequisite or the key's reported limit; its own cost stops, the SDK-estimate stop and the optional staff-only local budget, are unchanged. Historical evidence that records a provider key limit during a past staff campaign is unchanged. The digest is re-frozen for this explicit amendment.

## v7 amendment — no peer review, instructor grading, or outside-class work, 2026-10-04

Owner direction (2026-10-04): "We will not be doing any exercises like this: Your instructor or a classmate will choose one handoff and one material claim row. Remove that and any other case where a classmate or instructor grades work. The entire course is hands-on, individual effort. There is no graded exercise or homework."

The header's artifact-type line no longer refers to an independent evaluator. §4's timing note and §5 drop the remaining qualification wording. §7's evidence lanes drop peer review and human qualification, and its closing paragraph no longer contrasts agent operation with an independent classmate or qualifying human. The facilitator runbook drops the formal-result path that required an independent decision owner; in Module 0 the learner owns the class-review decision. The digest is re-frozen for this explicit amendment; historical records remain unchanged.

## v8 amendment — a send-or-hold decision instead of class review, 2026-10-04

Owner direction (2026-10-04): eliminate `PASS FOR CLASS REVIEW`, the phrase "Neither outcome is operational permission," and the abstract "named decision owner"; North Shelf is an individual exercise.

The learner is the Harbor Depot inventory clerk who would send the email, so the final decision is `READY TO SEND` or `HOLD`, backed by the source check, the checker result, and the falsifier. §4's stage list and §6's decision row now name that decision. In the lab, step 2 becomes writing down what the email must do (`email-requirements.md` replaces `acceptance-control.md`), the step 5 screen and step 6 direction ask who decides whether the email goes out, and the decision-owner figure is removed. The case packet, checker, and changed input are unchanged: the email still states its class-participant readership, and Ivo Marsh still owns any release. The digest is re-frozen for this amendment.

## v9 amendment — a long document you can trust, 2026-10-04

Owner direction (2026-10-04): "Rewrite the module to teach this lesson using OMP," where the lesson is the best way to get good long-form content from AI: write the brief and the tests first, outline before drafting, draft section by section from the sources, critique in separate sessions against references outside the draft, revise only flagged spans, and keep the final call with a person.

§4 now states that capability and the new stage list: the learner writes `brief.md` and `tests.md`, corrects and freezes an OMP-proposed outline, drafts one section per launcher session through `scripts/longform.py`, checks the 500–900-word draft with the practice checker, a failing copy, a number list, and four review passes run in isolated packets, verifies each finding, revises only the named sections, applies the changed count only where it is used, and decides `READY TO SEND` or `HOLD`. The case keeps its invariant facts but now sits in six source files; the email, its 130–190-word cap, the subject line, and the class-participants line are retired. The minimum responsibility screen moves into `brief.md`, which adds a disclosure line. §5 describes the checker's new shape checks, and §6 adds planned-drafting and review-and-revision rows. The stretch now compares a one-prompt draft with the planned one.

Live calibration with the course model set the word range: the one-note packet produced 341 words against a 700-word plan, and the six-source packet with five clinic questions produced 578 and 555 words against 680 and 650. The checker was corrected against those live drafts (list items under a "must not:" lead-in, contracted denials, "Harbor Depot holds N kits", "a request ... for 40 water-treatment kits"), and its fixtures were rebuilt from a new canonical brief: two passing briefs and 26 one-change failures. The digest is re-frozen for this explicit amendment: `e4339f3f02ab799e7a8b2bcee7bf9a0b5f95e7d117c68b30dbaf45d644ed7ced`.

## v10 amendment — rolling latest OMP, 2026-10-05 UTC

Owner direction removes the fixed OMP release requirement throughout the active course. Each platform resolves the official latest stable release once, retains its metadata, and downloads the binary and checksum list from that selected tag. Checksum-before-execution, conflicting-install preservation, shell boundaries, process-local credentials, provider/model pins, and the Python/Obsidian/n8n requirements remain unchanged.

Launchers record the successful executable's actual version in their policies and results. Saved-evidence audits compare those recorded identities offline, not against a hard-coded release or a new network lookup. A Copper Span dependency chain uses one runtime version; an upgrade requires a fresh fanout chain. Historical evidence retains the versions and hashes actually observed. The reference digest is re-frozen for this amendment; §9 records the new verification scope.

Follow-up verification rebuilt the published site and found no numeric OMP release requirement, old `18.3.5` reference, or hard-coded OMP release URL in its pages, search data, or downloads. Chromium checks covered all five platform routes, the setup overview, and required tool identities; the macOS copy button produced the exact authored installer. That installer ran in an isolated home, resolved `v18.6.1`, verified its official checksum, and made `omp/18.6.1` available in a fresh login shell. These are observed identities, not new course pins. Native execution in this follow-up was macOS only.

The saved-receipt audit also exposed an existing MCP result omission: the launcher emitted `PASS` without the MCP summary required by its offline auditor. The result now retains the configuration, authority, and server-audit hashes and the joined call count. A deterministic regression covers a completed revoked connection and rejects a falsified call count. A fresh real run (`d1843753-d802-49e7-9ce4-de0446251ead`) on the verified latest binary made exactly one authorized `Handbook/Handling rules.md` read, produced no work-file changes, and passed the independent saved-evidence audit. Earlier receipts are unchanged. Follow-up logs and desktop/mobile browser proof are retained outside the checkout at `/Users/ravistarzl/course-evidence/omp-latest-site-check-1791162031193/`.

## v11 amendment — staff-prepared two-service n8n, 2026-10-05

Owner direction: simplify Docker use to n8n plus external Code-node runners, move provisioning to staff, and validate the resulting exercise before integration. This replaces v5's full Assistant-stack requirement. The learner still operates a local n8n AI Agent, provides their own OpenRouter credential and downloads the generated spreadsheet; Assistant remains off.

Staff use the supplied Python lifecycle helper with official matching 2.41.5 images, loopback-only editor access, an authenticated external runner and a retained named data volume. No privileged Docker-in-Docker, Assistant sandbox, search service or Docker socket is needed. Native PowerShell invokes the helper and Docker CLI directly; the approved Linux-container backend remains a staff prerequisite, but the separate Ubuntu n8n bridge is removed. Installation, licensing and existing-data migration remain owner-approved staff operations. The helper preserves destinations and project identities and refuses configuration overrides or tampering. Its status is runtime-configuration evidence, not browser, Code-node, provider or learner-performance evidence.

The reference digest is re-frozen for this explicit amendment. Historical six-service and platform results remain unchanged; new observations and limits belong in the active exercise ledger.
