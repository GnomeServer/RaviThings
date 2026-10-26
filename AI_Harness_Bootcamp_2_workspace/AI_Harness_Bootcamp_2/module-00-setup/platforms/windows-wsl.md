# Windows WSL 2 with Ubuntu setup

Windows Subsystem for Linux 2 (WSL 2) runs Ubuntu on your Windows computer. Install the course tools inside Ubuntu and keep all course files in your Linux home folder. Never put course work under `/mnt/c`: from Ubuntu, that's the Windows C: drive. Plan for 60 to 120 minutes, plus a restart if WSL is new on this computer. This is an estimate, not a measured time.

Start in Windows PowerShell to choose and open Ubuntu. Then follow nine steps in the Ubuntu window to install the latest stable Oh My Pi release, run a live readiness check, and save a setup report. After that, set up Linux Obsidian; WSLg shows its window on your Windows desktop. Finally, set up local n8n 2.41.5 through Docker Desktop for Module 7. The only provider key is `OPENROUTER_API_KEY`, and the course launcher selects `openrouter/anthropic/claude-sonnet-4.6`. You don't install Node, npm, or another agent.

Paste each box as one block into the window named by its **Terminal:** label. **Expected:** shows what success looks like. **Stop:** tells you when not to continue, and **Recovery:** gives the first fix; longer fixes are in [If a step stops](#if-a-step-stops). Get the device owner's approval before installing software or changing Windows features. Keep any existing Ubuntu installation; never unregister or reset it.

## Choose and open Ubuntu

WSL needs Windows 10 build 19041 or newer, or Windows 11 ([Microsoft's WSL requirements](https://learn.microsoft.com/en-us/windows/wsl/install)). Obsidian and Docker Desktop need newer builds; their sections check that. Start by looking at what this computer already has.

**Terminal: Windows PowerShell, ordinary user, opened from Start.**

```powershell
$os = Get-CimInstance -ClassName Win32_OperatingSystem
'Windows: {0}, build {1}' -f $os.Caption, $os.BuildNumber
wsl --version
'WSL version exit: ' + $LASTEXITCODE
wsl --list --verbose
'Installed list exit: ' + $LASTEXITCODE
```

**Expected:** a build of 19041 or higher, the WSL component versions, and a table with NAME, STATE, and VERSION columns. If a NAME that starts with `Ubuntu` shows VERSION `2`, skip the install box and use the open box.

**Stop:** the build is below 19041, PowerShell doesn't recognize `wsl`, or a policy message blocks WSL.

**Recovery:** If no Ubuntu is installed, use the install box next, even if `wsl --version` failed; `wsl --install` also installs WSL itself. If an Ubuntu is installed and `wsl --version` failed, the Ubuntu shows VERSION `1`, or a policy blocks WSL, see [Windows and WSL problems](#windows-and-wsl-problems).

If no Ubuntu is installed, install Ubuntu 24.04 using its exact name. Open PowerShell with **Run as administrator** for this box only. A new installation runs as WSL 2.

**Terminal: Windows PowerShell, elevated (Run as administrator); only when no Ubuntu is installed.**

```powershell
wsl --install -d Ubuntu-24.04
if ($LASTEXITCODE -ne 0) { throw 'STOP: keep the install message; restart Windows if it asked you to.' }
```

**Expected:** Ubuntu-24.04 installs, or Windows asks you to restart. When Ubuntu first opens, create a Linux username and password; the password doesn't show while you type. Type `exit` to leave Ubuntu, then close this administrator window. In the open box, enter the NAME `Ubuntu-24.04`.

**Stop:** help text appears instead of an installation, the name isn't found, or the install fails.

**Recovery:** After a restart, run the first box again before you install anything else. For other failures, see [Windows and WSL problems](#windows-and-wsl-problems).

Use the exact Ubuntu NAME from the list to open it. The box checks that this NAME is installed and runs as WSL 2. It then opens Ubuntu in your Linux home folder in the same window. Opening it by name keeps you in the same Ubuntu even when the computer has several Ubuntu installations.

**Terminal: Windows PowerShell, ordinary user, opened from Start.**

```powershell
. {
  $CourseDistro = Read-Host 'Exact Ubuntu NAME from the list, for example Ubuntu-24.04'
  $CourseVersion = $null
  foreach ($CourseLine in @(wsl --list --verbose)) {
    if ((($CourseLine -replace "`0", '') -match '^\s*\*?\s*(\S+)\s.*\s(\d)\s*$') -and $Matches[1] -ceq $CourseDistro) { $CourseVersion = $Matches[2] }
  }
  if (-not $CourseVersion) { throw 'STOP: that exact NAME is not in the installed list.' }
  if ($CourseVersion -ne '2') { throw 'STOP: that Ubuntu runs as WSL 1; see If a step stops.' }
  wsl --distribution $CourseDistro --cd ~
}
```

**Expected:** an Ubuntu prompt that ends in `$`. Run the Ubuntu steps below in this window.

**Stop:** a `STOP:` line appears, or Ubuntu fails to start.

**Recovery:** Copy the NAME exactly as listed, including capital letters. For WSL 1 or an Ubuntu that won't start, see [Windows and WSL problems](#windows-and-wsl-problems).

## 1. Check this Ubuntu

This box checks your Linux account, Ubuntu release, processor, and free space. It lists packages you still need and finds Python 3.12 or newer. It saves Python's full path as `PY` for later steps.

**Terminal: Ubuntu Bash, ordinary Linux user, the window you just opened.**

```bash
course_find_python() {
  local candidate found
  for candidate in python3.12 python3 python; do
    found="$(type -P "$candidate")" || continue
    found="$(readlink -f -- "$found")" || continue
    case "$found" in /mnt/*|*.exe) continue ;; esac
    "$found" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null || continue
    printf '%s\n' "$found"
    return 0
  done
  return 1
}
course_check_wsl() {
  local release arch free_kb tool found missing=''
  if [ -z "${BASH_VERSION:-}" ] || [ "$(id -u)" -eq 0 ]; then
    printf 'STOP: use Bash as your ordinary Linux user, not root\n'; return 1
  fi
  cd "$HOME" || return 1
  case "$HOME" in /home/?*) ;; *) printf 'STOP: your home folder must be under /home\n'; return 1 ;; esac
  if [ "$(pwd -P)" != "$HOME" ] || [ ! -w "$HOME" ]; then
    printf 'STOP: your home folder is a link or is not writable\n'; return 1
  fi
  release="$(. /etc/os-release && printf '%s %s' "$ID" "$VERSION_ID")" || return 1
  arch="$(uname -m)"
  free_kb="$(df -Pk "$HOME" | awk 'NR == 2 {print $4}')"
  for tool in git curl; do
    found="$(type -P "$tool")" && found="$(readlink -f -- "$found")" || found=''
    case "$found" in ''|/mnt/*|*.exe) missing="$missing $tool" ;; esac
  done
  if [ "$(dpkg-query -W -f='${Status}' ca-certificates 2>/dev/null)" != 'install ok installed' ] || [ ! -s /etc/ssl/certs/ca-certificates.crt ]; then
    missing="$missing ca-certificates"
  fi
  PY="$(course_find_python)" || { PY=''; missing="$missing python3"; }
  [ -n "$missing" ] || missing=' none'
  printf 'USER %s\nHOME %s\nUBUNTU %s\nARCH %s\n' "$(id -un)" "$HOME" "$release" "$arch"
  printf 'WSL_DISTRO %s\nFREE_GB %s\n' "${WSL_DISTRO_NAME:-not reported}" "$(( ${free_kb:-0} / 1048576 ))"
  printf 'PACKAGES_TO_INSTALL %s\nPY %s\n' "${missing# }" "${PY:-not found}"
  case "$release" in 'ubuntu 24.04'|'ubuntu 26.04') ;; *) printf 'STOP: use Ubuntu 24.04 or 26.04\n'; return 1 ;; esac
  case "$arch" in x86_64|aarch64) ;; *) printf 'STOP: this processor is not supported\n'; return 1 ;; esac
  [ "${free_kb:-0}" -ge 26214400 ] || { printf 'STOP: free at least 25 GB in your Linux home\n'; return 1; }
  printf 'CHECK DONE\n'
}
course_check_wsl
```

**Expected:** your username, a `/home/` path, `UBUNTU ubuntu 24.04` or `ubuntu 26.04`, `ARCH x86_64` or `aarch64`, your Ubuntu NAME, `FREE_GB` of 25 or more, a `PACKAGES_TO_INSTALL` line, a `PY` line, and `CHECK DONE`. A new Ubuntu usually lists some packages; step 2 installs them.

**Stop:** a `STOP:` line appears.

**Recovery:** Use the Ubuntu and user the STOP line asks for, or free space inside Ubuntu. See [Ubuntu check and package problems](#ubuntu-check-and-package-problems).

## 2. Install Git and the other missing packages

**Git** copies the course files from GitHub to your computer and records exactly which version you have. Step 4 uses it to make your checkout in your Linux home. Install Git inside Ubuntu with Ubuntu's `git` package, as the [Git project](https://git-scm.com/install/linux) recommends for Linux. Git for Windows doesn't count here: Ubuntu needs its own Git, and step 1 ignores Windows programs under `/mnt/c`.

If step 1 printed `PACKAGES_TO_INSTALL none`, skip the install box and go to [Confirm Git works](#confirm-git-works). Otherwise, run this box to install the packages. `sudo` runs one command with administrator rights inside Ubuntu. At its password prompt, type your Linux password; nothing appears while you type.

**Terminal: Ubuntu Bash, ordinary Linux user using sudo for package changes, same window.**

```bash
sudo apt-get update && sudo apt-get install -y git python3 curl ca-certificates && course_check_wsl
```

**Expected:** apt finishes, and the repeated check prints `PACKAGES_TO_INSTALL none`, a `PY` path, and `CHECK DONE`.

**Stop:** apt reports no installation candidate, an unreachable source, or permission denied.

**Recovery:** Keep the apt output and ask the owner to fix Ubuntu's package sources; don't add other sources. See [Ubuntu check and package problems](#ubuntu-check-and-package-problems).

### Confirm Git works

This box shows which Git Ubuntu finds and asks it for its version. Run it even if you skipped the install box.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
command -v git && git --version
```

**Expected:** `/usr/bin/git`, then `git version 2.` followed by more numbers.

**Stop:** the box prints nothing, no `git version` line appears, or the path starts with `/mnt/`.

**Recovery:** Paste the step 2 box again in this Ubuntu window, not in PowerShell. See [Ubuntu check and package problems](#ubuntu-check-and-package-problems).

## 3. Install Oh My Pi

Run the one-line installer from [omp.sh](https://omp.sh/).

**Terminal: Ubuntu Bash inside WSL, ordinary user.**

```bash
curl -fsSL https://omp.sh/install | sh
```

**Restart your terminal after installing OMP so PATH changes take effect.** Follow any PATH instructions the installer prints, complete Step 4 in this window, then close and reopen your terminal as directed in Step 5 before starting OMP or entering your API key. On WSL, reopen Ubuntu.

**Expected:** The installer finishes successfully. In the new terminal, `omp --version` prints the installed version.

**Stop:** The installer reports an error or `omp` is not found.

**Recovery:** Check the installer’s error. For `omp` not found, use [PATH recovery](../shared/TROUBLESHOOTING.md#if-omp-is-not-found-after-restarting), then reopen the terminal and try `omp --version` again.

## 4. Get the course files

The course files are in a private GitHub repository. This box checks whether your existing Git credentials can read it. If they can, it uses the checkout at `~/Documents/AIHB_OCT_2026` or clones one there. It never replaces, resets, or cleans an existing folder.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
course_get_files() {
  local origin=https://github.com/TheHolofex/AIHB_OCT_2026.git
  R="$HOME/Documents/AIHB_OCT_2026"
  M="$R/AI_Harness_Bootcamp_2/module-00-setup"
  if ! GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code "$origin" HEAD; then
    printf 'STOP: GitHub access failed; use If GitHub access fails below\n'; return 1
  fi
  if [ -L "$R" ] || { [ -e "$R" ] && [ ! -d "$R" ]; }; then
    printf 'STOP: %s is not a plain folder; it was kept\n' "$R"; return 1
  fi
  if [ -d "$R" ]; then
    if [ ! -d "$R/.git" ] || [ "$(git -C "$R" remote get-url origin 2>/dev/null)" != "$origin" ]; then
      printf 'STOP: %s is not this course checkout; it was kept\n' "$R"; return 1
    fi
    printf 'Using the existing course checkout.\n'
  else
    mkdir -p -- "$HOME/Documents" || return 1
    GIT_TERMINAL_PROMPT=0 git -c core.autocrlf=false clone "$origin" "$R" || {
      printf 'STOP: clone failed; any partial folder was kept\n'; return 1; }
    printf 'Cloned the course checkout.\n'
  fi
  "$PY" - "$R" "$M" <<'PY'
from pathlib import Path
import sys
root, module = map(Path, sys.argv[1:])
required = [root/'shared/run_omp.py', root/'shared/course_guard.mjs', module/'shared/MODULE_00_LAB.md',
            module/'shared/VERSIONS.md', module/'shared/case/verify_tool_proof.py', module/'scripts/verify-setup.sh']
for file in required:
    if file.resolve() != file or not file.is_file():
        raise SystemExit('STOP: missing or linked course file: ' + str(file))
    if b'\r\n' in file.read_bytes():
        raise SystemExit('STOP: course file has Windows line endings: ' + str(file))
print('Required course files present with LF line endings')
PY
  [ $? -eq 0 ] || return 1
  printf 'R %s\nM %s\n' "$R" "$M"
}
course_get_files
```

**Expected:** a commit hash followed by `HEAD`, then `Using the existing course checkout.` or `Cloned the course checkout.`, then `Required course files present with LF line endings` and the `R` and `M` paths.

**Stop:** a `STOP:` line appears.

**Recovery:** If access failed, use [If GitHub access fails](#if-github-access-fails), then run this box again. For folder problems, see [Course file problems](#course-file-problems).

### If GitHub access fails

GitHub CLI (`gh`) can sign you in through your browser and give Git the credentials it needs. Use it only if the access check above failed. This first box uses `gh` if it's already installed in Ubuntu; otherwise it installs Ubuntu's package.

**Terminal: Ubuntu Bash, ordinary Linux user using sudo only if gh is missing, same window.**

```bash
if type -P gh >/dev/null; then gh --version; else sudo apt-get update && sudo apt-get install -y gh && gh --version; fi
```

**Expected:** a `gh version` line.

**Stop:** apt reports no installation candidate or a source error.

**Recovery:** Ask the owner to enable Ubuntu's approved package sources; don't add another source.

Sign in with the GitHub account invited to the repository. The command prints a one-time code and asks you to press Enter to open GitHub in a browser. Press Enter. If Ubuntu can't open a browser, it prints an error and keeps waiting. Open https://github.com/login/device in your Windows browser, enter the code, and check the account name before approving. If gh asks whether to set up Git, answer no; the next box does that.

**Terminal: Ubuntu Bash, ordinary Linux user, same window; interactive sign-in.**

```bash
gh auth login --hostname github.com --git-protocol https --web
```

**Expected:** gh reports that you are logged in as the invited account.

**Stop:** authorization is denied, or the account is wrong.

**Recovery:** Ask the repository owner to confirm the invitation for that account, then try again.

Check the sign-in, connect Git to it for github.com only, and repeat the access check.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
gh auth status --hostname github.com && gh auth setup-git --hostname github.com && GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code https://github.com/TheHolofex/AIHB_OCT_2026.git HEAD
```

**Expected:** the status names your account, and the last line is a commit hash followed by `HEAD`. Run the [Get the course files](#4-get-the-course-files) box again.

**Stop:** any of the three commands fails.

**Recovery:** Ask the repository owner to check your access. gh may keep its token in a plain file in your Linux home; if your device policy forbids that, see [Course file problems](#course-file-problems).

## 5. Open a new Ubuntu window and confirm

A freshly opened window shows what every future session will see. Open a new **Windows PowerShell** window from Start. Run the [open box](#choose-and-open-ubuntu) again with the same NAME. Don't type `bash` in the old window instead: a shell started there would inherit the old window's settings. The new Ubuntu window must find `omp` on its own and must not have a key yet. This box also sets `R`, `M`, and `PY` for the rest of setup.

**Terminal: Ubuntu Bash, ordinary Linux user, the newly opened window.**

```bash
course_confirm_window() {
  local candidate found version
  R="$HOME/Documents/AIHB_OCT_2026"
  M="$R/AI_Harness_Bootcamp_2/module-00-setup"
  PY=''
  for candidate in python3.12 python3 python; do
    found="$(type -P "$candidate")" && found="$(readlink -f -- "$found")" || continue
    case "$found" in /mnt/*|*.exe) continue ;; esac
    if "$found" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then PY="$found"; break; fi
  done
  [ -n "$PY" ] || { printf 'STOP: no Python 3.12 or newer found\n'; return 1; }
  [ -f "$M/shared/MODULE_00_LAB.md" ] || { printf 'STOP: the course checkout is missing at %s\n' "$R"; return 1; }
  printf 'R %s\nM %s\nPY %s\n' "$R" "$M" "$PY"
  found="$(command -v omp || true)"
  printf 'OMP_PATH %s\n' "${found:-missing}"
  case "$found" in /mnt/*|*.exe|'') printf 'STOP: Linux omp is not on PATH\n'; return 1 ;; /*) ;; *) printf 'STOP: omp is not an executable path\n'; return 1 ;; esac
  version="$("$found" --version)" || return 1
  printf 'OMP_VERSION %s\n' "$version"
  [[ "$version" =~ ^omp/[0-9]+\.[0-9]+\.[0-9]+$ ]] || { printf 'STOP: installed OMP did not report a version number\n' >&2; return 1; }
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    printf 'SET\nSTOP: a key is already present in this new window\n'; return 1
  fi
  printf 'MISSING\n'
}
course_confirm_window
```

**Expected:** `R`, `M`, and `PY` paths, `OMP_PATH` with the installed Linux command path, `OMP_VERSION omp/<semver>`, and `MISSING` as the last line.

**Stop:** a `STOP:` line, or `SET` before you've entered a key.

**Recovery:** Don't export PATH or enter the key in this window to hide the problem. See [New window problems](#new-window-problems).

## 6. Enter your OpenRouter key

The next box waits for your OpenRouter key at a hidden prompt. Paste or type the key and press Enter; nothing appears on screen. Never put the key in a command, a file, a profile, or a chat. [Connect the course account without leaking a key](../shared/CREDENTIALS.md) explains where a key must not go.

**Terminal: Ubuntu Bash, ordinary Linux user, same new window.**

```bash
IFS= read -r -s OPENROUTER_API_KEY
```

**Expected:** the prompt returns, and the key never appears on screen.

**Stop:** the key appears on screen, or you pasted it as a command instead of at the prompt.

**Recovery:** Revoke a displayed key at OpenRouter, then run this box again with the replacement key.

## 7. Confirm the key is loaded

Export the key so programs started from this Ubuntu window, including the course launcher, can use it. The box prints only `SET` or `MISSING`, never the key.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
export OPENROUTER_API_KEY
if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; else printf 'MISSING\n'; fi
```

**Expected:** `SET`.

**Stop:** `MISSING`, or any output that shows the key.

**Recovery:** Run step 6 and this box again in the same window. Don't save the key to `.profile` or any other file.

## 8. Run the readiness check

The readiness check is a short live task. The box creates a fresh attempt folder with a random token under `~/course-evidence`, outside the checkout. The course launcher then runs Oh My Pi once, allowing it to write only `from-omp.txt`. Finally, the checker confirms that the file contains `omp works` and this attempt's token, and that the write receipt agrees. Allow a few minutes for the model call.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
course_readiness_check() {
  local course_exit
  if [ -z "${PY:-}" ] || [ ! -x "$PY" ] || [ -z "${R:-}" ] || [ -z "${M:-}" ]; then
    printf 'STOP: run the step 5 box in this window first\n'; return 1
  fi
  attempt="$HOME/course-evidence/setup-wsl-proof-$(date -u +%Y%m%dT%H%M%SZ)-$$/module-00"
  proof="$attempt/proof"
  token_file="$attempt/run-token.txt"
  evidence="$attempt/receipts"
  prompt_file="$attempt/prompt.txt"
  "$PY" - "$attempt" <<'PY'
from pathlib import Path
import secrets, sys
attempt = Path(sys.argv[1])
attempt.mkdir(parents=True, exist_ok=False)
(attempt / 'proof').mkdir()
token = secrets.token_hex(16) + '\n'
(attempt / 'run-token.txt').write_text(token, encoding='utf-8')
(attempt / 'proof/run-token.txt').write_text(token, encoding='utf-8')
(attempt / 'prompt.txt').write_text('Read run-token.txt with course_read. Use course_write to create only from-omp.txt containing omp works, one space, and the exact token. Do not write another file.\n', encoding='utf-8')
print('FRESH ATTEMPT', attempt)
PY
  course_exit=$?
  [ "$course_exit" -eq 0 ] || return "$course_exit"
  "$PY" "$R/shared/run_omp.py" --workdir "$proof" --prompt "$prompt_file" --evidence "$evidence" --allow-write from-omp.txt
  course_exit=$?
  printf 'LAUNCH_EXIT %s\n' "$course_exit"
  [ "$course_exit" -eq 0 ] || return "$course_exit"
  "$PY" "$M/shared/case/verify_tool_proof.py" "$proof" "$token_file" "$evidence"
  course_exit=$?
  printf 'VERIFY_EXIT %s\n' "$course_exit"
  return "$course_exit"
}
course_readiness_check
```

**Expected:** `FRESH ATTEMPT` with a folder path, the launcher's output, `LAUNCH_EXIT 0`, the checker's `READINESS CHECK PASS`, and `VERIFY_EXIT 0`.

**Stop:** `LAUNCH_EXIT` or `VERIFY_EXIT` is not 0, or the checker prints `READINESS CHECK HOLD`.

**Recovery:** Keep the failed attempt folder and don't edit `from-omp.txt`. Read the `HOLD:` line, fix that cause, and run this box again for a new attempt. See [Key and readiness check problems](#key-and-readiness-check-problems).

## 9. Save the setup report and read the result

The setup report checks Git, Python, Oh My Pi, the checkout, and whether the key is present. It doesn't replace the readiness check you just passed. This box saves the report inside the attempt folder. It then shows the file Oh My Pi wrote so you can read it yourself.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
course_save_report() {
  local report course_exit
  if [ -z "${attempt:-}" ] || [ -z "${proof:-}" ] || [ -z "${R:-}" ] || [ -z "${M:-}" ]; then
    printf 'STOP: run steps 5 and 8 in this window first\n'; return 1
  fi
  report="$attempt/setup-report-$(date -u +%Y%m%dT%H%M%SZ)-$$.txt"
  bash "$M/scripts/verify-setup.sh" "$R" "$report"
  course_exit=$?
  printf 'REPORT_EXIT %s\nREPORT %s\n' "$course_exit" "$report"
  [ "$course_exit" -eq 0 ] || return "$course_exit"
  cat -- "$proof/from-omp.txt"
}
course_save_report
```

**Expected:** a report ending in `SETUP CHECK PASS`, `REPORT_EXIT 0`, the report path, and finally `omp works` followed by this attempt's token.

**Stop:** `SETUP CHECK HOLD`, a nonzero `REPORT_EXIT`, or a result file that's missing or different.

**Recovery:** Fix the first failed line the report names, then run this box again; each run writes a new report. Don't reset, pull, or clean the checkout because the report lists local changes.

## Set up local Obsidian

Obsidian lets you follow links and edit notes in a **vault**, which is an ordinary folder of Markdown text files. You'll run Linux Obsidian in the same Ubuntu and Linux home as Oh My Pi, and WSLg will show its window on your Windows desktop. Allow about 25 to 40 minutes. Keep the practice vault outside the checkout and outside any synced folder. Don't open a `\\wsl.localhost` vault in Windows Obsidian or copy it to `/mnt/c`. Keep any existing Obsidian installation and personal vaults as they are.

### Check that Ubuntu can show app windows

[WSLg](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps) needs Windows 10 build 19044 or newer, or Windows 11, with your Ubuntu running as WSL 2. The first box printed your build, and the open box confirmed WSL 2. Run these Obsidian steps in the window you used for steps 5 to 9.

**Terminal: Ubuntu Bash, ordinary Linux user, same window as steps 5 to 9.**

```bash
printf 'WSL_DISTRO %s\nHOME %s\nARCH %s\n' "${WSL_DISTRO_NAME:-not reported}" "$HOME" "$(uname -m)"
printf 'DISPLAY %s\nWAYLAND_DISPLAY %s\n' "${DISPLAY:-missing}" "${WAYLAND_DISPLAY:-missing}"
if [ -d /mnt/wslg ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then printf 'WSLG PRESENT\n'; else printf 'Obsidian HOLD: WSLg display support is missing\n'; fi
```

**Expected:** your Ubuntu NAME, a `/home/` path, `x86_64` or `aarch64`, at least one display value, and `WSLG PRESENT`. A Linux window still has to appear before Obsidian counts as working.

**Stop:** `Obsidian HOLD`, or a build below 19044 in the first box.

**Recovery:** Keep your Oh My Pi result and record **Obsidian HOLD**. See [Obsidian problems](#obsidian-problems).

### Install and open Obsidian

If Linux Obsidian is already installed in this Ubuntu, the box keeps it and downloads nothing. Otherwise it downloads the [official 1.13.7 release](https://api.github.com/repos/obsidianmd/obsidian-releases/releases/tags/v1.13.7) file for your processor into a new folder and checks its SHA-256 fingerprint before installing it. On `x86_64`, apt installs the Debian package; read its proposed changes before you answer `Y`. On `aarch64`, Obsidian is an AppImage, a single application file. It needs FUSE (`fuse3` and `libfuse2t64`; see the [AppImage FUSE guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html)) and `zlib1g-dev`, which supplies the `libz.so` name its ARM64 starter loads ([AppImage issue 964](https://github.com/AppImage/AppImageKit/issues/964)). If you run Linux Obsidian another way, such as your own AppImage, skip this box and open it your usual way.

**Terminal: Ubuntu Bash, ordinary Linux user using sudo only for the approved apt step, same window.**

```bash
course_install_obsidian() {
  local asset expected
  if command -v obsidian >/dev/null 2>&1 || dpkg-query -W -f='${Status}' obsidian 2>/dev/null | grep -q 'install ok installed'; then
    printf 'EXISTING Obsidian found; it was kept and nothing was downloaded\n'; return 0
  fi
  case "$(uname -m)" in
    x86_64) asset=obsidian_1.13.7_amd64.deb; expected=17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0 ;;
    aarch64) asset=Obsidian-1.13.7-arm64.AppImage; expected=e286fd2bb2a5d346a35a577bd764c73fd5537dddec2b99a1a3e5e35974085203 ;;
    *) printf 'Obsidian HOLD: no 1.13.7 build for this processor\n'; return 1 ;;
  esac
  ObsidianDownload="$(mktemp -d "$HOME/obsidian-download.XXXXXXXX")" || return 1
  curl --fail --location --show-error --output "$ObsidianDownload/$asset" "https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/$asset" || return 1
  (cd "$ObsidianDownload" && printf '%s  %s\n' "$expected" "$asset" | sha256sum --check -) || {
    printf 'Obsidian HOLD: checksum mismatch; the file was not installed or run\n'; return 1; }
  if [ "$asset" = obsidian_1.13.7_amd64.deb ]; then
    (cd "$ObsidianDownload" && sudo apt install "./$asset") || return 1
  else
    sudo apt update && sudo apt install fuse3 libfuse2t64 zlib1g-dev || return 1
  fi
  printf 'OBSIDIAN INSTALLED %s\n' "$asset"
}
course_install_obsidian
```

**Expected:** either `EXISTING Obsidian found`, or the file name followed by `OK`, a finished apt step, and `OBSIDIAN INSTALLED`.

**Stop:** `Obsidian HOLD`, a download error, or apt proposes removing or replacing other software.

**Recovery:** Answer `n` to an unexpected apt proposal and keep the download folder. See [Obsidian problems](#obsidian-problems).

The next box opens Obsidian, and you can run `course_open_obsidian` again whenever you need to reopen it in this window. On `aarch64`, the AppImage starts with `--no-sandbox`, as [Obsidian's install instructions](https://github.com/obsidianmd/obsidian-help/blob/master/en/Getting%20started/Download%20and%20install%20Obsidian.md) show. That flag turns off Chromium's renderer sandbox, so get the device owner's approval first and use only the practice vault in that session.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
course_open_obsidian() {
  if command -v obsidian >/dev/null 2>&1; then
    obsidian >/dev/null 2>&1 &
  elif [ "$(uname -m)" = aarch64 ] && [ -f "${ObsidianDownload:-}/Obsidian-1.13.7-arm64.AppImage" ]; then
    (cd "$ObsidianDownload" &&
      printf '%s  %s\n' e286fd2bb2a5d346a35a577bd764c73fd5537dddec2b99a1a3e5e35974085203 Obsidian-1.13.7-arm64.AppImage | sha256sum --check --quiet - &&
      chmod u+x Obsidian-1.13.7-arm64.AppImage &&
      ./Obsidian-1.13.7-arm64.AppImage --no-sandbox >/dev/null 2>&1) &
  else
    printf 'Obsidian HOLD: no Obsidian to open from this window\n'; return 1
  fi
  printf 'OBSIDIAN STARTING; wait for its window\n'
}
course_open_obsidian
```

**Expected:** `OBSIDIAN STARTING`, then an Obsidian window on your Windows desktop within about a minute.

**Stop:** `Obsidian HOLD`, or no window appears.

**Recovery:** Keep any error text for the owner, and don't add other sandbox or security changes. See [Obsidian problems](#obsidian-problems).

### Open the practice vault and save a reply

The course helper creates a fresh practice vault in your Linux home. It makes no model call and doesn't need the key.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
course_start_vault() {
  if [ -z "${PY:-}" ] || [ -z "${M:-}" ]; then printf 'Obsidian HOLD: run the step 5 box in this window first\n'; return 1; fi
  ObsidianHelper="$M/scripts/obsidian_readiness.py"
  ObsidianRoot="$HOME/obsidian-readiness-$("$PY" -c 'import uuid; print(uuid.uuid4().hex)')" || return 1
  "$PY" "$ObsidianHelper" initialize --root "$ObsidianRoot" || return 1
  ObsidianVault="$ObsidianRoot/vault"
  printf 'ROOT %s\nVAULT %s\n' "$ObsidianRoot" "$ObsidianVault"
}
course_start_vault
```

**Expected:** `Created practice vault:`, then `ROOT` and `VAULT` lines with paths under your Linux home.

**Stop:** a `HOLD:` line or any error.

**Recovery:** Keep the attempt folder and fix the named path problem. Don't initialize an existing vault or move it to `/mnt/c`.

**Window: Linux Obsidian on your Windows desktop.**

1. Choose **Open folder as vault**. If a personal vault opens instead, use **Open another vault** first and leave its settings alone. In the folder chooser, press **Ctrl+L**, enter the exact `VAULT` path, and select it.
2. In **Settings → Community plugins**, keep **Restricted mode** on. In **Settings → Core plugins**, turn **Sync** off if it's on. Note the version shown in **Settings → General**, then close Settings.
3. Open **Start**. In Reading view, click **Token**, read the token, then follow **Reply**.
4. Switch Reply to Editing view, type only the token on one line, and press **Ctrl+S**.
5. Return to **Token** and leave it showing in Reading view.

### Watch an outside change, then reopen

The next box checks your saved reply. If it passes, the box changes Token from outside Obsidian while the vault is open.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
"$PY" "$ObsidianHelper" check --root "$ObsidianRoot" && "$PY" "$ObsidianHelper" refresh --root "$ObsidianRoot"
```

**Expected:** `Token generation 1`, `PASS: Obsidian file round-trip; GUI observation still required`, a disk observation path, then `Source token rotated outside Obsidian; your saved reply was preserved.`

**Stop:** a `HOLD:` line from either command.

**Recovery:** Correct Reply in Obsidian so it matches Token, save, and run the box again. Never edit Start, Token, or the helper's records to force a pass.

**Window: Linux Obsidian, same practice vault.**

1. Watch Token change to a new value while the vault stays open.
2. Follow Reply, replace the old value with the new one, and press **Ctrl+S**.
3. Close Obsidian, run `course_open_obsidian` in Ubuntu, reopen the same vault if asked, and check that Reply still holds the new value.

**Terminal: Ubuntu Bash, ordinary Linux user, same window.**

```bash
"$PY" "$ObsidianHelper" check --root "$ObsidianRoot"
```

**Expected:** a refreshed token generation, the same `PASS: Obsidian file round-trip` line, and a new disk observation path.

**Stop:** a `HOLD:` line.

**Recovery:** Fix Reply in Obsidian, save, and run the check again. Reopening Obsidian to make a missed change appear doesn't show a live refresh; run the refresh box again with the vault open instead.

In your usual text editor, create `gui-observation.txt` directly inside the printed `ROOT` folder, next to `vault`, without replacing an existing file. From Windows, that folder is at `\\wsl.localhost\` followed by your Ubuntu NAME and the `ROOT` path with backslashes, for example `\\wsl.localhost\Ubuntu-24.04\home\yourname\obsidian-readiness-…`. Write the date, Windows build, Ubuntu NAME and release, processor, Obsidian version, vault path, and what you saw: the links you followed, both saves, the live change, and Reply after reopening. Add both disk observation paths. On `aarch64`, note whether the owner approved `--no-sandbox`. Record **Obsidian READY** only after you saw every action and both checks passed; otherwise record **Obsidian HOLD** and name what failed. An Obsidian HOLD doesn't change your Oh My Pi result.

## Set up local n8n for Module 7

n8n is the local workflow editor for Module 7. Staff prepare it for your Ubuntu shell through the approved Docker Desktop integration. Allow about 10 minutes to start it and check a saved workflow, plus the staff-assisted restart. Keep n8n readiness separate from OMP, Obsidian, and Local model.

Staff own installation, licensing, versions, and data storage. Preserve existing instances and workflows. If your environment is not prepared, record **n8n HOLD** and contact the device/support owner.

### Start the prepared instance

In a fresh Ubuntu window, repeat the step 5 box to set `PY`, `R`, and `M`.

**Terminal: WSL Ubuntu, Bash, ordinary user.**

```bash
"$PY" "$M/scripts/n8n_local.py" start &&
"$PY" "$M/scripts/n8n_local.py" status
```

**Expected:** `STARTED` or `RUNNING`, then a status report naming n8n 2.41.5, its external runner, and `127.0.0.1:5678`.

**Stop:** The helper reports `HOLD` or the browser page does not open.

**Recovery:** Keep the first message and contact the support owner. Don't install another Docker engine or change the integration yourself.

### Save and reopen a blank workflow

Open **http://localhost:5678** in your Windows browser. On a fresh instance, complete local owner setup. On an existing instance, use its existing login. Skip optional offers and leave **Assistant** off. Don't enter your OpenRouter key until Module 7.

Select **Overview → Build a workflow** (or **Create workflow**). Name the blank workflow **Module 7 readiness** and press Enter. If that name already holds work, choose a distinct name. Leave the canvas blank and unpublished. Reload, return to the workflow list, and reopen it. Confirm its name, empty canvas, and unpublished state.

**Expected:** The blank, unpublished workflow survives reload.

**Stop:** Login fails, owner setup appears unexpectedly, or the saved workflow is missing.

**Recovery:** Preserve the instance and contact the support owner. Don't create another owner account over existing work.

### Observe staff-assisted persistence

Ask staff to stop and restart only the recorded course instance without removing its data. After staff confirm restart, reopen the same workflow. Confirm its name, blank canvas, and unpublished state.

Record **n8n READY** only if status, browser access, reload/reopen, and staff-assisted persistence all succeed. Otherwise record **n8n HOLD** with the first failure.

In later sessions, repeat the step 5 variable block in a fresh Ubuntu window, then run the two helper commands above.

## If a step stops

Save the first error message before you change anything. A precisely recorded failure is the fastest way to a fix. General symptoms are covered in [Troubleshooting](../shared/TROUBLESHOOTING.md), and key handling is in [Connect the course account without leaking a key](../shared/CREDENTIALS.md).

### Windows and WSL problems

**`wsl` isn't recognized, prints help instead of installing, or reports a policy block.** Ask the device owner to work through [Microsoft's installation troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting#installation-issues). Don't paste feature-enabling commands from other guides.

**An Ubuntu is installed but `wsl --version` failed, or Docker needs WSL 2.1.5 or later.** This computer has the older built-in WSL or an outdated package. Save your work in every WSL distribution and Docker application first, because the update can stop them. With owner approval, update WSL.

**Terminal: Windows PowerShell, elevated (Run as administrator); owner-approved WSL update.**

```powershell
wsl --update
if ($LASTEXITCODE -ne 0) { throw 'STOP: keep the update message.' }
wsl --version
'wsl version exit: ' + $LASTEXITCODE
if ($LASTEXITCODE -ne 0) { throw 'STOP: version failed.' }
wsl --list --verbose
'list exit: ' + $LASTEXITCODE
if ($LASTEXITCODE -ne 0) { throw 'STOP: list failed.' }
```

**Expected:** a WSL version of 2.1.5 or later, and your Ubuntu still listed as VERSION `2`.

**Stop:** a `STOP:` line appears, or a restart is requested.

**Recovery:** Restart Windows if asked, then run the first box of [Choose and open Ubuntu](#choose-and-open-ubuntu) again.

**Your Ubuntu shows VERSION 1.** Converting it to WSL 2 can take a long time and can fail, so the owner should approve it and keep a backup. The box saves a backup file with `wsl --export` first, then converts the exact NAME, following [Microsoft's basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands). The backup folder must already exist on a drive with enough space.

**Terminal: Windows PowerShell, ordinary user; owner-approved conversion only.**

```powershell
. {
  $CourseDistro = Read-Host 'Exact NAME that shows VERSION 1'
  $CourseBackup = Read-Host 'Full path for a new backup file, for example D:\wsl-backup\ubuntu.tar'
  if (Test-Path -LiteralPath $CourseBackup) { throw 'STOP: that backup file already exists; choose a new path.' }
  wsl --export $CourseDistro $CourseBackup
  if ($LASTEXITCODE -ne 0) { throw 'STOP: the backup failed; nothing was converted.' }
  wsl --set-version $CourseDistro 2
  if ($LASTEXITCODE -ne 0) { throw 'STOP: conversion failed; keep the backup.' }
  wsl --list --verbose
  'list exit: ' + $LASTEXITCODE
  if ($LASTEXITCODE -ne 0) { throw 'STOP: list failed.' }
}
```

**Expected:** the export and conversion finish, and the list shows the NAME with VERSION `2`.

**Stop:** a `STOP:` line appears.

**Recovery:** Keep the original distribution and the backup, and ask the owner to resolve the reported error. Never unregister or reset a distribution as a repair.

**Ubuntu won't start, or its first-user setup didn't finish.** Keep the error and ask the owner to repair that distribution without resetting it.

### Ubuntu check and package problems

**Root or the wrong user.** If Ubuntu opens as root, ask the owner to create or select an ordinary Linux user for this distribution, then reopen it.

**Wrong Ubuntu release.** Keep the existing distribution. Install `Ubuntu-24.04` next to it with the install box, then open that NAME.

**Less than 25 GB free.** Free space inside Ubuntu or on the Windows drive that holds it. Don't move course work to `/mnt/c`.

**apt can't reach a source, or shows certificate errors.** This usually means a network proxy or a missing approved source. Ask the owner to fix it, and keep certificate checks on.

### Oh My Pi install problems

If the installer reports an error, check its message and the current instructions at [omp.sh](https://omp.sh/). Run the Linux installer inside Ubuntu. For a certificate or proxy error, ask for the approved network settings.

### Course file problems

**`is not this course checkout` or `is not a plain folder`.** A different folder already uses that path. Keep it; don't delete, reset, pull, or clean it. Ask the owner to move it or confirm it.

**`clone failed`.** Fix the access or network error first. Keep any partial folder and ask the owner before trying again into the same path.

**`course file has Windows line endings` or a missing file.** The checkout was copied or converted by a Windows tool. Keep it, and ask the owner for a fresh clone made inside Ubuntu.

**gh stores its token in a plain file.** When Ubuntu has no system keyring, [gh auth login](https://cli.github.com/manual/gh_auth_login) can save the token in a file in your Linux home. If your device policy forbids that, stop and ask the owner for an approved credential method. Don't use `--insecure-storage`.

### New window problems

**`OMP_PATH missing`.** Follow the installer’s PATH instructions, then close Ubuntu and reopen it from a new Windows PowerShell window using the [open box](#choose-and-open-ubuntu). Run `command -v omp` and `omp --version` inside Ubuntu to confirm the Linux installation is available.

**`SET` in a new window before you entered a key.** Something passes the key into new windows. The box lists which startup files mention the variable name and which Windows variables WSL forwards (the `WSLENV` setting), without printing any value.

**Terminal: Ubuntu Bash, ordinary Linux user, the new window where step 5 stopped.**

```bash
for f in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.bash_login" /etc/environment; do
  if [ -f "$f" ] && grep -q 'OPENROUTER_API_KEY' "$f"; then printf 'REFERENCE in %s; contents not printed\n' "$f"; fi
done
printf 'WSLENV names: %s\nPROFILE SCAN DONE\n' "${WSLENV:-none}"
```

**Expected:** any `REFERENCE in` lines, the forwarded variable names, and `PROFILE SCAN DONE`.

**Stop:** nothing explains the unexpected `SET`.

**Recovery:** Review the named file or Windows variable privately with the owner. If a key was saved there by mistake, remove it with their guidance and revoke it if it was exposed. Never print the value.

### Key and readiness check problems

**The key appeared on screen.** Revoke it at OpenRouter, then enter the replacement at the hidden prompt.

**`LAUNCH_EXIT 2`.** A prerequisite failed before any work began, and the `HOLD:` line names it. `OPENROUTER_API_KEY unavailable` means you should repeat steps 6 and 7 in this window. A message about `omp` on PATH or its version means you should return to step 5 in a new window. A missing `course_guard.mjs` means the checkout is incomplete.

**`LAUNCH_EXIT 1`.** The live attempt started and failed. Check your network and key, then run step 8 again; it creates a new attempt. Don't change the provider or model.

**`READINESS CHECK HOLD`.** The checker names what didn't match. Keep that attempt, fix the cause, and run step 8 again. Writing `from-omp.txt` yourself never counts.

**`SETUP CHECK HOLD`.** Fix the first `[FAIL]` line in the report, then run step 9 again for a new report.

### Obsidian problems

**`Obsidian HOLD: WSLg display support is missing`.** Check that your Windows build is 19044 or later and your Ubuntu is WSL 2, then update WSL with the owner's approval. Don't use a global `wsl --shutdown` while other work is running.

**apt proposes removing or replacing packages.** Answer `n`, keep the download, and ask the owner to review the package change.

**`libfuse2t64` won't install on `aarch64`.** Keep the error for the owner. Don't install the old `fuse` package or remove FUSE 3.

**No Obsidian window appears.** Keep any error text for the owner. Don't extract the AppImage, add sandbox flags to the Debian package, or change kernel security settings.

**`check` prints HOLD.** Reply doesn't match the current Token. Fix it in Obsidian, save, and check again.

### n8n and Docker problems

**The host misses a Docker requirement, or licensing isn't approved.** Record **n8n HOLD** and leave it for the owner; Oh My Pi and Obsidian results stand.

**Ubuntu already has its own Docker Engine.** Docker warns against running it alongside Docker Desktop. Ask its owner to back up and resolve that installation; don't uninstall or migrate it yourself.

**The helper cannot reach Docker.** Ask staff to check Docker Desktop, integration for the selected Ubuntu distribution, and the recorded engine. After they resolve the cause, open a fresh Ubuntu window and repeat the helper commands.

**`DOCKER_HOST`, `DOCKER_CONTEXT`, or another variable is reported.** A setting in this window would redirect Docker or Compose. Ask the owner to remove it from your startup files, then open a new window. Don't print its value.

**The helper cannot find the prepared record in `~/n8n-course`.** Keep any existing directory and data. Ask staff to identify and prepare the correct instance. An existing directory is expected after preparation; don't delete or reinstall over it.

**Port 5678 is in use, or a service keeps restarting.** Keep the configuration and volumes, and review the error with the owner. Don't stop other applications, delete volumes, or disable services to force a pass.

## Local model (capstone) readiness lane

Ask staff for the approved Linux `hf` and `llama-server` paths in this distribution, then [check local-model readiness](../../module-10-capstone/shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) before a download and again before launch. Use Linux paths, not Windows executables or a different distribution's observations. Missing tools, insufficient assigned memory or storage, an occupied endpoint, or an unresolved failed rehearsal mean **Local model HOLD**; preserve your other readiness results and contact the device/support owner.
