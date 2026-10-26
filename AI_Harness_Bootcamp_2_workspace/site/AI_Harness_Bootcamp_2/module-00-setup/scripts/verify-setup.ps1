[CmdletBinding()]
param(
    [string]$Root = (Get-Location).Path,
    [string]$ResultsPath = ""
)

# Setup report for native Windows PowerShell.
#
# Every check ends in one of three states:
#   PASS  the check ran and the observed value matched.
#   WARN  the check ran, the value is outside the expected set, the work can continue.
#   FAIL  the check ran and the value blocks later work, or the check could not run.
# A check that cannot run reports FAIL with the reason. Nothing degrades to PASS.
# Every non-PASS line carries a NEXT ACTION.
#
# Exit 0 when no check is FAIL. Exit 1 when any check is FAIL.
#
# The report names resolved paths so a stub earlier on PATH is visible, but it replaces
# the user profile directory with ~ and removes any credential embedded in a URL. No
# secret value is printed.
#
# No clean-tree requirement: git status is informational only. Unrelated changes are
# preserved; they do not trigger HOLD or advice to discard for QA.

$ErrorActionPreference = 'Continue'

$script:passCount = 0
$script:warnCount = 0
$script:failCount = 0
$script:lines = [System.Collections.Generic.List[string]]::new()

$resolvedRoot = (Resolve-Path -LiteralPath $Root -ErrorAction SilentlyContinue)
if ($resolvedRoot) { $Root = $resolvedRoot.Path }
$ModuleDir = Split-Path -Parent $PSScriptRoot
$PinsFile = Join-Path $ModuleDir 'shared\VERSIONS.md'
$StdErrFile = Join-Path ([IO.Path]::GetTempPath()) ("ahb-verify-{0}.txt" -f ([Guid]::NewGuid().ToString('N')))

if (-not $ResultsPath) {
    $evidenceDir = Join-Path $env:USERPROFILE 'course-evidence\module-00'
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
    $ResultsPath = Join-Path $evidenceDir ("setup-report-{0}.txt" -f [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))
}
if (Test-Path -LiteralPath $ResultsPath) {
    Write-Error 'HOLD: report already exists; choose a new external report path.'
    exit 1
}

# ------------------------------------------------------------------------------ reporting

function Get-Redacted {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return '' }
    $out = [regex]::Replace($Text, '://[^/@\s]*@', '://***@')
    if ($env:USERPROFILE) {
        $out = [regex]::Replace($out, [regex]::Escape($env:USERPROFILE), '~', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    }
    return $out
}

function Get-OrNone {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return 'none' }
    return (Get-Redacted $Text)
}

function Add-Result {
    param([string]$State, [string]$Name, [string]$Detail, [string]$Action = '')
    $line = "[$State] ${Name}: $Detail"
    if ($State -ne 'PASS') {
        if ([string]::IsNullOrWhiteSpace($Action)) {
            $Action = 'Save this line and stop at this boundary; the troubleshooting guide starts from the first failed check.'
        }
        $line = $line + "`n        NEXT ACTION: $Action"
    }
    $script:lines.Add($line)
    Write-Host $line
    switch ($State) {
        'PASS' { $script:passCount++ }
        'WARN' { $script:warnCount++ }
        default { $script:failCount++ }
    }
}

# --------------------------------------------------------------------- version comparison

function Test-VersionCommand {
    param(
        [string]$Name,
        [string]$Pattern = '',
        [string]$Command,
        [string[]]$Arguments = @()
    )
    $resolved = (Get-Command $Command -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if (-not $resolved) {
        Add-Result FAIL $Name "$Command is not on PATH" "Install $Command with the step for it in your platform guide, open a new PowerShell window, and run this check again."
        return
    }
    $versionOutput = @(& $Command @Arguments 2>$null)
    $commandExit = $LASTEXITCODE
    $out = [string]($versionOutput | Select-Object -First 1)
    $out = $out.Trim() -replace '\r',''
    if ($commandExit -ne 0 -or $versionOutput.Count -ne 1 -or -not $out) {
        Add-Result FAIL $Name "$Command did not return a successful version result" 'Preserve the failed command and repair this prerequisite.'
        return
    }
    $shown = (Get-Redacted $resolved) + " - " + $out
    if ($Pattern -and $out -cnotmatch $Pattern) {
        Add-Result FAIL $Name "Unrecognized version at $shown" "Install and verify the latest stable release, then re-run in a new PowerShell window."
    } else {
        Add-Result PASS $Name $shown
    }
}

# ----------------------------------------------------------------------- platform and machine

if ($env:OS -eq 'Windows_NT') {
    Add-Result PASS platform 'PowerShell on native Windows'
} else {
    Add-Result FAIL platform 'PowerShell helper running outside Windows; this is not native Windows setup evidence' 'Use the guide for this host. Native Windows verification needs a Windows host.'
}

$free = (Get-PSDrive -Name ([IO.Path]::GetPathRoot($HOME).TrimEnd('\'))[0]).Free / 1GB
if ($free -ge 15) {
    Add-Result PASS disk ("{0:N1} GB free (want >= 15)" -f $free)
} else {
    Add-Result FAIL disk ("{0:N1} GB free (want >= 15)" -f $free) "Free space and re-run."
}

# ------------------------------------------------------------------------------- tools

Test-VersionCommand -Name git -Command git -Arguments @('--version')
$pythonCmd = $null
$pythonCandidates = @()
foreach ($cmd in @(Get-Command py -CommandType Application -All -ErrorAction SilentlyContinue)) {
    $pythonCandidates += @{ Exe = $cmd.Source; Args = @('-3.12') }
    $pythonCandidates += @{ Exe = $cmd.Source; Args = @('-3') }
}
foreach ($name in @('python3.12', 'python', 'python3')) {
    foreach ($cmd in @(Get-Command $name -CommandType Application -All -ErrorAction SilentlyContinue)) {
        $pythonCandidates += @{ Exe = $cmd.Source; Args = @() }
    }
}
foreach ($candidate in $pythonCandidates) {
    $exe = $candidate.Exe
    if ($exe -like '*\WindowsApps\*') { continue }
    $item = Get-Item -LiteralPath $exe -Force -ErrorAction SilentlyContinue
    if (-not $item -or $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
    $argsForPython = @($candidate.Args) + @('-c', 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)')
    $output = @(& $exe @argsForPython 2>$null)
    if ($LASTEXITCODE -ne 0 -or $output.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$output[0])) { continue }
    $resolved = ([string]$output[0]).Trim()
    if ($resolved -notmatch '^[A-Za-z]:\\' -or $resolved -like '*\WindowsApps\*') { continue }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { continue }
    $item = Get-Item -LiteralPath $resolved -Force -ErrorAction SilentlyContinue
    if (-not $item -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { continue }
    $confirmed = @(& $resolved -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null)
    if ($LASTEXITCODE -ne 0 -or $confirmed.Count -ne 1 -or ([string]$confirmed[0]).Trim() -ine $resolved) { continue }
    $versionOutput = @(& $resolved --version 2>$null)
    if ($LASTEXITCODE -ne 0 -or $versionOutput.Count -ne 1) { continue }
    $pythonCmd = $resolved
    Add-Result PASS python "$($versionOutput[0]) at $(Get-Redacted $pythonCmd)"
    break
}
if (-not $pythonCmd) {
    Add-Result FAIL python 'No runnable Python 3.12+ found on PATH' 'Install or select Python 3.12+ using the platform guide.'
}

Test-VersionCommand -Name omp -Pattern '^omp/[0-9]+\.[0-9]+\.[0-9]+$' -Command omp -Arguments @('--version')

# ---------------------------------------------------------------------- course clone

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Add-Result FAIL repo.clone 'git not found' 'Install Git with Step 2 of your platform guide, open Windows PowerShell from Start, and run this check again.'
} else {
    $remote = (& git -C $Root remote get-url origin 2>$null).Trim()
    $revision = (& git -C $Root rev-parse --verify HEAD 2>$null).Trim()
    $dirty = @(& git -C $Root status --porcelain 2>$null)
    if ($remote -eq 'https://github.com/TheHolofex/AIHB_OCT_2026.git') {
        Add-Result PASS repo.remote $remote
    } else {
        Add-Result FAIL repo.remote "want the course HTTPS origin, observed $(Get-OrNone $remote)" 'Point origin at the course repository over HTTPS, or clone it again into a new directory, then run this check again.'
    }
    if ($revision -match '^[0-9a-f]{40}$') {
        Add-Result PASS repo.revision $revision.Substring(0,12)
    } else {
        Add-Result FAIL repo.revision "no commit is checked out in $(Get-Redacted $Root)" 'Run git log -1 in the repository root and read the error it prints.'
    }
    $dirtyCount = @($dirty | Where-Object { $_ -and $_.ToString().Trim() }).Count
    if ($dirtyCount -eq 0) {
        Add-Result PASS repo.clean 'no changed or untracked paths'
    } else {
        Add-Result WARN repo.clean "$dirtyCount changed or untracked paths; informational only" 'Preserve these changes and continue in a separate external work folder.'
    }
}

$missingModule = @()
foreach ($required in 'shared\MODULE_00_LAB.md', 'shared\VERSIONS.md', 'shared\case\verify_tool_proof.py', 'platforms') {
    if (-not (Test-Path -LiteralPath (Join-Path $ModuleDir $required))) { $missingModule += $required }
}
$moduleInRoot = $ModuleDir.StartsWith($Root.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
if ($missingModule.Count -gt 0) {
    Add-Result FAIL repo.module "this clone is missing $($missingModule -join ', ') under $(Get-Redacted $ModuleDir)" 'Preserve the checkout. Ask for the missing files or use a separate complete checkout; do not reset, clean, or pull over local work.'
} elseif (-not $moduleInRoot) {
    Add-Result FAIL repo.module "the checks you are running live in $(Get-Redacted $ModuleDir), which is outside $(Get-Redacted $Root)" 'Run this check from the repository root you cloned, using the copy of the script inside that clone.'
} else {
    Add-Result PASS repo.module "the course files for this session are present at $(Get-Redacted $ModuleDir)"
}

# --------------------------------------------------------------- credentials and auth

if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) {
    Add-Result FAIL secret.openrouter 'MISSING in current process' 'Enter the key again with the hidden-input step in your guide, in this same window, then run this check again.'
} else {
    Add-Result PASS secret.openrouter 'SET in current process; value not printed'
}

if (Get-Command omp -ErrorAction SilentlyContinue) {
    Add-Result PASS config.omp 'omp present and runnable'
} else {
    Add-Result FAIL config.omp 'omp not present or not runnable' 'Install omp with the step in your platform guide, open a new PowerShell window, and run this check again.'
}

# ------------------------------------------------------------------------------ verdict

if ($script:failCount -eq 0) {
    $verdict = 'SETUP CHECK PASS'
} else {
    $verdict = 'SETUP CHECK HOLD'
}

try {
    $stream = [IO.File]::Open($ResultsPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    $writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($false))
    try {
        foreach ($line in $script:lines) { $writer.WriteLine($line) }
        $writer.WriteLine("$verdict - report: $(Get-Redacted $ResultsPath)")
    } finally {
        $writer.Dispose()
        $stream.Dispose()
    }
} catch {
    Write-Error 'HOLD: could not create the report without overwriting an existing file.'
    exit 1
}

Write-Host "`n$verdict - report: $ResultsPath"
if ($script:failCount -eq 0) { exit 0 }
exit 1
