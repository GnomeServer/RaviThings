# Module 3 verdict

**Date:** 2026-08-23
**Standard:** `reference/REFERENCE.md`, SHA-256 recorded in `reference/REFERENCE.sha256`
**Amendments:** none. Reference frozen 2026-08-23.

Every executable row names the command that produces it and the file holding the output. Re-run any of them from the module directory. A row without a reproducible command is not evidence.

## Executable evidence

| Evidence | Command | Result file |
|---|---|---|
| Acceptance oracle | `python3 tests/test_module_03.py` | `evidence/oracle-final.txt` |
| Oracle adequacy | `python3 tests/test_adequacy.py` | `evidence/adequacy-final.txt` |
| Hash supplied note | `python3 shared/tools/hash_source.py shared/case/YARD_WINDOW_NOTE.md` | exit 0, line starts `sha256` |
| Path escape | `python3 shared/tools/hash_source.py /etc/passwd` | exit 1, `HOLD: path not allowed` |

## What the oracle does and does not certify

It certifies the implemented static criteria and that each of those IDs can fail. Zero survivors.

It does not certify six-concern quality, assistive technology, protected grading, or pilot timing.

## Target-platform execution status

| Surface | Status |
|---|---|
| `python3` hash tool on this checkout | Exercised by `test_module_03.py` |
| Learner revoke of a work copy | **UNTESTED** |
| Assistive technology | **UNTESTED** |
| Protected graded case | Not in the repository; **UNTESTED** |
| Windows PowerShell learner path | Commands present in the lab; **UNTESTED end to end** |

## Prose panel

Language-model seats. **Class F / human panel is UNMEASURED.**

| File | Seat | Total |
|---|---|---|
| `reviews/round-1-technical.md` | Technical | 32/40 REJECT |
| `reviews/round-1-curriculum.md` | Curriculum | 30/40 REJECT |
| `reviews/round-1-adversarial.md` | Adversarial | 31/40 REJECT |
| `reviews/round-1-voice.md` | Voice | 90/100 human craft, 6/100 AI mannerisms REJECT |

## Decision

**Accepted as a reviewed implementation package, ready for a controlled pilot with a facilitator present.**

**Not accepted as a measured learner experience, not accepted against Class F until three people score the prose, and not accepted as executed protected grading.**
