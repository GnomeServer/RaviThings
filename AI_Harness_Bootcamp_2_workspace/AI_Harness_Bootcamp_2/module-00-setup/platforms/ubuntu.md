# Ubuntu setup for Module 0

With an ordinary Ubuntu desktop account, you'll install Oh My Pi, get the course files, and run a live readiness check that writes one file. Plan for about 45 to 90 minutes (a rough estimate), plus download time.

You need Git, Python 3.12 or newer, a web browser, a text editor, and one OpenRouter key. The readiness check uses the latest stable Oh My Pi release with the model `openrouter/anthropic/claude-sonnet-4.6`.

Every command box is one paste: select all of it, paste it once, and press Return. Wait for the prompt before pasting the next box.

## 1. Check this computer

Use Ubuntu 24.04 or 26.04 on x86-64 or ARM64. This box checks your system, account, free space, installed packages, and Python without changing anything.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, current window.**

```bash
course_check() {
  local ID VERSION_ID machine free_g missing package candidate py
  [ -r /etc/os-release ] && . /etc/os-release || { printf 'STOP: cannot read /etc/os-release\n' >&2; return 1; }
  machine="$(uname -m)" || return 1
  printf 'OS %s %s\nARCH %s\n' "$ID" "${VERSION_ID:-rolling}" "$machine"
  case "$ID:${VERSION_ID:-rolling}:$machine" in
    ubuntu:24.04:x86_64|ubuntu:24.04:aarch64|ubuntu:24.04:arm64|ubuntu:26.04:x86_64|ubuntu:26.04:aarch64|ubuntu:26.04:arm64) ;;
    *) printf 'STOP: unsupported OS or architecture\n' >&2; return 1 ;;
  esac
  [ -n "${BASH_VERSION:-}${ZSH_VERSION:-}" ] || { printf 'STOP: use Bash or Zsh\n' >&2; return 1; }
  if [ "$(id -u)" -eq 0 ] || [ ! -w "$HOME" ] || [ ! -x "$HOME" ]; then
    printf 'STOP: use an ordinary account with a writable home folder\n' >&2; return 1
  fi
  df -h "$HOME" || return 1
  free_g="$(df --output=avail -BG "$HOME" | tail -n 1 | tr -dc '0-9')"
  [ "${free_g:-0}" -ge 15 ] || { printf 'STOP: less than 15G available\n' >&2; return 1; }
  missing=""
  for package in git curl python3 ca-certificates; do
    [ "$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null)" = "install ok installed" ] || missing="${missing:+$missing }$package"
  done
  if [ -z "$missing" ]; then printf 'PACKAGES present\n'; else printf 'PACKAGES missing: %s\n' "$missing"; fi
  py="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import os, sys; sys.exit(1) if sys.version_info < (3, 12) else print(os.path.realpath(sys.executable))' 2>/dev/null && break; done)"
  if [ -n "$py" ]; then printf 'PY %s\n' "$py"; "$py" --version; else printf 'PYTHON 3.12+ not found yet\n'; fi
}
course_check
```

**Expected:** `OS ubuntu 24.04` or `26.04`; a disk table showing at least 15G available; a `PACKAGES` line; and either a `PY` line with Python 3.12 or newer, or `PYTHON 3.12+ not found yet`.

**Stop:** Any `STOP:` line.

**Recovery:** If space is low, free some and paste the box again. For anything else, see [If a step stops](#if-a-step-stops). If packages or Python are missing, continue to step 2.

## 2. Install Git and the other missing packages

**Git** copies the course files from GitHub to your computer and records exactly which version you have. Step 4 uses it to make your checkout. Ubuntu packages Git as `git`, and the [Git project](https://git-scm.com/install/linux) recommends installing it with your distribution's package manager. The box below installs `git` together with the other packages step 1 checks.

If step 1 printed `PACKAGES present` and a `PY` line, skip this box and go to [Confirm Git works](#confirm-git-works). Otherwise, install the missing packages. Ubuntu 24.04's `python3` is Python 3.12 and 26.04's is 3.14, so Ubuntu's own package is enough. `sudo` asks for your password; nothing appears while you type.

**Terminal: Ubuntu, Bash or Zsh, same window; sudo elevates package installation.**

```bash
sudo apt-get update && sudo apt-get install -y git python3 ca-certificates curl
```

**Expected:** `apt-get` finishes and the prompt returns.

**Stop:** The password is refused, policy blocks the install, or `apt-get` prints an error.

**Recovery:** Do not add a PPA, download Python, or use pip; save the error and see [If a step stops](#if-a-step-stops).

### Confirm Git works

This box shows which Git your terminal finds and asks it for its version. Run it even if you skipped the install box.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
command -v git && git --version
```

**Expected:** `/usr/bin/git`, then `git version 2.` followed by more numbers.

**Stop:** the box prints nothing, or no `git version` line appears.

**Recovery:** Paste the step 2 box again and keep any error it prints. Don't add a PPA or download Git from another site; see [If a step stops](#if-a-step-stops).

## 3. Install Oh My Pi

Run the one-line installer from [omp.sh](https://omp.sh/).

**Terminal: Bash or zsh, ordinary user.**

```bash
curl -fsSL https://omp.sh/install | sh
```

**Restart your terminal after installing OMP so PATH changes take effect.** Follow any PATH instructions the installer prints, complete Step 4 in this window, then close and reopen your terminal as directed in Step 5 before starting OMP or entering your API key.

**Expected:** The installer finishes successfully. In the new terminal, `omp --version` prints the installed version.

**Stop:** The installer reports an error or `omp` is not found.

**Recovery:** Check the installer’s error. For `omp` not found, use [PATH recovery](../shared/TROUBLESHOOTING.md#if-omp-is-not-found-after-restarting), then reopen the terminal and try `omp --version` again.

## 4. Get the course files

First check that your GitHub account can read the private course repository. This uses existing credentials and changes no settings.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code https://github.com/TheHolofex/AIHB_OCT_2026.git HEAD
```

**Expected:** A commit hash followed by `HEAD`; skip to "Create or reuse the checkout."

**Stop:** An authentication, not-found, or network error.

**Recovery:** For missing credentials, use the next subsection; a network error or an uninvited account needs its owner.

### If GitHub access fails

Install the official GitHub CLI, `gh`, from Ubuntu's Universe component if it is missing. Do not add another repository.

**Terminal: Ubuntu, Bash or Zsh, same window; sudo elevates package installation.**

```bash
command -v gh >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y gh; }
gh --version
```

**Expected:** A `gh version` line.

**Stop:** The package is unavailable, the install is refused, or `gh` fails to run.

**Recovery:** Ask the device owner for the approved package; see [If a step stops](#if-a-step-stops).

Sign in through your browser with [`gh auth login`](https://cli.github.com/manual/gh_auth_login). Enter the one-time code on GitHub for the account invited to the course repository. If asked whether to authenticate Git now, choose **No**; the next box shows where the credential is stored first. Never use `--insecure-storage`.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window; interactive login.**

```bash
gh auth login --hostname github.com --git-protocol https --web
```

**Expected:** The terminal confirms you are logged in.

**Stop:** Login fails, the wrong account signs in, or policy refuses authorization.

**Recovery:** Ask the account or device owner; never paste a password or token into a command.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
gh auth status --hostname github.com
```

**Expected:** The invited account is logged in, and the storage shown in parentheses is `keyring` or a file location the device owner approved.

**Stop:** The account is wrong, or the storage is a plain file the device owner has not approved.

**Recovery:** Ask the device owner to approve or provide credential storage before you continue; do not add `--show-token` or share this output.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
gh auth setup-git --hostname github.com &&
GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code https://github.com/TheHolofex/AIHB_OCT_2026.git HEAD
```

**Expected:** A commit hash followed by `HEAD`.

**Stop:** Either command fails.

**Recovery:** Ask the repository owner to confirm the invitation for this account, then paste this box again.

### Create or reuse the checkout

This clones the course into `~/Documents/AIHB_OCT_2026`, or reuses a checkout of the same origin there without resetting, pulling, or cleaning it.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
course_use_checkout() {
  local origin_url helper
  R="$HOME/Documents/AIHB_OCT_2026"
  M="$R/AI_Harness_Bootcamp_2/module-00-setup"
  if [ -L "$HOME/Documents" ] || [ -L "$R" ]; then printf 'STOP: %s is a symlink; it was not replaced\n' "$R" >&2; return 1; fi
  if [ ! -e "$R" ]; then
    mkdir -p -- "$HOME/Documents" || return 1
    git clone https://github.com/TheHolofex/AIHB_OCT_2026.git "$R" || { printf 'STOP: clone failed\n' >&2; return 1; }
  elif [ ! -d "$R" ]; then
    printf 'STOP: %s is not a folder; it was not replaced\n' "$R" >&2; return 1
  else
    origin_url="$(git -C "$R" remote get-url origin 2>/dev/null || true)"
    [ "$origin_url" = "https://github.com/TheHolofex/AIHB_OCT_2026.git" ] || { printf 'STOP: %s is not the course checkout\n' "$R" >&2; return 1; }
    printf 'USE: existing checkout; no reset, pull, or clean\n'
  fi
  if [ -L "$R/.git" ] || [ "$(git -C "$R" rev-parse --show-toplevel 2>/dev/null)" != "$R" ]; then
    printf 'STOP: the folder is not the checkout root\n' >&2; return 1
  fi
  git -C "$R" rev-parse --verify HEAD >/dev/null || return 1
  for helper in "$R/shared/run_omp.py" "$R/shared/course_guard.mjs" "$M/scripts/verify-setup.sh" "$M/shared/case/verify_tool_proof.py"; do
    if [ ! -f "$helper" ] || [ -L "$helper" ]; then printf 'STOP: course helper missing or linked: %s\n' "$helper" >&2; return 1; fi
  done
  printf 'R %s\nM %s\n' "$R" "$M"
}
course_use_checkout
```

**Expected:** `USE:` or clone output, then `R` and `M` lines under your home folder.

**Stop:** Any STOP line.

**Recovery:** Leave the existing folder untouched and see [If a step stops](#if-a-step-stops).

## 5. Open a new terminal and confirm

Close this terminal, then open a new one from the desktop menu. Don't type `bash` or `su` in the old window, because a child shell inherits the old PATH and variables. Don't set PATH by hand; this check shows whether the startup file works.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, newly opened desktop window.**

```bash
course_confirm_new_terminal() {
  local resolved version candidate
  R="$HOME/Documents/AIHB_OCT_2026"
  M="$R/AI_Harness_Bootcamp_2/module-00-setup"
  PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; from pathlib import Path; sys.exit(1) if sys.version_info < (3, 12) else print(Path(sys.executable).resolve())' 2>/dev/null && break; done)"
  case "$PY" in /*) ;; *) printf 'STOP: no absolute Python 3.12+ executable\n' >&2; return 1 ;; esac
  "$PY" --version || return 1
  resolved="$(command -v git)" || return 1
  printf 'GIT_PATH %s\n' "$resolved"
  "$resolved" --version || return 1
  if [ -L "$R" ] || [ -L "$R/.git" ] || [ ! -d "$R" ]; then printf 'STOP: checkout is missing or linked\n' >&2; return 1; fi
  if [ "$(git -C "$R" remote get-url origin)" != 'https://github.com/TheHolofex/AIHB_OCT_2026.git' ] || [ "$(git -C "$R" rev-parse --show-toplevel)" != "$R" ]; then
    printf 'STOP: wrong checkout identity\n' >&2; return 1
  fi
  printf 'R %s\nM %s\nPY %s\n' "$R" "$M" "$PY"
  resolved="$(command -v omp 2>/dev/null || true)"
  printf 'OMP_PATH %s\n' "${resolved:-missing}"
  case "$resolved" in /*) ;; *) printf 'STOP: omp is not on PATH\n' >&2; return 1 ;; esac
  version="$("$resolved" --version 2>/dev/null)" || { printf 'STOP: installed OMP could not run\n' >&2; return 1; }
  printf 'OMP_VERSION %s\n' "${version:-missing}"
  [[ "$version" =~ ^omp/[0-9]+\.[0-9]+\.[0-9]+$ ]] || { printf 'STOP: installed OMP did not report a version number\n' >&2; return 1; }
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; printf 'STOP: this window already has the key variable\n' >&2; return 1; fi
  printf 'MISSING\n'
}
course_confirm_new_terminal
```

**Expected:** `R`, `M`, `PY`, `GIT_PATH`, `OMP_PATH` with the installed command path, `OMP_VERSION omp/<semver>`, and last `MISSING`.

**Stop:** Any STOP line, or `SET`.

**Recovery:** For a missing `omp`, return to step 3 and open another desktop terminal; for `SET` or anything else see [If a step stops](#if-a-step-stops).

## 6. Enter your OpenRouter key

The launcher reads your OpenRouter key only from this terminal's environment, so a new terminal starts without it. The next box reads the key without showing it. Paste the box and press Return. Then type or paste the key and press Return again; nothing appears while you do. The key stays in this terminal's memory only. Read [credentials](../shared/CREDENTIALS.md) first if the key may have been exposed.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
IFS= read -r -s OPENROUTER_API_KEY
```

**Expected:** Nothing is echoed, and the prompt returns, possibly on the same line.

**Stop:** Any character of the key appears on screen.

**Recovery:** Treat the key as exposed and follow [credentials](../shared/CREDENTIALS.md).

## 7. Confirm the key is loaded

Exporting the variable lets programs started from this terminal use it. It is still not written to disk.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
export OPENROUTER_API_KEY
if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; else printf 'MISSING\n'; fi
```

**Expected:** `SET`.

**Stop:** `MISSING`, or the key itself appears.

**Recovery:** Paste the step 6 box again, then this box; never put the key in a startup file.

## 8. Run the readiness check

This prepares a fresh attempt folder outside the checkout. It starts the launcher with OpenRouter and `openrouter/anthropic/claude-sonnet-4.6`, and lets the model write only `from-omp.txt`. The checker then confirms the file holds `omp works` and this attempt's token, and that the receipts show the course tool wrote it.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
course_run_readiness() {
  local attempt course_exit
  unset COURSE_PROOF_VERIFIED
  if [ -z "${PY:-}" ] || [ -z "${R:-}" ] || [ -z "${M:-}" ]; then printf 'STOP: PY, R, and M are not set; repeat step 5\n' >&2; return 1; fi
  if [ -L "$HOME/course-evidence" ] || [ -L "$HOME/course-evidence/reformation-qa" ]; then printf 'STOP: evidence parent is linked\n' >&2; return 1; fi
  attempt="module-00-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  BASE="$HOME/course-evidence/reformation-qa/$attempt"
  if [ -e "$BASE" ] || [ -L "$BASE" ]; then printf 'STOP: %s already exists\n' "$BASE" >&2; return 1; fi
  mkdir -p -- "$BASE/proof" "$BASE/receipts" || return 1
  EVIDENCE="$BASE/receipts/live-1"
  "$PY" -c 'import secrets; print(secrets.token_hex(16), end="")' > "$BASE/run-token.txt" || return 1
  [ "$(wc -c < "$BASE/run-token.txt" | tr -d '[:space:]')" -ge 16 ] || { printf 'STOP: token file is empty\n' >&2; return 1; }
  cp -- "$BASE/run-token.txt" "$BASE/proof/run-token.txt" || return 1
  cat > "$BASE/proof/prompt.txt" << 'COURSE_PROMPT'
Read run-token.txt with the course_read tool. Then write only from-omp.txt with the course_write tool. The file contents must be the words omp works, one space, and the exact token text from run-token.txt. Do not write any other file.
COURSE_PROMPT
  printf 'READINESS_WORK %s\nTOKEN_OUTSIDE %s\nEVIDENCE_NOT_CREATED %s\n' "$BASE/proof" "$BASE/run-token.txt" "$EVIDENCE"
  "$PY" "$R/shared/run_omp.py" --workdir "$BASE/proof" --prompt "$BASE/proof/prompt.txt" --evidence "$EVIDENCE" --allow-write from-omp.txt
  course_exit="$?"
  printf 'LAUNCH_EXIT %s\n' "$course_exit"
  if [ "$course_exit" -eq 2 ]; then printf 'STOP: prerequisite hold; do not reuse this attempt\n' >&2; return 2; fi
  if [ "$course_exit" -ne 0 ]; then printf 'STOP: live run failed; keep this attempt\n' >&2; return 1; fi
  [ -d "$EVIDENCE" ] || { printf 'STOP: evidence was not created\n' >&2; return 1; }
  "$PY" "$M/shared/case/verify_tool_proof.py" "$BASE/proof" "$BASE/run-token.txt" "$EVIDENCE"
  course_exit="$?"
  printf 'VERIFY_EXIT %s\n' "$course_exit"
  if [ "$course_exit" -eq 0 ]; then COURSE_PROOF_VERIFIED="$BASE"; fi
  return "$course_exit"
}
course_run_readiness
```

**Expected:** `READINESS_WORK`, `TOKEN_OUTSIDE`, `EVIDENCE_NOT_CREATED`, launcher output, `LAUNCH_EXIT 0`, `READINESS CHECK PASS`, and last `VERIFY_EXIT 0`.

**Stop:** `LAUNCH_EXIT 2` (usually a missing key), `LAUNCH_EXIT 1`, `READINESS CHECK HOLD`, a nonzero `VERIFY_EXIT`, or any STOP line.

**Recovery:** Keep the attempt folder, never create or edit `from-omp.txt` by hand, and see [If a step stops](#if-a-step-stops).

## 9. Save the setup report and read the result

The report checks the machine, tools, checkout, and key variable. It cannot replace the live readiness check above. The second function prints the result file from disk. Its token identifies this run and is not your API key.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window.**

```bash
course_save_report() {
  local course_exit
  if [ -z "${M:-}" ] || [ -z "${R:-}" ] || [ -z "${BASE:-}" ]; then printf 'STOP: report paths are not set\n' >&2; return 1; fi
  if [ -e "$BASE/setup-report.txt" ] || [ -L "$BASE/setup-report.txt" ]; then printf 'STOP: report already exists\n' >&2; return 1; fi
  bash "$M/scripts/verify-setup.sh" "$R" "$BASE/setup-report.txt"
  course_exit="$?"
  printf 'REPORT_EXIT %s\n' "$course_exit"
  return "$course_exit"
}
course_read_back_proof() {
  if [ -z "${BASE:-}" ] || [ "${COURSE_PROOF_VERIFIED:-}" != "$BASE" ]; then printf 'STOP: this attempt has not passed the readiness check\n' >&2; return 1; fi
  if [ ! -f "$BASE/proof/from-omp.txt" ] || [ -L "$BASE/proof/from-omp.txt" ]; then printf 'STOP: result file is missing or linked\n' >&2; return 1; fi
  printf 'FILE %s\n' "$BASE/proof/from-omp.txt"
  cat -- "$BASE/proof/from-omp.txt" || return 1
  printf '\nEND OF FILE\n'
}
course_save_report
course_read_back_proof
```

**Expected:** `SETUP CHECK PASS`, `REPORT_EXIT 0`, then `omp works` and this attempt's token between `FILE` and `END OF FILE`.

**Stop:** `SETUP CHECK HOLD`, a nonzero `REPORT_EXIT`, or any STOP line.

**Recovery:** Fix only the first FAIL line in the report, don't clean the checkout because of changed files, and see [If a step stops](#if-a-step-stops).

## Set up local Obsidian

Obsidian edits and links local notes for Module 2. Plan for about 10 to 20 minutes (a rough estimate), plus download time. First check your application menu. If Obsidian is already installed, open that copy, skip the download and install boxes, and record its version. Don't reinstall or downgrade it.

### Download and verify

For a fresh install, this box downloads the official 1.13.7 `.deb` on x86-64 or the AppImage on ARM64 from the [release page](https://github.com/obsidianmd/obsidian-releases/releases/tag/v1.13.7). It checks the SHA-256. An **AppImage** is an application file you run directly.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
course_download_obsidian() {
  unset OBS_ASSET OBS_SHA256
  [ -n "${PY:-}" ] || { printf 'HOLD: restore PY first.\n'; return 1; }
  case "$(uname -m)" in
    x86_64)
      OBS_ASSET=obsidian_1.13.7_amd64.deb
      OBS_SHA256=17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0 ;;
    aarch64|arm64)
      OBS_ASSET=Obsidian-1.13.7-arm64.AppImage
      OBS_SHA256=e286fd2bb2a5d346a35a577bd764c73fd5537dddec2b99a1a3e5e35974085203 ;;
    *) printf 'HOLD: unsupported Obsidian architecture.\n'; return 1 ;;
  esac
  OBS_DOWNLOAD="$HOME/course-evidence/obsidian-download-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  "$PY" - "$OBS_DOWNLOAD" <<'PYOBS'
from pathlib import Path
import sys
folder = Path(sys.argv[1])
if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
    raise SystemExit('HOLD: linked download path; preserve it.')
folder.mkdir(parents=True, exist_ok=False)
PYOBS
  [ "$?" -eq 0 ] || return 1
  curl --fail --location --output "$OBS_DOWNLOAD/$OBS_ASSET" "https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/$OBS_ASSET" || return 1
  (cd "$OBS_DOWNLOAD" && printf '%s  %s\n' "$OBS_SHA256" "$OBS_ASSET" | sha256sum --check -) || return 1
  printf 'SHA256 VERIFIED: %s\n' "$OBS_DOWNLOAD/$OBS_ASSET"
}
course_download_obsidian
```

**Expected:** `OK` for the file, then `SHA256 VERIFIED:` and its path.

**Stop:** Any error or hash mismatch.

**Recovery:** Keep the failed download and see [If a step stops](#if-a-step-stops).

### x86-64: install and launch

With device-owner approval, apt installs the checked package. Read the proposed transaction and refuse any unapproved removal.

**Terminal: Ubuntu x86-64, Bash or Zsh, same window; sudo elevates only apt.**

```bash
course_install_obsidian_deb() {
  [ "${OBS_ASSET:-}" = obsidian_1.13.7_amd64.deb ] && [ -n "${OBS_DOWNLOAD:-}" ] || { printf 'HOLD: complete the x86-64 download first.\n'; return 1; }
  if command -v obsidian >/dev/null 2>&1 || dpkg-query -W obsidian >/dev/null 2>&1; then
    printf 'HOLD: preserve the existing Obsidian installation.\n'; return 1
  fi
  (
    cd "$OBS_DOWNLOAD" || exit 1
    printf '%s  %s\n' '17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0' 'obsidian_1.13.7_amd64.deb' | sha256sum --check - || exit 1
    sudo apt install ./obsidian_1.13.7_amd64.deb
  )
}
course_install_obsidian_deb
```

**Expected:** Checksum `OK`, then the approved apt transaction completes. A final note that the download was "performed unsandboxed as root" because `_apt` couldn't read your home folder is normal for a local package file.

**Stop:** An error, an unapproved transaction, or an existing installation.

**Recovery:** Keep the existing app and ask the device owner to resolve the conflict.

**Terminal: Ubuntu x86-64, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
obsidian &
```

**Expected:** The Obsidian window opens and the terminal stays usable.

**Stop:** No window, a sandbox refusal, or a launch error.

**Recovery:** Record Obsidian HOLD with the error; don't add `--no-sandbox` or change system security settings.

### ARM64: install FUSE and launch

The AppImage needs `libfuse2t64` beside FUSE 3, and `zlib1g-dev`, which supplies the `libz.so` name its ARM64 starter loads ([AppImage issue 964](https://github.com/AppImage/AppImageKit/issues/964)). Type `n` if apt would remove FUSE 3. The vendor's [launch instructions](https://github.com/obsidianmd/obsidian-help/blob/master/en/Getting%20started/Download%20and%20install%20Obsidian.md) use `--no-sandbox`, which turns off Chromium's renderer sandbox for Obsidian. Get separate device-owner approval for that exception; without it, record Obsidian HOLD and skip this box.

**Terminal: Ubuntu ARM64, Bash or Zsh, same window; sudo elevates only the approved apt transaction.**

```bash
course_obsidian_fuse() {
  case "$(uname -m)" in aarch64|arm64) ;; *) printf 'HOLD: ARM64 step only.\n'; return 1 ;; esac
  if [ "$(dpkg-query -W -f='${Status}' libfuse2t64 2>/dev/null)" = 'install ok installed' ] && [ "$(dpkg-query -W -f='${Status}' zlib1g-dev 2>/dev/null)" = 'install ok installed' ]; then
    printf 'libfuse2t64 and zlib1g-dev already installed.\n'
  else
    sudo apt-get update && sudo apt install libfuse2t64 zlib1g-dev || return 1
  fi
  dpkg-query -W -f='${Package} ${Version} ${Status}\n' libfuse2t64 zlib1g-dev
}
course_launch_obsidian_arm64() {
  [ "${OBS_ASSET:-}" = Obsidian-1.13.7-arm64.AppImage ] && [ -n "${OBS_DOWNLOAD:-}" ] || { printf 'HOLD: complete the ARM64 download first.\n'; return 1; }
  (
    cd "$OBS_DOWNLOAD" || exit 1
    printf '%s  %s\n' 'e286fd2bb2a5d346a35a577bd764c73fd5537dddec2b99a1a3e5e35974085203' 'Obsidian-1.13.7-arm64.AppImage' | sha256sum --check - || exit 1
    chmod u+x ./Obsidian-1.13.7-arm64.AppImage || exit 1
    ./Obsidian-1.13.7-arm64.AppImage --no-sandbox &
  )
}
course_obsidian_fuse && course_launch_obsidian_arm64
```

**Expected:** `libfuse2t64 … install ok installed` and `zlib1g-dev … install ok installed`, checksum `OK`, then an Obsidian window.

**Stop:** No approval, an unapproved apt change, missing FUSE or `zlib1g-dev`, or no window.

**Recovery:** Record Obsidian HOLD with the error; don't run the AppImage as root or change kernel security settings.

### Open the practice vault and follow its links

A **vault** is a folder of notes. This box creates a fresh practice vault outside the checkout. It needs no account, plugin, or API key. Use the terminal where step 5 set `PY`, `R`, and `M`.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
course_initialize_obsidian() {
  [ -n "${PY:-}" ] && [ -n "${R:-}" ] && [ "${M:-}" = "$R/AI_Harness_Bootcamp_2/module-00-setup" ] || { printf 'HOLD: repeat step 5 in this terminal first.\n' >&2; return 1; }
  [ -f "$M/scripts/obsidian_readiness.py" ] && [ ! -L "$M/scripts/obsidian_readiness.py" ] || { printf 'HOLD: course readiness helper is missing or linked.\n' >&2; return 1; }
  OBS_ROOT="$HOME/course-evidence/obsidian-ubuntu-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  "$PY" "$M/scripts/obsidian_readiness.py" initialize --root "$OBS_ROOT" || return 1
  printf 'OPEN EXACT VAULT: %s\n' "$OBS_ROOT/vault"
}
course_initialize_obsidian
```

**Expected:** `Created practice vault:` and `OPEN EXACT VAULT:` name the same folder ending in `/vault`.

**Stop:** Any HOLD or error.

**Recovery:** If the vault was created, set `OBS_ROOT` to its parent and continue; otherwise see [If a step stops](#if-a-step-stops).

**Window: Obsidian, ordinary desktop account.**

1. Open Obsidian with the launch box above. If another vault opens, leave it alone and choose **Manage vaults → Open folder as vault → Open** from the vault switcher; on a first launch choose **Open folder as vault → Open** directly.
2. In the folder picker, press **Ctrl+L**, paste the printed `OPEN EXACT VAULT` path, and open it. Don't pick the checkout, the parent folder, or a personal vault.
3. In **Settings → Community plugins**, keep **Restricted mode** on. In **Settings → Core plugins**, turn **Sync** off if it is on. Note the version under **Settings → General**. Don't sign in or install a plugin.
4. Open `Start` and click its **Token** link (Ctrl+E switches to Reading view). The token is an exercise identifier, not a credential.
5. Click **Reply**, switch to editing view with Ctrl+E, paste only the token on one line with no heading, quotes, or backticks, and press **Ctrl+S**.

**Expected:** The links open the existing `Token` and `Reply` notes, and `Reply` shows the token.

**Stop:** The wrong vault opens, a link creates an empty note, or you cannot edit and save in the window.

**Recovery:** Reopen the exact printed vault and follow its links; if the window cannot be used, record Obsidian HOLD with the error.

Keep the practice vault open with `Token` visible. This box checks your saved reply on disk, then changes `Token` from outside Obsidian.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT" &&
"$PY" "$M/scripts/obsidian_readiness.py" refresh --root "$OBS_ROOT"
```

**Expected:** `Token generation 1: initial token; external refresh not yet exercised`, `PASS: Obsidian file round-trip; GUI observation still required`, a disk-record path, and `Source token rotated outside Obsidian; your saved reply was preserved.`

**Stop:** Any HOLD or error; don't continue with an old token after a failed refresh.

**Recovery:** If the reply doesn't match, copy the current token into `Reply` in Obsidian, save, and paste this box again; never edit the helper's records.

**Window: Obsidian, same practice vault.**

1. Look at `Token` in the open app and confirm its token now differs from the one in `Reply`. If needed, follow **Token** from `Start` again.
2. Follow **Reply**, replace the old line with the new token, and press **Ctrl+S**. Don't run refresh again.
3. Close only the practice vault's window and leave other vault windows open. Launch Obsidian again the same way. If it restores the practice vault, confirm its folder is exactly the printed vault path; otherwise use **Manage vaults → Open folder as vault → Open** to select it.
4. Open `Start`, follow **Token**, then **Reply**, and confirm the new token is still saved.

**Expected:** You see the outside change, save the new reply, and see it again after reopening the same folder.

**Stop:** The app doesn't show the changed token, the edit disappears, or you can't tell which vault reopened.

**Recovery:** Record Obsidian HOLD with the failed action; a match on disk alone doesn't show the app worked.

**Terminal: Ubuntu, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"
```

**Expected:** `Token generation 2: refreshed token; GUI observation still required`, `PASS: Obsidian file round-trip; GUI observation still required`, and a new disk-record path.

**Stop:** HOLD, or a GUI action you could not see in the window.

**Recovery:** Correct the reply in Obsidian, save, close and reopen the vault, then paste this box again.

### Record Obsidian readiness

In a text editor, create `gui-observation.txt` beside the vault, in the `OBS_ROOT` folder. Record the date, system and architecture, app version, exact vault path, both disk-record paths, that Restricted mode was on and Sync off, and what you saw at each GUI step. Write `Obsidian READY` only if both checks passed and you saw every GUI step in the window; otherwise write `Obsidian HOLD` and the missing step or error. These GUI steps have not been checked on Ubuntu, so record what actually happens.

## Prepare local n8n for Module 7

n8n is the local workflow editor for Module 7. Staff prepare and qualify its two-service environment before you use it. Allow about 10 minutes to start it and check a saved workflow, plus staff-assisted restart. Keep n8n readiness separate from OMP, Obsidian, and Local model.

Staff own Docker installation, access, licensing, image versions, project identity, and persistence. Keep any existing installation and its data; do not install or migrate yourself. If staff have not prepared your environment, record **n8n HOLD** and contact the device/support owner.

### Start and inspect the prepared instance

Use the Ubuntu terminal where step 5 set `PY` and `R`. In a new terminal, repeat the step 5 box first.

**Terminal: Ubuntu, Bash or Zsh, ordinary user.**

```bash
"$PY" "$M/scripts/n8n_local.py" start &&
"$PY" "$M/scripts/n8n_local.py" status
```

**Expected:** The helper reports the prepared n8n 2.41.5 instance and its external task runner, editor at `http://localhost:5678`.

**Stop:** The helper reports `HOLD`, the environment is not prepared, or the browser page does not open.

**Recovery:** Keep the first error and contact the device/support owner. Don't create a project or change Docker settings.

### Save and reopen a blank workflow

Open **http://localhost:5678**. On a fresh instance, complete local owner setup. On an existing instance, use its existing login. Skip optional offers and leave **Assistant** off. Don't enter your OpenRouter key until Module 7.

Select **Overview → Build a workflow** (or **Create workflow**). Name the blank workflow **Module 7 readiness** and press Enter. If that name already holds work, choose a distinct name. Leave the canvas blank and unpublished. Reload, return to the workflow list, and reopen it. Confirm the name, empty canvas, and unpublished state.

**Expected:** Named blank workflow survives reload.

**Stop:** Owner setup appears unexpectedly, login fails, or you cannot confirm the saved workflow.

**Recovery:** Keep the first error and ask the support owner. Don't create another owner account over an existing instance.

### Observe staff-assisted persistence

Ask staff to stop and restart only this recorded course instance without removing data. Reopen the workflow after. Record **n8n READY** only if helper status, browser, reload/reopen, and staff-assisted persistence succeed. Otherwise **n8n HOLD**.

In later session, repeat the two helper lines in your shell. Do not run the staff stop procedure.

## Later sessions

After a restart, open a new terminal, repeat the step 5 box to set `PY`, `R`, and `M`, then run the two `n8n_local.py` lines above. Sign in with the existing local owner account and reopen your workflow.

## If a step stops

Find the step that stopped. Keep the exact error, the attempt folder, and the last thing you saw. Never delete, reset, or overwrite an existing file, checkout, binary, vault, or Docker resource to get past a stop. Then use [when setup stops](../shared/TROUBLESHOOTING.md) and, for anything about the key, [credentials](../shared/CREDENTIALS.md).

### Steps 1 to 3

- Unsupported OS, shell, or account: ask the device owner for a supported Ubuntu 24.04 or 26.04 account. Don't choose another processor's binary.
- Package install refused: save the error and ask the device owner. Don't add a PPA, download Git or Python, or use pip.
- Download or certificate error: keep the installer’s error. Install `ca-certificates` through step 2 if it is missing, or ask about the approved proxy settings, then retry the official installer.
- An existing `omp` reports an unexpected version: check `command -v omp` and `omp --version`, then confirm you are using the installation you intended.

### Step 4

- Access check fails after login: the repository owner must invite or approve your account; login alone can't grant access.
- `gh` package unavailable: Universe may be disabled by policy. Ask the device owner; don't edit package sources.
- Wrong project, a file, or a symlink at `~/Documents/AIHB_OCT_2026`: leave it and ask its owner. Don't delete, reset, or pull it.
- Missing course helper: ask the course owner; don't update the checkout to create it.

### Step 5

- `omp` missing: follow the installer’s PATH instructions, close the terminal, and open a new one from the desktop menu before retrying `omp --version`.
- `SET` in a new window: close it. If you opened it from an old terminal, open the next one from the desktop menu. If a desktop terminal still prints `SET`, follow [credentials](../shared/CREDENTIALS.md).

### Steps 6 and 7

- Key shown on screen: treat it as exposed, follow [credentials](../shared/CREDENTIALS.md), and use a replacement key in a new window.
- `MISSING` after export: paste steps 6 and 7 again in the same window.

### Steps 8 and 9

- `LAUNCH_EXIT 2`: usually the key is missing. Paste steps 6 and 7 in this window, then paste step 8 again; it makes a new attempt.
- `LAUNCH_EXIT 1` or `READINESS CHECK HOLD`: keep the attempt and its receipts, and send the first failure to the course owner. Don't point the launcher at another provider or model.
- `SETUP CHECK HOLD`: fix only the first FAIL line. Changed or untracked files are not a failure, so don't clean the checkout. A passing report never replaces `READINESS CHECK PASS`.

### Obsidian

- Existing installation: keep it, its profile, and its vaults, and record its version.
- No approval for `--no-sandbox` on ARM64: record Obsidian HOLD.
- Closed terminal: paste step 5 again, then set `OBS_ROOT` to the folder printed before `/vault`.
- Check HOLD: correct `Reply` in Obsidian and check again. Never edit the helper's expected records or remove its lock.

### n8n (prepared helper)

- Environment not prepared or helper HOLD: record n8n HOLD and contact owner. Do not create project.
- Port 5678 in use or wrong bind: ask owner; preserve existing.
- Wrong version or missing runner after helper status: record HOLD; owner resolves.
- Workflow fails reload or staff restart: record HOLD; keep volumes; confirm recorded instance with owner.

## Local model (capstone) readiness lane

Ask staff for the approved `hf` and `llama-server` paths, then [check local-model readiness](../../module-10-capstone/shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) before a download and again before launch. Quoted executable paths support spaces. Missing tools, insufficient capacity, an occupied endpoint, or an unresolved failed rehearsal mean **Local model HOLD**; preserve your other readiness results and contact the device/support owner.
