# Module 0 verdict

The 2026-08-23 verdict below is historical. Current local n8n evidence and its platform limits are recorded in [Native local n8n cutover](#native-local-n8n-cutover--2026-10-02). The setup guides as rewritten on 2026-10-03 were run end to end in Docker and on a sandboxed Mac on 2026-10-04; see [Setup guides run end to end](#setup-guides-run-end-to-end--2026-10-04). The earlier counts and qualification language are not current acceptance claims.

**Date:** 2026-08-23
**Standard:** `reference/REFERENCE.md` v2, SHA-256 recorded in `reference/REFERENCE.sha256`
**Changes from v1 and what forced them:** `reference/AMENDMENTS.md`

Every row below names the command that produces it and the file holding the output. Re-run any of
them from the module directory. A row without a reproducible command is not evidence, which is the
defect this table exists to avoid: the v1 verdict reported `171 PASS / 0 FAIL` for a suite whose
checks had never been shown to fail, on a tree containing three of v1's own absolute failures.

## Executable evidence

| Evidence | Command | Result |
|---|---|---|
| Acceptance oracle, all criteria | `python3 tests/oracle.py` | see `evidence/v2/suite.txt` |
| Oracle adequacy: every criterion proven able to fail | `python3 tests/test_module_00.py` | 37 mutations, 0 survivors — `evidence/v2/suite.txt` |
| Practice checker adequacy | `python3 tests/test_checker.py` | 18 checks, 18 killing fixtures — `evidence/v2/checker-adequacy.txt` |
| Checker rejects a fact-inverted draft | `python3 shared/case/check_artifact.py <inverted draft>` | 7 checks fail — `evidence/v2/checker-rejects-inverted.txt` |
| Checker fails a correct changed-input revision, as the lab states | `python3 shared/case/check_artifact.py <revised draft>` | fails on capacity only — `evidence/v2/checker-changed-input.txt` |
| n8n check rejects a non-n8n listener | `python3 -m http.server 5678` then `python3 shared/case/verify_n8n.py` | HOLD — `evidence/v2/n8n-rejects-any-listener.txt` |
| Tool proof rejects hand-created files | `python3 shared/case/verify_tool_proof.py <dir> <token>` | HOLD on all three — `evidence/v2/tool-proof-rejects-handmade.txt` |
| Starting state before any fix | `python3 tests/oracle.py` at the v1 tree | 12 PASS / 18 FAIL — `evidence/v2/oracle-red.txt` |
| macOS Apple Silicon verify-setup — $HOME/course-evidence/module-00/macos-apple-silicon-verify.txt | `bash scripts/verify-setup.sh` | SETUP CHECK HOLD — 15 PASS, 10 FAIL including repo.clean and secret.xai; log at $HOME/course-evidence (module-00/macos-apple-silicon-verify.txt); `evidence/REVIEW_VERDICT.md` |
| macOS Apple Silicon check_artifact canonical — $HOME/course-evidence/module-00/macos-apple-silicon-check-artifact.txt | `python3.12 shared/case/check_artifact.py tests/fixtures/pass/canonical.md` | last line `PASS: mechanical requirements passed; this is practice only`; log at $HOME/course-evidence (module-00/macos-apple-silicon-check-artifact.txt); `evidence/REVIEW_VERDICT.md` |
| macOS Apple Silicon check_artifact inverted-entrance — $HOME/course-evidence/module-00/macos-apple-silicon-check-artifact.txt | `python3.12 shared/case/check_artifact.py tests/fixtures/fail/inverted-entrance.md` | `FAIL: entrance`; log at $HOME/course-evidence (module-00/macos-apple-silicon-check-artifact.txt); `evidence/REVIEW_VERDICT.md` |
| macOS Apple Silicon check_artifact capacity-45 — $HOME/course-evidence/module-00/macos-apple-silicon-check-artifact.txt | `python3.12 shared/case/check_artifact.py tests/fixtures/fail/capacity-changed-to-45.md` | `FAIL: capacity 60`; log at $HOME/course-evidence (module-00/macos-apple-silicon-check-artifact.txt); `evidence/REVIEW_VERDICT.md` |

## Evidence inherited from the v1 build, not re-run here

These were produced during the v1 build and are kept because they remain true statements about the
external world. Neither was re-run for v2, so neither appears in the table above.

- `evidence/url-check.txt` — every public source link resolved on 2026-08-12.
- `evidence/ubuntu-container-subset.txt` — Ubuntu 24.04 ARM64 base packages and Python, in a
  container, at v1. A subset of one platform's step 3, not a platform run.

## What the oracle does and does not certify

It certifies that every criterion in Reference v2 §6 passes against this tree, and — separately, and
this is the part v1 had no equivalent of — that every one of those criteria fails when the module is
broken in the corresponding way. `tests/mutations.py` holds one mutation per criterion;
`tests/test_module_00.py` applies each to a temporary copy and requires the named criterion to fail.
Zero survivors.

It does not certify that any command runs on any target platform. Static acceptance is not execution.

## Target-platform execution status

| Platform | Status |
|---|---|
| Windows PowerShell on native Windows | **UNTESTED end to end** |
| Windows WSL 2 with Ubuntu | **UNTESTED end to end** |
| macOS Apple Silicon | verify-setup.sh and check_artifact.py exercised on this checkout; full clean-machine install, billed tool-proof, n8n, and Obsidian GUI recorded as run or HOLD/UNTESTED from the log |
| macOS Intel | **UNTESTED** |
| Ubuntu 24.04 ARM64 | base package and Python subset executed in a container; **GUI and provider path untested** |
| Ubuntu 26.04 | **UNTESTED** |
| Arch Linux x86_64 | **UNTESTED** |

Reference §1.1 is the reason this table is stated so plainly. Mirhosseini and Parnin executed 14,876
blocks from 616 setup tutorials in fresh virtual machines: **0 of 40 hand-annotated tutorials reached
a working setup.** A five-platform path that has not been run on five clean machines should be read
as broken on at least one of them right now. Nothing in this package changes that, and no row above
should be read as if it did.

## Class F — the prose panel

`reviews/round-1-*.md` hold three reviews scoring 23/32, 26/32 and 24/32 against a bar of 32/32.
Every deduction cites a sentence. Their findings were fixed and the fixes are in this tree.

**Class F is UNMEASURED.** The three reviewers are language models reading from an assigned seat.
Reference §6 Class F requires three people — one technical beginner, one experienced cross-platform
operator, one professional editor. The round-1 files say so in their own headers, and check D2
refuses a Class F pass claim until three reviews declare a human reviewer. The scores above are the
state of the prose *before* the fixes; no one has scored it since.

No AI-detector result appears anywhere in this package, and none would be accepted. At a 5%
false-positive operating point the best detector in RAID (ACL 2024) reaches 85.0% and most sit at
65–75%, a homoglyph substitution costs the strongest one 41.9 points, and Liang et al. (2023) found
over 61% of TOEFL essays by non-native writers flagged as machine-written.

## Still unmeasured

Every one of these needs a pilot, not an argument:

- setup duration on clean and partly configured machines, per platform;
- whether the first checked draft lands inside 60 minutes;
- provider spend per learner;
- keyboard and assistive-technology operation in Obsidian and n8n — the guidance in
  `shared/ACCESSIBILITY.md` names real tools and real operations, and none of it has been run by
  someone using them;
- managed-machine escalation time;
- scorer time and agreement on the rubric;
- protected-case custody at cohort scale.

Reference §1.2 forbids this package from authoring those numbers: Nathan and Petrosino (2003) found
experts underestimate novice completion time and do not improve when told about the bias. The
figures in Reference §4.6 are planning placeholders marked `UNMEASURED`, and the pilot replaces them.

## Decision

**Accepted as a reviewed implementation package, ready for a controlled pilot on one platform with a
facilitator present.**

**Not accepted as working on five platforms, not accepted as a measured learner experience, and not
accepted against Class F until three people score the prose.**

## Native local n8n cutover — 2026-10-02

**Active contract:** `reference/REFERENCE.md` v6, explicitly amended in `reference/AMENDMENTS.md` and re-frozen in `REFERENCE.sha256`. OMP/Python/Git/credentials/course work remain native on the PowerShell route; WSL is used only as its n8n bridge. The separate WSL course route is unchanged in that respect.

The five platform guides now require the full official n8n 2.41.5 stack, approval for Docker/licensing/privileged runners, preservation of existing installs/context/data, loopback binding, a collision-checked recorded Compose project, explicit guarded lifecycle commands, local owner access and a saved-workflow restart proof. No cloud account or AI provider key is required for this n8n work.

| Evidence | Exercised result |
|---|---|
| Complete authored command extraction and parsing | 206 Bash/PowerShell blocks; 322 Bash/zsh/PowerShell 7 parser runs; no parse failures |
| Controlled host-shell project/lifecycle checks | 216 passing cases: fresh project record; existing file/symlink preservation; invalid/colliding names; failed inspection; nine inherited overrides both empty and nonempty; explicit project/environment/Compose arguments |
| Native n8n stack | Apple Silicon Docker Desktop, six-service official stack, version 2.41.5, loopback editor, healthy sandbox API, successful certificate service, owner setup and saved-workflow persistence after down/up |
| Exact authored macOS helper | `course_n8n ps --all`, `course_n8n port n8n 5678`, `course_n8n exec -T n8n n8n --version`: expected services, `127.0.0.1:5678`, `2.41.5` |
| Remaining Module 0 oracle/adequacy | `tests/test_module_00.py`: 12 PASS, 0 FAIL; all 10 current mutations caught |
| Integrated publication | All 27 scoped gates passed; publisher and exact-byte check passed for 32 instructional pages, 692 raw downloads and 38 UI/generated assets |
| Browser | Every generated setup route opened at the prefixed mount in Full mode; no document-width overflow at 1440 or 390 CSS pixels; long code blocks scroll within their own boxes |

Detailed host-shell and browser observations, native execution IDs and the redacted gate transcript are retained in `../../module-06-batch-workflow/evidence/native/`. Raw runtime secrets, screenshots and renderer output remain outside the checkout.

The first integrated run exposed obsolete A1/A4 scans that treated `printf '%s/get-n8n.sh'` as an executed relative file and A3's blanket ban on `exit`, which rejected safe subshell refusals and the intentional WSL-to-PowerShell return. Those incidental-source tests and their mutations were removed, not re-pinned. The surviving oracle is scoped; it does not certify execution of every platform command. PowerShell argument passing, subprocess stdin and complete-file extraction mistakes in the throwaway harness were corrected before recording the successful matrices.

**Limits:** PowerShell 7 parsing on macOS is not native Windows PowerShell 5.1 verification; controlled Bash/zsh checks use a Docker stub. Native Windows/WSL, Intel macOS, Ubuntu and Arch n8n startup were not observed. Direct course-page screen capture timed out; Chromium screen-media PDF and print output were successfully rendered and visually inspected instead. No new human learner-performance, assistive-technology, paid provider, or hosted-deployment result is claimed.

## Setup guides run end to end — 2026-10-04

The five platform guides were rewritten on 2026-10-03 (commit `e047199`) and had no recorded run. Each Linux route was run top to bottom on a fresh machine by pasting every box exactly as published into a real interactive shell: bracketed paste, one Return, and only the inputs a learner gives (sudo password, the hidden key, `q` in a pager, typed answers). New terminals and re-logins open with a desktop session's environment, and a reboot is a restart of the machine. The harness is `tests/guide_lab/run_guide.py`; per-box results are in `evidence/guide-runs-2026-10-04/`. A box passes only when its exit status and the output its Expected note names both appear.

| Route | Machine | Result |
|---|---|---|
| Ubuntu 24.04, Bash | x86-64 (emulated), systemd | 36 of 36 boxes: steps 1 to 9 with one live readiness call, GitHub access recovery, Obsidian (`.deb`), Docker Engine, n8n 2.41.5 start, saved-workflow restart, and the later-session steps after a reboot |
| Ubuntu 24.04, zsh | x86-64 (emulated) | steps 1 to 5: the PATH line reaches a new zsh window |
| Ubuntu 24.04, Bash | ARM64, systemd | 35 of 35 boxes, including the ARM64 AppImage route |
| Ubuntu in WSL 2 | ARM64; WSL session markers, Windows PATH entries, Xvfb for WSLg, a separate engine in place of Docker Desktop | 26 of 26 Ubuntu-side boxes, including the later session after a restart |
| Windows PowerShell route, Ubuntu part | same WSL machine | 9 of 9 Ubuntu-side n8n boxes and the later session |
| Arch Linux | x86-64 (emulated), no systemd | 34 of 35 boxes through step 13; `course_n8n up -d` can't start containers under emulation |
| Arch Linux ARM, substitute for steps 10 to 15 | ARM64, systemd | 22 of 22 boxes: Docker, group re-login, n8n, saved-workflow restart, and the later-session steps after a reboot |
| macOS | this Mac, throwaway HOME, login zsh windows | 17 of 17 boxes run: steps 1 to 9 with one live call, GitHub access recovery, the Obsidian practice vault, the Docker check, and n8n file generation; the Obsidian `.dmg` box ran in a separate pass |

**Defects found and fixed**

- Arch step 13: the box that runs the reviewed n8n installer had lost its closing `}`, so pasting it left the shell waiting for more input.
- Arch step 14: the project-record write was missing, so `course_n8n` refused every later command.
- Windows step 9: `verify-setup.ps1` held three em dashes; Windows PowerShell 5.1 reads a script without a byte-order mark as ANSI, where they end strings early, so the checker never parsed. The box then printed a stale `REPORT_EXIT 0`. The script is ASCII now, the box resets the exit code first, and it requires a report ending in `SETUP CHECK PASS`.
- WSL: the open-Ubuntu and WSL 1 backup boxes weren't wrapped in `. { }`, so a pasted `Read-Host` took the next line as its answer and a failed backup didn't stop the conversion.
- Ubuntu and WSL ARM64: Obsidian's AppImage starter needs `libz.so`, which only `zlib1g-dev` provides; WSL Ubuntu also lacks FUSE 3. The app never started before; it starts now.
- macOS: BSD `wc -l` pads its count with spaces, so the generate box always reported the wrong number of port lines and stopped. It also generated files while another service held port 5678.
- Windows PowerShell route: the guide didn't reopen Ubuntu after turning on WSL integration.
- Ubuntu, Arch, macOS and the Windows PowerShell route: nothing said how to bring n8n back after a restart; the stack stays stopped, and on Arch Docker does too.
- Module 0 oracle: A11 now parses every shell box, and A12 requires ASCII PowerShell scripts; each has a killing mutation.

**Stand-ins:** the GitHub browser sign-in (a token from an existing `gh` login), the Obsidian window (the same file edits the app makes; the app process was started under Xvfb), the n8n editor (its own owner-setup, workflow and login requests), Docker Desktop on WSL (a separate engine sharing the network, home folder and socket), and, on emulated Arch, starting `dockerd` by hand after the `systemctl` box. Six live readiness calls were made across the final runs.

**Limits:** No native Windows. The PowerShell boxes were parsed and reviewed against Windows PowerShell 5.1 behavior, and the Step 9 logic was exercised in PowerShell 7, but none ran on Windows. Docker containers aren't desktops: no GUI window was inspected, WSL is an emulation, and x86-64 machines ran under emulation on Apple Silicon. On macOS, nothing was installed system-wide, and n8n wasn't started because another session holds port 5678 on this Mac. This is setup execution only, not learner timing or human review.

## Staff-prepared two-service n8n — 2026-10-06 UTC

The active setup uses n8n 2.41.5 and matching external task runners. Staff own Docker preparation, permission/licensing checks, project identity and recovery. Learners run the supplied Python start/status helper, open the editor, save a blank unpublished workflow and observe a staff-assisted restart. The five platform guides no longer provision Assistant, its sandbox services or search.

Private evidence is retained under `~/course-evidence/reformation-qa/20261006T021456Z-simplify-local-n8n/`; the repository ledger records evidence hashes. Historical results above are not inherited.

| Evidence | Observed result |
|---|---|
| Real runtime | Apple Silicon Docker Desktop; exactly n8n and external runners; neither privileged; no host bind mounts or Docker socket; only the n8n editor exposed on loopback |
| Isolated port | Final run used `127.0.0.1:15679`, not the learner port `5678`, to preserve the existing instance. Generated test-form URLs used the isolated port. |
| Runner execution | A real JavaScript Code node returned `42`; the runner registered and executed the task. The live Module 7 run also exercised both authored Code nodes. |
| Persistence | Resumed stopped containers, then removed/recreated only the owned containers without deleting their named volume. All four workflows retained their nodes, connections and unpublished state; the retained OpenRouter credential passed its connection test. |
| Preservation | Real occupied-port and inherited-empty-override checks returned HOLD; the existing user container retained its identity and loopback binding. |
| Regression and course gates | All 19 helper tests passed, including stopped/partial runtime, changed identity/configuration, collision and mount boundaries. All 35 scoped course gates passed. |
| Commands and publication | 472 maintained Bash/PowerShell fences passed 739 parser invocations. Publication and byte checks passed for 35 instructional pages, 437 downloads and 40 assets. |
| Browser | Eleven affected pages at 1440, 390 and 320 pixels in Dark and Sand: 66 live layout observations, no document overflow, five exact platform command-copy checks. |

Real execution exposed and repaired Docker's named-volume representation in `HostConfig.Binds`, POSIX TIME_WAIT port reuse, restart of stopped owned containers, and the advertised form URL on a nondefault port. Direct course-page screenshot capture timed out; Chromium also failed to produce an animation frame after an active-lifecycle reset. Wide Sand setup and narrow Dark Module 7 screen-media PDFs were rendered, rasterized and visually inspected instead. These are PDF renders, not screenshots. An automation clipboard permission denial was recorded, then the copy check passed with explicit permissions; course copy code was unchanged.

**Limits:** This is native Apple Silicon runtime evidence, not native Windows PowerShell 5.1, WSL, Intel macOS, Ubuntu or Arch qualification. PowerShell parsing used 7.6.6 on macOS. Workflows were assembled through the authenticated local n8n API; browser upload, execution, download and close actions were exercised. No measured learner timing, independent human review or assistive-technology result is claimed.
