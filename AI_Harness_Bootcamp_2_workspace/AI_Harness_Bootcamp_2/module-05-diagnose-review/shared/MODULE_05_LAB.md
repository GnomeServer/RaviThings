# Module 5 lab · Orchestrate an OMP agent team

Build a checked status brief for fictional CS-2, carrying IV fluid cases from Basin Depot to Clinic F-9. Inventory, release authority and timing are separate sources. A complete inventory report cannot fill a missing timing handoff.

## Before the first wave

Plan 90–150 minutes. Keep one ordinary terminal open for the four stages. Use Python 3.12+, a latest stable OMP release (the launcher records the observed `omp/<semver>` from a successful `--version`) and the course OpenRouter credential in the current process. Restore a missing prerequisite through [setup](../../module-00-setup/README.md) or [credential handling](../../module-00-setup/shared/CREDENTIALS.md), not by switching providers or borrowing another login.

The launcher starts a fresh isolated OMP runtime for each stage. Your terminal retains the work and evidence paths; the model does not inherit your personal OMP profile.
## Prepare a work attempt

Set `R` to your existing checkout. Change that one path if your checkout is elsewhere. The preparer creates `W` outside the repository and refuses to overwrite an earlier attempt. Stage evidence paths must not already exist; the launcher creates them.

**Terminal:** Bash or zsh, ordinary user.

```bash
R="$HOME/Documents/AIHB_OCT_2026"
PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>/dev/null && break; done)"
[ -n "$PY" ] || { printf '%s\n' 'HOLD: Python 3.12 or newer is required.' >&2; exit 1; }
RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$HOME/course-evidence"
printf '%s\n' "$RUN" > "$HOME/course-evidence/module-05-run"
W="$HOME/course-evidence/module-05-$RUN/work"
E="$HOME/course-evidence/module-05-$RUN/evidence"
FANOUT_E="$E/fanout"
REPAIR_E="$E/repair"
INTEGRATE_E="$E/integrate"
REVIEW_E="$E/review"
"$PY" "$R/shared/prepare_work.py" 05 "$W"
```

**Terminal:** PowerShell, ordinary user.

```powershell
$R = "$HOME\Documents\AIHB_OCT_2026"
$PY = $(foreach ($candidate in 'python3.12','python3','python') { try { $resolved = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0 -and $resolved) { $resolved.Trim(); break } } catch {} })
if (-not $PY) { throw 'HOLD: Python 3.12 or newer is required.' }
$RUN = [guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Force -Path "$HOME\course-evidence" | Out-Null
Set-Content -LiteralPath "$HOME\course-evidence\module-05-run" -Value $RUN
$W = "$HOME\course-evidence\module-05-$RUN\work"
$E = "$HOME\course-evidence\module-05-$RUN\evidence"
$FANOUT_E = "$E\fanout"
$REPAIR_E = "$E\repair"
$INTEGRATE_E = "$E\integrate"
$REVIEW_E = "$E\review"
& $PY "$R\shared\prepare_work.py" 05 "$W"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preparation failed; preserve this attempt.' }
```

**Expected:** `PASS: created` and the absolute work path. The work folder contains two Python controls under `scripts/`, three case sources, four roles, specialist and stage briefs, and an empty `out/`.

**Stop:** Preparation fails, the destination already exists, or the interpreter is not verified. Do not reset the checkout or delete an old work folder. Resolve the prerequisite and choose a new `RUN`.

## Assign ownership and write a complete brief

Open the three specialist briefs under `W/shared/prompts/`: `inventory.md`, `authority.md`, `timing.md`. Read their Input line, target, allowed work, acceptance condition and stop condition. Read the corresponding role definitions under `W/shared/agents/`.

Write a short work plan in your own notes, outside the evidence directories:

1. Name each specialist's input and the fact it owns. Explain why these three assignments can run independently.
2. Draw the join before integration. Name the file's sole writer.
3. Draw the edge from the actual candidate to its reviewer. Explain why putting the reviewer in the first batch would be wrong.
4. State what counts as a complete, accepted handoff and what must happen when one is blocked.
5. Predict which work could remain valid if only Timing's assignment changed.

Rewrite the Target paragraph in `inventory.md` in your own words so a child with no parent conversation can execute it. Keep its Input line, output field names and read-only boundary. Add a specific acceptance sentence that prevents a quantity report from being presented as release authority. Do this **before** dispatch; later edits invalidate the handoff produced from the earlier brief.

Keep the supplied role frontmatter and execution controls unchanged. Leave Timing's Input line unchanged for the first wave. The first run must expose its actual missing-input boundary rather than silently substituting another file.

Use the [native task and role contract](ORCHESTRATION_GUIDE.md#native-task-arguments) when checking whether a brief is self-contained.

## Inspect the frozen inputs

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" "$W/scripts/orchestrate.py" inspect --work "$W"
```

**Terminal:** PowerShell, ordinary user.

```powershell
& $PY "$W\scripts\orchestrate.py" inspect --work "$W"
```

**Expected:** JSON with `status: "PASS"`, release policy `"latest"`, the model, the graph and three assignments. Each assignment identifies its brief, input, existence and fingerprint. Timing names `shared/case/timing-pending.json` and has `source_exists: false`.

Inspect is offline. Its PASS does not prove the installed OMP release, credential, provider access or a child execution; run preflight checks those prerequisites before dispatch.
**Stop:** The graph, assigned paths or permissions differ from your plan, or inspect returns HOLD. **Recover:** Correct the named work brief or restore an accidentally changed control from the supplied preparation source; inspect again before dispatch.

## Run the independent wave

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" "$W/scripts/orchestrate.py" run --work "$W" --evidence "$FANOUT_E" --stage fanout
```

**Terminal:** PowerShell, ordinary user.

```powershell
& $PY "$W\scripts\orchestrate.py" run --work "$W" --evidence "$FANOUT_E" --stage fanout
```

If you maintain multiple OMP installations, `--omp` can name the absolute path to a verified latest stable executable. The launcher records the actual `omp/<semver>` reported by a successful `--version`; it rejects malformed or unsuccessful identity output. Do not treat an unverified global installation as the one under test.

Keep the same OMP version throughout one chain. If you upgrade between stages, start a fresh fanout chain and preserve the earlier evidence; handoffs from different runtime versions cannot be combined.

**Expected for the supplied failure case:** Exit 1 and JSON `status: "HOLD"`; `dispatched` contains inventory, authority and timing; `accepted_roles` contains inventory and authority; `blocked_roles` contains timing. The issue names the missing Timing input. No combined brief is written.

**Stop:** A credential, provider or runtime failure is not this expected case result. **Recover:** Inspect the actual issue, resolve its cause and choose a fresh evidence path. Preserve the failed attempt. Never prewrite a blocked report or modify a result to match the expected state.

## Trace the blocked handoff

Run the independent saved-evidence check, then open the derived handoffs.

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" "$W/scripts/orchestrate.py" check --work "$W" --evidence "$FANOUT_E"
"$PY" -m json.tool "$FANOUT_E/reports.json"
```

**Terminal:** PowerShell, ordinary user.

```powershell
& $PY "$W\scripts\orchestrate.py" check --work "$W" --evidence "$FANOUT_E"
& $PY -m json.tool "$FANOUT_E\reports.json"
```

**Expected:** Check exits 1 with the same two accepted roles and blocked Timing handoff. A child can have native exit code 0 while returning `status: "blocked"`; completion and acceptance are different.

Trace one successful specialist and Timing through these actual files:

| Record | What to establish |
|---|---|
| `policy.json` → `task_call.tasks` | Requested child name, role, complete brief and schema. |
| `guard.jsonl` → `guard_ready` | That child's actual model, role hash and active tools. |
| `guard.jsonl` → `execution_result` | Successful read hash, or Timing's `ok: false`, `code: "ENOENT"` and exact path. |
| `sessions/<parent-session>/Timing.jsonl` | Native read call and failed tool result, followed by the structured yield. Join the tool-call ID to the guard record. |
| `sessions/<parent-session>/Timing.json` | The returned blocked data, not a parent paraphrase. |
| `reports.json` | The original producing attempt/child identity and source-bearing report. |

There is one parent-session directory for this stage. Open it in your file browser or editor; do not substitute a transcript from another attempt.

Write down why the two complete reports are reusable and why integration is not yet allowed. Do not call the missing-input read a denied permission: the read was authorized, actually attempted and failed because the assigned file was absent.

**Stop:** A child session, real read outcome or producing identity is missing or disagrees with the report. **Recover:** Resolve the evidence discrepancy before reuse; choose a fresh run rather than filling missing native records by hand.

## Repair only its assignment

Change the single Input line in `W/shared/prompts/timing.md` from `timing-pending.json` to `timing.json`. Preserve every evidence file and leave the other specialist briefs unchanged.

The bounded replacement below refuses to proceed unless exactly one old Input line exists.

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" -c 'from pathlib import Path; import sys; p=Path(sys.argv[1]); text=p.read_text(encoding="utf-8"); old="Input: shared/case/timing-pending.json"; new="Input: shared/case/timing.json"; assert text.splitlines().count(old)==1, "HOLD: expected exactly one old Input line"; p.write_text(text.replace(old,new,1),encoding="utf-8"); print(new)' "$W/shared/prompts/timing.md"
"$PY" "$W/scripts/orchestrate.py" inspect --work "$W"
```

**Terminal:** PowerShell, ordinary user.

```powershell
@'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
old = "Input: shared/case/timing-pending.json"
new = "Input: shared/case/timing.json"
assert text.splitlines().count(old) == 1, "HOLD: expected exactly one old Input line"
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print(new)
'@ | & $PY - "$W\shared\prompts\timing.md"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: timing assignment was not corrected.' }
& $PY "$W\scripts\orchestrate.py" inspect --work "$W"
```

**Expected:** Timing now names `shared/case/timing.json`, with `source_exists: true` and a changed assignment fingerprint. Inventory and Authority fingerprints remain unchanged. The original blocked attempt remains a record of the original assignment; do not edit it into a successful attempt.

**Stop:** The replacement fails, Timing still lacks its source, or another assignment changed. **Recover:** Correct only the intended Input line. Restore accidentally changed briefs from their first attempt's frozen `inputs/briefs/` copies, then inspect again.

## Run and check selective repair

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" "$W/scripts/orchestrate.py" run --work "$W" --evidence "$REPAIR_E" --stage repair --prior "$FANOUT_E"
"$PY" "$W/scripts/orchestrate.py" check --work "$W" --evidence "$REPAIR_E"
"$PY" -m json.tool "$REPAIR_E/reports.json"
```

**Terminal:** PowerShell, ordinary user.

```powershell
& $PY "$W\scripts\orchestrate.py" run --work "$W" --evidence "$REPAIR_E" --stage repair --prior "$FANOUT_E"
& $PY "$W\scripts\orchestrate.py" check --work "$W" --evidence "$REPAIR_E"
& $PY -m json.tool "$REPAIR_E\reports.json"
```

**Expected:** Run and check exit 0 with `status: "PASS"`; `dispatched: ["timing"]`; `reused: ["inventory", "authority"]`; all three accepted and none blocked.

Compare `attempt_id` and `child_id` for Inventory and Authority with their entries in the first attempt. They must still identify the original producing run. Timing has a new producing attempt and native child session. A matching child name alone is not a matching run identity.

Read Timing's current revision and supersession. Do not select an old fact merely because it looks plausible. `accepted-handoffs.json` is created by a dependent integration/review attempt, not by this check.

**Stop:** A source, brief, role or control changed unexpectedly; a reused result has a new claimed producing identity; extra children ran; or the saved check is HOLD. **Recover:** Resolve the named cause and rerun only invalidated work with fresh evidence before integration.

## Integrate accepted handoffs

Only continue with a checked, current three-specialist set.

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" "$W/scripts/orchestrate.py" run --work "$W" --evidence "$INTEGRATE_E" --stage integrate --prior "$REPAIR_E"
"$PY" "$W/scripts/orchestrate.py" check --work "$W" --evidence "$INTEGRATE_E"
"$PY" -m json.tool "$W/out/status-brief.json"
```

**Terminal:** PowerShell, ordinary user.

```powershell
& $PY "$W\scripts\orchestrate.py" run --work "$W" --evidence "$INTEGRATE_E" --stage integrate --prior "$REPAIR_E"
& $PY "$W\scripts\orchestrate.py" check --work "$W" --evidence "$INTEGRATE_E"
& $PY -m json.tool "$W\out\status-brief.json"
```

**Expected:** Run and check exit 0 with `status: "PASS"`. No specialist is dispatched. The coordinator reads `accepted-handoffs.json` and all three sources, then writes `out/status-brief.json` once. The integration evidence retains a `candidate.json` snapshot.

The brief separates scanned from usable quantity, cites the current release and timing records, and retains all three original handoff identities. Explain why the authority record's later archive receipt timestamp does not override its explicit supersession chain. Explain why technical acceptance can coexist with a movement decision of HOLD.

**Stop:** Any check holds, a required citation is absent, a source changed, or a write occurred outside the single candidate path. **Recover:** Return to the producing work, resolve the discrepancy and create a new integration attempt. Do not ask a reviewer to bless an unaccepted candidate.

## Review the actual candidate

The reviewer is required, read-only and dependent on the actual integrated candidate.

**Terminal:** Bash or zsh, ordinary user.

```bash
"$PY" "$W/scripts/orchestrate.py" run --work "$W" --evidence "$REVIEW_E" --stage review --prior "$INTEGRATE_E"
"$PY" "$W/scripts/orchestrate.py" check --work "$W" --evidence "$REVIEW_E"
"$PY" -c 'from pathlib import Path; import sys; files=list(Path(sys.argv[1]).glob("sessions/*/Review.json")); assert len(files)==1, "HOLD: expected one native review"; print(files[0].read_text(encoding="utf-8"))' "$REVIEW_E"
```

**Terminal:** PowerShell, ordinary user.

```powershell
& $PY "$W\scripts\orchestrate.py" run --work "$W" --evidence "$REVIEW_E" --stage review --prior "$INTEGRATE_E"
& $PY "$W\scripts\orchestrate.py" check --work "$W" --evidence "$REVIEW_E"
@'
from pathlib import Path
import sys
files = list(Path(sys.argv[1]).glob("sessions/*/Review.json"))
assert len(files) == 1, "HOLD: expected one native review"
print(files[0].read_text(encoding="utf-8"))
'@ | & $PY - "$REVIEW_E"
```

**Expected:** CLI run/check exit 0 with `status: "PASS"` and only review dispatched. The separate native review payload has `role: "review"`, `status: "accepted"`, the actual `candidate_sha256`, and no issues. The review reads the candidate, accepted handoffs and current sources; it performs no write.

A reviewer HOLD remains a HOLD. Read its concrete findings. Correct the producing work, preserve the old candidate and evidence, and use fresh evidence paths for the necessary downstream runs. Never alter a review into acceptance or treat a second agent's agreement as source authority.

## Make the human use decision

Write a short decision note outside the evidence directories. Identify the candidate hash and the final checked evidence path. State one of **use as a status brief**, **revise**, or **hold**, with a source-backed reason and the remaining human owner.

Answer these transfer questions in the same note:

- Which native records show that Timing actually failed to read its assigned input?
- Which two reports were retained, and what made their reuse legitimate?
- If Authority changes next, which specialist and downstream results become stale? Which independent work can stay?
- What does the review establish, and what authority does it not establish?

A technical PASS does not grant permission to move goods. This is a fictional status-brief decision only.

## When a stage holds

| Observation | Action |
|---|---|
| Exit 2 with `HOLD: ...` before dispatch | Fix the named prerequisite or dependency. Do not switch model/provider or invent a receipt. |
| First fan-out: two accepted, Timing blocked on the named absent file | Preserve the attempt; correct only the affected assignment and run selective repair. |
| Exit 1 for a failed/aborted/malformed native attempt | Preserve partial records. Diagnose the actual failure; do not assume incomplete evidence is reusable. |
| A saved input, role or brief is stale | Reconsider its consumer and downstream work. Do not relabel an old result as a new run. |
| A native record, prior seal or source citation disagrees | Stop automatic reuse. Resolve the evidence discrepancy. |
| Review holds or candidate bytes changed | Resolve the candidate's producing work and repeat its dependent checks/review with fresh evidence. |
| Evidence destination already exists | Keep it. Choose a new literal path and record that path in your notes. |

Ctrl+C requests a stop during a headless run. Partial records may remain; cancellation does not promise complete child reports or rollback. A separate interactive OMP process cannot attach to this headless team's Agent Hub. [Native supervision and its process boundary](ORCHESTRATION_GUIDE.md#supervise-an-interactive-native-team).

## Retain the handoff

Keep the work plan, edited briefs, four evidence directories, candidate and human decision note. The evidence chain includes frozen policy/inputs, actual native parent and child sessions, guard records, derived handoffs, process outcome and local hashes.

Do not put notes into sealed evidence directories or move those directories while using their recorded prior links. The checker uses their exact identities and locations. A handoff to another person must preserve those locations or explicitly arrange a new checked run; copying files alone is not proof that the workflow was replayed.

## Recover terminal variables

If you open another terminal, reselect the verified interpreter and restore the exact saved attempt. Load the credential into that process using the existing credential procedure. Do not infer the attempt from whichever directory looks newest.

**Terminal:** Bash or zsh, ordinary user.

```bash
PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>/dev/null && break; done)"
[ -n "$PY" ] || { printf '%s\n' 'HOLD: Python 3.12 or newer is required.' >&2; exit 1; }
RUN="$(cat "$HOME/course-evidence/module-05-run")"
W="$HOME/course-evidence/module-05-$RUN/work"
E="$HOME/course-evidence/module-05-$RUN/evidence"
FANOUT_E="$E/fanout"
REPAIR_E="$E/repair"
INTEGRATE_E="$E/integrate"
REVIEW_E="$E/review"
printf '%s\n' "RUN=$RUN" "W=$W" "E=$E"
```

**Terminal:** PowerShell, ordinary user.

```powershell
$PY = $(foreach ($candidate in 'python3.12','python3','python') { try { $resolved = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0 -and $resolved) { $resolved.Trim(); break } } catch {} })
if (-not $PY) { throw 'HOLD: Python 3.12 or newer is required.' }
$RUN = (Get-Content -LiteralPath "$HOME\course-evidence\module-05-run" -Raw).Trim()
$W = "$HOME\course-evidence\module-05-$RUN\work"
$E = "$HOME\course-evidence\module-05-$RUN\evidence"
$FANOUT_E = "$E\fanout"
$REPAIR_E = "$E\repair"
$INTEGRATE_E = "$E\integrate"
$REVIEW_E = "$E\review"
"RUN=$RUN"; "W=$W"; "E=$E"
```

**Expected:** The printed identifier and paths match your retained notes. **Stop:** The saved identifier is missing or identifies a different attempt. **Recover:** Restore the exact identifier and paths from your notes, not the newest directory. If you deliberately chose another evidence path for a later attempt, restore that literal path instead of the default variable above.
