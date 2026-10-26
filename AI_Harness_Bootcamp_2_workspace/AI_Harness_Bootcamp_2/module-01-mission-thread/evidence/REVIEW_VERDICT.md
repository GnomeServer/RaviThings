# Module 1 verdict

**Date:** 2026-08-23
**Standard:** `reference/REFERENCE.md`, SHA-256 recorded in `reference/REFERENCE.sha256`
**Amendments:** none. Reference frozen 2026-08-14.

Every executable row names the command that produces it and the file holding the output. Re-run any of them from the module directory. A row without a reproducible command is not evidence.

## Executable evidence

| Evidence | Command | Result file |
|---|---|---|
| Acceptance oracle | `python3 tests/test_module_01.py` | `evidence/oracle-final.txt` |
| Oracle adequacy | `python3 tests/test_adequacy.py` | `evidence/adequacy-final.txt` |
| Packet inventory | `python3 scripts/verify_content.py` | `evidence/content-final.json` |
| Visible workflow + negative contracts | `python3 tests/test_workflow.py` | `evidence/workflow-tests-final.txt` |
| Starting RED | `python3 tests/test_module_01.py` at the first tree | `evidence/oracle-red.txt` |

`evidence/starter-existing-hold.txt` remains a distinct negative contract for `scripts/start_work.py` refusing an existing directory. The starter was not changed in this closeout; the file was not regenerated.

## What the oracle does and does not certify

It certifies the implemented static criteria and that each of those 21 IDs can fail. `tests/mutations.py` holds one mutation per live oracle ID; `tests/test_adequacy.py` applies each to a temporary copy and requires the named criterion to fail. Zero survivors.

It does not certify source applicability, second-person review-surface use, assistive technology, protected grading, or pilot timing.

## Target-platform execution status

| Surface | Status |
|---|---|
| `python3` scripts on this checkout | Exercised by `test_workflow.py` and `verify_content.py` |
| Learner `review.html` with a second person | **UNTESTED** |
| Assistive technology | **UNTESTED** |
| Protected graded case | Not in the repository; **UNTESTED** |
| Windows PowerShell learner path | Commands present in the lab; **UNTESTED end to end** |

## Prose panel

Language-model seats. Scores are the pre-fix state. **M1-27 is UNMEASURED.**

| File | Seat | Total |
|---|---|---|
| `reviews/round-1-technical.md` | Technical | 31/40 REJECT |
| `reviews/round-1-curriculum.md` | Curriculum | 28/40 REJECT |
| `reviews/round-1-adversarial.md` | Adversarial | 29/40 REJECT |
| `reviews/round-1-voice.md` | Voice | 74/100 human craft, 18/100 AI mannerisms REJECT |

## Still unmeasured

M1-04 novice-packet audit; M1-17 second-person surface; M1-25 accessibility operation; M1-26 observed delivery; M1-28 transfer spot check; M1-29–M1-33 pilot metrics. No authored numbers.

## Decision

**Accepted as a reviewed implementation package, ready for a controlled pilot with a facilitator present.**

**Not accepted as a measured learner experience, not accepted against M1-27 until three people score the prose, and not accepted as executed protected grading.**
