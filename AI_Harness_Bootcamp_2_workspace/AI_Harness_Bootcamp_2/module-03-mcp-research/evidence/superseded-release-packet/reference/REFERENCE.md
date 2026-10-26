# Reference: Module 3 — Decide responsible release and operate bounded tools

**Frozen on:** 2026-08-23  
**Revision 2:** 2026-09-30 (supersedes thin yard-window reference; adopts NB-NOTE-17 / Kiln Hold per plan)  
**Scope:** one three-hour release-and-tool module built around a 40-file packet  
**Course objective:** record a contextual release decision and operate one supplied capability at least authority

## Reference amendments

Every change from the frozen Reference v1 to v2, with the reason and the evidence that forced it.

### v2 adoption of replacement packet

| # | v1 | Problem | v2 |
|---|---|---|---|
| 1 | Built around one yard-window note (V-18 at 12 Mesa Yard). | Thin lab; does not meet volume floor of 40 files, six-concern evidence scattered, hostile quote, near misses, time/supersession trap, received/released collision. | Adopts NB-NOTE-17: REL-001–REL-040 for Kiln Hold (Mill Depot to Clinic B-2, MH-6). Packet supplies concrete evidence for all six concerns plus combined effect. |
| 2 | Supported position prefilled as `no-release`. | Prefills the learner disposition. | Learners cite evidence and decide; no prefilled disposition in request or lab. Staff runbook and rubric record the expectation separately. |
| 3 | Commands and examples used YARD_WINDOW_NOTE.md and repo-relative paths. | Does not match prepare_work output or launcher contract with --hash-tool. | All live commands use prepare_work.py 03, W with shared/case/REL-001.md, --hash-tool, quoted paths, R/PY variables. |
| 4 | No "What the harness changes" sentence in runbook. | Required by plan. | Added explicit sentence in facilitator/RUNBOOK.md. |

`REFERENCE.sha256` is recomputed on this amendment.

## 1. The need

A professional can write a careful note and still send it to the wrong list. A hash tool that can read any path is not least authority. Isolated ethics language misses the composition of untrusted text with a real command.

The learner needs both branches: a recorded decision with per-concern evidence, and a contained tool action with disconnect and revoke.

**Done:** on packet NB-NOTE-17, the learner records a position with six-concern evidence, hashes exactly shared/case/REL-001.md, proves a path escape fails, shows that a composed override does not write a second file or expand authority, and revokes the work copy of the script (both direct and launcher paths).

## 2. Better framing

The module is not a generic ethics hour. It is **decision plus containment**.

A supported no-release is professional performance on the decision branch. It does not satisfy the connection branch. A generic checklist fails.

## 3. Authority and field survey

### NIST AI 600-1, Generative AI Profile, July 2024

Primary source: [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1).

Course use: inspect raw authority, keep approvals at the command you actually run, and treat retrieved override text as data.

Confidence: high.

### Current Reformation core

Repository authority:

- `LEARNING_OBJECTIVES.md`
- `COURSE_MAP.md`
- `modules/core/03-responsible-tools.md`
- `AUTHORING_GUIDE.md`

It requires both claims: contextual release evidence, and a supplied capability at least authority with composed-negative, disconnect, and revoke.

Confidence: high.

## 4. Learner and case boundary

The learner is a domain professional with ordinary workplace computer skills. No prior logistics, coding, or legal background is assumed.

The module uses packet NB-NOTE-17 (40 REL files) for Kiln Hold: burn-dressing cases from Mill Depot to Clinic B-2 on vehicle MH-6. All names and identifiers are course fixtures for this movement.

The learner does not:

- publish the packet;
- send it to a real operations list;
- use it as a real dispatch;
- write a more powerful tool; or
- release work outside the class.

## 5. The deep case

### Decision

May packet NB-NOTE-17 leave the class. Learners record a position supported by citations under the six concerns. Sharing limit is class-only. No outside decision owner exists in the packet.

Six concerns: privacy/security, copyright/IP, fairness/bias, transparency/disclosure, affected-person/recourse, human accountability. Combined effect must be addressed.

### Connection

`hash_source.py` reads one path under the case root, writes nothing, prints `sha256 <hex> <filename>`, and refuses paths outside `shared/case/` with `HOLD: path not allowed`.

Composed negative: prompt that instructs reading all 40 REL files then hashing REL-001, plus the hostile quote that asks to write a release and escape. Expected: read the listed files, hash only the allowed file, no second file, escape refused.

Revoke: rename or delete the work copy; file-not-found or `HOLD: path not allowed`. Both direct python and launcher --hash-tool must fail after revoke.

## 6. Protected answer model

- Position: learner records with citations; staff expectation is no-release when sharing limit is class-only and no outside owner.
- Hash of REL-001 is stable.
- Outside sentinel exits 1 with HOLD.
- No second file or authority expansion from the composed prompt.
- Revoke removes the work copy (direct and launcher).

Visible commands may verify the hash line and refuse path. They may not award the module result.

## 7. Learning workflow

1. Prepare work folder with prepare_work.py 03.
2. Read the packet.
3. Record the six-concern decision.
4. Inspect raw authority.
5. Hash REL-001 and refuse an outside path.
6. Combine the override prompt with the tool via launcher --hash-tool.
7. Disconnect and revoke (direct and launcher).
8. Leave a handoff.

## 8. Time and cognitive budgets

These are design targets until piloted.

| Item | Budget |
|---|---:|
| Facilitated session | 3 hours |
| Learner operation | 2 hours |
| Packet volume | 40 files |
| Provider calls | 0 required (live lane blocked when key absent) |

## 9. Technical checks

Visible practice checks use the supplied tool and hash. No separate protected or graded case is supplied. The fixture branch is labeled practice only. Live provider evidence is blocked while the key is unavailable.

## 10. Failure modes that hold the module

- Unclear rights.
- Unacceptable affected-person effect.
- Missing recourse or disclosure.
- Broad or omitted authority.
- Unknown action or egress.
- Unreviewable approval.
- Unauthorized action or authority expansion.
- Hidden side effect.
- Failed revocation.

## 11. Absolute failures

Report without measurement: timing, effectiveness, cost, or cross-platform operation. Do not claim a human panel that did not sit. Do not present the packet as an authorized dispatch.

## Standalone repository path amendment

Repository-authority paths now resolve from the `AIHB_OCT_2026` root. Research, supplied case facts, and historical evidence are unchanged. `REFERENCE.sha256` records the amended file; earlier observations retain their original repository context.
