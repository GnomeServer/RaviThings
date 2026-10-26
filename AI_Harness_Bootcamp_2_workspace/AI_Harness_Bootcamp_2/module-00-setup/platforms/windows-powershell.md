# Windows PowerShell setup

Setup takes this Windows laptop from no course tools to a live readiness check, in which Oh My Pi writes one file you can verify. It has three parts. First you install Oh My Pi and pass the readiness check in Steps 1 to 9. Then you set up local Obsidian, and finally local n8n for Module 7. Plan for roughly 60 to 120 minutes for Steps 1 to 9 and about 20 to 30 minutes for Obsidian. The n8n time depends on downloads and restarts.

You need Git, Python 3.12 or newer, a browser, a plain text editor, local Obsidian, and the latest stable Oh My Pi release. The only provider key is `OPENROUTER_API_KEY`, and the course launcher selects `openrouter/anthropic/claude-sonnet-4.6`. Oh My Pi, Python, Git, Obsidian, the course checkout, and your key stay on native Windows. Staff prepare n8n in Docker Desktop; you start it from PowerShell and use it in your browser. Don't install Node, npm, or another agent.

Open **Windows PowerShell** (version 5.1) from the Start menu as your ordinary user. Check with the device owner that you're allowed to install these tools. If an installer asks for administrator approval, use the owner's approved route. If policy denies an installer, stop and keep the message. Don't open an Administrator window to get around a denial.

To run a block, copy all of it, paste it into the PowerShell window, and press Enter if the prompt is still waiting. Most blocks are wrapped in `. { ... }`. That wrapper makes PowerShell read the whole block before it runs anything, so a failed check stops the rest of the block. A line that starts with `STOP:` or `HOLD:` names the problem. Go to [If a step stops](#if-a-step-stops) for that step, or start from the first failed check in [When setup stops](../shared/TROUBLESHOOTING.md).

## 1. Check this computer

This step checks Windows, PowerShell, free disk space, and your processor. It also looks for Git and a real Python 3.12 or newer, then lists anything you still need to install. Windows includes a Python shortcut that only opens the Microsoft Store, so the check skips anything under `WindowsApps` and asks each Python candidate for its actual path. Your Windows edition must still get security updates. WinGet, Microsoft's package installer, needs at least build 17763. See [WinGet requirements](https://learn.microsoft.com/en-us/windows/package-manager/winget/).

**Terminal: Windows PowerShell 5.1, ordinary user, opened from Start.**

```powershell
. {
  if ($env:OS -ne 'Windows_NT') { throw 'STOP: use native Windows.' }
  $ps = $PSVersionTable.PSVersion
  if ($PSVersionTable.PSEdition -ne 'Desktop' -or $ps.Major -ne 5 -or $ps.Minor -ne 1) { throw 'STOP: open Windows PowerShell 5.1 from Start.' }
  $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
  if ([int]$os.BuildNumber -lt 17763) { throw 'STOP: this Windows build is older than 17763.' }
  $freeGb = [math]::Round((Get-PSDrive -Name $HOME.Substring(0, 1) -ErrorAction Stop).Free / 1GB, 1)
  if ($freeGb -lt 15) { throw ('STOP: ' + $freeGb + ' GB free on the home drive; free at least 15 GB.') }
  $archCode = (Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop | Select-Object -First 1).Architecture
  if ($archCode -eq 12) {
    $asset = 'omp-windows-arm64.exe'
  } elseif ($archCode -eq 9) {
    $asset = 'omp-windows-x64.exe'
  } else {
    throw 'STOP: no published Oh My Pi binary matches this processor.'
  }
  $R = Join-Path $HOME 'Documents\AIHB_OCT_2026'
  $M = Join-Path $R 'AI_Harness_Bootcamp_2\module-00-setup'
  $missingTools = @()
  $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($git) {
    $gitVersion = & $git.Source --version
    if ($LASTEXITCODE -ne 0) { throw 'STOP: the installed Git failed to run.' }
  } else {
    $missingTools += 'Git'
  }
  $PY = $null
  foreach ($candidate in @('py -3.12', 'py -3', 'python', 'python3')) {
    $parts = $candidate -split ' '
    $extra = @($parts | Select-Object -Skip 1)
    foreach ($cmd in @(Get-Command $parts[0] -CommandType Application -All -ErrorAction SilentlyContinue)) {
      if ($PY -or $cmd.Source -like '*\WindowsApps\*') { continue }
      $out = @(& $cmd.Source @extra -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null)
      if ($LASTEXITCODE -eq 0 -and $out.Count -eq 1) {
        $exe = ([string]$out[0]).Trim()
        if ($exe -match '^[A-Za-z]:\\' -and $exe -notlike '*\WindowsApps\*' -and (Test-Path -LiteralPath $exe -PathType Leaf)) { $PY = $exe }
      }
    }
  }
  if (-not $PY) { $missingTools += 'Python 3.12+' }
  Write-Output ('WINDOWS ' + $os.Caption + ' build ' + $os.BuildNumber)
  Write-Output ('POWERSHELL ' + $ps)
  Write-Output ('FREE_GB ' + $freeGb)
  Write-Output ('OMP_ASSET ' + $asset)
  if ($git) { Write-Output ('GIT ' + $gitVersion) }
  if ($PY) { Write-Output ('PYTHON ' + $PY) }
  if (Get-Command winget -CommandType Application -ErrorAction SilentlyContinue) { Write-Output 'WINGET found' } else { Write-Output 'WINGET missing' }
  if ($missingTools.Count -eq 0) { Write-Output 'MISSING TOOLS: none' } else { Write-Output ('MISSING TOOLS: ' + ($missingTools -join ', ')) }
}
```

**Expected:** lines for Windows, PowerShell `5.1`, free space, and either `omp-windows-arm64.exe` or `omp-windows-x64.exe`, ending with `MISSING TOOLS: none` or a list of tools to install.

**Stop:** a `STOP:` line, or you aren't sure this Windows edition still gets updates or that installs are allowed.

**Recovery:** settle permission and support questions with the device owner first. For other stops, see [If a step stops](#steps-1-and-2-tools).

## 2. Install Git and Python

**Git** copies the course files from GitHub to your computer and records exactly which version you have. Step 4 uses it to make your checkout. On Windows, the course uses [Git for Windows](https://git-scm.com/install/windows), the Windows build that the Git project links to. It includes Git Credential Manager, which lets Git sign you in to GitHub through your browser. WinGet installs it as the package `Git.Git`.

If Step 1 printed `MISSING TOOLS: none`, skip the install block and go to [Confirm Git works](#confirm-git-works). Otherwise WinGet installs only the missing tools: Git for the machine, which may ask for approval, and Python 3.12 for your user only. If WinGet shows source or package agreements, read them and accept only if you're authorized. See [WinGet install](https://learn.microsoft.com/en-us/windows/package-manager/winget/install).

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Step 1.**

```powershell
. {
  if ($null -eq $missingTools) { throw 'STOP: run Step 1 in this window first.' }
  if ($missingTools.Count -eq 0) { Write-Output 'Nothing to install.'; return }
  if (-not (Get-Command winget -CommandType Application -ErrorAction SilentlyContinue)) { throw 'STOP: WinGet is missing.' }
  if ($missingTools -contains 'Git') {
    winget install --exact --id Git.Git --source winget
    if ($LASTEXITCODE -ne 0) { throw 'STOP: Git did not install. Keep the installer message.' }
  }
  if ($missingTools -contains 'Python 3.12+') {
    winget install --exact --id Python.Python.3.12 --source winget --scope user
    if ($LASTEXITCODE -ne 0) { throw 'STOP: Python did not install. Keep the installer message.' }
  }
  Write-Output 'INSTALLED: close every terminal window, open Windows PowerShell from Start, and run Step 1 again.'
}
```

**Expected:** each installer finishes and the last line starts with `INSTALLED:`. Close every terminal window, including Windows Terminal tabs and editor terminals, then open PowerShell from Start and run [Step 1](#1-check-this-computer) until it prints `MISSING TOOLS: none`.

**Stop:** a `STOP:` line, a denied approval prompt, or Step 1 still lists a tool after reopening.

**Recovery:** keep the installer message for the device owner. If WinGet is missing, see [If a step stops](#steps-1-and-2-tools).

### Confirm Git works

This block shows which `git.exe` PowerShell finds and asks it for its version. Run it in a window you opened after the install, even if you skipped the install block.

**Terminal: Windows PowerShell 5.1, ordinary user, opened from Start.**

```powershell
. {
  $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $git) { throw 'STOP: this window does not find Git.' }
  Write-Output ('GIT_PATH ' + $git.Source)
  & $git.Source --version
  if ($LASTEXITCODE -ne 0) { throw 'STOP: Git did not run.' }
}
```

**Expected:** `GIT_PATH` and the full path to `git.exe`, usually `C:\Program Files\Git\cmd\git.exe`, then `git version 2.` followed by more numbers and `.windows.`, such as `.windows.1`.

**Stop:** a `STOP:` line.

**Recovery:** Close every terminal window, including Windows Terminal tabs and editor terminals, then open Windows PowerShell from Start and run this block again. A window opened before the install doesn't see the new Git. If it still stops, run [Step 1](#1-check-this-computer) and this step again, or see [If a step stops](#steps-1-and-2-tools).

## 3. Install Oh My Pi

Run the one-line installer from [omp.sh](https://omp.sh/).

**Terminal: Windows PowerShell, ordinary user.**

```powershell
irm https://omp.sh/install.ps1 | iex
```

**Restart your terminal after installing OMP so PATH changes take effect.** Follow any PATH instructions the installer prints, complete Step 4 in this window, then close and reopen your terminal as directed in Step 5 before starting OMP or entering your API key.

**Expected:** The installer finishes successfully. In the new terminal, `omp --version` prints the installed version.

**Stop:** The installer reports an error or `omp` is not found.

**Recovery:** Check the installer’s error. For `omp` not found, use [PATH recovery](../shared/TROUBLESHOOTING.md#if-omp-is-not-found-after-restarting), then reopen the terminal and try `omp --version` again.

## 4. Get the course files

The course repository is private. This block checks whether your saved Git sign-in can read it, without asking for a password in the terminal. Then it clones the course into `Documents\AIHB_OCT_2026` in your home folder, or reuses a checkout of the same course already there. The clone keeps Git from changing line endings, the hidden character at the end of each line, because later checks compare exact bytes. The block reads three frozen course files and puts the checkout on hold if their line endings have changed. See [git ls-remote](https://git-scm.com/docs/git-ls-remote).

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Step 1.**

```powershell
. {
  if (-not $R) { throw 'STOP: run Step 1 in this window first.' }
  $origin = 'https://github.com/TheHolofex/AIHB_OCT_2026.git'
  $savedPrompt = $env:GIT_TERMINAL_PROMPT
  $env:GIT_TERMINAL_PROMPT = '0'
  git ls-remote --exit-code $origin HEAD
  $access = $LASTEXITCODE
  if ($null -eq $savedPrompt) { Remove-Item Env:\GIT_TERMINAL_PROMPT } else { $env:GIT_TERMINAL_PROMPT = $savedPrompt }
  if ($access -ne 0) { throw 'STOP: GitHub access failed. Use "If GitHub access fails".' }
  Write-Output 'ACCESS OK'
  if (Test-Path -LiteralPath $R) {
    foreach ($probe in @($R, (Join-Path $R '.git'))) {
      if ((Test-Path -LiteralPath $probe) -and ((Get-Item -LiteralPath $probe -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'STOP: the checkout or its .git folder is a link. It was not followed.' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $R '.git') -PathType Container)) { throw 'STOP: Documents\AIHB_OCT_2026 exists and is not a Git checkout. It was not changed.' }
    $remote = git -C $R remote get-url origin
    if ($LASTEXITCODE -ne 0 -or ([string]$remote).Trim() -ne $origin) { throw 'STOP: the existing checkout has a different origin. It was not changed.' }
    Write-Output 'CHECKOUT reused'
  } else {
    git -c core.autocrlf=false clone $origin $R
    if ($LASTEXITCODE -ne 0) { throw 'STOP: clone failed. Keep the message.' }
    Write-Output 'CHECKOUT cloned'
  }
  if (-not (Test-Path -LiteralPath (Join-Path $M 'shared\MODULE_00_LAB.md'))) { throw 'STOP: this checkout has no Module 0 lab. It was not changed.' }
  foreach ($rel in @('AI_Harness_Bootcamp_2\module-01-mission-thread\shared\case\SOURCE_MANIFEST.json', 'AI_Harness_Bootcamp_2\module-08-change-eval\shared\controls\policy.json', 'AI_Harness_Bootcamp_2\module-10-capstone\shared\baseline\run.json')) {
    $path = Join-Path $R $rel
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw ('STOP: ' + $rel + ' is missing. The checkout was not changed.') }
    if ([Array]::IndexOf([IO.File]::ReadAllBytes($path), [byte]13) -ge 0) { throw 'HOLD: a frozen control has rewritten line endings. The checkout was not reset, cleaned, pulled, or renormalized.' }
  }
  Write-Output 'Line endings unchanged.'
  Write-Output ('COURSE ' + $R)
}
```

**Expected:** a commit ID followed by `HEAD`, then `ACCESS OK`, `CHECKOUT cloned` or `CHECKOUT reused`, `Line endings unchanged.`, and the course path.

**Stop:** `STOP: GitHub access failed`, any other `STOP:` line, or the line-ending `HOLD:`.

**Recovery:** for access, use the next subsection. For an existing folder or the line-ending hold, leave the folder untouched and see [If a step stops](#step-4-github-access-and-the-checkout).

### If GitHub access fails

Git for Windows includes Git Credential Manager, which signs you in to GitHub through a browser window and stores the sign-in in Windows Credential Manager. Run this command by itself. When the sign-in window opens, use the GitHub account that was invited to the course repository. That account is separate from your course-site password and your OpenRouter key.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
git ls-remote --exit-code https://github.com/TheHolofex/AIHB_OCT_2026.git HEAD
```

**Expected:** after you sign in, a commit ID followed by `HEAD`. Then run [Step 4](#4-get-the-course-files) again.

**Stop:** the window asks `Username for 'https://github.com'` instead of opening a sign-in window, or Git reports that the repository wasn't found.

**Recovery:** press Ctrl+C at a username prompt. Use the GitHub CLI route in [If a step stops](#step-4-github-access-and-the-checkout), and ask the repository owner to confirm your invitation.

## 5. Open a new window and confirm

Opening PowerShell from Start creates a new process, and a **process** is one running program with its own settings. A new process reads your saved PATH, but it should not have any key. Seeing `MISSING` here shows that no key was saved where new windows pick it up. Close every terminal window, including Windows Terminal tabs and editor terminals. Then open **Windows PowerShell** from Start. Don't type `powershell` inside an old window, because a child window inherits the parent's settings.

**Terminal: Windows PowerShell 5.1, ordinary user, newly opened from Start.**

```powershell
. {
  $R = Join-Path $HOME 'Documents\AIHB_OCT_2026'
  $M = Join-Path $R 'AI_Harness_Bootcamp_2\module-00-setup'
  $PY = $null
  foreach ($candidate in @('py -3.12', 'py -3', 'python', 'python3')) {
    $parts = $candidate -split ' '
    $extra = @($parts | Select-Object -Skip 1)
    foreach ($cmd in @(Get-Command $parts[0] -CommandType Application -All -ErrorAction SilentlyContinue)) {
      if ($PY -or $cmd.Source -like '*\WindowsApps\*') { continue }
      $out = @(& $cmd.Source @extra -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null)
      if ($LASTEXITCODE -eq 0 -and $out.Count -eq 1) {
        $exe = ([string]$out[0]).Trim()
        if ($exe -match '^[A-Za-z]:\\' -and $exe -notlike '*\WindowsApps\*' -and (Test-Path -LiteralPath $exe -PathType Leaf)) { $PY = $exe }
      }
    }
  }
  if (-not $PY) { throw 'STOP: Python 3.12+ was not found in this window.' }
  if (-not (Test-Path -LiteralPath (Join-Path $M 'shared\MODULE_00_LAB.md'))) { throw 'STOP: the course checkout was not found. Run Step 4 first.' }
  $found = (Get-Command omp -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
  if (-not $found) { throw 'STOP: omp is not on PATH. Restart PowerShell after installation.' }
  Write-Output ('OMP_PATH ' + $found)
  $version = @(& $found --version)
  $v = if ($version.Count -ge 1) { ([string]$version[0]).Trim() } else { '' }
  if ($LASTEXITCODE -ne 0 -or $version.Count -ne 1 -or ($v -notmatch '^omp/[0-9]+\.[0-9]+\.[0-9]+$')) { throw 'STOP: omp --version did not print a usable omp/<semver>.' }
  Write-Output ('OMP_VERSION ' + $v)
  Write-Output ('PYTHON ' + $PY)
  Write-Output ('COURSE ' + $R)
  if ([string]::IsNullOrEmpty($env:OPENROUTER_API_KEY)) { Write-Output 'MISSING' } else { Write-Output 'SET' }
}
```

**Expected:** `OMP_PATH`, `OMP_VERSION omp/<semver>`, the Python and course paths, and `MISSING` as the last line.

**Stop:** a `STOP:` line, or `SET` before you've typed a key in this window.

**Recovery:** if the window prints `SET`, don't print the variable; run the saved-key check in [If a step stops](#step-5-a-new-window). For a missing `omp`, make sure you opened this window from Start.

## 6. Enter your OpenRouter key

Run this command by itself. Type or paste your OpenRouter key at the hidden prompt, then press Enter. The command only waits for your input. Never put the key in a command, a file, a profile, or a chat. See [Use one OpenRouter key without putting it in your work](../shared/CREDENTIALS.md).

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Step 5.**

```powershell
$secret = Read-Host -Prompt 'OpenRouter API key' -AsSecureString
```

**Expected:** the prompt returns, and the key isn't readable on screen. PowerShell may show asterisks, which is still hidden input.

**Stop:** the key appears as readable text, or you pasted it onto the command line instead of the prompt.

**Recovery:** revoke a displayed key with OpenRouter, then run this command again with the replacement.

## 7. Confirm the key is loaded

This block puts the hidden key into this terminal's environment only, clears the temporary copy, and prints `SET` or `MISSING`. To read the hidden value, it briefly uses a BSTR, an unmanaged string, then zeroes that memory with [ZeroFreeBSTR](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.marshal.zerofreebstr). It writes nothing to a file, a profile, or your saved user settings.

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Step 6.**

```powershell
$bstr = [IntPtr]::Zero
$plain = $null
try {
  if ($null -eq $secret) { throw 'STOP: run the hidden read in this window first.' }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  if ([string]::IsNullOrWhiteSpace($plain)) {
    Write-Output 'MISSING'
  } else {
    $env:OPENROUTER_API_KEY = $plain
    Write-Output 'SET'
  }
} finally {
  if ($bstr -ne [IntPtr]::Zero) {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
  $plain = $null
  if ($null -ne $secret) { $secret.Dispose() }
  $secret = $null
}
```

**Expected:** `SET`.

**Stop:** `MISSING`, an error, or any output that contains the key.

**Recovery:** run Step 6 and this block again in the same window. Don't check the key by printing the environment.

## 8. Run the readiness check

This block creates a fresh attempt folder under `course-evidence\reformation-qa` in your home folder, outside the course checkout. It writes a random token beside the work folder and copies the token into it. Then it runs the course launcher once. The launcher starts Oh My Pi with permission to write only `from-omp.txt`. Finally, the verifier checks that the file contains `omp works`, one space, and this attempt's token. It also checks that Oh My Pi's write receipt matches the file on disk. Don't create the evidence folder or `from-omp.txt` yourself.

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Steps 5 to 7.**

```powershell
. {
  if (-not $PY -or -not $R -or -not $M) { throw 'STOP: run Step 5 in this window first.' }
  if ([string]::IsNullOrEmpty($env:OPENROUTER_API_KEY)) { throw 'STOP: the key is not loaded in this window. Repeat Steps 6 and 7.' }
  $attempt = Join-Path $HOME ('course-evidence\reformation-qa\' + [guid]::NewGuid().ToString('n') + '\module-00')
  $proof = Join-Path $attempt 'proof'
  $tokenFile = Join-Path $attempt 'run-token.txt'
  $evidence = Join-Path $attempt 'evidence'
  New-Item -ItemType Directory -Path $proof -ErrorAction Stop | Out-Null
  $bytes = New-Object byte[] 16
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $utf8 = New-Object Text.UTF8Encoding $false
  [IO.File]::WriteAllText($tokenFile, (-join ($bytes | ForEach-Object { $_.ToString('x2') })), $utf8)
  Copy-Item -LiteralPath $tokenFile -Destination (Join-Path $proof 'run-token.txt') -ErrorAction Stop
  $promptFile = Join-Path $proof 'prompt.txt'
  [IO.File]::WriteAllText($promptFile, "Read run-token.txt with the course_read tool. Then write only from-omp.txt with the course_write tool. The file contents must be the words omp works, one space, and the exact token text from run-token.txt. Do not write any other file.`n", $utf8)
  Write-Output ('ATTEMPT ' + $attempt)
  & $PY (Join-Path $R 'shared\run_omp.py') --workdir $proof --prompt $promptFile --evidence $evidence --allow-write from-omp.txt
  $launchExit = $LASTEXITCODE
  Write-Output ('LAUNCH_EXIT ' + $launchExit)
  if ($launchExit -ne 0) { throw 'HOLD: the launcher did not succeed. Keep this attempt and read its message.' }
  & $PY (Join-Path $M 'shared\case\verify_tool_proof.py') $proof $tokenFile $evidence
  $verifyExit = $LASTEXITCODE
  Write-Output ('VERIFY_EXIT ' + $verifyExit)
  if ($verifyExit -ne 0) { throw 'HOLD: the readiness check did not pass. Keep this attempt.' }
}
```

**Expected:** the attempt path, `LAUNCH_EXIT 0`, the verifier's `READINESS CHECK PASS`, then `VERIFY_EXIT 0`. The launcher may print its own status line too, but that line alone doesn't complete the check.

**Stop:** `LAUNCH_EXIT` or `VERIFY_EXIT` other than `0`, or `READINESS CHECK HOLD`.

**Recovery:** keep the attempt folder and read the named failure. Running this block again makes a new attempt; see [If a step stops](#step-8-the-readiness-check).

## 9. Save the setup report and read the result

The setup report checks your prerequisites separately: Git, Python, Oh My Pi, the checkout, and whether this terminal has the key. It doesn't repeat the live write, so you need both `SETUP CHECK PASS` and `READINESS CHECK PASS`. Open `scripts\verify-setup.ps1` under the Module 0 folder in your text editor and read it before running it. Run this block only if you have permission to run the checker you've reviewed. Windows PowerShell's **execution policy** controls which scripts can run. First, the block checks for a restrictive policy explicitly set outside the Process scope, or an explicit Process restriction. If it finds one, it stops. If the current effective policy allows local scripts and no restrictive policy is set, it runs the checker directly. If no policy has been set anywhere on this computer, the default Restricted policy blocks scripts. In that case, the block runs the checker in a child PowerShell with `-ExecutionPolicy RemoteSigned`, only for that child process. See [about_Execution_Policies](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1). Finally, the block reads `from-omp.txt` directly from disk.

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Step 8.**

```powershell
. {
  if (-not $attempt -or -not $proof) { throw 'STOP: run Step 8 in this window first.' }
  $report = Join-Path $attempt 'setup-report.txt'
  $checker = Join-Path $M 'scripts\verify-setup.ps1'
  $list = Get-ExecutionPolicy -List
  $configured = @($list | Where-Object { $_.Scope -ne 'Process' -and [string]$_.ExecutionPolicy -ne 'Undefined' })
  $restrictiveConfigured = @($configured | Where-Object { [string]$_.ExecutionPolicy -in @('Restricted', 'AllSigned') })
  $processRestrictive = @($list | Where-Object { $_.Scope -eq 'Process' -and [string]$_.ExecutionPolicy -in @('Restricted', 'AllSigned') })
  $effective = [string](Get-ExecutionPolicy)
  $global:LASTEXITCODE = -1
  if ($restrictiveConfigured.Count -gt 0 -or $processRestrictive.Count -gt 0) {
    throw ('STOP: a restrictive execution policy is set on this computer (Get-ExecutionPolicy -List). Ask the device owner for an approved way to run the reviewed local course checker.')
  } elseif ($effective -notin @('Restricted', 'AllSigned')) {
    & $checker -Root $R -ResultsPath $report
  } elseif ($configured.Count -eq 0) {
    & (Join-Path $PSHOME 'powershell.exe') -NoProfile -ExecutionPolicy RemoteSigned -File $checker -Root $R -ResultsPath $report
  } else {
    throw ('STOP: execution policy ' + $effective + ' was set on this computer. Ask the device owner for an approved way to run the checker.')
  }
  $reportExit = $global:LASTEXITCODE
  Write-Output ('REPORT_EXIT ' + $reportExit)
  if ($reportExit -ne 0) { throw 'HOLD: the setup report found a problem. Fix its first FAIL line.' }
  if (-not (Test-Path -LiteralPath $report -PathType Leaf) -or -not ((Get-Content -LiteralPath $report -Tail 1) -like 'SETUP CHECK PASS*')) { throw 'HOLD: the setup report did not end with SETUP CHECK PASS.' }
  Get-Content -LiteralPath (Join-Path $proof 'from-omp.txt') -Raw -ErrorAction Stop
}
```

**Expected:** report lines ending in `SETUP CHECK PASS`, then `REPORT_EXIT 0`, then `omp works` followed by this attempt's token. The report never contains the key.

**Stop:** `STOP: a restrictive execution policy is set on this computer (Get-ExecutionPolicy -List)`, `SETUP CHECK HOLD`, a nonzero `REPORT_EXIT`, `HOLD: the setup report did not end with SETUP CHECK PASS.`, a message that running scripts is disabled or the file isn't signed, or file text that differs.

**Recovery:** fix the first `FAIL` line's `NEXT ACTION`, then run Step 8 again for a new attempt. For a policy block, see [If a step stops](#step-9-the-setup-report).

## Set up local Obsidian

Obsidian lets you follow links and edit notes in a **vault**, an ordinary folder of Markdown text files. You'll install it, open a fresh practice vault, and prove three things in the app window: links work, your saved edits reach the disk, and an edit made outside the app shows up while the vault is open. Keep this vault on the native Windows disk, outside the course checkout and any synced folder. Obsidian [stores plain local files and picks up outside changes](https://github.com/obsidianmd/obsidian-help/blob/master/en/Files%20and%20folders/How%20Obsidian%20stores%20data.md).

### Install Obsidian

First look for **Obsidian** in Start and in **Settings → Apps → Installed apps**. If it's already installed, keep it as it is, without upgrading or downgrading it, and skip this block. Otherwise the block downloads the official 1.13.7 Windows installer, which covers both x64 and ARM64. It checks the fingerprint published in the [release metadata](https://api.github.com/repos/obsidianmd/obsidian-releases/releases/tags/v1.13.7) and starts the installer only if it matches. When the installer asks who to install for, choose **Only for me**. Cancel if it asks to replace an existing installation or needs approval you don't have.

**Terminal: Windows PowerShell 5.1, ordinary user, same window as Step 9.**

```powershell
. {
  foreach ($existing in @((Join-Path $env:LOCALAPPDATA 'Programs\Obsidian\Obsidian.exe'), (Join-Path $env:ProgramFiles 'Obsidian\Obsidian.exe'))) {
    if (Test-Path -LiteralPath $existing) { Write-Output ('OBSIDIAN already installed at ' + $existing + '; kept as it is'); return }
  }
  [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
  $folder = Join-Path $env:LOCALAPPDATA ('obsidian-download-' + [guid]::NewGuid().ToString('n'))
  New-Item -ItemType Directory -Path $folder -ErrorAction Stop | Out-Null
  $installer = Join-Path $folder 'Obsidian-1.13.7.exe'
  Write-Output 'Downloading about 330 MB; this can take several minutes.'
  & {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri 'https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/Obsidian-1.13.7.exe' -OutFile $installer -UseBasicParsing -ErrorAction Stop
  }
  $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($hash -cne 'f233dc24896b3f2d5f9e4b01111181a561d0760b2105f0a474024c5f3143a9bc') { throw 'Obsidian HOLD: checksum mismatch. The installer was not run.' }
  Write-Output 'OBSIDIAN CHECKSUM OK'
  $setup = Start-Process -FilePath $installer -PassThru
  $null = $setup.Handle
  $setup.WaitForExit()
  if ($setup.ExitCode -ne 0) { throw ('Obsidian HOLD: the installer exited with ' + $setup.ExitCode + '.') }
  Write-Output 'OBSIDIAN INSTALLED'
}
```

**Expected:** `OBSIDIAN already installed`, or `OBSIDIAN CHECKSUM OK` followed by `OBSIDIAN INSTALLED`. After that, **Start → Obsidian** opens the app window.

**Stop:** an `Obsidian HOLD:` line, an installer refusal, or no app window.

**Recovery:** never run a download whose checksum failed; running the block again uses a new folder. Keep any refusal message for the device owner and see [If a step stops](#local-obsidian-problems).

### Open the practice vault and save a reply

This block creates a fresh practice vault under your home folder and records the expected values outside the vault. It uses `$PY` and `$M` from Step 5; if you opened a new window, run the [Step 5](#5-open-a-new-window-and-confirm) block first.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
. {
  if (-not $PY -or -not $M) { throw 'Obsidian HOLD: run Step 5 in this window first.' }
  $ObsidianRoot = Join-Path $HOME ('obsidian-readiness-' + [guid]::NewGuid().ToString('n'))
  & $PY (Join-Path $M 'scripts\obsidian_readiness.py') initialize --root $ObsidianRoot
  if ($LASTEXITCODE -ne 0) { throw 'Obsidian HOLD: initialize failed; keep this attempt.' }
  Write-Output ('OBSIDIAN_ROOT ' + $ObsidianRoot)
}
```

**Expected:** `Created practice vault:` followed by a path ending in `\vault`, then the `OBSIDIAN_ROOT` line. Note both paths.

**Stop:** a `HOLD:` line or any helper error.

**Recovery:** keep the attempt and the message, and see [If a step stops](#local-obsidian-problems).

**Window: native Windows Obsidian, ordinary user.**

1. In the vault chooser, choose **Open folder as vault**. If a personal vault opens instead, use **Open another vault** and leave its files and settings alone. Select the exact folder printed after `Created practice vault:`, not its parent.
2. In this vault's **Settings → Community plugins**, keep **Restricted mode** on. Under **Settings → Core plugins**, turn **Sync** off if it's on. Don't sign in, install plugins, or connect a remote vault. Note the version shown in **Settings → General**, then close Settings.
3. Open **Start**. Switch to **Reading view** if the links aren't clickable, click **Token**, and read the token. Then follow **Reply** from Token.
4. Switch Reply to **Editing view**, type only the token on one line, and press **Ctrl+S**.
5. Open **Token** again in Reading view and leave it showing.

### Watch an outside edit and reopen

This block first checks that your saved reply matches the token. Only if it does, it changes Token on disk from outside Obsidian, while keeping your reply. Keep Token showing in Obsidian while it runs.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
. {
  if (-not $ObsidianRoot) { throw 'Obsidian HOLD: run the practice vault block in this window first.' }
  & $PY (Join-Path $M 'scripts\obsidian_readiness.py') check --root $ObsidianRoot
  if ($LASTEXITCODE -ne 0) { throw 'Obsidian HOLD: the saved reply did not match. Nothing was refreshed.' }
  & $PY (Join-Path $M 'scripts\obsidian_readiness.py') refresh --root $ObsidianRoot
  if ($LASTEXITCODE -ne 0) { throw 'Obsidian HOLD: refresh failed; keep this attempt.' }
}
```

**Expected:** `Token generation 1: initial token; external refresh not yet exercised` and `PASS: Obsidian file round-trip; GUI observation still required`, then `Source token rotated outside Obsidian; your saved reply was preserved.`

**Stop:** an `Obsidian HOLD:` line or a helper `HOLD:` line.

**Recovery:** in Obsidian, correct only Reply so it matches Token, save, and run this block again. Don't edit Start, Token, or the records outside `vault`.

**Window: native Windows Obsidian, same practice vault.** Before you close anything, look at Token and confirm its value changed while the vault was open. Follow **Reply**, replace the old value with the new one in Editing view, and press **Ctrl+S**. Close Obsidian, open it again from Start, and reopen the same vault if it doesn't reopen on its own. Open Reply and confirm the new value is still there.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
& $PY (Join-Path $M 'scripts\obsidian_readiness.py') check --root $ObsidianRoot
```

**Expected:** `Token generation 2: refreshed token; GUI observation still required`, the same `PASS:` line, and a new `Disk observation saved:` path.

**Stop:** a `HOLD:` line or a different result.

**Recovery:** confirm the vault path and the saved Reply in Obsidian, then run this check again. If Token changed only after a restart, see [If a step stops](#local-obsidian-problems).

### Record what you saw

In Notepad, create a new plain-text file named `gui-observation.txt` directly in the folder printed after `OBSIDIAN_ROOT`, beside `vault` rather than inside it. Write the date, your Windows build and processor, the Obsidian version, the exact vault path, and what happened at each point: following Start → Token → Reply, both saves, the outside change appearing while the vault was open, and Reply after reopening. Add the two `Disk observation saved:` paths and anything that failed.

Record **Obsidian READY** only if you saw every one of those actions in the app on this laptop and both checks passed. Otherwise record **Obsidian HOLD** and name the action that failed or that you didn't see. A helper `PASS` alone isn't enough. Keep this result separate from the Oh My Pi and n8n results.

## Prepare local n8n for Module 7

n8n is the local workflow editor for Module 7. Staff prepare and qualify the two-service environment (n8n + runner) using Docker Desktop's Linux backend on this Windows machine. Run the common Python helper from native PowerShell. Keep n8n separate from SETUP CHECK PASS and READINESS CHECK PASS.

Staff prepare Docker Desktop and its approved Linux-container backend, check licensing, and verify that workflows survive a restart. You stay in PowerShell; no Ubuntu window is needed for n8n. Preserve any existing instances and data. If your environment is not prepared, record **n8n HOLD** and contact the device/support owner.


### Start the prepared instance from native PowerShell

Use the PowerShell window where step 5 set the variables. In a new window, repeat the step 5 box first.

**Terminal: Windows PowerShell 5.1, ordinary user, opened from Start.**

```powershell
& $PY "$M\scripts\n8n_local.py" start
if ($LASTEXITCODE -ne 0) { throw 'HOLD: keep the helper message and contact the support owner.' }
& $PY "$M\scripts\n8n_local.py" status
```

**Expected:** `STARTED` or `RUNNING`, then a status report naming n8n 2.41.5, its external runner, and `127.0.0.1:5678`.

**Stop:** The helper reports `HOLD` or the page does not open.

**Recovery:** Keep the first message and contact the support owner. Staff must resolve a stopped or unavailable Docker Desktop; don't change its settings yourself.

### Save and reopen blank workflow

Open **http://localhost:5678** in a Windows browser. On a fresh instance, complete local owner setup. On an existing instance, use its existing login. Skip optional offers and leave **Assistant** off. Don't enter your OpenRouter key until Module 7.

Select **Overview → Build a workflow** (or **Create workflow**). Name the blank workflow **Module 7 readiness** and press Enter. If that name already holds work, choose a distinct name. Leave the canvas blank and unpublished. Reload, return to the workflow list, and reopen it. Confirm the name, empty canvas, and unpublished state.

**Expected:** Blank unpublished workflow survives reload.

**Stop:** Login fails, owner setup appears unexpectedly, or the saved workflow is missing.

**Recovery:** Preserve the instance and contact the support owner. Don't create another owner account over existing work.

### Staff-assisted persistence

Ask staff to stop and restart only the recorded course instance without removing its data. After staff confirm restart, reopen the same workflow. Confirm its name, blank canvas, and unpublished state.

Record **n8n READY** only if status, browser access, reload/reopen, and staff-assisted persistence all succeed. Otherwise record **n8n HOLD** with the first failure. Keep OMP, Obsidian, and Local model results separate.

In a later session, open fresh PowerShell, repeat the step 5 variable block, then run the two helper commands above.

## If a step stops

Work through the first failure only, and keep its exact message. Keep every existing installation, checkout, vault, attempt folder, container, and volume while you fix it. [When setup stops](../shared/TROUBLESHOOTING.md) covers support packets and telling slow work from a stopped process.

### Steps 1 and 2: tools

- **PowerShell version stop:** you may be in PowerShell 7 (`pwsh`). Open **Windows PowerShell** from Start instead.
- **Low disk space:** free space on the drive that holds your home folder, then run Step 1 again.
- **No published binary for this processor:** save the message and ask for a supported laptop. Don't download the other architecture.
- **Python still missing after installing:** open **Settings → Apps → Advanced app settings → App execution aliases**, turn off the `python.exe` and `python3.exe` aliases, reopen PowerShell from Start, and run Step 1 again. Don't type a guessed Python path.
- **Git still not found after installing:** close every terminal window, including Windows Terminal tabs and editor terminals, then open Windows PowerShell from Start and run [Confirm Git works](#confirm-git-works) again. A window opened before the install keeps the old PATH.
- **WinGet missing:** with the owner's approval, install only the missing tools from the official [Git for Windows installer](https://git-scm.com/downloads/win) and [Python Windows installer](https://www.python.org/downloads/windows/). For Python, choose 3.12 or newer, install for your user, and select **Add python.exe to PATH**.
- **Installer denied or failed:** keep the message for the device owner. Don't reinstall over an existing tool that fails for an unknown reason.

### Step 3: Oh My Pi

- **The installer reports an error:** keep the error and check [omp.sh](https://omp.sh/) for the current installation instructions.
- **`omp` is not found:** follow any PATH instructions the installer printed, close every terminal window, and reopen PowerShell from Start.
- **Windows blocks OMP from starting:** save the message and ask the device owner.

### Step 4: GitHub access and the checkout

- **Signed in to the wrong account:** open **Credential Manager → Windows Credentials** from the Start menu and remove only the `git:https://github.com` entry, then run the sign-in command again with the invited account.
- **No sign-in window appears:** use GitHub CLI with the three blocks below, then run Step 4 again.
- **`Documents\AIHB_OCT_2026` exists but isn't this course, or has a different origin:** leave it untouched, and choose another location only with the person who supports your machine.
- **Line-ending `HOLD:`:** don't edit or renormalize those files. After the person who supports your machine moves the folder aside, run Step 4 again so it makes a fresh copy.
- **Clone failed partway:** keep the partial folder and its message for support rather than deleting it.

If `gh` is already installed, this block only prints its version. The installer may ask for approval. See [GitHub CLI on Windows](https://github.com/cli/cli/blob/trunk/docs/install_windows.md).

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
. {
  if (Get-Command gh -CommandType Application -ErrorAction SilentlyContinue) { gh --version; if ($LASTEXITCODE -ne 0) { throw 'STOP: the existing GitHub CLI failed. Keep its message.' }; return }
  if (-not (Get-Command winget -CommandType Application -ErrorAction SilentlyContinue)) { throw 'STOP: WinGet is missing; ask the device owner to install GitHub CLI.' }
  winget install --exact --id GitHub.cli --source winget
  if ($LASTEXITCODE -ne 0) { throw 'STOP: GitHub CLI did not install. Keep the message.' }
  Write-Output 'INSTALLED: close every terminal window, open Windows PowerShell from Start, and run Step 1 again.'
}
```

**Expected:** a `gh version` line, or `INSTALLED:`. After an install, reopen PowerShell from Start and run Step 1 before continuing.

**Stop:** a `STOP:` line or a denied approval.

**Recovery:** keep the message and ask the device owner to provide GitHub CLI.

Run the browser login by itself. Use the invited account, and when asked whether to authenticate Git with your GitHub credentials, choose **Yes**. Don't share the one-time code. See [gh auth login](https://cli.github.com/manual/gh_auth_login).

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
gh auth login --hostname github.com --git-protocol https --web
```

**Expected:** the browser authorization completes and the command reports that you're logged in.

**Stop:** the wrong account, a denied authorization, or an error.

**Recovery:** fix the account or invitation with the repository owner before you log in again.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
gh auth status --hostname github.com
```

**Expected:** `Logged in to github.com account` with the invited account and `(keyring)`. Then run Step 4 again.

**Stop:** the wrong account, or a file path in place of `(keyring)`, which means the token is stored in a plain file.

**Recovery:** ask the device owner whether that storage is allowed before you continue. Don't add `--show-token` or share this output.

### Step 5: a new window

- **`omp` missing or a different program:** follow the installer’s PATH instructions, close every terminal window, and reopen PowerShell from Start. Use `Get-Command omp` and `omp --version` to check what runs.
- **`SET` before you typed a key:** something supplies the key to new windows. This check looks for it in your saved environment and PowerShell profiles without printing the value.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
. {
  foreach ($scope in @('User', 'Machine')) {
    if (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY', $scope))) { throw ('STOP: a saved ' + $scope + ' environment entry exists. The value was not printed.') }
  }
  foreach ($path in @($PROFILE.CurrentUserCurrentHost, $PROFILE.CurrentUserAllHosts, $PROFILE.AllUsersCurrentHost, $PROFILE.AllUsersAllHosts)) {
    if ($path -and (Test-Path -LiteralPath $path) -and (Select-String -LiteralPath $path -Pattern 'OPENROUTER_API_KEY' -SimpleMatch -Quiet)) { throw 'STOP: a PowerShell profile names the key variable. The line was not printed.' }
  }
  Write-Output 'No saved environment entry or profile reference was found.'
}
```

**Expected:** a `STOP:` line that names where the key is saved, or the no-entry line.

**Stop:** the no-entry line while new windows still print `SET` means another program supplies the key.

**Recovery:** revoke a key that was saved without authorization. For a Machine entry or a profile line, ask the owner to fix it. For a User entry, run the next block.

Run this only if the check named the **User** scope.

**Terminal: Windows PowerShell 5.1, ordinary user, same window.**

```powershell
[Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY', $null, 'User')
```

**Expected:** no output and no key text.

**Stop:** the check didn't name the User scope.

**Recovery:** use the owner route for Machine or profile findings, then open a new window from Start and run Step 5 again.

### Steps 6 and 7: the key

- **The key appeared on screen or in a command:** revoke it with OpenRouter, then repeat Step 6 with the replacement.
- **`MISSING` after Step 7:** run Step 6 and Step 7 again in the same window. [Use one OpenRouter key without putting it in your work](../shared/CREDENTIALS.md) covers where the key must never go.

### Step 8: the readiness check

- **`LAUNCH_EXIT 2`:** a prerequisite failed before the live attempt, such as a missing key or `omp` not being on PATH, and the evidence folder wasn't created. Fix the named cause, then run Step 8 again for a new attempt.
- **`LAUNCH_EXIT 1`, `VERIFY_EXIT 1`, or `READINESS CHECK HOLD`:** the live attempt ran and failed. Keep both folders, read the `FAIL:` line or the launcher's message, and fix that cause. Common causes are a rejected key, an OpenRouter account problem, or a network block.
- Never write or edit `from-omp.txt` yourself, and never run the launcher again in the same attempt folder.

### Step 9: the setup report

- **`STOP: a restrictive execution policy is set on this computer (Get-ExecutionPolicy -List)`, running scripts is disabled, or the file isn't digitally signed:** a restrictive policy (on Machine/User or explicit Process) or other restriction is configured on this computer, or your organization manages it. The gate checks configured restrictive scopes before allowing any permissive run or child. Ask the device owner for an approved way to run the reviewed checker. Don't use `Bypass` or `Unrestricted`, change the policy yourself, unblock files, or paste the script's contents.
- **`SETUP CHECK HOLD`:** fix the first `FAIL` line's `NEXT ACTION`, then run Steps 8 and 9 again for a new attempt.
- **The report already exists:** the checker never overwrites a report. Run Step 8 again for a new attempt.

### Local Obsidian problems

- **Obsidian was already installed:** keep it, use it as it is, and record the version it shows.
- **The installer refuses, wants to replace an install, or needs approval:** cancel, record **Obsidian HOLD**, and keep the message for the owner. Don't delete a profile or reinstall over an app.
- **The check doesn't match:** in Obsidian, correct only Reply to match the current Token, save it, and check again. Don't edit Start, Token, or the records.
- **Token changed only after a restart:** that doesn't show a live refresh. With the correct vault open and Token showing, run the outside-edit block again, then repeat the edit, save, and reopen.

### Local n8n problems

- **The helper reports missing preparation:** contact staff. Don't create another project or install a second stack.
- **Docker Desktop is stopped or `docker.exe` is missing:** ask the device owner to start the approved Linux-container backend and check Docker in a fresh PowerShell window.
- **The helper reports a changed engine, configuration or project:** keep the message and existing work. Ask staff to identify the prepared instance before another operation.
- **Port 5678 is occupied:** ask the device owner to identify its owner. Don't stop another service or select another port yourself.
- **A runner is missing, the version differs, or workflows disappear:** record **n8n HOLD**. Preserve the configuration and data volumes for staff inspection.
- **The browser asks for owner setup again on an existing instance:** don't create another owner account. Ask staff to verify the engine, project and retained data.

## Local model (capstone) readiness lane

Ask staff for the approved native Windows `hf` and `llama-server` paths, then [check local-model readiness](../../module-10-capstone/shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) before a download and again before launch. Use `&` with each quoted executable path. Missing tools, insufficient capacity, an occupied endpoint, or an unresolved failed rehearsal mean **Local model HOLD**; preserve your other readiness results and contact the device/support owner. Linux or PowerShell 7 observations do not establish native Windows PowerShell 5.1 operation.
