# Cold Foundry facilitator runbook

## Session result

The learner stands up the pinned uncensored model on their own laptop under OMP orchestration, proves a live loopback-only interaction, stops and restores it, and freezes a kit they can use again without the chat that built it. All work is individual within the Thursday session. The package carries everything except the weights. The structure check does not carry out the package's instructions and does not start the service. The learner keeps the kit and the evidence. This is the learner's own capability, not a handoff to another person.
## Staff release validation

Complete the current full lifecycle on every distinct intended runtime/architecture, including the facilitator's machine, before Thursday:

1. Obtain device-owner installation approval and inventory existing tools. Provision only missing tools using the procedure below. Preserve all existing installations and profiles.
2. Have OMP run the lab's readiness prompt before any HF login or download. Retain actual volume free bytes/GiB, installed and available RAM, tool paths/versions/help, workload, and free-endpoint evidence.
3. Let the account owner authenticate and accept repository conditions. Download the fixed revision/filename and verify the real byte count and SHA-256 already in `shared/case/model-card.json`; never replace the identity to admit a file. Preserve incomplete downloads and resume with the same pinned request.
4. Complete verify, wire, learner-approved launch through OMP's named managed service, ownership proof, then health at `127.0.0.1:8080`, context 32768, one real OMP interaction, stop/unreachable, disabled-control refusal, digest-checked restore, byte comparison, frozen copy, cold technical replay and final stop. Record load/probe/interaction timings; no speed guarantee follows from RAM.
5. Use 24 GiB installed RAM as a planning floor. At least 16 GiB but less than 24 GiB is conditional on the full rehearsal. Below 16 GiB, or after any failed full rehearsal, arrange an owner-approved qualified machine. Observing another person's probe loop supports participation but does not establish operating evidence.

Hold the affected lane and release when required machines, approvals, or full current observations are missing. Never bind beyond loopback, change port/context/model, edit the pin, or claim another process's health response as this attempt.
## Provision only missing capstone tools

Use an ordinary account and the Python 3.12+ executable resolved by the selected Module 00 platform route (`PY`). Keep a private record of approval, OS/version/architecture, executable paths and existing versions before making changes. An existing `hf` or `llama-server` is not a missing installation: retain it, inspect version/help, and qualify its complete model run separately. If it fails, obtain an owner decision; do not overwrite it.

### Official Hugging Face CLI

Only when `hf` is missing, choose an approved unused absolute directory. The commands create a separate environment, install the fixed official wheel with digest verification, and retain pip's dependency URLs/hashes in `install.json`. No login or model download occurs. Retain the printed dependency versions too; [pip's installation report](https://pip.pypa.io/en/stable/reference/installation-report/) is an observation, not a lockfile. Freeze the resolved artifacts after successful native rehearsal.

**Terminal: Bash or zsh, ordinary user.**

```bash
printf 'Approved unused HF tool directory: '; IFS= read -r HF_ROOT
"$PY" -c 'from pathlib import Path; import sys; Path(sys.argv[1]).mkdir(parents=True,exist_ok=False)' "$HF_ROOT" &&
"$PY" -m venv "$HF_ROOT/env" &&
"$HF_ROOT/env/bin/python" -m pip --isolated --disable-pip-version-check install --no-input --only-binary=:all: --index-url https://pypi.org/simple --report "$HF_ROOT/install.json" "https://files.pythonhosted.org/packages/33/23/885b3a3b510c305f1d84421913935e19b6a48b93d173a0541674c1e88c2a/huggingface_hub-2.1.1-py3-none-any.whl#sha256=d76fa1d8e6a59e01f012b1d88da604c099c7a0f2e26b1cc7d708f0a4283bd2a2" &&
"$HF_ROOT/env/bin/python" -m pip --isolated freeze --all
```

**Terminal: Windows PowerShell 5.1, ordinary user.**

```powershell
$HF_ROOT = Read-Host 'Approved unused HF tool directory'
& $PY -c 'from pathlib import Path; import sys; Path(sys.argv[1]).mkdir(parents=True,exist_ok=False)' "$HF_ROOT"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: destination must be new.' }
& $PY -m venv "$HF_ROOT/env"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: isolated environment failed.' }
& "$HF_ROOT/env/Scripts/python.exe" -m pip --isolated --disable-pip-version-check install --no-input --only-binary=:all: --index-url https://pypi.org/simple --report "$HF_ROOT/install.json" "https://files.pythonhosted.org/packages/33/23/885b3a3b510c305f1d84421913935e19b6a48b93d173a0541674c1e88c2a/huggingface_hub-2.1.1-py3-none-any.whl#sha256=d76fa1d8e6a59e01f012b1d88da604c099c7a0f2e26b1cc7d708f0a4283bd2a2"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve installation diagnostics.' }
& "$HF_ROOT/env/Scripts/python.exe" -m pip --isolated freeze --all
```

After success, the environment's standard entry point is `env/bin/hf` on Unix or `env/Scripts/hf.exe` on native Windows. Confirm that file exists and save its absolute path as the learner's approved `HF` value. Run its `--version`, `--help` and `download --help` through the lab preflight. Expect 2.1.1 and the `--revision`/`--local-dir` flags; a missing entry point, version mismatch or install failure remains HOLD. Do not activate or edit a global profile to conceal a path problem.

### Official llama.cpp archive

Only when `llama-server` is missing:

1. Select the exact OS/architecture archive and SHA-256 from [VERSIONS](../../module-00-setup/shared/VERSIONS.md#local-model-readiness-lane-module-10). Download that official fixed URL to a new approved staging directory, not a live installation. Retain its source URL, filename, bytes and observed digest.
2. Compare the complete SHA-256 before extraction. On Unix, use `shasum -a 256` or `sha256sum`; on Windows, use `Get-FileHash -Algorithm SHA256 -LiteralPath` with the actual downloaded path. A mismatch is HOLD; never update the expected digest to fit it.
3. Extract the verified `.tar.gz` or `.zip` with the platform archive tool into a new approved per-user directory. Keep the complete archive layout and neighboring libraries; do not copy only the executable or replace system libraries. Inspect the extracted files and record the actual `llama-server`/`llama-server.exe` path—do not guess a Windows install location.
4. Run that exact executable's `--version` and `--help`; confirm build 11146 and `-m`, `--host`, `--port`, `-c`. The lab preflight repeats these observations. Missing native libraries or an architecture mismatch remains HOLD for the device owner.
5. Open a new desktop terminal, give OMP the approved paths when it asks, then complete the lifecycle through the lab prompts in a new terminal and ordinary OMP conversation. Record the archive hash and final binary hash separately. Leave VERSIONS unqualified for any native combination that has not completed this rehearsal.
The b11146 Ubuntu CPU archives are candidates on Linux, not proof of Arch or WSL compatibility. If no suitable official artifact exists for an actual cohort runtime, use only an owner-approved source build pinned to commit `7fe450e19305b828c199d602c23a8337aaa1f03b`, with the official [build instructions at that commit](https://github.com/ggml-org/llama.cpp/blob/7fe450e19305b828c199d602c23a8337aaa1f03b/docs/build.md). Record compiler/native dependencies, build flags and binary hash, then perform the same rehearsal. Do not silently substitute an old package, another model, or a source build for a merely untested archive.

### Qualify the machine, not just the installation

Retain the helper report and complete current lab/package observations outside the repository. Native Windows includes the actual Windows PowerShell 5.1 parser results for the staff installation fences, OMP's managed start/stop and process/listener inspection on that platform, a UTF-8 stop receipt written by OMP in a path containing spaces, actual stop-verifier execution, and the package's real probe during cold replay. Account owners authenticate and accept model conditions themselves; provisioning grants neither account authority nor permission to stop an existing service.
## Thursday delivery route

Total facilitated allocation: 180 minutes (13:30–16:30). The blocks are planning allocations, not measured learner times. Preserve the three-hour block. All work is individual within the Thursday session.

| Block | Allocation | Facilitator action |
|---|---|---|
| Boundary discussion | 20 min | Service rules, uncensored behaviour, the community note as data |
| Account and download | 25 min | Device login, accepted conditions, resumable download |
| Verify and wire | 15 min | Pinned identity check, loopback overlay |
| Bring-up and probe | 25 min | OMP proposes the launch, learner approves, OMP starts its owned managed service, ownership then probe |
| Live interaction and observation | 30 min | One real exchange, observed response/refusal/warning, named boundary |
| Stop and restore | 25 min | OMP stops its owned service with exit/listener/unreachable proof before the receipt, control disable/restore, byte comparison, approved restart and final stop |
| Package freeze and fresh-terminal check | 25 min | Freeze the declared eleven-file bundle, make a digest-checked copy into `F`, then from a new terminal and new ordinary OMP conversation rooted in `F` run `scripts/check_package.py shared/PACKAGE.md` and record the observed result |
| Close | 15 min | Learner confirms the final service is down and records verified identity, live interaction, stop receipt, restore comparison, fresh-terminal structure check, what ran, and unresolved limits in `E/close-out.md` |

## Close-out observations

The learner records the checks they actually ran and their limits. The fresh-terminal structure check confirms named fields and files within `F`. It does not carry out the package's instructions, and it does not hand the model to anyone else. The learner is the one who runs it.

Hold the affected work and name the reason when: the repository conditions are not accepted; the downloaded file's size or digest differs; disk space runs out during download; the server binds any address other than `127.0.0.1`; the endpoint becomes reachable from another machine; a helper pass is forced by editing `model-card.json` or any fixture; the fresh-terminal structure check fails; or access, download, or hardware prevents required steps. Preserve every artifact of a held attempt. Access, hardware, or time misses close as honest HOLD in the session. No one else finishes the attempt, and no work continues after the session.
