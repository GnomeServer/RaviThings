# Reference: Module 1 — Verify a logistics mission thread

**Frozen on:** 2026-08-14  
**Scope:** one three-hour source-verification module built around one fictional logistics mission thread  
**Course objective:** verify sources and outputs for bounded internal use

## 1. The need

A professional receives a polished AI brief that says a logistics mission can proceed. The brief is plausible because many of its fragments are true: cargo was scanned, a vehicle has enough rated capacity, a route appears open, and a permit application was accepted. The end-to-end claim is still false if those facts refer to the wrong lots, omit required equipment, use a superseded time, substitute receipt for authorization, or fail at a handoff.

The learner needs to verify the whole claim without becoming a logistics planner. They must resolve the exact entities, current sources, calculations, dependencies, and unresolved conditions that connect the requested effect to the claimed outcome.

This prevents four failures:

1. treating fluent synthesis as evidence;
2. promoting a true local fact into an unsupported end-to-end conclusion;
3. allowing an error at one step to disappear inside a summary of the whole thread; and
4. asking the producing AI system to certify its own work.

**Done:** on a new fictional case, the learner independently determines which parts of an AI logistics brief are supported, computes the deterministic consequences, rejects misleading and hostile material, predicts the effect of one source revision, and issues a bounded `ACCEPT`, `REVISE`, `REJECT`, or `HOLD` verdict whose material claims can be traced to current sources of record.

## 2. Better framing

The module is not primarily about finding citations. It is about **compositional truth**.

A mission thread is an end-to-end sequence of tasks and handoffs that produces a defined result. Each task can be opened into smaller claims:

- **identity:** the same mission, vehicle, route, destination, permit, lot, and revision;
- **authority:** the source is allowed to establish this kind of fact;
- **time:** the source was effective at the decision time and its time zone is understood;
- **quantity:** counts, units, included equipment, and arithmetic are correct;
- **condition:** received, released, serviceable, admitted, delivered, and usable are not treated as synonyms;
- **dependency:** the task can begin only when its entering conditions are true; and
- **handoff:** the output of one task satisfies the next task's actual entry requirement.

Each subclaim can itself depend on more sources and transformations. That is the recursive difficulty. The learner stops decomposing when the remaining statement is directly observable in a named source, mechanically calculable from supported premises, explicitly marked as an assumption, or reserved for a human decision.

## 3. Authority and field survey

### DoD Mission Engineering Guide, November 2020

Primary source: [Mission Engineering Guide](https://ac.cto.mil/wp-content/uploads/2020/12/MEG-v40_20201130_shm.pdf), public release.

It establishes that:

- a mission thread comprises end-to-end tasks or activities within a scenario or vignette;
- threads show how systems, people, data, methods, timing, and interfaces interact;
- detailed systems and capabilities turn a generic mission thread into a mission engineering thread;
- trustworthy data must connect to the question being answered;
- assumptions, constraints, metrics, sources, and model fidelity must be documented;
- error and uncertainty propagate from source data through models to conclusions;
- curated data should record timeliness, lineage, validity, accuracy, linkage, and profile; and
- a changed input should be traced to the outputs it actually affects.

What it gets right: end-to-end structure, dependency, data lineage, uncertainty, and the distinction between a task sequence and its detailed realization.

Where it does not solve this course need: it is an engineering guide, not a novice AI-verification lesson. Its scope and terminology would overload a three-hour nondeveloper class if taught directly.

Course use: one fictional thread, ordinary language, one visible dependency model, and no architecture notation or force-planning doctrine.

Confidence: high.

### NIST AI 600-1, Generative AI Profile, July 2024

Primary source: [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1).

It establishes that generative systems can confidently produce false content and false citations, that people may over-rely on polished outputs, that provenance should include source and version information, and that retrieved data can contain indirect prompt injections.

What it gets right: it treats false confidence, provenance, human oversight, and hostile retrieved instructions as separate risks.

Where it does not solve this course need: it gives risk-management actions, not a concrete learner workflow for deciding whether one mission claim is supported.

Course use: the learner opens sources directly, treats source text as data rather than instructions, and does not use the producer's self-assessment as evidence.

Confidence: high.

### Current Reformation core

Repository authority:

- `LEARNING_OBJECTIVES.md`
- `COURSE_MAP.md`
- `modules/core/01-verify-sources.md`
- `AUTHORING_GUIDE.md`

It requires one independent source-verification performance with known-answer, misleading-source, changed-source, real-surface, protected-evidence, and bounded-verdict gates.

What it gets right: it separates source fact, transformation, inference, and human decision; makes material misses hard failures; and denies consequential release.

Where implementation must add value: it needs a complete case, learner workflow, visible practice checks, protected-assessment contract, facilitator controls, and evidence package.

Confidence: high.

## 4. Learner and case boundary

The learner is a domain professional with ordinary workplace computer skills. No prior logistics, mission engineering, coding, military planning, or mathematical modeling is assumed.

The module uses **Operation Cold Lantern**, a fictional civilian emergency-medical resupply case. A truck may carry sealed medicine kits from a fictional depot to a fictional clinic. All names, identifiers, routes, documents, rules, and values are course fixtures.

The learner is a verification officer. They do not:

- choose a real route;
- dispatch a real vehicle;
- interpret law;
- issue a permit;
- make a clinical decision;
- optimize a logistics network;
- estimate unknown performance;
- write software; or
- release work outside the class.

Logistics is the setting. Verification is the assessed skill.

## 5. The deep case

### End-to-end claim under review

At 14:05 Mountain Daylight Time on 6 October 2026, the North Basin desk must decide whether refrigerated truck `VX-204` is documented as ready to carry at least 180 usable medicine kits from Red Mesa Depot to Clinic `H-17` over Route `R-71` by 16:00.

The supplied AI brief recommends `GO` and claims:

- all 216 scanned kits are usable;
- cargo weighs 1,584 kg and fits under a 1,650 kg payload limit;
- Route R-71 remains open until 20:50;
- permit PR-4418 has been accepted;
- the truck can reach the clinic at 15:33; and
- the mission requirement is met.

The learner must prove, revise, reject, or hold that conclusion.

### Thread structure

1. **Requirement defined** — exact destination, usable quantity, deadline, route, and decision time.
2. **Cargo received** — exact totes and lots scanned into custody.
3. **Cargo released** — quality authority determines which lots are usable.
4. **Vehicle made ready** — cargo plus required refrigeration equipment fits the mission payload.
5. **Movement authorized** — current permit status applies to the exact vehicle and route.
6. **Route window met** — loading and depot-to-gate timing place the truck at the gate before closure.
7. **Cargo delivered** — gate-to-clinic timing can meet the deadline if admission occurs.
8. **Usable effect confirmed** — the clinic receives the required released quantity; in the baseline packet this final event has not happened and cannot be claimed.

### Recursive claim structure

Every thread row carries these fields:

| Field | Question |
|---|---|
| Exact entity | Which mission, vehicle, route, clinic, permit, tote, lot, and source revision? |
| Entry condition | What must already be true before this step can begin? |
| Claim | What is said to be true? |
| Source of record | Which source has authority for this type of fact? |
| Locator | Where is the exact supporting text or row? |
| As-of time | When was the source effective, and in which time zone? |
| Transformation | What deterministic calculation or conversion is applied? |
| Output condition | What state exists if the step passes? |
| Next handoff | What must the next step receive? |
| Uncertainty | What remains unknown, assumed, or unresolved? |
| Result | Supported, contradicted, unresolved, or not yet occurred? |

The module goes deep by making the learner reopen any unsupported row. It does not add more missions, routes, or cargo types.

## 6. Source packet design

The baseline practice packet contains nine compact, accessible local files. The work starter copies each file into `inbox/` under a dump name from `INBOX_MAP.json`. `inbox/INCOMING.txt` is a received-time list only: `received`, a tab, and the dump filename, sorted by the received string. It names no issuer, no authorized use, and no S0x id.

| ID | Source | Authorized use | Designed challenge |
|---|---|---|---|
| `S01` | Mission order `MO-27` revision 4 | Requirement, route, deadline, step times | Exact identity and current revision |
| `S02` | Warehouse receipt `RCPT-8821` | Custody, tote/lot scan, gross mass | Receipt is not usability |
| `S03` | QA release `QA-661` | Released and quarantined lots | 180 usable versus 216 scanned |
| `S04` | Fleet card `VX-204` revision 7 | Payload and required rack | Similar vehicle distractor; omitted rack mass |
| `S05` | Route bulletin set v4/v5 | Current closure and supersession | UTC/local conversion and stale version |
| `S06` | Permit packet `PR-4418` | Intake receipt plus current registry status | Accepted for processing is not authorization |
| `S07` | Vendor note for `VX-240` | Packing dimensions only | Wrong vehicle and indirect prompt injection |
| `S08` | Community route update | No authority for R-71 | Newer, keyword-rich, wrong route/jurisdiction |
| `S09` | AI dispatch draft | Output under inspection | Fluent unsupported composition |

A sealed source change, `S10`, changes only the current R-71 closure from 20:50Z to 21:20Z and explicitly supersedes v5. It is released after the baseline ledger and verdict are frozen.

All files are synthetic, text-accessible, versioned, and local. No decisive fact depends on a map, image, live website, or outside logistics knowledge.

## 7. Protected answer model

### Baseline deterministic facts

- Scanned kits: `12 totes × 18 kits = 216 kits`.
- Released totes: lots `CR-09` through `CR-18` = 10 totes.
- Usable kits: `10 × 18 = 180 kits`.
- Released cargo gross mass: `10 × 132 kg = 1,320 kg`.
- Required refrigeration rack: `84 kg`.
- Mission payload: `1,320 + 84 = 1,404 kg`.
- Payload margin: `1,650 − 1,404 = 246 kg`.
- Loading every scanned tote would weigh `12 × 132 + 84 = 1,668 kg`, 18 kg over limit.
- Current v5 closure: `20:50Z = 14:50 MDT`.
- Earliest departure: `14:05 + 20 minutes = 14:25 MDT`.
- Earliest gate arrival: `14:25 + 28 minutes = 14:53 MDT`.
- Baseline gate miss: 3 minutes late.
- Earliest clinic arrival if admitted: `14:53 + 40 minutes = 15:33 MDT`.
- Clinic deadline margin if admitted: 27 minutes.

### Baseline verdict

`HOLD`.

Exactly 180 kits are released and fit within payload. The current route window is missed by three minutes, permit PR-4418 remains pending, and no delivery/receipt has occurred. The brief must not claim mission completion or readiness to depart.

### Changed-source answer

With route bulletin v6:

- closure changes to `21:20Z = 15:20 MDT`;
- gate margin changes from 3 minutes late to 27 minutes early;
- route feasibility changes from failed to supported;
- source version, closure, gate margin, route status, and route rationale change;
- cargo identity, usable quantity, payload, destination, step durations, expected clinic arrival, permit status, and delivery status do not change; and
- final verdict remains `HOLD` because the permit is pending and delivery has not occurred.

The visible practice checker may verify the exact arithmetic and required records. It may not award the module result.

## 8. Learning workflow

### Phase 1 — See the whole claim

The learner opens `REQUEST.md` and every file under `inbox/`. They do not open a labeled S0x index. Before trusting a filename, they mark which words would have to be true for `GO` to be defensible.

### Phase 2 — Hash the inbox and freeze identity

The learner hashes every inbox markdown file, then fills the source register from the files themselves: dump filename, issuer, version, time, and allowed use. Similar identifiers remain visible so rejection is demonstrated rather than avoided.

### Phase 3 — Decompose the thread

The learner creates one row per thread step, then opens each material row into identity, authority, time, quantity, condition, dependency, and handoff subclaims. The recursive stop rule is explicit: stop only at a directly observed source fact, deterministic calculation, named assumption, unresolved item, or human decision.

### Phase 4 — Classify every material statement

Each claim is labeled:

- `SOURCE FACT` — directly stated in an applicable source of record;
- `CALCULATION` — deterministic transformation with visible premises and units;
- `INFERENCE` — interpretation that needs a stated warrant and uncertainty;
- `DECISION` — action or disposition owned by a named person; or
- `UNSUPPORTED` — no admissible basis.

### Phase 5 — Recompute rather than repeat

The learner calculates usable quantity, payload, UTC/local time, earliest gate arrival, and clinic arrival from supported premises. Copying the AI brief's number does not count.

### Phase 6 — Write a challenge matrix from the inbox

The learner authors the challenge matrix. No heading list is supplied. Each unused file must say what it proves, what it cannot prove, the mismatch, and who would have to speak.

### Phase 6b — Run the producer rebuttal

The learner runs `run_producer_rebuttal.py`. If a live producer is unavailable, the script writes the sealed fluent `GO` fixture. The learner adds one challenge block for any claim still unrejected. They do not ask that tool whether its `GO` is right.

### Phase 7 — Inspect the desk packet

The learner renders `review.html` as the decision surface: a Cold Lantern desk packet with the verdict, thread strip, blockers, standing rule, and five questions. The page alone must answer:

- What can proceed?
- What cannot proceed?
- Which exact condition blocks the decision?
- Which source and calculation establish that result?
- What would have to change?

File presence alone does not pass this phase.

### Phase 8 — Freeze the baseline verdict

The learner chooses `ACCEPT`, `REVISE`, `REJECT`, or `HOLD` for class-only use, names the decision owner, and states the strongest evidence and unresolved conditions.

### Phase 9 — Predict and apply the source change

Before opening v6, the learner predicts the fields that would change if route closure moved to 21:20Z and the fields that must not change. After release, they update only the dependent claims, rerun checks, and explain why the overall verdict remains held.

### Phase 10 — Leave a standing rule and handoff

The learner writes one reusable rule in ordinary language and leaves a handoff containing the thread, source boundary, traced claim, rejected sources, changed-source delta, current verdict, and next check.


## 9. Time and cognitive budgets

These are design targets until piloted.

| Item | Budget |
|---|---:|
| Session length | about 3 hours |
| Mission/domain orientation | ≤15 minutes |
| Arithmetic and time conversion | ≤20 minutes |
| Source inspection and claim ledger | ≥60 minutes |
| Baseline verdict frozen | by minute 105 |
| Changed-source challenge | 25 minutes |
| Handoff | 20 minutes |
| Source files | 9 baseline + 1 sealed change |
| Thread rows | 8 |
| Material AI-brief claims | 6–10 |
| New logistics terms | ≤8, defined at first use |
| Required calculations | 6, all one- or two-step arithmetic |
| Provider calls | ≤3 short calls; verification remains learner-owned |

Kill the case or simplify it if novice pilots spend more than 25% of learner time decoding logistics terms or arithmetic.

## 10. Acceptance oracle

### Structure and scope

| ID | Criterion | Evidence |
|---|---|---|
| M1-01 | The package contains one learner lab, one fictional case, one facilitator runbook, one public rubric, one custody contract, one accessibility guide, one Module 2 handoff, and executable checks. | File/inventory test |
| M1-02 | The case uses one mission, route, vehicle, destination, permit, and cargo family; distractors are near identifiers, not extra scenarios. | Static case audit |
| M1-03 | No real operational order, real route recommendation, legal determination, clinical decision, or logistics optimization is required. | Scope judge |
| M1-04 | All logistics knowledge needed to solve the case appears in the packet or plain-language orientation. | Novice judge and source audit |
| M1-05 | Learner-facing material contains no PO IDs, internal evidence tokens, hidden answers, or qualification implementation language. | Forbidden-term scan |

### Recursive mission-thread reasoning

| ID | Criterion | Evidence |
|---|---|---|
| M1-06 | The learner traces the end-to-end claim through all eight thread steps. | Required ledger rows and human review |
| M1-07 | Every material step addresses identity, authority, time, quantity/condition, dependency, handoff, and unresolved uncertainty where applicable. | Ledger-schema test |
| M1-08 | The recursive stop rule prevents unsupported decomposition and infinite elaboration. | Learner instructions and judge review |
| M1-09 | Receipt, release, authorization, arrival, delivery, and usable effect remain distinct states. | Case answer tests and human judge |
| M1-10 | A locally true fact cannot pass an end-to-end claim whose next handoff fails. | Baseline hard gate |

### Source and output verification

| ID | Criterion | Evidence |
|---|---|---|
| M1-11 | Every material claim is labeled fact, calculation, inference, decision, or unsupported. | Ledger validation |
| M1-12 | At least one consequential claim is traced to exact source ID, version, locator, excerpt, and warrant. | Thread ledger and source register |
| M1-13 | Source authority is claim-specific; no source is globally labeled trustworthy. | Source register and judge review |
| M1-14 | The learner independently recomputes all six required calculations from supported premises and units. | Visible arithmetic checker |
| M1-15 | The learner rejects stale, similar-identifier, receipt/effect, irrelevant, and hostile-instruction sources with a reason. | Challenge matrix |
| M1-16 | The producing AI's citation, confidence, or self-review never counts as independent evidence. | Instructions and evidence audit |
| M1-17 | The corrected result is inspected in the supplied decision surface, not inferred from files or narration. | Functional surface procedure |
| M1-18 | Any material unsupported or contradicted claim blocks `ACCEPT`. | Rubric hard gate |

### Changed-source reasoning

| ID | Criterion | Evidence |
|---|---|---|
| M1-19 | Baseline values, prediction, and verdict are frozen before v6 is released. | Timestamp/order check |
| M1-20 | The learner updates exactly the dependent fields and preserves unaffected claims. | Allowed-delta manifest and checker |
| M1-21 | No stale v5 closure or baseline route verdict remains in the changed result. | Stale-value test |
| M1-22 | The learner distinguishes a changed step result from an unchanged end-to-end `HOLD`. | Verdict explanation and hard gate |

### Evidence, accessibility, and voice

| ID | Criterion | Evidence |
|---|---|---|
| M1-24 | A missing, inaccessible, compromised, or unstable decisive source produces `HOLD`, not simulated credit. | Accessibility and degraded-case review |
| M1-25 | Every decisive source has semantic text, stable local identity, keyboard access, and no color-only meaning. | Accessibility audit |
| M1-26 | Facilitator coaching cannot supply source authority, arithmetic premise, rejection rationale, delta, or verdict. | Runbook and observed delivery |
| M1-27 | Learner prose scores 100/100 human craft authority and 0/100 AI mannerisms under the cited-sentence panel rubric. | Three-person panel |
| M1-28 | The handoff alone contains the thread, source boundary, traced claim, rejected sources, changed-source delta, current verdict, and next check, so the verdict can be reconstructed from it. | Handoff template |

### Empirical criteria

| ID | Criterion | Evidence |
|---|---|---|
| M1-29 | At least 80% of domain novices complete the practice case without logistics coaching. | Pilot, n≥10 |
| M1-30 | Median time is about three hours or less. | Timestamped pilot |
| M1-33 | Provider spend remains inside the course's declared learner budget. | Usage telemetry |

## 11. Absolute failures

The module fails regardless of other scores if:

- a learner can pass by copying the AI brief;
- the AI producer grades its own output;
- a citation passes without source identity, applicability, and support;
- the warehouse receipt is treated as QA release;
- permit intake is treated as approval;
- a stale or wrong-route source supports the route claim;
- the source-embedded instruction is obeyed;
- required rack mass is omitted;
- 20:50Z is treated as 20:50 MDT;
- delivery or usable effect is claimed before it occurs;
- the source change overwrites baseline evidence or changes unrelated claims;
- the visible checker's result is described as the evidence for the verdict;
- logistics expertise or outside research is required;
- inaccessible source presentation is treated as learner failure;
- the exercise becomes a real logistics recommendation; or
- any claim of timing, effectiveness, cost, or cross-platform operation is reported without measurement.

## 12. Parsimony

One case carries the module. Shared instructions appear once. The source packet contains only facts or distractors needed by an acceptance criterion. The ledger is the only central learner record; other files are brief, verdict, change prediction, and handoff.

Every file must name a learner action, facilitator action, source fact, checker, accessibility need, or review artifact. Anything else is removed.

## 13. Obsolescence

Revisit this Reference if any of these occur:

- the Reformation PO-01 gate changes;
- current AI systems reliably expose cryptographically verifiable claim-to-source lineage in ordinary work;
- indirect prompt injection through retrieved documents is prevented by the common harness layer rather than user procedure;
- mission-thread practice adopts a materially different authoritative definition; or
- pilot evidence shows logistics context, not verification judgment, drives performance.

The earliest warning would be novice learners asking for logistics coaching before they ask how to inspect a source, or learners reaching different verdicts because the case requires unstated domain judgment.

## Standalone repository path amendment

Repository-authority paths now resolve from the `AIHB_OCT_2026` root. Research, supplied case facts, and historical evidence are unchanged. `REFERENCE.sha256` records the amended file; earlier observations retain their original repository context.

## 2026-10-04 amendment — no peer review, instructor grading, or protected grading

The owner directed on 2026-10-04 that the course is hands-on, individual work with no graded exercise and no homework, and that no classmate or instructor grades a learner's work. The thread walk and claim defense, chosen by an instructor or classmate, are removed from the lab and runbook, and the classmate review of the review page becomes the learner's own check that the page alone answers the five questions.

- Phase 7: the page alone must answer the five questions.
- Time budget: the handoff row no longer includes a protected check.
- M1-07 and M1-12 keep their criteria; their evidence no longer names a protected rubric or protected check. M1-14, M1-15, and M1-16 drop the protected case, protected check, and grader observation.
- M1-23 (visible checks separated from protected grading), M1-31 (grader agreement), and M1-32 (scoring time) are removed; no protected or graded case exists.
- M1-28 is restated as a property of the handoff rather than another person's reconstruction.
- §11, §12, and §13 drop the graded-evidence, protected-control, protected-assessment, and grader wording.

`REFERENCE.sha256` records the amended file. Historical evidence is unchanged.
