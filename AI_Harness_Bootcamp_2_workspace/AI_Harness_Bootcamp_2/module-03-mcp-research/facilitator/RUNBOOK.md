# Module 3 facilitator runbook

## What the harness changes

Learners connect an assistant to a program that acts on their files. The launcher's MCP profile freezes the declaration and the connection before any model call, hides every tool the declaration does not name, and re-checks the tool list in the provider's own request. The server keeps its own log, and the verifier joins that log, the launcher's receipts, and the files on disk. A clean transcript then becomes evidence about what could have happened, and the probe supplies the cases where the model never tried.

## Session result

The learner reads the server's contract before connecting it and finds the mismatched read-only mark and the steering instructions. They declare the research limits and show with the probe that an open server breaches them and a bounded server holds them. They decide six notes before the assistant works, check the assistant's handling proposals for all forty notes against the rules, and mark nothing less restricted than the rules require. They narrow the connection for the partner phase, produce a cited extract that repeats no STAFF-only fact, remove the connection, and pass the verifier.

## Before class

1. Run `python tests/test_module_03.py` and `python tests/test_adequacy.py` from this module's folder, and confirm every criterion passes and every mutation is killed.
2. Run `python tests/test_runtime_launcher.py` and `python tests/test_runtime_guard.py` from the repository's `tests` folder and confirm both pass.
3. Run the lab once on your own machine with a live key: prepare a work copy, inspect the contract, run both probes, and read the research run's `mcp-audit.jsonl` to see what the model actually did with the two notes addressed to automation. That behavior varies by run, so decide in advance how you will use it.
4. Confirm Obsidian is installed on each class machine and opens a folder as a vault. Confirm each learner's process-local OpenRouter key is set before the first live run.
5. Open the verifier's source and confirm that its embedded key still matches `scripts/handling_key.json`; the oracle's corpus criterion fails when they differ.

## Tuesday delivery route

Module 3 is the second Tuesday block, about three hours. Pacing marks below count minutes from the start of the block, exclude breaks, and are approximate planning guides: follow the learners' progress, not the clock. The break falls after the learner's calibration is frozen and before the first live run, roughly 100 minutes in. The day's clock is in `COURSE_MAP.md`.

| Roughly (minutes in) | Action and result |
|---|---|
| 0–10 | What an MCP server is, and why a connection entry is a program the machine will run. Learner can say what `mcp.json` decides. |
| 10–20 | Read a contract live: run the inspector on the screen and point at the instructions, the tool table, and the two findings. Learner can name a claim to check rather than trust. |
| 20–30 | The four layers: allow-list, guard, server limits, evidence. Learner can say which layer answers which question. |
| 30–40 | The handling rules H1 to H7 with the two worked examples in `Handbook/Handling rules`. Learner predicts the level of a third example you make up, not from the vault. |
| 40–50 | Aggregation and notes addressed to automation. Learner can explain why three shareable facts can make a STAFF summary, and why reading an instruction is not obeying it. |
| 50–60 | What a probe proves that a transcript does not. Learner can state why a model that never attempted a forbidden action leaves the limit untested. |
| 60–68 | Prepare the work copy and open the vault in Obsidian. Work copy exists and the vault opens. |
| 68–76 | Inspect the contract and write `contract.md`. `contract-inspection.json` and `contract.md` exist. |
| 76–96 | Declare the research limits, run the unbounded probe, set the server's limits, and run the bounded probe. `probe-raw.json` shows breaches and `probe-research.json` passes. |
| 96–104 | Decide the six calibration notes and freeze them. `calibration-frozen.json` exists before any live run. |
| 104–128 | Smoke run, research run, and review of the AI's notes in Obsidian. Two run folders pass; the learner has checked at least two claims against their sources. |
| 128–150 | Fill the handling register for all forty notes and stage the releasable folder. The register is complete and the staged folder matches it. |
| 150–168 | Narrow the connection, probe it, run the partner phase, and scan the extract. `probe-partner.json` passes before the run and the scan passes. |
| 168–180 | Revoke, run once, write the handoff, and run the verifier. Verifier PASS or a documented HOLD, and a handoff with all six sections. |

Keep the order that the verifier checks: contract before any live run, declaration before the unbounded probe, bounded probe before each live run, calibration before the research run, and revocation last. A probe made after the run it describes is a HOLD, not an equivalent.

Hold the clock without cutting the work:

- Save time by shortening plenaries, pointing to the lab's existing explanations, and coaching while learners operate. Do not remove a lab step or hand over a declaration or a register to meet the clock.
- Live runs take minutes. Use that time to read the previous run's receipts with the learner rather than to start a second run.
- If a learner cannot finish an operation in its window, preserve the first failure and the current state, record the unfinished lane as `HOLD`, and start the next independent block on schedule. Do not add a teaching day, move required hands-on work into homework, or label an incomplete technical claim complete.

## Coaching boundary

You may:

- define a term already stated in the lab or in the vault's reference notes;
- point to the current step or file;
- help open a vault in Obsidian or run a supplied command with the correct arguments;
- ask the learner which folders the current prompt reads and writes, and which setting in `mcp.json` matches each field of the declaration.

You may not supply:

- the contents of `AUTHORITY.md`, or the arguments for `mcp.json`;
- the handling of any note in the vault, or the rule that decides it;
- the text of the partner extract;
- the verifier's output, or the decision that a transcript is sufficient.

## Common problems

- **The launcher refuses with `read limits differ` or `write limits differ`.** The declaration and the server arguments disagree; the message names the field. Fix the file that is wrong.
- **The unbounded probe passes.** The learner added limit arguments before running it. Remove them and run it again under a new name.
- **A run ends with `OMP exited 1`.** Preserve the folder under a new name and run again. The most common cause is a provider error, which the folder's `stderr.txt` shows.
- **A learner typed in Obsidian during a run.** The verifier reports an unexplained vault change. Preserve the attempt and run the phase again into a fresh folder name.
- **The model never tries anything forbidden.** That is a valid outcome for a run. The probe is what shows the limit, so do not rerun until the model misbehaves.

## Operational readiness notes

See Module 00 facilitator runbook for shared staff operational procedures, T-relative schedule, privacy-safe register, platform matrix, and evidence collection. This module: human contract inspection + six human-first calibration decisions (model cannot supply baseline) + unbounded then bounded probes in order + 40-note handling + narrowed partner + final revoked.

Record machine, source hashes, outcomes, and HOLDs for the published controls. No blind provider retry.
