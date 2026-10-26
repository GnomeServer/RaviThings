from pathlib import Path
import difflib
import hashlib
import json
import sys

ROOT = Path('/home/dow_admin/Documents/AIHB_OCT_2026')
WORK = Path(__file__).parent
MODULE = Path('AI_Harness_Bootcamp_2/module-00-setup')
changes = {}


def replace(relative, old, new):
    relative = str(relative)
    original, current = changes.get(relative, ((ROOT / relative).read_text(),) * 2)
    if current.count(old) != 1:
        raise SystemExit(f'Expected one replacement target in {relative}')
    changes[relative] = (original, current.replace(old, new, 1))


def current(relative):
    return changes.get(str(relative), ((ROOT / relative).read_text(),) * 2)[1]


def section(relative, start, end, replacement):
    text = current(relative)
    a = text.index(start)
    b = text.index(end, a)
    replace(relative, text[a:b], replacement)


def line(relative, prefix, replacement):
    matches = [value for value in current(relative).splitlines() if value.startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f'Expected one line starting {prefix!r} in {relative}')
    replace(relative, matches[0] + '\n', replacement + '\n' if replacement else '')


replace(
    MODULE / 'README.md',
    'The platform guide keeps **PATH**, the saved list of folders your shell searches for commands. Check it in a new terminal after installation, not just the install window.',
    '**Restart your terminal after installing OMP so PATH changes take effect.** Close the installation window and open a new terminal before starting OMP or entering your API key. **PATH** is the list of folders your shell searches for commands.',
)

quickstart = '''## Start OMP with your OpenRouter key

After restarting your terminal, run the commands for your shell. Replace the placeholder with your complete API key.

**Terminal: Bash or zsh on macOS, Linux, or WSL, ordinary user.**

```bash
export OPENROUTER_API_KEY='YOUR_COMPLETE_API_KEY'
omp
```

**Terminal: PowerShell on Windows, ordinary user.**

```powershell
$env:OPENROUTER_API_KEY = 'YOUR_COMPLETE_API_KEY'
omp
```

1. Press **Esc** to skip provider setup.
2. Select the OpenRouter model **`openrouter/anthropic/claude-sonnet-4.6`**.
3. Choose your font, style, and other preferences.
4. Send `hello` and confirm the model replies, then start chatting.

**No sign-in or YAML configuration is required.** Keep using the same terminal; enter the key again if you open a new one. For hidden key entry, use the [credential guide](shared/CREDENTIALS.md#enter-the-key-through-a-hidden-prompt).

'''
replace(MODULE / 'README.md', '## When a step fails\n', quickstart + '## When a step fails\n')

replace(
    MODULE / 'shared/CREDENTIALS.md',
    "Don't put it in a prompt, command argument, file, shell profile, Git setting, screenshot, chat, ticket, or evidence record.",
    "Don't put it in a prompt, file, shell profile, Git setting, screenshot, chat, ticket, or evidence record. Supply it through `OPENROUTER_API_KEY` rather than an OMP command-line argument.",
)
replace(
    MODULE / 'shared/CREDENTIALS.md',
    '## Enter the key through a hidden prompt\n\n',
    '## Enter the key through a hidden prompt\n\n**Restart your terminal after installing OMP so PATH changes take effect.** Enter the key in the new terminal, then start OMP in that same window.\n\n',
)
replace(
    MODULE / 'shared/CREDENTIALS.md',
    '''After the hidden input and export above, run this in the same terminal from the folder where you want to work. No config file or provider sign-in is required.

**Terminal: Bash or zsh, ordinary user, same window.**

```bash
omp --model openrouter/anthropic/claude-sonnet-4.6
```

**Terminal: PowerShell, ordinary user, same window.**

```powershell
omp --model openrouter/anthropic/claude-sonnet-4.6
```

**Expected:** OMP opens with the selected model. Send a short message to check actual access; opening OMP alone does not validate the key. A model request can incur charges.''',
    '''After entering and exporting the key above, run `omp` in the same terminal from the folder where you want to work.

**Terminal: Bash or zsh, ordinary user, same window.**

```bash
omp
```

**Terminal: PowerShell, ordinary user, same window.**

```powershell
omp
```

1. Press **Esc** to skip provider setup.
2. Select the OpenRouter model **`openrouter/anthropic/claude-sonnet-4.6`**.
3. Choose your font, style, and other preferences.
4. Send `hello` and confirm the model replies, then start chatting.

**No sign-in or YAML configuration is required.**

**Expected:** OMP opens with the selected model and replies to your message. Opening OMP alone does not validate the key. A model request can incur charges.''',
)

for platform in ['arch-linux', 'macos', 'ubuntu', 'windows-powershell', 'windows-wsl']:
    relative = MODULE / f'platforms/{platform}.md'
    windows = platform == 'windows-powershell'
    shell = 'Windows PowerShell' if windows else 'Ubuntu Bash inside WSL' if platform == 'windows-wsl' else 'Bash or zsh'
    fence = 'powershell' if windows else 'bash'
    command = 'irm https://omp.sh/install.ps1 | iex' if windows else 'curl -fsSL https://omp.sh/install | sh'
    install = f'''## 3. Install Oh My Pi

Run the one-line installer from [omp.sh](https://omp.sh/).

**Terminal: {shell}, ordinary user.**

```{fence}
{command}
```

**Restart your terminal after installing OMP so PATH changes take effect.** Follow any PATH instructions the installer prints, then close and reopen your terminal before starting OMP or entering your API key. On WSL, reopen Ubuntu.

**Expected:** The installer finishes successfully. In the new terminal, `omp --version` prints the installed version.

**Stop:** The installer reports an error or `omp` is not found.

**Recovery:** Check the installer's error or PATH instructions, then reopen the terminal and try `omp --version` again.

'''
    if platform != 'windows-wsl':
        install = install.replace(' On WSL, reopen Ubuntu.', '')
    section(relative, '## 3. Install Oh My Pi\n', '## 4. Get the course files\n', install)

for platform in ['arch-linux', 'ubuntu']:
    relative = MODULE / f'platforms/{platform}.md'
    prefix = '  if [ "$resolved" != "$HOME/.local/bin/omp" ];' if platform == 'arch-linux' else '  [ "$resolved" = "$HOME/.local/bin/omp" ]'
    line(relative, prefix, '  case "$resolved" in /*) ;; *) printf \'STOP: omp is not on PATH\\n\' >&2; return 1 ;; esac')
    if platform == 'arch-linux':
        replace(relative, 'version="$("$HOME/.local/bin/omp" --version 2>/dev/null)"', 'version="$("$resolved" --version 2>/dev/null)"')
    else:
        replace(relative, '`OMP_PATH` ending in `/.local/bin/omp`', '`OMP_PATH` with the installed command path')

relative = MODULE / 'platforms/macos.md'
section(relative, '  if [ "$omp_path" != "$HOME/.local/bin/omp" ]; then\n', '  version="$(omp --version 2>/dev/null)"', '  case "$omp_path" in /*) ;; *) printf \'STOP: omp is not on PATH\\n\' >&2; return 1 ;; esac\n')
replace(relative, '  version="$(omp --version 2>/dev/null)"', '  version="$("$omp_path" --version 2>/dev/null)"')
replace(relative, '`OMP_PATH` ending in `/.local/bin/omp`, `PATH_FIRST`,', '`OMP_PATH` with the installed command path,')
replace(relative, '### Confirm Git works\n', 'If you installed Homebrew, follow its **Next steps** to add `brew shellenv` to your shell startup file. This keeps Homebrew and its Python available after you restart Terminal.\n\n### Confirm Git works\n')
line(relative, 'Checksum mismatch or conflicting destination:', 'If the installer fails, keep its error and check [omp.sh](https://omp.sh/) for the current installation instructions. If macOS blocks OMP from starting, follow Apple’s Gatekeeper guidance at https://support.apple.com/en-us/102445 with the device owner.')
line(relative, 'Tools not found after reopening:', 'Tools not found after reopening: follow the OMP installer’s PATH instructions or Homebrew’s **Next steps**, then open another new window from the Shell menu and repeat step 5. If `SET` appears before key entry, open a fresh window directly from the Shell menu.')

relative = MODULE / 'platforms/windows-powershell.md'
line(relative, "  $dest = Join-Path $env:LOCALAPPDATA 'omp\\omp.exe'", '')
line(relative, "  if ($found -ine $dest)", "  if (-not $found) { throw 'STOP: omp is not on PATH. Restart PowerShell after installation.' }")
replace(relative, '  $version = @(& $dest --version)', "  Write-Output ('OMP_PATH ' + $found)\n  $version = @(& $found --version)")
replace(relative, '**Expected:** `OMP_VERSION omp/<semver>`, the Python and course paths,', '**Expected:** `OMP_PATH`, `OMP_VERSION omp/<semver>`, the Python and course paths,')
start = next(value for value in current(relative).splitlines() if value.startswith('### Step 3:'))
section(relative, start + '\n', '### Step 4:', start + '\n\n- **The installer reports an error:** keep the error and check [omp.sh](https://omp.sh/) for the current installation instructions.\n- **`omp` is not found:** follow any PATH instructions the installer printed, close every terminal window, and reopen PowerShell from Start.\n- **Windows blocks OMP from starting:** save the message and ask the device owner.\n\n')
line(relative, '- **`omp` missing or a different program:**', '- **`omp` missing or a different program:** follow the installer’s PATH instructions, close every terminal window, and reopen PowerShell from Start. Use `Get-Command omp` and `omp --version` to check what runs.')

relative = MODULE / 'platforms/windows-wsl.md'
line(relative, '  [ "$found" = "$HOME/.local/bin/omp" ]', '  case "$found" in /mnt/*|*.exe|\'\') printf \'STOP: Linux omp is not on PATH\\n\'; return 1 ;; /*) ;; *) printf \'STOP: omp is not an executable path\\n\'; return 1 ;; esac')
replace(relative, '  version="$(omp --version)"', '  version="$("$found" --version)"')
replace(relative, '`OMP_PATH` ending in `/.local/bin/omp`', '`OMP_PATH` with the installed Linux command path')
section(relative, '### Oh My Pi install problems\n', '### Course file problems\n', '### Oh My Pi install problems\n\nIf the installer reports an error, check its message and the current instructions at [omp.sh](https://omp.sh/). Run the Linux installer inside Ubuntu. For a certificate or proxy error, ask for the approved network settings.\n\n')
section(relative, '**`OMP_PATH missing` or a different path.**', '**`SET` in a new window before you entered a key.**', '**`OMP_PATH missing`.** Follow the installer’s PATH instructions, then close Ubuntu and reopen it from a new Windows PowerShell window using the [open box](#choose-and-open-ubuntu). Run `command -v omp` and `omp --version` inside Ubuntu to confirm the Linux installation is available.\n\n')

relative = MODULE / 'platforms/ubuntu.md'
line(relative, '- Download or certificate error:', '- Download or certificate error: keep the installer’s error. Install `ca-certificates` through step 2 if it is missing, or ask about the approved proxy settings, then retry the official installer.')
line(relative, '- Checksum mismatch:', '')
line(relative, '- A different `omp`, or a symlinked', '- An existing `omp` reports an unexpected version: check `command -v omp` and `omp --version`, then confirm you are using the installation you intended.')
line(relative, '- `omp` missing or not `~/.local/bin/omp`:', '- `omp` missing: follow the installer’s PATH instructions, close the terminal, and open a new one from the desktop menu before retrying `omp --version`.')

relative = MODULE / 'platforms/arch-linux.md'
line(relative, '- OMP checksum or install stop:', '- OMP install error: keep the installer’s message and check [omp.sh](https://omp.sh/). If `omp` is missing, follow the installer’s PATH instructions and restart the terminal.')

relative = MODULE / 'shared/VERSIONS.md'
replace(relative, "Verify the selected release's checksum before executing it and retain its reported version with the run evidence.", 'Install OMP with the official one-line command from [omp.sh](https://omp.sh/) and retain its reported version with the run evidence.')
line(relative, '| Oh My Pi |', '| Oh My Pi | latest stable release from the official installer | In a restarted terminal, `omp --version` reports `omp/<semver>`; record the resolved command path and actual version. |')
section(relative, 'Download the OMP binary and `SHA256SUMS.txt`', '## Match the package route to the operating system\n', 'Use the macOS/Linux installer inside macOS, Linux, or WSL Ubuntu. Use the PowerShell installer for native Windows. Follow any PATH instructions the installer prints, then restart your terminal before running OMP or entering the API key. The installer chooses its installation location; confirm `omp` is available in the new terminal.\n\n')

relative = MODULE / 'shared/TROUBLESHOOTING.md'
line(relative, '| The checksum fails or the selected asset', '| The OMP installer reports an error | Keep the error and check the current installation instructions at [omp.sh](https://omp.sh/). |')
line(relative, '| `omp` is not found |', '| `omp` is not found | Follow the installer’s PATH instructions, then close and reopen the terminal. Check the resolved command path below and run `omp --version`. |')
line(relative, '| `omp` reports a different version |', '| `omp` reports a different version | Note the path and version you found, then confirm PATH selects the intended installation. The official installer supplies the latest stable release; record the actual version used. |')

replace('README.md', "Setup resolves [the official latest release](https://github.com/can1357/oh-my-pi/releases/latest) once and verifies the binary against that release's checksum list.", 'Setup uses the official one-line installer from [omp.sh](https://omp.sh/), followed by a terminal restart and an `omp --version` check.')

if '--apply' in sys.argv:
    expected = json.loads((WORK / 'omp-setup-baseline.json').read_text())
    for relative, (original, _) in changes.items():
        if hashlib.sha256(original.encode()).hexdigest() != expected[relative]:
            raise SystemExit(f'Source changed since preparation: {relative}')
    for relative, (_, updated) in changes.items():
        (ROOT / relative).write_text(updated)
        print(f'Updated {relative}')
else:
    (WORK / 'omp-setup-baseline.json').write_text(json.dumps({
        name: hashlib.sha256(original.encode()).hexdigest()
        for name, (original, _) in changes.items()
    }, indent=2))
    diff = ''.join(''.join(difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile=name, tofile=name,
    )) for name, (original, updated) in changes.items())
    (WORK / 'omp-setup.patch').write_text(diff)
    for name, (original, updated) in changes.items():
        print(f'{name}: {len(original.splitlines())} -> {len(updated.splitlines())} lines')
    print(f'Prepared patch: {WORK / "omp-setup.patch"}')
