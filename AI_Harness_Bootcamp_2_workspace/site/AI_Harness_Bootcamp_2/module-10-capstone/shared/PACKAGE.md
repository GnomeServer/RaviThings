# Runnable local AI service package

## Purpose

Bring the named uncensored model up on this laptop, where only this laptop can reach it. Get one real reply, stop it, and bring it back. Then save the eleven files and check a fresh copy from a new terminal on this same machine. You keep this. You are not handing it to someone else.

## Bounds

One person at a time, and that person is you. The server listens on `127.0.0.1` only. The model file stays on this machine. Don't upload it again, don't share the address, and don't let anyone else send requests to it. Prompts and replies are recorded in the evidence folder. The model is uncensored. Every limit in this section is yours to hold, not the model's.

## Inputs

The fresh copy carries only these eleven files. The model file is not one of them:

- `shared/PACKAGE.md`
- `scripts/local_ai.py`
- `scripts/check_package.py`
- `scripts/check_readiness.py`
- `shared/case/model-card.json`
- `shared/case/SERVICE_RULES.md`
- `shared/case/task.json`
- `shared/case/hostile-note.md`
- `shared/controls/run.json`
- `shared/baseline/run.json`
- `shared/baseline/run.json.sha256`

The 15.7 GB model file stays where you downloaded it. The final check uses only `scripts/check_package.py` and the other copied files. It does not need a second download, and it does not need the server to be running.

## Controls / config identity

`shared/controls/run.json` is the on/off switch. It accepts only a true or false `enabled` field, and every check command looks at it before acting. `shared/baseline/run.json` plus `shared/baseline/run.json.sha256` is the copy you restore from. Check the fingerprint before you restore. The wire step writes `omp-local.yml` and `omp-launch.json` fresh in the work folder, and you compare those bytes after any rerun. A fingerprint shows that a file changed against the record you kept. It does not prove who wrote the file.

## Run

### Resolve the approved tools and check capacity

Open a fresh terminal **inside the received package folder**. Use an owner-approved machine on which staff have provisioned the missing tools and rehearsed this exact model with context 32768. Keep existing installations. If a tool is outside PATH, enter the approved full path when prompted; the quoted variables below preserve spaces and apostrophes. Repeat this resolution in every new terminal.

#### Resolve approved tool paths

**Terminal: Bash or zsh, ordinary user.**

```bash
PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>/dev/null && break; done)"
HF="${HF:-$(command -v hf)}"
LLAMA="${LLAMA:-$(command -v llama-server)}"
if [ -z "$HF" ]; then printf 'Approved hf executable path: '; IFS= read -r HF; fi
if [ -z "$LLAMA" ]; then printf 'Approved llama-server executable path: '; IFS= read -r LLAMA; fi
```

**Terminal: PowerShell, ordinary user.**

```powershell
$PY = $(foreach ($candidate in 'python3.12','python3','python') { try { $resolved = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0 -and $resolved) { $resolved.Trim(); break } } catch {} })
if (-not $PY) { throw 'HOLD: Python 3.12 or newer is required.' }
if (-not $HF) { $HF = (Get-Command hf -CommandType Application -ErrorAction SilentlyContinue).Source }
if (-not $LLAMA) { $LLAMA = (Get-Command llama-server -CommandType Application -ErrorAction SilentlyContinue).Source }
if (-not $HF) { $HF = Read-Host 'Approved hf executable path' }
if (-not $LLAMA) { $LLAMA = Read-Host 'Approved llama-server executable path' }
```

#### Check capacity before a new download

The pre-download policy is 35 GiB total free space on the actual destination and each applicable HF cache volume, not 35 GiB in addition to the weights. At least 16 GiB but less than 24 GiB installed RAM is conditional on a full rehearsal; 24 GiB is a planning floor, not a speed guarantee. Below 16 GiB or after a failed full rehearsal, arrange an owner-approved qualified machine. The check does not authenticate, download, launch, or prove model operation.

With the fixed `--local-dir weights` command, metadata stays under `weights/.cache/huggingface`; an unused Hub file-cache volume is not a weight destination. The preflight measures the actual destination and HF Xet cache.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" scripts/check_readiness.py --work-dir . --hf "$HF" --llama-server "$LLAMA"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY scripts/check_readiness.py --work-dir . --hf "$HF" --llama-server "$LLAMA"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: do not log in, download, or launch.' }
```

**Expected:** Exact tool paths/versions/help flags, actual volume free bytes/GiB, RAM observations, pinned identity, and a free `127.0.0.1:8080`. `READY_FOR_REHEARSAL` or `CONDITIONAL` does not establish a completed rehearsal.

On Linux, obtain the device owner's installed-RAM inventory and add `--installed-ram-gib` followed by that actual value to every preflight invocation. `MemTotal` is usable memory, not installed capacity; never round it up or guess. Retain the inventory source and any VM/container limits in private evidence.

**Stop:** Any prerequisite is held or the endpoint belongs to an existing service.

**Recovery:** Preserve the report and contact the device/support owner. Do not stop someone else's server, change port 8080, lower the context, or substitute a model.

### Download, verify, and wire

Use your own Hugging Face account. Open the model repository page and accept its conditions yourself before downloading. Keep tokens out of commands, notes, and the package.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$HF" auth login &&
"$HF" download orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF "OrcaSAQ-2-27B-Uncensored.gguf" --revision a0ebe1b5ad5c009cd382908585c04b7e9e0cf0c0 --local-dir weights &&
"$PY" scripts/local_ai.py verify --model weights/OrcaSAQ-2-27B-Uncensored.gguf --control shared/controls/run.json &&
"$PY" scripts/local_ai.py wire --port 8080 --control shared/controls/run.json --work-dir .
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $HF auth login
if ($LASTEXITCODE -ne 0) { throw 'HOLD: account access.' }
& $HF download orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF "OrcaSAQ-2-27B-Uncensored.gguf" --revision a0ebe1b5ad5c009cd382908585c04b7e9e0cf0c0 --local-dir weights
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preserve the incomplete download.' }
& $PY scripts/local_ai.py verify --model weights/OrcaSAQ-2-27B-Uncensored.gguf --control shared/controls/run.json
if ($LASTEXITCODE -ne 0) { throw 'HOLD: pinned identity not verified.' }
& $PY scripts/local_ai.py wire --port 8080 --control shared/controls/run.json --work-dir .
```

**Expected:** `PASS: pinned weight identity verified`, then `WIRED loopback service at 127.0.0.1:8080`.

**Stop:** Account access, download, byte count, digest, or wiring fails.

**Recovery:** Keep partial downloads and rerun the same pinned download after resolving the cause. Do not change the identity card or overwrite existing wire outputs. Keep the original failure.

### Start your own server and observe the listener

Read the launch line before running it: this executable, this weight file, `127.0.0.1:8080`, context 32768. Keep this terminal for the server; it does not return a prompt while serving. Repeat the free-endpoint preflight immediately before every start, including a restart after restore.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" scripts/check_readiness.py --work-dir . --hf "$HF" --llama-server "$LLAMA" --before-launch &&
"$LLAMA" -m weights/OrcaSAQ-2-27B-Uncensored.gguf --host 127.0.0.1 --port 8080 -c 32768
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY scripts/check_readiness.py --work-dir . --hf "$HF" --llama-server "$LLAMA" --before-launch
if ($LASTEXITCODE -ne 0) { throw 'HOLD: do not start a server.' }
& $LLAMA -m weights/OrcaSAQ-2-27B-Uncensored.gguf --host 127.0.0.1 --port 8080 -c 32768
```

Wait for this new process to report loading complete and listening. Using the machine's process/network inspector, retain its process ID, executable/arguments and loopback listener as evidence for this attempt. Only then open a second terminal inside the package folder. Run only [Resolve approved tool paths](#resolve-approved-tool-paths) above to set `PY`, `HF`, and `LLAMA`, then run the probe below. Resolving paths does not check capacity or contact the service. Do not run either capacity check against the service you just started.



```bash
"$PY" scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
```

```powershell
& $PY scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
```

**Expected:** `PASS: local service reachable on loopback` after the owned server reports listening. Record actual load time, available RAM and competing workload.

**Stop:** Loading fails, the listener does not belong to this attempt, or the probe is unreachable.

**Recovery:** Preserve the failure and arrange a qualified machine after a failed full rehearsal. Never treat another server's health response as your own bring-up.

### Keep one real OMP interaction

From the second terminal, run the exact command recorded in `omp-launch.json`:

```bash
omp --model llama.cpp/OrcaSAQ-2-27B-Uncensored --config omp-local.yml --no-session --no-title --no-skills --no-rules --no-extensions --no-lsp --no-prewalk --mode json -p "Answer in one sentence: what are you?"
```

```powershell
omp --model llama.cpp/OrcaSAQ-2-27B-Uncensored --config omp-local.yml --no-session --no-title --no-skills --no-rules --no-extensions --no-lsp --no-prewalk --mode json -p "Answer in one sentence: what are you?"
```

**Expected:** A real reply in an event stream naming `llama.cpp`, with zero provider cost. Retain the transcript outside the frozen package. Preserve any refusal or warning as observed.

**Stop:** A context-size refusal or connection failure.

**Recovery:** Preserve the failure. Re-establish the exact service and ownership evidence before another attempt; do not widen the context or bind.

## Check

```bash
"$PY" scripts/local_ai.py verify --model weights/OrcaSAQ-2-27B-Uncensored.gguf --control shared/controls/run.json
"$PY" scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
"$PY" scripts/check_package.py shared/PACKAGE.md
```

```powershell
& $PY scripts/local_ai.py verify --model weights/OrcaSAQ-2-27B-Uncensored.gguf --control shared/controls/run.json
& $PY scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
& $PY scripts/check_package.py shared/PACKAGE.md
```

**Expected:** `PASS: pinned weight identity verified`, `PASS: local service reachable on loopback`, and `PASS: package structure checked`.

**Stop:** Any check holds.

**Recovery:** Keep the first failure. The structure check does not run the commands. It tells you the named sections and files are present. It does not start the server, and it does not mean someone else can run this. You run it. The final fresh-copy check, after you freeze the files, runs only `check_package.py` from the new terminal on the copied files. It does not download anything, and it does not start the server.

## Stop

Interrupt the server process, then prove it stopped.

```bash
"$PY" scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
```

```powershell
& $PY scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
```

**Expected:** The probe exits 1 with `HOLD: service is not reachable`. Only after observing this, write a UTF-8 receipt of the stop you performed:

```bash
"$PY" -c "from pathlib import Path; import json,sys; p=Path(sys.argv[1]); p.write_text(json.dumps({'action':'stop','port':8080,'stopped_by':'operator Ctrl+C at the server terminal'})+'\n',encoding='utf-8'); print(p.read_text(encoding='utf-8'))" "stop-receipt.json"
```

```powershell
& $PY -c "from pathlib import Path; import json,sys; p=Path(sys.argv[1]); p.write_text(json.dumps({'action':'stop','port':8080,'stopped_by':'operator Ctrl+C at the server terminal'})+'\n',encoding='utf-8'); print(p.read_text(encoding='utf-8'))" "stop-receipt.json"
```

**Expected:** The probe exits 1 with `HOLD: service is not reachable`. Only after observing this, write a UTF-8 receipt of the stop you performed:

```bash
"$PY" scripts/local_ai.py stop --port 8080 --control shared/controls/run.json --receipt stop-receipt.json
```

```powershell
& $PY scripts/local_ai.py stop --port 8080 --control shared/controls/run.json --receipt stop-receipt.json
```

**Expected:** `PASS: service is stopped and unreachable on loopback`. If you do not have that line, you do not have a stopped server.

**Stop:** The check still says the server can be reached.

**Recovery:** Stop the server process and check again. Do not record a stop that did not happen.

## Restore

Run these commands only after the server is stopped. Save the wire bytes, validate the frozen control baseline, restore the control, and compare the wire bytes:

```bash
"$PY" - <<'PY'
from pathlib import Path
import hashlib, json
before = {name: Path(name).read_bytes() for name in ('omp-local.yml', 'omp-launch.json')}
root = Path.cwd().resolve()
source = root/'shared/baseline/run.json'
target = root/'shared/controls/run.json'
raw = source.read_bytes()
listed = (root/'shared/baseline/run.json.sha256').read_text().split()[0]
if hashlib.sha256(raw).hexdigest() != listed:
    raise SystemExit('HOLD: baseline digest invalid')
target.write_bytes(raw)
if any(Path(name).read_bytes() != raw for name, raw in before.items()):
    raise SystemExit('HOLD: wire bytes changed')
print('RESTORE OK; wire bytes unchanged')
PY
```

```powershell
@'
from pathlib import Path
import hashlib
before = {name: Path(name).read_bytes() for name in ('omp-local.yml', 'omp-launch.json')}
root = Path.cwd().resolve()
source = root/'shared/baseline/run.json'
target = root/'shared/controls/run.json'
raw = source.read_bytes()
listed = (root/'shared/baseline/run.json.sha256').read_text().split()[0]
if hashlib.sha256(raw).hexdigest() != listed:
    raise SystemExit('HOLD: baseline digest invalid')
target.write_bytes(raw)
if any(Path(name).read_bytes() != raw for name, raw in before.items()):
    raise SystemExit('HOLD: wire bytes changed')
print('RESTORE OK; wire bytes unchanged')
'@ | & $PY -
```

Restoring the control does not restart the server. In its separate terminal, repeat **Start your own server and observe the listener**, including the before-launch preflight and process/listener evidence. Then probe from this terminal:

```bash
"$PY" scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
```

```powershell
& $PY scripts/local_ai.py probe --port 8080 --control shared/controls/run.json
```
**Expected:** `RESTORE OK; wire bytes unchanged`, followed by a reachable probe from the newly started owned server. After retaining the restored-service evidence, repeat **Stop** and retain the final unreachable proof.

**Stop:** The baseline fingerprint fails, the check fails, or the wire bytes differ.


**Stop:** The baseline fingerprint fails, the check fails, or the wire bytes differ.

**Recovery:** Keep every file from the failed attempt. Do not run the next command after a failed restore.

## Strongest evidence

The identity card from the verify step, the live reply that names `llama.cpp` as the provider at zero cost, the stop receipt, and the restore comparison that matches byte for byte. Together these show the named model file, a server only this laptop can reach, and a stopped state you can reach again after you restore from the saved baseline.

## Limitations

The identity card identifies the downloaded file; it does not guarantee any answer, refusal, warning, safety, accuracy, or fitness for use. You retain the decisions about every reply. The quantization is not lossless. The kit demonstrates only the operations actually observed, not production serving or model quality. A structural check is not a live replay, and the author's replay is not another person's independent operation.

## Next owner

You keep the kit and the evidence on your laptop. You are the owner. Finish the live run, the stop and restore proof, and the fresh-copy check in this session. If a required step cannot finish, write the reason for `HOLD` and close the attempt before the session ends.
