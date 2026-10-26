# Module 3 · Research the notes, then limit what the AI can touch

You’ll connect the assistant to a folder of notes, research a supply problem, and check the markings it proposes. Then you’ll limit what that connection can do, remove it, and show the tools are gone.

You’re a staff action officer in Task Force Marlin at Forward Base Brandt. Clinic B-2 is running low on burn-dressing cases. The Base Medical Logistics Officer wants to know what is known about getting 40 cases from Mill Depot to the clinic by 100600Z October 2026, what blocks the move, and what is still unknown. Forty notes in `Sources` hold the evidence. A partner medical cell wants a short extract, and only the Release Authority may decide what leaves the task force. The case is fictional and stays in class.

The connection is a small program on your laptop that reads and writes those notes. `mcp.json` names the program your machine will start. Turning it on means you agree to let that program run as you. The notes live in an Obsidian vault, which is just a folder of Markdown files. Obsidian shows the links between them.

Plan for about three hours on Tuesday (a rough estimate).

You’ll do seven things:

1. Make a work copy and open the notes.
2. Read what the connection claims before you turn it on.
3. Write what it may do, then prove the limits.
4. Mark six notes yourself before the assistant works.
5. Research through the connection and read what it wrote.
6. Check its markings against the rules, then narrow the connection for the partner extract.
7. Disconnect, show that nothing is connected, and hand off.

## Prepare the work copy and open the vault

Use the checkout, Python, and OMP you already checked in [setup](../../module-00-setup/README.md), and your OpenRouter key. You enter the key in the terminal rather than save it in a file. Open an ordinary terminal. The commands work from any directory. `W` is your work copy. `E` is where you keep the check results, your frozen markings, your notes about the connection, and one folder per live run. The launcher creates those run folders itself.

**Terminal: Bash or zsh, ordinary user.**

```bash
R="$HOME/Documents/AIHB_OCT_2026"
PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; sys.exit(1) if sys.version_info < (3, 12) else print(sys.executable)' 2>/dev/null && break; done)"
[ -n "$PY" ] || echo 'HOLD: Python 3.12 or newer is required.' >&2
M="$R/AI_Harness_Bootcamp_2/module-03-mcp-research"
RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$HOME/course-evidence" && printf '%s\n' "$RUN" > "$HOME/course-evidence/module-03-run" && printf 'RUN=%s\n' "$RUN"
BASE="$HOME/course-evidence/module-03-$RUN"
W="$BASE/work"
E="$BASE/receipts"
"$PY" "$R/shared/prepare_work.py" 03 "$W" && mkdir -p "$E"
```

**Terminal: PowerShell, ordinary user.**

```powershell
$R = "$HOME\Documents\AIHB_OCT_2026"
$PY = $(foreach ($candidate in 'python3.12','python3','python') { try { $resolved = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0 -and $resolved) { $resolved.Trim(); break } } catch {} })
if (-not $PY) { throw 'HOLD: Python 3.12 or newer is required.' }
$M = "$R\AI_Harness_Bootcamp_2\module-03-mcp-research"
$RUN = [guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Force -Path "$HOME\course-evidence" | Out-Null; Set-Content -LiteralPath "$HOME\course-evidence\module-03-run" -Value $RUN; "RUN=$RUN"
$BASE = "$HOME\course-evidence\module-03-$RUN"
$W = "$BASE\work"
$E = "$BASE\receipts"
& $PY "$R\shared\prepare_work.py" 03 "$W"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: preparation failed.' }
New-Item -ItemType Directory -Path $E | Out-Null
```

**Expected:** The terminal prints `RUN=` and this attempt's identifier, followed by `PASS: created` and the work path. It then prints two `Next` commands; you can ignore them because the next step runs the inspector itself. In your file browser, `W` holds `vault`, `mcp.json`, `AUTHORITY.md`, `shared/mcp`, and `shared/prompts`. The vault's `Drafts` and `Estimate/Releasable` folders also exist and are empty.

**Stop:** Preparation fails, the destination already exists, or a path is inside the checkout instead of this external attempt.

**Recovery:** Keep the existing attempt. Repair the prerequisite, then repeat this block to choose a fresh `RUN`. Never reset or clean the checkout to make an external attempt possible.

Install Obsidian from [obsidian.md](https://obsidian.md) if you don’t have it. You don’t need an account, Sync, or a plugin. Open Obsidian, choose **Open folder as vault**, and select the `vault` folder inside `W`. Keep Restricted mode on so no community plugin runs. If you can’t install Obsidian, open the same folder in a text editor and work from the file list. You’ll lose the backlinks and the graph. Nothing else changes.

In the vault, read `Start here`, then `Handbook/Handling rules`. The rules are numbered H1 to H7. They use OPEN, PARTNER, and STAFF. Those stand for real ideas, but they are not a real marking system. Mark six notes yourself before the assistant marks all forty.

Obsidian writes a hidden `.obsidian` folder into the vault. The connection never serves it, and the launcher ignores it. Leave Obsidian idle during a live run. The launcher compares the vault before and after. If you edit a note mid-run, that edit shows up as a change you can’t explain.

### If you open a new terminal

A closed terminal forgets these variables. In a new terminal, run this block to reload them for the same attempt instead of preparing another one. It reads the attempt identifier that the first block saved.

**Terminal: Bash or zsh, ordinary user.**

```bash
R="$HOME/Documents/AIHB_OCT_2026"
PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; sys.exit(1) if sys.version_info < (3, 12) else print(sys.executable)' 2>/dev/null && break; done)"
[ -n "$PY" ] || echo 'HOLD: Python 3.12 or newer is required.' >&2
RUN="$(cat "$HOME/course-evidence/module-03-run")"
M="$R/AI_Harness_Bootcamp_2/module-03-mcp-research"
BASE="$HOME/course-evidence/module-03-$RUN"
W="$BASE/work"
E="$BASE/receipts"
printf '%s\n' "RUN=$RUN" "W=$W"
```

**Terminal: PowerShell, ordinary user.**

```powershell
$R = "$HOME\Documents\AIHB_OCT_2026"
$PY = $(foreach ($candidate in 'python3.12','python3','python') { try { $resolved = & $candidate -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0 -and $resolved) { $resolved.Trim(); break } } catch {} })
if (-not $PY) { throw 'HOLD: Python 3.12 or newer is required.' }
$RUN = (Get-Content -LiteralPath "$HOME\course-evidence\module-03-run" -Raw).Trim()
$M = "$R\AI_Harness_Bootcamp_2\module-03-mcp-research"
$BASE = "$HOME\course-evidence\module-03-$RUN"
$W = "$BASE\work"
$E = "$BASE\receipts"
"RUN=$RUN"; "W=$W"
```

**Expected:** The terminal prints `RUN=` followed by the identifier you saw when you prepared this attempt, then `W=` followed by the existing work folder.

**Stop:** The identifier differs from the one you recorded, or the folder named after `W=` does not exist.

**Recovery:** A different identifier means a later attempt overwrote the saved marker; set `RUN` by hand to the value you recorded and run the block again. A missing folder means the attempt was never prepared, so prepare it with the first block.

### Enter your key in this terminal

Enter the key through a hidden prompt. The launcher reads your OpenRouter key only from this terminal's environment. Paste the first command, press Enter, type or paste the key (it shows nothing), press Enter, then paste the second block.

**Terminal: Bash or zsh, ordinary user.**

```bash
IFS= read -r -s OPENROUTER_API_KEY
```

**Terminal: PowerShell, ordinary user.**

```powershell
$secret = Read-Host 'OpenRouter key' -AsSecureString
```

**Expected:** The terminal waits silently for the key, then returns to its ordinary prompt without showing the value.

**Stop:** Characters appear as you type, or you are not sure which program is reading the input.

**Recovery:** Cancel with Ctrl+C and close that terminal. If the value was shown, revoke the key at OpenRouter and use a replacement.

**Terminal: Bash or zsh, ordinary user.**

```bash
export OPENROUTER_API_KEY
if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; else printf 'MISSING\n'; fi
```

**Terminal: PowerShell, ordinary user.**

```powershell
$bstr = [IntPtr]::Zero
try {
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
  $env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
  if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  if ($secret) { $secret.Dispose() }
  Remove-Variable secret,bstr -ErrorAction SilentlyContinue
}
if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) { 'MISSING' } else { 'SET' }
```

**Expected:** `SET` proves the key is present in this terminal, but not that it is valid or has credit.

**Stop:** `MISSING`, or any part of the key appears in the output.

**Recovery:** Repeat the hidden prompt in this terminal. Never print the environment to troubleshoot a key, and never save the key in a file or a shell profile.

## Read what the connection claims before you turn it on

Read what it claims before you turn it on. It will tell the assistant its name, a block of instructions, and a short description of each tool, including whether a tool only reads. The assistant takes those descriptions at face value. This check starts only the supplied program from your work copy and refuses any other.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/mcp_inspect.py" --config "$W/mcp.json" --out "$E/contract-inspection.json"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\mcp_inspect.py" --config "$W\mcp.json" --out "$E\contract-inspection.json"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the inspection failed; preserve this attempt.' }
```

**Expected:** The inspector prints the server's instructions and a table of twelve tools. Its two columns show whether each tool claims to be read-only and whether it can change notes. The `FINDINGS` list has two entries: one names a tool marked read-only whose own description says it adds and removes tags, and the other says the server's instructions steer the model toward changing the vault.

**Stop:** The inspector prints `HOLD` or refuses the entry, or the findings list is empty.

**Recovery:** A refusal means `mcp.json` points to a program other than the supplied server in your work copy. Do not edit the inspector. Prepare a fresh work copy because this check is meant to stop a connection entry from starting another program.

![Check what each tool can actually change. A read-only label, or the program’s own instructions, does not enforce your limits.](figures/m03-contract-authority.png)

*Check what each tool can actually change. A read-only label, or the program’s own instructions, does not enforce your limits.*

<details markdown="1">
<summary>Figure text</summary>

`manage_tags` says it only reads, but its description says it adds or removes tags. Check what each tool does. Don’t trust the read-only label by itself. The program’s instructions can also steer the assistant. They don’t give permission, and they don’t enforce your limits.

</details>

Write `contract.md` in `E` and answer three questions in your own words. What will the assistant be told if you pass those instructions along? Which tools can change a note? Which tool is marked read-only even though its description says it changes notes, and what could go wrong if you trusted that mark? Name `manage_tags` and the instructions. Write at least forty words. A shorter note fails the final check.

## Write what the connection may do, then prove the limits

The assistant might never try a forbidden action, so a clean run proves little. A probe tries each forbidden action without the assistant, on a throwaway copy of the notes, and records what happens. Write your limits first so the probe can judge the connection against them.

![Three stops, in order. A tool you leave off the list is never sent. A guard can stop a call before the program sees it. The program can refuse a folder or a write and leave the files alone.](figures/m03-authority-layers.png)

*Three stops, in order. A tool you leave off the list is never sent. A guard can stop a call before the program sees it. The program can refuse a folder or a write and leave the files alone.*

<details markdown="1">
<summary>Figure text</summary>

A request hits three stops before it can change a file. First, is the tool even offered? Second, does the guard stop it? Third, does the program itself refuse the folder or the kind of write? A tool you left off the list is never sent. The guard can stop a call before the program sees it. The program can refuse a call and leave the files alone. Once a call is stopped, it goes no further. If the program never saw the call, look at the probe record. If it did see the call, look at its log and the files, even when it said no. The program can’t record a call it never got.

</details>

Open `W/shared/prompts/RESEARCH.md`. List every folder the prompt tells the assistant to read and every folder it tells the assistant to write. Use those folders, and no others, for this part of the work. From the tool table, allow only the tools that work needs. Then open `W/AUTHORITY.md` and fill in its one JSON block with `"phase": "research"`, your tools, your two folder lists, and `"create_only": true`. That last setting means an existing note can never be changed. The table in the file shows which setting in `mcp.json` matches each field. Leave `mcp.json` unchanged for now.

Run the probe against the connection as it stands, with no limits yet.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/authority_probe.py" --config "$W/mcp.json" --authority "$W/AUTHORITY.md" --vault "$W/vault" --out "$E/probe-raw.json"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\authority_probe.py" --config "$W\mcp.json" --authority "$W\AUTHORITY.md" --vault "$W\vault" --out "$E\probe-raw.json"
if ($LASTEXITCODE -ne 1) { throw 'HOLD: the unbounded probe was expected to report HOLD.' }
```

**Expected:** The probe ends with `HOLD`. Several attempts show `BREACHED`: one overwrites a source note, one creates a note outside your write folder, and one reads a note from a folder you did not declare. Tools left off your list show `HELD` by the allow-list. The allow-list stops whole tools, but it cannot stop `write_note` from writing to the wrong folder while the server has no folder limit.

**Stop:** The probe ends with `PASS`, or it refuses your declaration.

**Recovery:** If the declaration is refused, the message names the field to fix. If the probe passes, `mcp.json` already carries limit arguments. Rename the result to `probe-raw-attempt-1.json` and keep it, remove those arguments so only the server script, `--root`, and the vault path remain, and run the probe again into `probe-raw.json`.

Now make the connection match what you wrote. In `W/mcp.json`, use the table in `AUTHORITY.md` to add the limit arguments to the server’s `args` list, after the vault path that follows `--root`. A folder limit takes two list items: the flag and the folder, each in its own quotes, separated by commas. A flag with no value takes one item. For example, a connection that may read one folder named `Example/` and never change an existing note would end its list with `"--read-prefix", "Example/", "--no-overwrite"`. Repeat a flag once for each folder. Decide whether `"instructions"` stays `true`, then run the probe again.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/authority_probe.py" --config "$W/mcp.json" --authority "$W/AUTHORITY.md" --vault "$W/vault" --out "$E/probe-research.json"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\authority_probe.py" --config "$W\mcp.json" --authority "$W\AUTHORITY.md" --vault "$W\vault" --out "$E\probe-research.json"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the research limits did not hold; preserve this attempt.' }
```

**Expected:** `PASS: no forbidden attempt had an effect`, with every forbidden attempt `HELD` and the permitted reads and the new-note write marked `WORKS`.

**Stop:** The probe ends with `HOLD`, lists a `BREACHED` attempt, or reports that a permitted action is `UNAVAILABLE`.

**Recovery:** A `BREACHED` line names the attempt, so find the flag that should have stopped it. An `UNAVAILABLE` permitted action means a limit is tighter than the work needs. Rename the held result, for example to `probe-research-attempt-1.json`, keep it, and run the probe again into `probe-research.json`.

![Deleting a source is stopped by the tool list in both checks, so that row can’t tell you how the program would answer. Only the stretch sends that call to the program.](figures/m03-probe-proof.png)

*Deleting a source is stopped by the tool list in both checks, so that row can’t tell you how the program would answer. Only the stretch sends that call to the program.*

<details markdown="1">
<summary>Figure text</summary>

The check tries four forbidden actions on an open connection and on a limited one. Reading outside the folders, overwriting a source, and creating a note outside the write folder each show `BREACHED` when the connection is open and `HELD` when it is limited. Deleting a source shows `HELD (allow-list)` both times, because you left deletion off the tool list. That call was never sent: `server.outcome` is `NOT_SENT`, so this result doesn’t tell you how the program would answer. Only the stretch, run with `--ignore-allow-list`, sends the delete to the program. Its evidence is the program’s refusal and a check that the files didn’t change. Actions you allowed must still work. A limit that blocks needed work is too tight.

</details>

<details class="rf-stretch" markdown="1">
<summary>Stretch: see what the program itself stops</summary>

## Stretch: see what the program itself stops

The tool list is one stop. The program’s own limits are another. Run the research probe again on the limited connection with the tool list ignored, so every attempt, including the tools you left off, reaches the program.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/authority_probe.py" --config "$W/mcp.json" --authority "$W/AUTHORITY.md" --vault "$W/vault" --out "$E/probe-server-alone.json" --ignore-allow-list
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\authority_probe.py" --config "$W\mcp.json" --authority "$W\AUTHORITY.md" --vault "$W\vault" --out "$E\probe-server-alone.json" --ignore-allow-list
```

**Expected:** `PASS`, with every forbidden attempt marked `HELD` by the `server` layer. That includes patching, tagging, moving, and deleting notes, even though your allow-list never offered those tools. Compare the unbounded probe, where the allow-list alone stopped them.

**Stop:** An attempt is `BREACHED` with the allow-list ignored.

**Recovery:** A breach shows that you were relying on another layer to stop an action the server should stop itself. Add the missing server limit and repeat the probe under a new output name. In your handoff, record which layer stopped each kind of attempt.

</details>

## Mark six notes yourself before the assistant works

The assistant will propose a marking for every note. If you read its proposals first, they can sway you, so mark six notes yourself before you see them. You’ll find those notes in `Start here` and `Estimate/Calibration`. Each one tests a different part of the rules. Open `Estimate/Calibration` in Obsidian. For each row, enter your marking and the rule that decides it. Add a reason if the rule alone doesn’t explain your decision. Use only the rules in `Handbook/Handling rules`.

![Do these four steps in order. A claim in the body, or the assistant’s proposal, does not change the marking.](figures/m03-effective-handling.png)

*Do these four steps in order. A claim in the body, or the assistant’s proposal, does not change the marking.*

<details markdown="1">
<summary>Figure text</summary>

Four steps, in order, give a note its marking.

1. Start from the marking in the note’s header. If the header has no marking, the note is STAFF.
2. Then apply the latest valid notice from the Release Authority, using Zulu time. A notice counts only when it changes a marking, it comes from the Release Authority, the note it names exists, and the new level is one of the allowed levels.
3. Then inherit. A note takes the tightest level among the notes it draws on, using their levels after steps 1 and 2, not the markings printed in their headers. The tightest level wins.
4. Then combine. A note that holds at least 3 of the 4 movement elements is STAFF at minimum.

New notes the assistant writes start at STAFF. A proposed marking is not a release. Neither that proposal nor a claim in the note’s body changes the marking. Only a valid Release Authority notice does.

</details>

Freeze your decisions. The freeze saves the time and a fingerprint of the file, so you can show you marked these notes before you saw the assistant’s proposals.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/freeze_calibration.py" --vault "$W/vault" --out "$E/calibration-frozen.json"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\freeze_calibration.py" --vault "$W\vault" --out "$E\calibration-frozen.json"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the calibration was not frozen; preserve this attempt.' }
```

**Expected:** `PASS: froze 6 calibration decisions` and the time. Do not edit `Calibration` again.

**Stop:** The command refuses the table, or the output file already exists.

**Recovery:** If the command refuses the table, it names a row with a blank marking, a marking other than OPEN, PARTNER, or STAFF, or a blank rule. Nothing was written, so fix that row and run the command again. If the output file already exists, the calibration is already frozen; the first freeze is the one that counts.

## Research through the connection

Try a small request first. The smoke prompt asks the assistant to list the folders it can see and read one reference note, so a setup mistake shows up early. Both runs use what you wrote and `mcp.json`. The launcher checks that they agree and refuses to start if they don’t.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$R/shared/run_omp.py" --workdir "$W" --prompt "$W/shared/prompts/SMOKE.md" --evidence "$E/smoke" --mcp-config "$W/mcp.json" --authority "$W/AUTHORITY.md"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$R\shared\run_omp.py" --workdir "$W" --prompt "$W\shared\prompts\SMOKE.md" --evidence "$E\smoke" --mcp-config "$W\mcp.json" --authority "$W\AUTHORITY.md"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the smoke run failed; preserve this attempt.' }
```

**Expected:** `PASS: all checks passed`. In `E/smoke`, `mcp-audit.jsonl` is the server's own record of what it was asked, and `response.md` holds the model's answer. That answer should name only folders you declared readable.

**Stop:** The launcher prints `HOLD`, exits with 2, or the answer names a folder you did not declare.

**Recovery:** A message beginning `read limits differ` or `write limits differ` points to the field where `AUTHORITY.md` and `mcp.json` disagree. Fix the wrong file. The probe fingerprints both files, so rename `probe-research.json` to `probe-research-attempt-1.json`, run the research probe again into `probe-research.json`, and then repeat the smoke test. If a run was incomplete, keep its folder by renaming it `smoke-attempt-1`, then run again into `E/smoke`.

Now run the research. The prompt asks the assistant to read every source note, write findings linked to their sources, list what is still unknown, and propose a marking for all forty notes. Two notes talk about automation directly. The prompt tells the assistant to treat what the notes say as information, not as orders. Leave Obsidian idle until the run ends.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$R/shared/run_omp.py" --workdir "$W" --prompt "$W/shared/prompts/RESEARCH.md" --evidence "$E/research" --mcp-config "$W/mcp.json" --authority "$W/AUTHORITY.md"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$R\shared\run_omp.py" --workdir "$W" --prompt "$W\shared\prompts\RESEARCH.md" --evidence "$E\research" --mcp-config "$W\mcp.json" --authority "$W\AUTHORITY.md"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the research run failed; preserve this attempt.' }
```

**Expected:** `PASS: all checks passed`, and a `Drafts/research` folder in the vault with at least six `fact-` notes, `open-questions`, and `handling-proposal`. The run can take several minutes.

**Stop:** The launcher prints `HOLD`, a run ends before the model finishes, or any source note changed.

**Recovery:** Rename the held folder `research-attempt-1` and keep it. Move any notes the run created under `Drafts/research` into that folder because the server will not replace a note that already exists. Then run again into `E/research`. Never repair a changed source note by hand. A changed source means a limit failed, so keep the receipts and stop.

Now read what the assistant wrote in Obsidian. Open `Drafts/research/open-questions`, then each fact note. Click a `[[KH-…]]` link to open the source it cites. Open the Backlinks pane on a source note to see which findings cite it. Open the Graph view to spot source notes that no finding mentions. Search the vault for `QA hold`, `deadlined`, and `MLC`. Pick two conflicts and check what the assistant claimed against the sources. Candidates: which stock count is current, whether the lot on hand is the lot that can be issued, whether the truck on the convoy table can run, whether the bridge on the main route takes its weight, and whether the approved flight falls inside the dust forecast. A finding you can’t trace to a source note is not yet a finding.

Open `E/research/mcp-audit.jsonl` and look for rows with `"allowed": false`. Each one is a call the program refused. If you see none, the assistant never tried anything outside its limits during this run. Your probe is what shows the limits hold.

A quoted instruction in a source does not change what the connection may do. Check which calls were made and what changed on disk. If you didn’t see an attempt, don’t claim one happened.

## Check the assistant’s markings against the rules

Treat the proposal as a proposal. Under rule H6, only the Release Authority changes a marking. If you accept the proposal without checking it, the mistake is yours. A summary may need a tighter marking than any of its source notes. Three facts may each be safe to share alone: a place, a time with a zone, and a named route. Together, they can tell a reader where and when a convoy moves.

![When any three movement details land in one note, that note is STAFF at minimum, even if each source note is OPEN or PARTNER.](figures/m03-aggregation.png)

*When any three movement details land in one note, that note is STAFF at minimum, even if each source note is OPEN or PARTNER.*

<details markdown="1">
<summary>Figure text</summary>

There are four movement details: a location grid, a time with a zone letter, a named route, and a quantity or lot. When any three of the four land in one note, that note is STAFF at minimum. Separate notes that each hold one detail, kept apart, are not one product, so this rule doesn’t apply to them. Shareable parts don’t make a shareable combination.

</details>

Copy the assistant’s proposal into your register beside your first markings. The command fills only the `AI proposed` column.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/seed_register.py" --vault "$W/vault"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\seed_register.py" --vault "$W\vault"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the register was not seeded; preserve this attempt.' }
```

**Expected:** `PASS: filled the AI proposed column for 40 of 40 notes`, with `Final`, `Rule`, and `Reason` still empty.

**Stop:** The command cannot find the proposal, or reports notes without a usable proposal.

**Recovery:** A missing proposal means the research run did not write `Drafts/research/handling-proposal`; look at that run's receipts before running it again. For a note without a usable proposal, leave the cell empty and decide the note from the rules.

Open `Estimate/Handling register` in Obsidian and set `Final` for all forty notes. Start with the six you marked and any note where your marking differs from the assistant’s proposal. If `Final` differs from the proposal, name the rule that decides it, one of H1 to H7, and give a one-sentence reason. Read each note’s header as well as its body. Words in the body that claim clearance don’t change a marking. Only a valid notice from the Release Authority counts. Compare times in Zulu.

Then copy the notes you marked OPEN or PARTNER into `Estimate/Releasable`.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/stage_releasable.py" --vault "$W/vault"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\stage_releasable.py" --vault "$W\vault"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the releasable folder was not staged; preserve this attempt.' }
```

**Expected:** An `added` line and a `removed` line, then `PASS: Estimate/Releasable/ holds N notes, the ones you marked OPEN or PARTNER`, where N is your own count. The folder holds byte-identical copies of exactly those notes.

**Stop:** The command lists notes whose `Final` is blank or not OPEN, PARTNER, or STAFF.

**Recovery:** Fix the rows it names and run it again; it adds missing copies and removes stale ones. It never changes `Sources`.

## Narrow the connection for the partner extract

Read `W/shared/prompts/PARTNER_EXTRACT.md` and set the new folders the same way you did for research. Allow reads only from material the extract may use, and writes only to the folder the prompt names. Change `phase` to `partner` in `AUTHORITY.md` and update its tools and folders. Then set the program’s arguments in `mcp.json` to match. If this part can still read `Sources`, it could repeat a STAFF fact no matter how carefully the extract is worded.

Prove the new limits before the live run, then run the partner phase.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/authority_probe.py" --config "$W/mcp.json" --authority "$W/AUTHORITY.md" --vault "$W/vault" --out "$E/probe-partner.json" \
  && "$PY" "$R/shared/run_omp.py" --workdir "$W" --prompt "$W/shared/prompts/PARTNER_EXTRACT.md" --evidence "$E/partner" --mcp-config "$W/mcp.json" --authority "$W/AUTHORITY.md"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\authority_probe.py" --config "$W\mcp.json" --authority "$W\AUTHORITY.md" --vault "$W\vault" --out "$E\probe-partner.json"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the partner limits did not hold; preserve this attempt.' }
& $PY "$R\shared\run_omp.py" --workdir "$W" --prompt "$W\shared\prompts\PARTNER_EXTRACT.md" --evidence "$E\partner" --mcp-config "$W\mcp.json" --authority "$W\AUTHORITY.md"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the partner run failed; preserve this attempt.' }
```

**Expected:** The probe passes before the run starts, and the run passes with a new note, `Drafts/partner/partner-extract`, in the vault. Every note the AI read came from `Estimate/Releasable`.

**Stop:** The probe holds, the launcher refuses to start, or the run ends without writing the extract.

**Recovery:** Fix the limits named by the probe or launcher and prove them again before any live run. If you change either connection file, rename `probe-partner.json` to `probe-partner-attempt-1.json` and probe again. Rename a held run folder to `partner-attempt-1` and keep it. Move any note that run created under `Drafts/partner` into that folder, then run again into `E/partner`.

The extract is a draft for the Release Authority, not a release. Scan it for what a program can check: whether every line cites a note you may share, whether it repeats any fact found only in notes you marked STAFF, and whether it holds fewer than three movement details.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$W/shared/mcp/scan_extract.py" --extract "$W/vault/Drafts/partner/partner-extract.md" --vault "$W/vault"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$W\shared\mcp\scan_extract.py" --extract "$W\vault\Drafts\partner\partner-extract.md" --vault "$W\vault"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the extract needs work; preserve this attempt.' }
```

**Expected:** `PASS`, and the list of movement elements the extract contains.

**Stop:** The scan prints `HOLD` with the rule that decides each finding.

**Recovery:** The scan finds only what a program can find. Fix the cause: a line without a link, a note you should not have marked shareable, or an extract that joins too many movement elements. If you change your register, stage again. Then rename `E/partner` to `partner-attempt-1` and move `Drafts/partner/partner-extract.md` into that folder. Run the partner phase again into `E/partner`. The extract is a draft, so moving it loses no source. You still decide whether the wording is wise.

## Disconnect and prove it

End the connection by removing it, then show that a fresh run is offered no tools. To remove the connection, empty the server map in `W/mcp.json` so it reads exactly this:

```json
{"mcpServers": {}}
```

Change `AUTHORITY.md` to the revoked phase, which allows nothing:

```json
{"schema_version": 1, "phase": "revoked", "allow_tools": [], "read_scope": [], "write_scope": [], "create_only": false}
```

Run once more. The revoked prompt asks the assistant to list its vault tools and try to read a note. It should have none, and the run should say so.

![Give each part of the work only the folders it needs, then remove the connection and confirm a fresh run was offered no tools.](figures/m03-phase-scope-revoke.png)

*Give each part of the work only the folders it needs, then remove the connection and confirm a fresh run was offered no tools.*

<details markdown="1">
<summary>Figure text</summary>

Three parts follow one another. Nothing carries over.

- Research: reads `Handbook/` and `Sources/`; new writes only in `Drafts/research/`.
- Partner: reads only `Estimate/Releasable/`; new writes only in `Drafts/partner/`.
- Revoked: the server map is `mcpServers: {}`. A fresh run is offered no tools, and no program starts, so there is nothing to refuse a request.

</details>

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$R/shared/run_omp.py" --workdir "$W" --prompt "$W/shared/prompts/REVOKED.md" --evidence "$E/revoked" --mcp-config "$W/mcp.json" --authority "$W/AUTHORITY.md"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$R\shared\run_omp.py" --workdir "$W" --prompt "$W\shared\prompts\REVOKED.md" --evidence "$E\revoked" --mcp-config "$W\mcp.json" --authority "$W\AUTHORITY.md"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the revoked run failed; preserve this attempt.' }
```

**Expected:** `PASS: all checks passed`. In `E/revoked`, the guard log shows every provider request with an empty tool list, and no `mcp-audit.jsonl` exists because no server started.

**Stop:** The launcher refuses the revoked declaration or the run offered a tool.

**Recovery:** The revoked phase needs an empty server map and a declaration with no tools or folders. Fix the file named in the message, then run again.

Your handoff says what each part was allowed to do.

## Hand off and run the final check

The next person needs your finding, the limits that were in force, and what the probes showed. The check reads these back. Write `handoff.md` in `E` with these six headings, each followed by a few specific sentences: `# Handoff`, `## Finding`, `## Authority in force`, `## What the probes showed`, `## Classification decisions and overrides`, and `## Residual risk and owner`. In the finding, answer the Base Medical Logistics Officer’s question with what the sources support and what they don’t. In the residual-risk section, say what the limits do not prevent and who owns that. A connection that can only create notes in one folder can still create a misleading note there.

Run the check. It reads your work copy and receipts, matches the launcher’s receipts against the program’s own log and the files on disk, and checks your markings against the rules.

**Terminal: Bash or zsh, ordinary user.**

```bash
"$PY" "$M/shared/verify/verify_research.py" "$W" "$E"
```

**Terminal: PowerShell, ordinary user.**

```powershell
& $PY "$M\shared\verify\verify_research.py" "$W" "$E"
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the receipts need attention; preserve this attempt.' }
```

**Expected:** One `OK` line for each claim, some informational lines about how the AI's proposal compared with the rules, and a final `PASS`.

**Stop:** Any `HOLD` line.

**Recovery:** Each `HOLD` names the claim and the reason. Preserve the attempt and fix the cause rather than changing the evidence: a probe made after a live run, a note marked less restricted than the rules require, or a register that disagrees with the AI's own proposal. A `PASS` means the receipts agree with each other and with the rules, but it cannot judge whether your reasoning was wise. Ask someone to read your handoff.

## Class-only boundary

The names, places, and facts are fictional. Don’t use this folder, these markings, or these notes to plan, authorize, or describe a real movement, or to handle real information. Your result is for class use only.
