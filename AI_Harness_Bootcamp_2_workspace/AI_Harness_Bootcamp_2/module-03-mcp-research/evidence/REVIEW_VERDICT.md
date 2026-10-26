# Module 3 verdict

**Date:** 2026-10-02
**Standard:** `reference/REFERENCE.md`, SHA-256 recorded in `reference/REFERENCE.sha256`
**Amendments:** none. The retired release-packet case and its evidence are under `evidence/superseded-release-packet/` and describe a different module.

## Executable evidence

| Evidence | Command | Result |
|---|---|---|
| Acceptance oracle | `python tests/test_module_03.py` | `evidence/oracle-final.txt` |
| Oracle adequacy | `python tests/test_adequacy.py` | `evidence/adequacy-final.txt` |
| Launcher MCP receipts, tampering, and connection refusals | `python tests/test_runtime_launcher.py` (repository `tests/`) | 14 tests pass |
| Guard tool-set enforcement | `python tests/test_runtime_guard.py` (repository `tests/`) | 9 tests pass |
| Work-copy preparation | `python tests/test_publication.py` (repository `tests/`) | 9 tests pass |
| Whole course | `python scripts/check_course.py` | every scoped gate passes |
| Lab on the real pinned harness | Oh My Pi 18.3.5 binary through `shared/run_omp.py`, a scripted local provider, the supplied server, and `shared/verify/verify_research.py` | three whole-lab runs: a complete attempt passes; an attempt in which the model obeys the notes addressed to automation passes, with the writes refused; an attempt that copies the AI's proposals unreviewed holds on under-protected notes and on STAFF notes in the releasable folder |

The real-harness runs exercised the shared launcher, the guard, the server, the probe, and the verifier against the actual binary. The model in those runs was a script that replayed fixed tool calls. They show that the machinery joins receipts, server log, and disk correctly; they say nothing about how a live model behaves.

## Independent reads

| Read | Result |
|---|---|
| A reader given only the learner-facing vault files and the handling rules classified all forty notes | 40 of 40 matched the key |
| A reviewer checked every lab command, flag, expected output, recovery path, and the order the verifier requires | Found recovery paths that failed against the tools, a figure that revealed scopes the learner derives, a wrong sentence in the overview, and a timing overrun. The recovery paths, the figure placement, the overview sentence, and the lab's workload were revised. |

## Not exercised

- A live OpenRouter model: whether the model attempts the actions the notes addressed to automation ask for varies by run, and no live run was made.
- The Obsidian application: opening the vault, the backlinks pane, and the graph view were not exercised. The server reads the vault's files directly.
- Native Windows and the PowerShell command blocks.
- Learner timing. The lab's two hours of practice is a planning allowance. A reviewer's estimate of the original lab was about 165 hands-on minutes before retries, and the lab was trimmed afterward without being re-measured.
- A human panel for prose and voice.

## Decision

Implemented and technically exercised on one platform. **Not yet reviewed by a human panel and not measured with learners.** A facilitator should run the lab once with a live key before class and decide how to use what the model does with the two notes addressed to automation.
