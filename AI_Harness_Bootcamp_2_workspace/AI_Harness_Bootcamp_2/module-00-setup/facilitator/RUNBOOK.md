# Module 0 facilitator runbook

## What this session must prove

Each learner can get a long document they can trust from AI: write the brief (with the minimum screen) and the tests before any prose, correct and freeze an AI-proposed outline, have OMP draft one section per session, check the draft against references outside it, verify every review finding before accepting it, revise only the flagged sections, apply one changed fact only where it is used, decide send or hold, and leave a handoff that makes the work locatable from the handoff alone.

Setup is an entry condition, not the lesson, and it is not part of the PO-00 result. A learner whose machine is not ready records `HOLD` on setup and moves to a loaner machine or a paired observation path. Observation keeps the learner in the room but does not pass the operating task.

The supplied North Shelf packet (the request, six sources, the style rules, and the changed input) is public practice. Its checker and the helper `scripts/longform.py`, with its session instructions in `shared/case/prompts/`, are inspectable. Do not invent a second case or describe a public file as secret.

## Before learners arrive

1. Run the relevant setup path on the actual classroom images, including the separate local Obsidian and n8n readiness checks.
2. Record each platform, architecture, installed versions, and date.
3. Confirm the intended repository is reachable and its frozen inputs are intact. Preserve unrelated local changes; do not reset or clean it.
4. Confirm the latest stable Oh My Pi (the observed `omp/<semver>` is recorded in receipts), the exact `openrouter/anthropic/claude-sonnet-4.6` selector, and a participant-supplied process-local `OPENROUTER_API_KEY`. There is no direct-provider login, model fallback, or automatic retry.
5. Choose fresh readiness-check work directories and preserve every prior attempt.
6. Confirm a same-state path for every control a learner must operate. Record any unverified operation explicitly.
7. Prepare a support owner for managed-machine and account problems.
8. Put a visible clock where learners can observe the 60-minute first-result design target: a frozen plan and a first section checked against its sources. Record actual timing and assistance; this target has not been validated with learners.
9. Confirm the classroom network reaches OpenRouter. The lab runs about 14 short launcher sessions per learner (one outline, five or six sections, five review sessions, two revisions); a second review round adds six.
10. Confirm T (first teaching day). At T-7 the coordinator sends setup instructions and access requirements. At T-3 each participant returns readiness status, evidence, and blockers via the register below. By T-1 device/support owners resolve blockers and staff complete capstone rehearsals/downloads on intended machines. Missing deadlines produce named HOLD records.
11. Maintain one privacy-safe readiness register (participant alias only, no real names/contact; route/platform, OS/architecture, device owner, required check, due date, status, evidence locator + date + redacted hash, support owner, disposition). Private details stay outside the repo and public site. Use actual cohort intake; do not assume availability of people or machines.
12. Record separately: GitHub account/invitation acceptance and repository read probe; participant-authorized OpenRouter access/key readiness and funded-credit readiness; HF access/conditions; device-owner installation approval; local n8n runtime/access and Local model tool/storage/RAM/port status. Exact local paths and private approvals belong in the external register, not this source. The US$25 staff verification admission remains separate from learner instructions.
13. Freeze the platform rehearsal matrix from the actual cohort inventory plus the mandatory changed-path routes (host macOS/Apple Silicon, native Windows PowerShell 5.1, clean Arch). At least one clean owner-approved machine per required combination completes the checks. Missing required machines hold release; unrepresented advertised routes remain explicitly runtime-unobserved.
14. Exercise the published commands for each required live lane on actual machines and preserve failures. Confirm class-work authorization and funded-credit readiness with the participant's account owner. Staff verification campaigns use their separately authorized [campaign ledger](../../../evidence/exercise-runs.json); its additional admission controls do not change the learner contract.

## Keep four readiness lanes separate

Record **OMP**, **Obsidian**, **n8n**, and **Local model** separately. The OMP lane retains both its prerequisite report and live `READINESS CHECK PASS/HOLD`; a passing report never replaces the live tool-write proof. Record **Obsidian READY/HOLD** from its two disk checks plus separate actual GUI observation, and **n8n READY/HOLD** from runtime, browser, and persistence checks. Record **Local model READY/HOLD** from approved tool identities, actual destination/cache volumes, installed and available RAM, a free `127.0.0.1:8080` before launch, and the complete exact-model lifecycle in Module 10. A preflight alone cannot make the Local model lane READY. No lane establishes another lane's result.

## Set up local Obsidian

Allow 15–30 minutes after installation to observe the practice workflow; record actual time rather than treating that allowance as measured. Use the existing platform's **Set up local Obsidian** section: [native Windows](../platforms/windows-powershell.md#set-up-local-obsidian), [WSL Ubuntu](../platforms/windows-wsl.md#set-up-local-obsidian), [macOS](../platforms/macos.md#set-up-local-obsidian), [Ubuntu](../platforms/ubuntu.md#set-up-local-obsidian), or [Arch](../platforms/arch-linux.md#set-up-local-obsidian). Require local vault storage, Restricted community plugins, and Sync off. No account, community plugin, or MCP service is needed.

Preserve the installed app, profile, and personal vaults. Fresh vendor installs use [1.13.7 and the exact asset hashes](../shared/VERSIONS.md#local-obsidian-for-module-2); an existing version may remain when its actual version and successful workflow are recorded. Arch uses its signed Extra package in the approved full-upgrade transaction, without a downgrade or partial upgrade. On WSL, require Linux Obsidian through WSLg in the same Ubuntu Linux home as OMP. The [Microsoft GUI floor](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps) is build 19044+ or Windows 11 with WSL 2. Do not reset a distribution, use a native app on a WSL UNC vault, or move it to `/mnt/c`; coordinate any restart with owners of active distributions and Docker workloads.

On Ubuntu/WSLg ARM64, require the approved `libfuse2t64` transaction while retaining FUSE 3, as described in the [AppImage FUSE guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html). Separately obtain device-owner approval for the vendor's [AppImage `--no-sandbox` launch](https://github.com/obsidianmd/obsidian-help/blob/master/en/Getting%20started/Download%20and%20install%20Obsidian.md). Explain that it disables Chromium's renderer sandbox for Obsidian and does not replace the course tool guard. Missing approval or display support remains Obsidian HOLD; no kernel-wide toggles, world-writable binaries, or privileged sandbox repairs.

Follow **Set up local Obsidian** in the learner's [platform guide](../README.md#set-up-local-obsidian) as an ordinary user with the platform-resolved Python 3.12+ executable. The overview links to the five routes; perform only the selected route's practice. The helper interface is `obsidian_readiness.py initialize|refresh|check --root PATH`; PATH must be a fresh external attempt directory. Open only its `vault` child. Observe this order:

1. `initialize --root PATH` creates linked `Start.md`, `Token.md`, blank `Reply.md`, and external `expected`/`observations` directories without overwriting an attempt.
2. In Obsidian, the learner opens `Start`, follows `Token`, follows `Reply`, enters the token on one line, and saves.
3. `check --root PATH` records the first disk result. Require `PASS: Obsidian file round-trip; GUI observation still required` for generation 1.
4. With the vault still open, `refresh --root PATH` rotates the token from outside Obsidian and preserves the old reply and observation.
5. The learner observes the changed token in Obsidian, follows `Reply`, edits and saves the new token, closes the vault window, reopens the same vault, and inspects the saved reply.
6. `check --root PATH` records the second disk result. Require the same qualified PASS for generation 2 and keep both check records and the refresh record.

Record actual platform, architecture, app version, date, observer, attempt location, and the GUI actions seen separately from helper output. The helper deliberately records `gui_observed: false`; never edit that field to manufacture desktop evidence. A token copied by a script, a matching disk file, or `.obsidian` presence does not prove GUI operation. Capture only credential-free practice-window evidence. Preserve every HOLD and use [Obsidian troubleshooting](../shared/TROUBLESHOOTING.md#when-local-obsidian-stops).

The observed reference GUI is **1.13.7 on Darwin arm64**. Native Windows, WSLg, Intel macOS, Ubuntu, and Arch GUI lanes remain unobserved in this record. Do not infer their success from the Mac observation or from shell parsing. Keep the learner's process-local hidden key entry, no-secret-files procedure, fixed provider/model, and no automatic retries unchanged; a maintainer credential exception grants no learner exception.

## Local n8n readiness

Staff own Docker installation, licensing review, engine privileges, image pins at 2.41.5, and the prepared destination using the helper. Learners run only the recorded start/status (and observe stop/start when staff perform it). Preserve existing stacks, containers, volumes, and data; no migration or removal without owner authorization.

The procedures and helper establish on the learner's device:

- `docker info` and `docker compose version` succeed in the shell used for the helper.
- Staff invoke `.../n8n_local.py prepare --project <fresh-approved-name> [--port 5678] --directory <destination>`; the helper refuses existing (or linked) destinations, colliding or reserved project resources, occupied 127.0.0.1 ports, any inherited Docker/Compose/N8N_* overrides, non-local engines, and unapproved configuration.
- Identity (project, port, engine context, file hashes) recorded in .course-n8n.json; start/status/stop always use that identity with explicit project/env-file/compose arguments. No pass-through flags.
- Editor bound to 127.0.0.1:5678. Services are exactly `n8nio/n8n:2.41.5` and `ghcr.io/n8n-io/runners:2.41.5`, with external runner mode, broker on 0.0.0.0 inside the Compose network, and diagnostics off. No privileged containers, host ports on runners, or Docker socket mounts.
- Helper `status` reports both services running, correct loopback binding, and the reviewed runner configuration (no Assistant or sandbox keys present).
- Staff run a real Code node (simple JS or Python) through the external runner and confirm a successful execution result appears; HOLD if the runner does not execute user code.
- Named blank unpublished workflow survives browser reload and a staff-assisted stop/start cycle via the helper. Named data volume is retained (down without -v or prune).
- An existing six-service installation stays under its owner's control. Export and back up its workflows and encrypted credentials only with permission; never print decrypted credentials. Prepare a fresh project and destination on an approved machine, import through n8n's supported mechanisms and verify operation before considering removal of the original. The helper does not migrate data. If staff select a nondefault directory, supply the learner's exact commands with `--directory` on every operation.
- Assistant remains off. Module 7 uses the AI Agent node on the canvas; the OpenRouter key belongs only in the n8n credential.

For a fresh instance, complete local owner account setup, skip offers and surveys, leave Assistant off. From Overview choose Build a workflow (or Create), name the blank readiness workflow, press Enter (auto-save), reload the page or return via list and reopen. Confirm name, empty canvas, unpublished.

Staff stop the recorded project (helper stop), then start again; learners reopen the same named workflow from the list and confirm it survived. Record n8n READY/HOLD from the combination of helper status, browser success, real Code-node execution, and observed persistence. Record actual platform/version/port/service state, workflow name, and any owner approvals or blocks. Unexercised combinations stay unobserved.

Use the n8n troubleshooting section for engine, port, login, or persistence problems. The helper never prints tokens or claims browser/Code-node readiness from a port response alone.

### Provision before handing over the machine

Use the participant's ordinary account. Install Docker only when missing, with device-owner approval: [Docker Desktop on macOS](https://docs.docker.com/desktop/setup/install/mac-install/), [Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/), [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/), or [the Arch Docker procedure](https://wiki.archlinux.org/title/Docker). Review [Docker Desktop licence eligibility](https://docs.docker.com/subscription/desktop-license/). Docker daemon access on Linux grants powerful host access; follow the owner's approved access policy rather than making the socket world-writable.

On native Windows, use Docker Desktop's Linux-container backend and native `docker.exe`; no separate Ubuntu distribution is needed for the n8n commands. On the WSL course route, enable Docker Desktop integration for the intended Ubuntu distribution and keep its configuration in Linux home. Do not install a second engine over an existing setup. Reopen the intended terminal after installation. Check `docker info` and `docker compose version`; missing access or approval is HOLD.

In the chosen platform guide, complete step 5 to resolve `PY`, `R`, and `M`. These commands create a new private configuration at `$HOME/n8n-course`, select an unused project and start only that project. If that destination or project already exists, stop for owner review; do not delete it to make preparation pass.

**Terminal: Bash or zsh, ordinary participant account; approved local Docker engine running.**

```bash
"$PY" "$M/scripts/n8n_local.py" prepare --project n8n-course &&
"$PY" "$M/scripts/n8n_local.py" start &&
"$PY" "$M/scripts/n8n_local.py" status
```

**Terminal: native Windows PowerShell 5.1, ordinary participant account; approved Docker Desktop running.**

```powershell
& $PY "$M\scripts\n8n_local.py" prepare --project n8n-course
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the preparation error.' }
& $PY "$M\scripts\n8n_local.py" start
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the startup error.' }
& $PY "$M\scripts\n8n_local.py" status
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the status error.' }
```

**Expected:** `PREPARED`, then `STARTED` or `RUNNING`, and a status report naming n8n 2.41.5, external runners and `127.0.0.1:5678`. Preparation generates a private runner-authentication token; it is not an OpenRouter credential. Never publish `.env`, the n8n database or resolved Compose configuration.

**Stop:** Any HOLD, a different port/version, a partial startup, or a request to change an existing installation.

**Recovery:** Inspect the recorded project privately with its owner. Keep failed configuration and logs. Correct the actual engine, access, registry or project conflict before another attempt; do not use another image or remove resources automatically. Initial browser startup can take longer than container creation: open the editor only when it responds.

Complete local owner setup and the browser save/reopen sequence above. In a separate unpublished readiness workflow, add a Manual Trigger and a Code node containing `return [{json: {runner_check: 42}}];`. Execute it and require the actual output `runner_check: 42`, then use the current Module 07 workflow for its separately authorized provider rehearsal. A running container alone does not prove external Code-node execution.

### Prove stop/start persistence

Keep the saved blank readiness workflow. Run the following in the same approved account and shell.

**Terminal: Bash or zsh, ordinary participant account.**

```bash
"$PY" "$M/scripts/n8n_local.py" stop &&
"$PY" "$M/scripts/n8n_local.py" start &&
"$PY" "$M/scripts/n8n_local.py" status
```

**Terminal: native Windows PowerShell 5.1, ordinary participant account.**

```powershell
& $PY "$M\scripts\n8n_local.py" stop
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the stop error.' }
& $PY "$M\scripts\n8n_local.py" start
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the restart error.' }
& $PY "$M\scripts\n8n_local.py" status
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the status error.' }
```

**Expected:** The named volume is retained. Once the editor responds, the same local login and blank workflow remain available. Observe the learner reopening it. **Stop:** Missing work, renewed owner setup, or any HOLD. **Recovery:** Keep the volumes and configuration and inspect the recorded engine/project with its owner; do not initialize another instance over missing data.

For isolated staff validation only, `prepare --port PORT --directory PATH --project NAME` may select a free alternate loopback port without touching an existing instance. The helper sets `N8N_WEBHOOK_URL` so generated test-form URLs use that port too; verify the displayed URL before uploading. Record the deviation; it is not execution of the default `5678` path. Learner machines retain `127.0.0.1:5678`.

## Session shape

Plan about three hours. The clock marks below are approximate planning guides, not measured completion times: follow the learners' progress, not the clock. You are with the room throughout. The first table lists the moments when you address everyone; the second lists what learners work on and the evidence to look for. Preserve a HOLD rather than rushing a blocked action into a claimed pass.

### When you address the room

| Segment | Roughly | What you do |
|---|---|---|
| Opening | 0:00–0:20 | Record setup state and route blocked learners. Name the fictional case and sharing limit. Explain the inspectable practice checker and helper, and start the visible clock. |
| Checkpoint | 1:00–1:15 | Record whether each learner has a frozen plan and a checked first section, and the actual elapsed time. Confirm `brief.md` and `tests.md` predate the outline. Don't read drafts aloud. |
| Close | 2:40–3:00 | Preserve every version, the review files, the receipts, and any first failure. Name unresolved dependencies. |

### What learners work on

| Roughly | Learner work | Evidence you should see |
|---|---|---|
| 0:20–0:35 | Work folder created; request, six sources, and the checker's opening comment read | The learner can name what each source can't establish and which clinic questions the sources don't answer |
| 0:35–0:50 | Brief and tests written | `brief.md` with every screen line answered; `tests.md` with all three headings, including tests the checker can't run |
| 0:50–1:05 | Outline proposed, corrected, and frozen | `outline-proposed.md` beside a corrected `outline.md`; `PLAN FROZEN` and `E/plan.json` |
| 1:05–1:15 | First section drafted and read | `draft/v1/01.md`, its receipts, and any problem quoted in `notes.md` |
| 1:15–1:35 | Remaining sections drafted and read | `draft-v1.md` and the word table; notes on anything wrong |
| 1:35–1:50 | Checker run, failing copy, number list | Checker output; `checker-test.md` failing on the on-hand count; every `NOT IN SOURCES` resolved |
| 1:50–2:20 | Review sessions run and every finding verified | `review/r1/` files and `fixes.md` with each finding accepted (with its source, test, or rule) or rejected (with a reason) |
| 2:20–2:30 | Flagged sections revised and rechecked | `draft-v2.md`; `SAME`/`CHANGED` only where fixes named a section |
| 2:30–2:40 | Changed fact applied | `change-fixes.md` written before the revision; `draft-v3.md`; the stale-count checker failure; `ORIGINAL UNCHANGED` |
| 2:40–2:50 | Decision and handoff | `decision.md` starting `READY TO SEND` or `HOLD`, each reason pointing to a file; `handoff.md` |

## Coaching limits

You may:

- point to the current step;
- define a term in plain language;
- help recover the machine or open a supplied file;
- ask what source supports a claim;
- remind the learner that revision stops after two rounds.

You may not:

- write or fix the brief, the tests, or the outline;
- say which review findings to accept or reject;
- identify the material source line;
- tell the learner which sections the changed input should move;
- edit a draft, a section file, or the checker;
- run another review round past the second;
- accept a narrated action in place of an operation.

If coaching crosses one of those lines, mark that part of the attempt as guided practice in the evidence record.

## Setup triage

| State | Action |
|---|---|
| Command missing in every new terminal | Return to the PATH step; do not reinstall all tools |
| Key missing in a new terminal | Expected; repeat hidden entry |
| Repository dirty before learner work | Inspect and preserve it; frozen-input integrity matters, not a clean working tree |
| Provider or participant key unavailable | Preserve the blocked live lane; no provider/model substitute or invented artifact |
| Platform operation unavailable | Record exactly what was not exercised; parsing or another OS is not native proof |
| Managed policy | Capture the exact message and route it to the IT owner |
| A material finding remains after two revision rounds | Preserve every version and record the decision as `HOLD` |
| A launcher session holds mid-lab | Keep the receipts; fix the named cause and rerun the same helper command, which skips finished work |

The shared receipt auditor accounts for OMP 18.3.5's stream-only `completedAt`
timestamp. It still requires every other final assistant field to match the
terminal record, plus the tool/guard/filesystem joins. If an older auditor holds
an otherwise completed readiness check on that timestamp, retain its original HOLD and
receipts. After updating the supplied helper, use a fresh work root and token;
do not rewrite the earlier result or reuse its output for the new readiness check.

## End-of-session collection

Collect or verify:

- OMP setup report path and separate live readiness result;
- Obsidian READY/HOLD, both disk-check paths, refresh record, actual version/platform, and separate GUI observations;
- separate n8n READY/HOLD, observed platform/version/port/service state, workflow name, reload and stop/start persistence observations, and unresolved owner approvals;
- separate Local model readiness status, preflight report, intended machine, and complete exact-model rehearsal evidence or the missing prerequisite;
- readiness-register entries with evidence locators and platform-matrix status;
- actual pilot observations, facilitator rehearsal records with source hashes and machines, and human peer-review records where observed;
- the relevant staff-verification ledger entry for campaign work, kept separate from class-work authorization;
- `brief.md`, `tests.md`, `outline-proposed.md`, and the corrected `outline.md`, with `E/plan.json`;
- the time the first section was checked;
- `draft/v1/` to `draft/v3/` and the assembled versions;
- checker outputs, `checker-test.md`, and the number lists;
- `review/r1/` (and `review/r2/` if used) with `fixes.md`;
- `change-fixes.md` and the `ORIGINAL UNCHANGED` result;
- `decision.md` and `handoff.md`;
- reason for any `HOLD`;
- support packet for any blocked dependency.

Do not collect API keys, environment dumps, account screenshots, or the learner's full home path.

## Pre-release operational evidence requirements

These procedures are exercised on actual cohort machines and participants. Record actual observations only; do not fabricate participants, approvals, or results. Report missing people, machines, authorizations, and any unresolved staff-campaign admission prerequisite.

**Readiness register and schedule:** Use the privacy-safe register defined above. Collect from actual intake. T-7 / T-3 / T-1 deadlines govern; missing items produce named HOLDs. Staff-verification spending and its additional admission controls belong in the separate campaign ledger.

**Platform matrix:** Mandatory: host macOS/Apple Silicon, native Windows PowerShell 5.1, clean Arch. Plus every OS/version/arch in the confirmed cohort. One clean owner-approved machine per required combo must complete install + fresh-terminal + repo auth + OMP + Obsidian GUI + n8n + capstone where assigned. WSL2 Ubuntu, native Ubuntu, Intel macOS added where present in cohort. Unrepresented routes: explicitly unobserved.

**Three nondeveloper pilots (Modules 00-02):** Recruit three representative nondevelopers. Exercise Modules 00, 01, 02 in order on the candidate generated site served locally. Observe setup, source verification, Obsidian workflow, navigation/search, elapsed time, questions, interventions, friction, outcomes. Record failures and assistance. Fix instruction/UI defects and re-observe affected path. No scores or qualification decisions.

**Current Module 00-10 facilitator controls (rehearsals):** Facilitators perform each current lab using its owning runbook. Record source/config hashes, operator alias, actual machine/date, outputs, assistance, HOLDs. Particular controls:
- 00: separate OMP/Obsidian/n8n/Local model lanes + register.
- 01: baseline/prediction before sealed change; thread walk and claim defense.
- 02: real Obsidian GUI + cold retrieval + admission.
- 03: human contract inspection, six human-first calibration decisions (model does not supply baseline), unbounded then bounded probes in order, forty-note handling, narrowed partner, final revoked.
- 04: labels before model answers/adjudication; ten-message sample limits stated.
- 05: restore before fault/sealed first miss/authorized correction/three recovery runs.
- 06: sample before categories/held-out labels after prediction; first-failure notes.
- 07: blank-canvas build, frozen deltas, both waves, restored reports; three-hour block preserved.
- 08: pre-result policy, 120 authored rows, six designated failures, restoration; 38-call stretch only after mandatory lanes and budget gate.
- 09: three core probes + strict planted-question verifier; human peer review of policy/probe/measurement evidence.
- 10: individual in-session exact-model lifecycle (weights, 127.0.0.1:8080, 32768, health after listening, OMP reply, stop/unreachable, digest restore, frozen copy and fresh-terminal structure check); no recipient or after-hours attempt.

**Module 09 human peer review:** Obtain real human peer review of current Module 09 policy/probe/measurement evidence and handoff from someone able to inspect the mechanisms. Technical peer critique is distinct from novice pilot. Current evidence is ungraded observation.


**Billing and evidence integrity:** Record every paid staff-verification attempt in its campaign ledger, including facilitator, pilot, and platform work. Preserve receipts, planned/attempted/completed/held counts, and actual billing when observable. No synthetic evidence. Retired evidence stays in the archived prior report.
