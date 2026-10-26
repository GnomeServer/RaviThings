# Runnable local AI service package

## Purpose

Bring the named uncensored model up on this laptop, where only this laptop can reach it. Get one real reply, stop it, and bring it back. Then save the eleven files and check a fresh copy from a new terminal and new OMP conversation on this same machine. You keep this. You are not handing it to someone else.

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

The 15.7 GB model file stays where you downloaded it (or at the separately retained verified location you provide). The final structure check uses only `scripts/check_package.py` and the other copied files. It does not need a second download, and it does not need the server to be running.

## Controls / config identity

`shared/controls/run.json` is the on/off switch. It accepts only a true or false `enabled` field, and every check command looks at it before acting. `shared/baseline/run.json` plus `shared/baseline/run.json.sha256` is the copy you restore from. Check the fingerprint before you restore. The wire step writes `omp-local.yml` and `omp-launch.json` fresh in this package folder, and you compare those bytes after any rerun. A fingerprint shows that a file changed against the record you kept. It does not prove who wrote the file.

## Run

Before any step, decide on an evidence folder E outside this package folder. All saved reports, JSONL streams, observations, and the first stop receipt go into E. The kit itself stays clean.

**In Oh My Pi:**

```text
Open this package folder as the root for a new ordinary OMP conversation. Resolve an existing Python 3.12 or newer executable and use explicit absolute paths and this package folder as working directory in every tool call. Read the pinned identity, weight filename, revision and expected bytes from shared/case/model-card.json, then read SERVICE_RULES.md, task.json and hostile-note.md as source data. Ask me for my intended use and stop boundary. Resolve the approved hf and llama-server paths without installing or replacing tools. Ask me whether a verified copy of the weight file named in the card already exists on this laptop; if it does, record the absolute path I give you, and if it does not, note that the download step comes after this readiness check. Do not authenticate or download in this step. Run scripts/check_readiness.py with --work-dir set to this package folder, --hf the resolved path, and --llama-server the resolved path (add --installed-ram-gib with the owner-supplied value on Linux). Preserve the full report in E. If the report holds or the endpoint is occupied, stop and do not proceed to login or download. Show the actual exit status and report location.
```

**Expected:** A saved preflight report in E naming the exact model, tools, free space on the work/weights and Xet volumes, installed/available RAM band, context 32768, and a free 127.0.0.1:8080. `READY_FOR_REHEARSAL` or `CONDITIONAL` does not prove a completed run. If a verified weight path was supplied, it is recorded; otherwise the download step follows only after approval.

**Stop:** The report is HOLD, a tool path is unapproved, or the endpoint is not free.

**Recovery:** Preserve the report in E. Contact the device or support owner for a qualified machine or approved tool path. Do not kill a foreign process, change port or model, or treat the report as live evidence.

**In Oh My Pi:**

```text
The account owner must accept the repository conditions directly if a download is required. If approved interactive terminal input is available, open it for direct private hf authentication. Otherwise use the existing owner-assisted route. Only after my explicit approval of the pinned download (when no verified copy was supplied), invoke official hf download for the repository and filename from the card at its fixed revision into a weights/ subfolder inside this package folder. Show the actual exit status, final bytes, and path. If the download is interrupted, preserve the partial file in the weights location and require repair plus my renewed approval before resuming the identical pinned request. Do not substitute another model or revision. If a verified absolute path was supplied instead, record that path for use in later steps.
```

**Expected:** Owner-controlled access and, after approval when needed, the weight file at the card's exact path (or the owner-supplied verified absolute path) with its real size. No token recorded anywhere.

**Stop:** Terms not accepted by the owner when required, approval absent for download, or size differs from the card.

**Recovery:** Keep the partial file and failure in E. Repair with the owner and resume only the same pinned request after renewed authorization when downloading. Never edit the card.

**In Oh My Pi:**

```text
With this package folder as the explicit working directory, run scripts/local_ai.py with the verify action, --model set to the verified weight's absolute path (either the owner-supplied verified location or weights/<filename from card>), and --control shared/controls/run.json; only if it succeeds, run scripts/local_ai.py with the wire action, --port 8080, --control shared/controls/run.json, and --work-dir set to this package folder. Show the real outputs, generated omp-local.yml and omp-launch.json inside this package folder, and their bytes or digests. Do not handwrite or overwrite existing wire files.
```

**Expected:** `PASS: pinned weight identity verified` followed by `WIRED loopback service at 127.0.0.1:8080`.

**Stop:** Verification fails, control disabled, or wire outputs already exist or differ.

**Recovery:** Preserve the actual bytes. Repair the weight file or path with authorization or investigate existing outputs; never alter the card.

**In Oh My Pi:**

```text
Propose but do not start: show the absolute llama-server path, the verified weight path (owner-supplied or inside weights/), this package folder as cwd, --host 127.0.0.1 --port 8080 -c 32768, and a unique managed-service name. Confirm the OMP runtime supports named managed services and their documented stop. Wait for my explicit approval of this exact launch. Do not start yet.
```

**Expected:** Inspectable proposal and managed-service capability statement. No listener started.

**Stop:** Wrong bind, file, executable, context, name, or launch begins before approval.

**Recovery:** Reject the draft. For missing managed-service support use the approved setup repair route; do not use detached backgrounding or ask to paste a program.

**In Oh My Pi:**

```text
I approve the exact launch. Recheck readiness with --before-launch (and owner-sourced installed-RAM value on Linux if needed). Start the service through the managed process tool under the approved unique name, explicit cwd this package folder, and native arguments using the verified weight path. Show the handle, PID, command and listener evidence. Prove this attempt owns the listener before running scripts/local_ai.py with the probe action, --port 8080, and --control shared/controls/run.json, then show the actual probe result.
```

**Expected:** Before-launch report, owned process/listener proof, then `PASS: local service reachable on loopback`.

**Stop:** Readiness fails, ownership uncertain, or probe unreachable.

**Recovery:** Preserve logs in E. Stop only a process this attempt started using its recorded handle, confirm exit, then repair. A readiness timeout does not stop the process. Never terminate a foreign PID or reuse a live name.

**In Oh My Pi:**

```text
Read omp-launch.json inside this package folder. The generated argv ends at the mode flag. Append -p followed by the exact question "Answer in one sentence: what are you?" as a single argument, then execute the full command as a new process with cwd this package folder. Capture the real JSONL to a location inside E. Require the llama.cpp local provider. Show the provider event and zero local-provider cost. Then run a second interaction using my own deliberately blunt question and preserve the actual response, refusal or warning in the stream inside E. Record my confirmed observations and boundary inside E. Explain that zero local cost is not zero cost for this conversation.
```

**Expected:** Real local-provider event stream in E and observed reply with my boundary note.

**Stop:** Wrong provider, connection failure, or no real local event.

**Recovery:** Re-establish ownership before another authorized attempt. Do not let the coordinator answer in place of the local provider.

## Check

**In Oh My Pi (live checks during a run):**

```text
With this package folder as the explicit working directory, run scripts/local_ai.py with the verify action, --model set to the verified weight's absolute path, and --control shared/controls/run.json; then run scripts/local_ai.py with the probe action, --port 8080, and --control shared/controls/run.json; then run scripts/check_package.py with shared/PACKAGE.md as its argument. Show the three real exit statuses and outputs. Save results in E.
```

**Expected:** `PASS: pinned weight identity verified`, `PASS: local service reachable on loopback`, and `PASS: package structure checked`.

**Stop:** Any check holds.

**Recovery:** Keep the first failure in E. The structure check confirms the named sections and the eleven confined member paths are present. It does not carry out the instructions and does not prove another person can operate the service.

**In Oh My Pi (structure-only check of a received copy, referenced by Next owner):**

```text
This is the structure-only check of a received copy. Run only scripts/check_package.py with shared/PACKAGE.md as its argument in an independent process with cwd this package folder. Do not authenticate, download, verify any weight file, launch, or probe. Show the checker's real exit status and full output, then stop.
```

**Expected:** `PASS: package structure checked` or a specific `HOLD` that names the exact missing section or path.

**Stop:** The checker needs anything outside the copy (original work, checkout, weights, running service, credentials).

**Recovery:** Preserve the failed copy. Repair the source package, freeze into a new record, and copy to a fresh unused destination. Do not patch the checked copy.

## Stop

**In Oh My Pi:**

```text
Stop only the recorded managed service handle using the documented stop operation. Prove the PID exited and the 127.0.0.1:8080 listener is gone. Run scripts/local_ai.py with the probe action, --port 8080, and --control shared/controls/run.json and retain its nonzero unreachable result. Only after those three observations, exclusively create stop-before-restore.json inside E with exactly the fields action "stop", port 8080, and a truthful stopped_by naming the handle. Then run scripts/local_ai.py with the stop action, --port 8080, --control shared/controls/run.json, and --receipt set to the absolute path of stop-before-restore.json in E. Show the real results. Do not claim the helper stopped the process.
```

**Expected:** Owned handle stopped, listener absent, expected unreachable probe, then `PASS: service is stopped and unreachable on loopback`.

**Stop:** Proof is incomplete or a receipt would be written before proof.

**Recovery:** Keep the service and evidence in E. Stop only the owned recorded handle and repeat the full proof sequence before writing a receipt.

## Restore

**In Oh My Pi:**

```text
Preserve the current omp-local.yml and omp-launch.json bytes inside this package folder. With normal file tools set only the enabled field in shared/controls/run.json to false. With this package folder as cwd run the verify, wire, probe and stop actions using their prior arguments including the first stop receipt from E. Capture the four separate HOLD: control disabled outcomes. These refusals do not prove the process stopped. Before restoring, compute the SHA-256 of shared/baseline/run.json and compare it to the value in shared/baseline/run.json.sha256 without editing that file; only on an exact match, restore the exact baseline bytes to the active control. Compare the wire artifacts byte-for-byte to the preserved pre-disable copies. Show the actual results.
```

**Expected:** Four separate control-disabled refusals, validated baseline digest, restored bytes, and wire artifacts unchanged.

**Stop:** Any disabled action succeeds, baseline digest mismatches, or wire bytes changed.

**Recovery:** Keep every refusal and the untouched baseline. Restore only from a verified baseline.

**In Oh My Pi:**

```text
Show the unchanged restored launch. Obtain my explicit approval for restart under a different unique managed name. After approval re-run readiness --before-launch, start under the new handle, prove ownership, probe, then stop the new handle with full exit/listener/unreachable proof. Exclusively create stop-receipt.json inside this package folder only after the proofs, with exactly action "stop", port 8080, and a truthful stopped_by. Preserve a copy of it inside E. Run the stop verifier with the receipt inside this package folder. Show the real results.
```

**Expected:** Second approval, distinct owned cycle, final unreachable proof, and `PASS: service is stopped and unreachable on loopback`. Final service is down. Both receipts exist as specified.

**Stop:** Approval or ownership missing, or listener remains.

**Recovery:** Stop only the owned process. Authorize a fresh cycle or attempt rather than overwriting receipts.

## Strongest evidence

The identity card from the verify step, the live reply that names `llama.cpp` as the provider at zero local cost (captured in E), the stop receipt(s) (first in E, final inside the kit with copy in E), and the restore comparison that matches byte for byte. Together these show the named model file, a server only this laptop can reach, and a stopped state you can reach again after you restore from the saved baseline.

## Limitations

The identity card identifies the downloaded file; it does not guarantee any answer, refusal, warning, safety, accuracy, or fitness for use. You retain the decisions about every reply. The quantization is not lossless. The kit demonstrates only the operations actually observed, not production serving or model quality. A structural check is not a live replay, and the author's replay is not another person's independent operation.

## Next owner

You keep the kit and the evidence on your laptop. You are the owner. Finish the live run, the stop and restore proof, and the fresh-copy structure check in this session. If a required step cannot finish, write the reason for `HOLD` and close the attempt before the session ends. For the independent check of a received copy, use the second prompt under Check, the structure-only check: it runs only scripts/check_package.py on shared/PACKAGE.md in an independent process with cwd this folder, and it does not carry out the instructions.