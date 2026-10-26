# Module 2 verdict

**Date:** 2026-08-23
**Standard:** `reference/REFERENCE.md`, SHA-256 recorded in `reference/REFERENCE.sha256`
**Amendments:** none. Reference frozen 2026-08-23.

Every executable row names the command that produces it and the file holding the output. Re-run any of them from the module directory. A row without a reproducible command is not evidence.

## Executable evidence

| Evidence | Command | Result file |
|---|---|---|
| Acceptance oracle | `python3 tests/test_module_02.py` | `evidence/oracle-final.txt` |
| Oracle adequacy | `python3 tests/test_adequacy.py` | `evidence/adequacy-final.txt` |
| Guard accepts yard ticket | `python3 shared/case/guard.py shared/case/sources/RCPT-19_YARD_TICKET.md` | exit 0, captured in oracle output |
| Guard rejects crate note | `python3 shared/case/guard.py shared/case/sources/V18_CRATE_NOTE.md` | exit 1, captured in oracle output |

## What the oracle does and does not certify

It certifies the implemented static criteria and that each of those IDs can fail. `tests/mutations.py` holds one mutation per live oracle ID; `tests/test_adequacy.py` applies each to a temporary copy and requires the named criterion to fail. Zero survivors.

It does not certify resolved-state quality, assistive technology, protected grading, or pilot timing.

## Target-platform execution status

| Surface | Status |
|---|---|
| `python3` guard on this checkout | Exercised by `test_module_02.py` |
| Learner reload of a work folder | **UNTESTED** |
| Assistive technology | **UNTESTED** |
| Protected graded case | Not in the repository; **UNTESTED** |
| Windows PowerShell learner path | Commands present in the lab; **UNTESTED end to end** |

## Prose panel

Language-model seats. Scores are the first-pass state. **Class F / human panel is UNMEASURED.**

| File | Seat | Total |
|---|---|---|
| `reviews/round-1-technical.md` | Technical | 32/40 REJECT |
| `reviews/round-1-curriculum.md` | Curriculum | 30/40 REJECT |
| `reviews/round-1-adversarial.md` | Adversarial | 31/40 REJECT |
| `reviews/round-1-voice.md` | Voice | 88/100 human craft, 8/100 AI mannerisms REJECT |

## Still unmeasured

Novice-packet audit; observed reload; accessibility operation; observed delivery; transfer spot check; pilot metrics. No authored numbers.

## Decision

**Accepted as a reviewed implementation package, ready for a controlled pilot with a facilitator present.**

**Not accepted as a measured learner experience, not accepted against Class F until three people score the prose, and not accepted as executed protected grading.**
