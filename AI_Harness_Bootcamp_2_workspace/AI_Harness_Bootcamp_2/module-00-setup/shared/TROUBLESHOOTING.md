# When setup stops

Start with the first failed action. Copy and paste its error into the harness, describe what you were doing when it appeared, and explain what you are trying to accomplish. Finish with **“Fix this issue.”**

Review and apply the fix, then rerun the failed check. If it still fails, paste the new error into the same conversation and describe what you tried. Keep the earlier error so you can compare the results. If the harness itself cannot start, find the symptom below.

## Choose the next action from the observed failure

| What you see | What to do next |
|---|---|
| Git or Python is missing | Return to step 2 of your platform guide; for Git, finish with its **Confirm Git works** box. On a managed device, stop when policy blocks installation and send the support packet below. |
| `git --version` fails right after Git installs | Open a new terminal window and run it again; a window opened before the install can miss the new Git. On Windows, close every terminal window and open Windows PowerShell from Start. On a Mac, a dialog that offers the command line developer tools is Apple's Git installer; approve it only if the device owner allows you to install software. |
| A download fails | Keep the HTTP, proxy, or certificate error. Use the official release URLs. Do not disable TLS verification or execute an incomplete download. |
| The OMP installer reports an error | Keep the error and check the current installation instructions at [omp.sh](https://omp.sh/). |
| `omp` is not found | Follow the installer’s PATH instructions, then close and reopen the terminal. Check the resolved command path below and run `omp --version`. |
| `omp` reports a different version | Note the path and version you found, then confirm PATH selects the intended installation. The official installer supplies the latest stable release; record the actual version used. |
| A course directory already exists | Confirm that it is the intended checkout. Use it without reset, pull, or clean when it is valid; otherwise leave it untouched and resolve the path conflict. |
| Git cannot read the private course repository | A website password is not GitHub access. Follow the platform's read check with prompts disabled, then use the browser-login steps if needed. Login does not grant permission. Ask the repository owner about the invitation or organization approval, and keep any existing checkout. |
| GitHub CLI reports unapproved credential storage | Stop before configuring the Git helper or cloning. Ask the device owner to set up approved credential storage or approved Git credentials. Do not request plaintext storage or share authentication output. |
| The conditional GitHub CLI package is unavailable | Use only the named platform's official package route. Ubuntu's `gh` requires Universe; ask the owner to approve that component if unavailable. Do not silently add sources. Arch's `github-cli` installation uses a full upgrade, not a partial upgrade. |
| The new terminal has tools but the key is `MISSING` | That's expected in an independently opened terminal. Enter the key through the hidden prompt in that terminal. Never put the key in a shell profile. |
| A new process reports an unexpected `SET` | Check if the new process inherited the environment from a parent. `SET` alone does not tell you whether the key was saved or exposed. Do not include an environment dump in the evidence. |
| The launcher exits 2 | Read its prerequisite message. Missing key, wrong OMP version, missing input, conflicting permissions, or an existing attempt can stop before a provider request. No live success has occurred. |
| The launcher exits 1 | Keep the entire attempted run. Check `result.json` and the raw receipts. A file left behind does not make an incomplete turn successful. |
| The provider returns 401 or 403 | Confirm the participant key and model access in OpenRouter without printing the key. Do not try a direct-provider login or silently switch models. |
| The provider returns 402 or 429 | Stop. Keep the response and sort out account or rate availability before starting a new attempt on purpose. Do not loop retries. |
| The assistant claims it wrote a file, but the file or receipt is absent | Record `HOLD`. Check the declared work root and authorized filename. Do not create the file yourself or use chat text in place of a tool-write receipt. |
| A write or evidence destination already exists | Keep that attempt. After you record the cause, start with new work/output and receipt paths. Changing only E does not make an existing output new. |
| A Windows script is blocked by execution policy or signing requirements | Check the effective policy and every scope. Leave organizational and intentionally configured restrictions as they are, and ask the device owner for an approved route. Temporary Process-scope `RemoteSigned` applies only to the native setup when the unmanaged default is explicitly authorized; it does not change CurrentUser or LocalMachine. |
| A new Windows tab cannot find an installed tool | Close all relevant terminal windows and reopen Windows PowerShell from Start. A new tab can inherit the old terminal application's PATH. Check which Git, Python, and OMP commands the reopened terminal finds before proceeding. |
| WSL paths point under `/mnt/c` | Use the selected Ubuntu distribution's Linux home and Linux OMP asset. Do not mix Windows executable/configuration paths with the WSL attempt. `df` reports filesystem space; its mount name need not begin with `/home`. |
| The chosen WSL distribution shows VERSION 1 | Setting the default version affects new distributions only. Keep the existing distribution and get the owner's approval for backup and conversion before proceeding. Do not unregister or reset it. |
| A fresh macOS terminal cannot find Homebrew or Python | Check the saved `brew shellenv` and versioned Python PATH settings for the shell you use, then open another independent terminal. Do not repair PATH inside the verification block. |

## If omp is not found after restarting

On macOS, Linux, or WSL, the installer may print its installation folder without adding it to PATH. Open the startup file for your shell in a text editor:

| Shell | Startup file |
|---|---|
| zsh | `~/.zshrc` (or `.zshrc` inside your configured `ZDOTDIR`) |
| Bash on Linux or WSL | `~/.bashrc` |
| Bash in macOS Terminal | `~/.bash_profile` |

For the default standalone or Bun installation, add this line once and save the file:

```text
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"
```

If the installer printed a different installation folder, include that folder instead. Close and reopen the terminal, then run `omp --version` again. On native Windows, close every terminal window and reopen PowerShell from Start so it reads the installer’s saved PATH changes.

## When local Obsidian stops

Save the first error, app version, platform, attempt folder, and last Obsidian action before changing anything. Keep **Obsidian READY/HOLD** separate from OMP and n8n. Module 2 needs local Obsidian READY; another editor or a disk PASS cannot replace what you saw in Obsidian. Use your existing guide's **Set up local Obsidian** section: [native Windows](../platforms/windows-powershell.md#set-up-local-obsidian), [WSL Ubuntu](../platforms/windows-wsl.md#set-up-local-obsidian), [macOS](../platforms/macos.md#set-up-local-obsidian), [Ubuntu](../platforms/ubuntu.md#set-up-local-obsidian), or [Arch](../platforms/arch-linux.md#set-up-local-obsidian).

| What you see | What to do next |
|---|---|
| Obsidian is absent or installation is blocked | Use the guide's approved official route and [reference asset table](VERSIONS.md#local-obsidian-for-module-2). Record Obsidian HOLD if device policy or install approval blocks it. Keep the OMP and n8n results; do not disable Gatekeeper, antivirus, or package-signature checks. |
| Obsidian already exists, possibly at another version | Keep its binary, profile, and personal vaults. Record the version you have and use a new local practice vault. Complete the same steps in the app without forcing an upgrade, downgrade, profile reset, or replacement. |
| Asset SHA-256 differs from the reference value | Do not execute it. Keep the filename, source URL, expected hash, hash you got, and failed download. Resolve the release or architecture mismatch before downloading to a new location. Use the [official release metadata](https://api.github.com/repos/obsidianmd/obsidian-releases/releases/tags/v1.13.7); renaming a file does not verify it. |
| Arch package version differs from the reference 1.13.7-2 | Record the signed Extra version you have and check whether Obsidian is ready. Use only the guide's approved full-upgrade route; never downgrade or run a partial upgrade to match the reference version. See [Arch maintenance](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported). |
| WSL command-line tools work but Obsidian has no window | Record Obsidian HOLD. Check the [WSLg requirement](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps): build 19044+ or Windows 11, WSL 2, and GUI support in the selected Ubuntu. Builds 19041–19043 cannot use this windowed-app route. Keep the distribution and ask for an approved time to update and restart. Do not shut down active Docker or another distribution without approval. |
| WSL vault is a UNC path or lies under `/mnt/c` | Stop this attempt and keep it. Use Linux Obsidian and a fresh readiness root in the same Ubuntu Linux home as OMP. Do not use native Windows Obsidian on the WSL vault, relocate earlier work, or create a synchronized duplicate. |
| Linux reports a missing display or cannot open the window | Confirm that you are in the intended graphical desktop or WSLg session, not a headless/remote-only shell. Keep the exact display error and use the owner's approved way to open the app window. A CLI launch without a usable window is HOLD. |
| Ubuntu ARM64 AppImage reports missing FUSE | Use the guide's owner-approved apt step for `libfuse2t64` on Ubuntu 24.04/26.04. Keep FUSE 3; do not replace it with obsolete `fuse`. See [AppImage's FUSE guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html). If the approved package is unavailable, stay on HOLD. |
| ARM64 AppImage renderer sandbox prevents launch, or exception approval is absent | The vendor's [AppImage route](https://github.com/obsidianmd/obsidian-help/blob/master/en/Getting%20started/Download%20and%20install%20Obsidian.md) uses `--no-sandbox`, which disables Chromium's renderer sandbox for this app. Get separate approval from the device owner through the platform step or keep Obsidian HOLD. Do not change kernel-wide security, make binaries world-writable, or improvise privileged sandbox fixes. |
| `initialize` reports an existing, linked, or overlapping root | Keep that root, even if the attempt is incomplete. Choose a fresh local child outside every checkout and outside synced folders. On WSL, use its Linux home. Never remove an existing root to make the command pass. |
| `Start` or `Token` links are absent, or a link creates an empty note | Confirm that Obsidian opened this attempt's `vault` child, not its parent or the checkout. Use Reading view to follow `Start` → `Token` → `Reply`. Keep any supplied notes that were altered and the failed attempt. If the notes' content changed, initialize a fresh root. |
| `check` reports that the saved reply does not match | In the same vault's Obsidian window, follow `Token` and replace `Reply` with only its current token on one line. Save with Cmd+S on macOS or Ctrl+S on Windows/Linux, then rerun `check` against the same root. Keep the failed check record. Do not edit the external expected record. |
| `refresh` succeeds but Obsidian still shows the old token | Confirm the open vault and helper root match. Return to `Token` and watch for the change in Obsidian. If the old token remains, keep a record of what you saw and record HOLD. Do not keep rotating the token, copy it from the terminal, or use another editor to show that Obsidian refreshed. You still need to see Obsidian's [external-refresh behavior](https://github.com/obsidianmd/obsidian-help/blob/master/en/Files%20and%20folders/How%20Obsidian%20stores%20data.md) work on your device. |
| The reply changes or disappears after closing/reopening | Confirm the reopened vault is the same local folder and that Sync remains off. Keep a record of the failure. Fix the save or path issue you found, then repeat the affected edit, save, and reopen steps in Obsidian and check the file on disk. If you never saw the external refresh in Obsidian, that part remains HOLD. |
| Helper reports changed expected identity, changed source, or an interrupted operation | Keep the whole attempt, including any `.readiness-operation` directory. Do not hand-edit records or remove locks to obtain PASS. Resolve the cause and use a fresh root for a complete new sequence. |
| Helper prints its qualified PASS but no one watched the GUI actions in Obsidian | The disk record shows what happened on disk, not what happened in Obsidian. Follow the link/edit/save/refresh/reopen steps in your [platform guide](../README.md#set-up-local-obsidian) and record what you see in the Obsidian window before recording Obsidian READY. Never change `gui_observed: false` in the helper's receipt. |

Run the helper in a terminal as an ordinary user, and make edits in the Obsidian window. Keep Restricted community plugins on and Sync off. An account, plugin, MCP service, or provider call cannot repair this readiness check. Follow the [hidden-input credential procedure](CREDENTIALS.md), and never store a provider key in notes, a shell profile, or another secret file. When you report Obsidian HOLD, keep the earlier OMP and n8n results and every failed attempt.

## When local n8n stops

Keep **n8n READY/HOLD** separate from the OMP setup report and the live OMP readiness result. Module 7 requires n8n READY, but checking n8n needs no model call, n8n Cloud signup, or Assistant key. Use the n8n section in your platform guide and the common helper.

| What you see | What to do next |
|---|---|
| Helper reports not prepared or HOLD | Keep the exact message and contact the device/support owner. Missing preparation, changed configuration, a stopped service, or a different engine can each cause HOLD. Don't create another project to bypass it. |
| Docker/Desktop not running or unreachable from helper | Ask owner to start the approved engine (Desktop or service). Repeat the helper start/status in a fresh shell after it is up. Do not start it yourself if policy requires approval. |
| Port 5678 occupied | Identify listener with owner. Do not kill or change port. Use another approved machine if needed. |
| `$HOME/n8n-course` or project record exists (or resources under name) | Leave in place. Ask owner to identify the instance/version/data. Use only the recorded project via the helper. Existing work is owner-controlled. |
| Helper or status shows wrong version, port not 127.0.0.1:5678, or runner missing | Record n8n HOLD. Keep the instance. Owner must resolve. Do not repin, upgrade, or edit config. |
| Browser cannot reach or login fails for existing | Confirm localhost:5678 and instance identity with owner. Do not reset owner account. |
| Workflow does not survive reload or staff restart | Record n8n HOLD. Keep directory/volumes. Confirm with owner that the same recorded instance and volumes were used. Never use down -v. |
| Native PowerShell cannot find Docker | Ask staff to check Docker Desktop's Linux-container backend and `docker.exe` in a fresh PowerShell window. Keep OMP and the other tools native. |
| WSL Ubuntu cannot reach Docker Desktop | Ask staff to check integration for the selected Ubuntu distribution. Don't install a second engine or move the prepared directory to a Windows mount. |

Verify status, browser access, and saved-workflow persistence on your own device. Share only redacted errors; never include credentials or the full private configuration.

## Confirm the command you are actually running

These checks make no provider call and print no credential. Run the block in the same terminal that failed.

**Terminal: Bash or zsh, ordinary user.**

```bash
command -v omp && omp --version
```

**Terminal: PowerShell, ordinary user.**

```powershell
$ompCommand = Get-Command omp -CommandType Application -ErrorAction Stop
$ompCommand.Source
& $ompCommand.Source --version
if ($LASTEXITCODE -ne 0) { throw 'HOLD: the selected OMP executable failed its version check.' }
```

**Expected:** The path is the installation you verified, and the version is the observed `omp/<semver>` from the resolved release.

**Stop:** The command is missing, resolves to an unexpected installation, fails to run, or reports another version.

**Recovery:** Fix only the installation or PATH issue shown in the output. Keep other installations and repeat the check before a model turn.

**PATH** is the ordered list of directories your terminal searches for a command. Changing PATH does not install a program, and an open terminal does not pick up settings saved later. The key works differently: keep it in the current terminal process only, even if you save a non-secret PATH setting.

## Distinguish slow work from a stopped process

Keep the original terminal visible. In Activity Monitor on macOS, Task Manager on Windows, or your Linux system monitor, find the named download or package-manager process and check its current CPU, disk, and network activity. A single check showing no activity does not mean the process has hung.

If an installation was interrupted, follow the package manager's recovery instructions instead of killing or restarting without checking. For a provider turn, the launcher times out after a set limit and records an incomplete attempt. Wait for it to report the failure instead of starting a second provider process.

## Capture a support packet

```text
Platform, version, and architecture:
Terminal and privilege level:
Step title:
Command or UI action, with no key value:
Resolved tool path and version:
First error and exit code:
Expected observation:
Last known-good observation:
What changed immediately before the failure:
External attempt/report location:
Whether any output or forbidden effect appeared:
```

Redact personal paths, account IDs, internal hosts, and credentials from what you share. Keep command names, versions, exit codes, and the first error. An exposed key must be revoked; deleting it from a screenshot does not revoke access.

Give the harness the support packet along with your goal and the request **“Fix this issue.”** After you review and apply the fix, repeat the failed check and report the result in the same conversation. If you cannot explain a correction, a rollback fails, or device policy blocks the action, record `HOLD` and contact the responsible owner. Do not disable certificate checks, Gatekeeper, antivirus, or protected filesystem permissions to force progress.
