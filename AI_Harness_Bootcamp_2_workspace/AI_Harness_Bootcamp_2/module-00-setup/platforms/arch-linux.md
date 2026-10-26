# Arch Linux setup for Module 0

With an ordinary Arch Linux desktop account, you'll install and check Oh My Pi, get the course checkout, and run a live readiness check that writes a file. Plan for roughly 45 to 90 minutes. Arch's package step upgrades the whole system. Wait for your terminal prompt to return before pasting the next box.

You'll need Git, Python 3.12 or newer, a web browser, an ordinary text editor, and the latest stable Oh My Pi release. The readiness check uses one OpenRouter key and the model `openrouter/anthropic/claude-sonnet-4.6`. You won't install Node, npm, or a second AI tool, and you won't need to log in to a model vendor.

Paste every line of each box at once, then press Return. The commands use absolute paths, so your current folder does not matter. A home folder with spaces is fine because every path is quoted.

## 1. Check this computer

Use official Arch Linux on x86-64, not Arch Linux ARM, which is a different distribution. Before downloading anything, check your operating system, architecture, shell, account, free space, packages, and Python version. Use an ordinary account; get the device owner's approval before installing packages.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, current window.**

```bash
course_check_computer() {
  local ID VERSION_ID machine missing package py
  [ -r /etc/os-release ] || { printf 'STOP: cannot read /etc/os-release\n' >&2; return 1; }
  . /etc/os-release || return 1
  machine="$(uname -m)" || return 1
  printf 'OS %s %s\nARCH %s\n' "$ID" "${VERSION_ID:-rolling}" "$machine"
  case "$ID:${VERSION_ID:-rolling}:$machine" in
    arch:*:x86_64) ;;
    *) printf 'STOP: unsupported OS or architecture\n' >&2; return 1 ;;
  esac
  if [ -z "${BASH_VERSION:-}" ] && [ -z "${ZSH_VERSION:-}" ]; then
    printf 'STOP: use Bash or Zsh\n' >&2; return 1
  fi
  if [ "$(id -u)" -eq 0 ] || [ ! -w "$HOME" ] || [ ! -x "$HOME" ]; then
    printf 'STOP: use an ordinary account with a writable home folder\n' >&2; return 1
  fi
  df -h "$HOME" || return 1
  missing=""
  for package in git curl python ca-certificates diffutils less obsidian; do
    pacman -Q "$package" >/dev/null 2>&1 || missing="${missing:+$missing }$package"
  done
  if [ -z "$missing" ]; then
    printf 'PACKAGES present\n'
  else
    printf 'PACKAGES missing: %s\n' "$missing"
  fi
  py="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import os, sys; sys.exit(1) if sys.version_info < (3, 12) else print(os.path.realpath(sys.executable))' 2>/dev/null && break; done)"
  if [ -n "$py" ]; then
    printf 'PY %s\n' "$py"
    "$py" --version || return 1
  else
    printf 'PY missing: step 2 installs or upgrades python\n'
  fi
}
course_check_computer
```

**Expected:** The OS line shows `arch`, and ARCH shows `x86_64`. Available space is at least 15G. The package line is `PACKAGES present` or names some of `git curl python ca-certificates less obsidian`. The last lines show a `PY` path with `Python 3.12` or newer, or `PY missing: step 2 installs or upgrades python`.

**Stop:** Any STOP line appears, or Available is below 15G.

**Recovery:** Free space if needed, then paste this box again. For an unsupported OS, shell, architecture, or account, ask the device owner for a supported environment. A missing package or `PY missing` is not a stop; step 2 handles it.

## 2. Install Git and the other missing packages

**Git** copies the course files from GitHub to your computer and records exactly which version you have. Step 4 uses it to make your checkout. Arch packages Git as `git`, and the [Git project](https://git-scm.com/install/linux) installs it on Arch with `pacman`. Here it comes in the same full upgrade as the other packages.

Skip this box if step 1 printed both `PACKAGES present` and a `PY` path, and go to [Confirm Git works](#confirm-git-works). Arch does not support partial upgrades. This command upgrades the whole system with `-Syu` and installs the listed packages in the same transaction. Read the entire transaction. Type `y` only if the device owner has approved every package listed; otherwise type `n` and stop. The `python` package from core provides Python, and `obsidian` is the signed package from extra.

If step 1 lists `obsidian` as missing, check your application menu first. If Obsidian is already installed outside pacman (Flatpak, an AppImage, or a vendor package), stop and ask the device owner before installing a second copy. Remove `obsidian` from the command only with their approval.

**Terminal: Arch Linux, Bash or Zsh, same window; sudo elevates the approved full upgrade.**

```bash
sudo pacman -Syu --needed git python curl ca-certificates diffutils less obsidian
```

**Expected:** Pacman shows the full transaction including any system updates and the missing course packages. Prompt returns after completion. Already-current packages are not reinstalled.

**Stop:** sudo missing, password rejected, policy refusal, conflict, or unapproved replacement in the list.

**Recovery:** Stop. Do not use AUR, partial `-Sy`, or other workarounds. When the owner approves the full transaction, paste again. Use [when setup stops](../shared/TROUBLESHOOTING.md) for the exact error.

### Confirm Git works

This box shows which Git your terminal finds and asks it for its version. Run it even if you skipped the install box.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
command -v git && git --version
```

**Expected:** `/usr/bin/git`, then `git version 2.` followed by more numbers.

**Stop:** the box prints nothing, or no `git version` line appears.

**Recovery:** Paste the step 2 box again and approve the full transaction. Don't use AUR or a partial upgrade to get Git; see [If a step stops](#if-a-step-stops).

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

This command checks access to the private repository, then clones the course into the checkout at `"$HOME/Documents/AIHB_OCT_2026"`. If that folder is already a checkout of the course origin, the command leaves it unchanged and does not reset, pull, or clean it. GitHub credentials are separate from your course-site password and OpenRouter key.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
course_use_checkout() {
  local origin_url checkout_top helper
  R="$HOME/Documents/AIHB_OCT_2026"
  ORIGIN="https://github.com/TheHolofex/AIHB_OCT_2026.git"
  if [ -L "$HOME/Documents" ] || [ -L "$R" ]; then printf 'STOP: Documents or checkout is a link\n' >&2; return 1; fi
  if [ ! -e "$R" ]; then
    GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code "$ORIGIN" HEAD || return 1
    mkdir -p -- "$HOME/Documents" || return 1
    git clone "$ORIGIN" "$R" || { printf 'STOP: clone failed\n' >&2; return 1; }
  elif [ ! -d "$R" ]; then
    printf 'STOP: exists but not a directory\n' >&2; return 1
  else
    origin_url="$(git -C "$R" remote get-url origin 2>/dev/null || true)"
    if [ "$origin_url" != "$ORIGIN" ]; then printf 'STOP: not the course checkout\n' >&2; return 1; fi
    printf 'USE: existing checkout; no reset, pull, or clean\n'
  fi
  if [ -L "$R/.git" ]; then printf 'STOP: .git is a link\n' >&2; return 1; fi
  checkout_top="$(git -C "$R" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [ "$checkout_top" = "$R" ] || { printf 'STOP: not the checkout root\n' >&2; return 1; }
  git -C "$R" rev-parse --verify HEAD >/dev/null || return 1
  M="$R/AI_Harness_Bootcamp_2/module-00-setup"
  if [ ! -f "$R/shared/run_omp.py" ] || [ ! -f "$R/shared/course_guard.mjs" ] || [ ! -f "$M/scripts/verify-setup.sh" ] || [ ! -f "$M/shared/case/verify_tool_proof.py" ]; then
    printf 'STOP: checkout missing a course helper\n' >&2; return 1
  fi
  for helper in "$R/shared/run_omp.py" "$R/shared/course_guard.mjs" "$M/scripts/verify-setup.sh" "$M/shared/case/verify_tool_proof.py"; do
    [ ! -L "$helper" ] || { printf 'STOP: helper is a link\n' >&2; return 1; }
  done
  printf 'R %s\nM %s\n' "$R" "$M"
}
course_use_checkout
```

**Expected:** For a new clone, a commit hash followed by `HEAD`, then Git's `Cloning into` progress. For an existing checkout, `USE: existing checkout; no reset, pull, or clean`. Either way, the last lines are the `R` and `M` paths under your home folder.

**Stop:** Authentication, network, or not-found error on ls-remote; any STOP from the function.

**Recovery:** Keep the error. For a network problem ask the owner. For missing credentials use the subsection below. If the account lacks access, the repository owner must invite it.

### If GitHub access fails

Check whether `gh` is present.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
if command -v gh >/dev/null 2>&1; then gh --version; else printf 'GH MISSING\n'; fi
```

**Expected:** A `gh version` line or `GH MISSING`. Skip the install command when a version is shown.

**Stop:** Existing gh fails to run.

**Recovery:** Ask owner to repair existing gh. Install only when missing.

Install only with owner approval for the full upgrade. Use the official package.

**Terminal: Arch Linux, Bash or Zsh, same window; sudo elevates.**

```bash
sudo pacman -Syu --needed github-cli
```

**Expected:** Transaction completes.

**Stop:** Refused, unavailable, or conflict.

**Recovery:** Keep error; ask owner for the official package. No AUR or partial sync.

Sign in through your browser. The terminal shows a one-time code and may ask you to press Return to open the browser. Enter the code on GitHub and authorize the account invited to this repository. If the terminal asks whether to authenticate Git with your GitHub credentials, choose **No**; the next two boxes check where credentials are stored before Git uses them. Don't add `--insecure-storage`.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; interactive login.**

```bash
gh auth login --hostname github.com --git-protocol https --web
```

**Expected:** Browser completes and the terminal confirms login for the invited account.

**Stop:** Login fails or wrong account.

**Recovery:** Stop; ask owner or account owner to resolve. Never paste a password or token.

Check status. The storage location must be approved by device policy.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
gh auth status --hostname github.com
```

**Expected:** Success for invited account and approved storage.

**Stop:** Fails, wrong account, or unclear storage.

**Recovery:** Ask owner for approved credentials/storage.

Set up the helper and recheck access.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
gh auth setup-git --hostname github.com &&
GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code https://github.com/TheHolofex/AIHB_OCT_2026.git HEAD
```

**Expected:** A commit hash followed by `HEAD`. Now paste the step 4 box again to clone the course.

**Stop:** Either command fails. Do not clone.

**Recovery:** Keep the error. The repository owner must confirm the invitation and any organization approval for this account. After that, paste this box again, then the step 4 box.

## 5. Open a new terminal and confirm

Close the current terminal completely. Open a fresh one from the desktop menu. Do not export PATH or run commands in the old window. The new window must read the startup files and show `MISSING` for the key.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, newly opened desktop window.**

```bash
course_confirm_new_terminal() {
  local resolved version candidate origin_url
  R="$HOME/Documents/AIHB_OCT_2026"
  M="$R/AI_Harness_Bootcamp_2/module-00-setup"
  PY="$(for candidate in python3.12 python3 python; do "$candidate" -c 'import sys; from pathlib import Path; sys.exit(1) if sys.version_info < (3, 12) else print(Path(sys.executable).resolve())' 2>/dev/null && break; done)"
  case "$PY" in /*) ;; *) printf 'STOP: no absolute Python 3.12+ executable\n' >&2; return 1 ;; esac
  "$PY" -c 'import sys; print(sys.version); sys.exit(sys.version_info < (3, 12))' || return 1
  resolved="$(command -v git)" || return 1
  case "$resolved" in /*) ;; *) printf 'STOP: Git is not an absolute executable\n' >&2; return 1 ;; esac
  printf 'GIT_PATH %s\n' "$resolved"
  "$resolved" --version || return 1
  if [ -L "$HOME/Documents" ] || [ -L "$R" ] || [ -L "$R/.git" ] || [ ! -d "$R" ]; then
    printf 'STOP: checkout is missing or linked\n' >&2; return 1
  fi
  origin_url="$(git -C "$R" remote get-url origin)" || return 1
  if [ "$origin_url" != 'https://github.com/TheHolofex/AIHB_OCT_2026.git' ] || [ "$(git -C "$R" rev-parse --show-toplevel)" != "$R" ]; then
    printf 'STOP: wrong checkout identity\n' >&2; return 1
  fi
  git -C "$R" rev-parse --verify HEAD >/dev/null || return 1
  printf 'R %s\nM %s\nPY %s\n' "$R" "$M" "$PY"
  resolved="$(command -v omp 2>/dev/null || true)"
  printf 'OMP_PATH %s\n' "${resolved:-missing}"
  case "$resolved" in /*) ;; *) printf 'STOP: omp is not on PATH\n' >&2; return 1 ;; esac
  version="$("$resolved" --version 2>/dev/null)" || { printf 'STOP: installed OMP could not run\n' >&2; return 1; }
  printf 'OMP_VERSION %s\n' "${version:-missing}"
  [[ "$version" =~ ^omp/[0-9]+\.[0-9]+\.[0-9]+$ ]] || { printf 'STOP: installed OMP did not report a version number\n' >&2; return 1; }
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\nSTOP: this window already has the key\n' >&2; return 1; fi
  printf 'MISSING\n'
}
course_confirm_new_terminal
```

**Expected:** `R`, `M`, `PY`, `GIT_PATH`, `OMP_PATH`, `OMP_VERSION omp/<semver>`, and final line `MISSING`.

**Stop:** Any failure, wrong paths/versions, or `SET` for the key.

**Recovery:** If Python/Git/omp/ checkout problem, fix the prerequisite with the owner and repeat from the affected step, then open another fresh desktop terminal. If `SET` appears, close the window and open the next from the desktop menu without printing the key.

## 6. Enter your OpenRouter key

The launcher reads your OpenRouter key only from this terminal's environment. This box reads the key without showing it; step 7 makes it available to the commands you run here. Paste the box by itself and press Return. Then type or paste the key and press Return again; nothing appears while you do. The key exists only in this terminal process.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
IFS= read -r -s OPENROUTER_API_KEY
```

**Expected:** Nothing echoed. Prompt returns after Return (may stay on same line).

**Stop:** Any character of the key appears, or you paste the key into the box.

**Recovery:** Treat displayed key as exposed. Follow [credentials](../shared/CREDENTIALS.md). Use a replacement key in a new terminal.

## 7. Confirm the key is loaded

Export makes the variable visible to programs started from this terminal. `SET` confirms a non-empty value in this process only. A closed terminal forgets the key.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
export OPENROUTER_API_KEY
if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; else printf 'MISSING\n'; fi
```

**Expected:** The only new line is `SET`.

**Stop:** `MISSING`, or any command prints the key value.

**Recovery:** Paste the read box again, then this box again. Never write the key to a file to keep `SET` across terminals.

## 8. Run the readiness check

Prepare a fresh attempt outside the checkout. The launcher runs the model with the key from the environment and writes only the result file. The verifier checks the token match and the write provenance. All three steps run in one paste; keep the attempt on any failure.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
course_run_readiness() {
  local attempt course_exit
  unset COURSE_PROOF_VERIFIED
  if [ -z "${PY:-}" ] || [ -z "${R:-}" ]; then printf 'STOP: PY and R not set\n' >&2; return 1; fi
  if [ -L "$HOME/course-evidence" ] || [ -L "$HOME/course-evidence/reformation-qa" ]; then printf 'STOP: evidence parent linked\n' >&2; return 1; fi
  attempt="module-00-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  BASE="$HOME/course-evidence/reformation-qa/$attempt"
  if [ -e "$BASE" ] || [ -L "$BASE" ]; then printf 'STOP: attempt exists\n' >&2; return 1; fi
  mkdir -p -- "$BASE/proof" "$BASE/receipts" || return 1
  EVIDENCE="$BASE/receipts/live-1"
  if [ -e "$EVIDENCE" ] || [ -L "$EVIDENCE" ]; then printf 'STOP: evidence exists\n' >&2; return 1; fi
  "$PY" -c 'import secrets; print(secrets.token_hex(16), end="")' > "$BASE/run-token.txt" || return 1
  [ "$(wc -c < "$BASE/run-token.txt" | tr -d '[:space:]')" -ge 16 ] || { printf 'STOP: token too short\n' >&2; return 1; }
  cp -- "$BASE/run-token.txt" "$BASE/proof/run-token.txt" || return 1
  cat > "$BASE/proof/prompt.txt" << 'COURSE_PROMPT'
Read run-token.txt with the course_read tool. Then write only from-omp.txt with the course_write tool. The file contents must be the words omp works, one space, and the exact token text from run-token.txt. Do not write any other file.
COURSE_PROMPT
  if [ -e "$BASE/proof/from-omp.txt" ] || [ -L "$BASE/proof/from-omp.txt" ]; then printf 'STOP: from-omp.txt exists\n' >&2; return 1; fi
  printf 'READINESS_WORK %s\nTOKEN_OUTSIDE %s\nEVIDENCE_NOT_CREATED %s\n' "$BASE/proof" "$BASE/run-token.txt" "$EVIDENCE"
  "$PY" "$R/shared/run_omp.py" --workdir "$BASE/proof" --prompt "$BASE/proof/prompt.txt" --evidence "$EVIDENCE" --allow-write from-omp.txt
  course_exit="$?"
  printf 'LAUNCH_EXIT %s\n' "$course_exit"
  if [ "$course_exit" -eq 2 ]; then printf 'STOP: prerequisite hold\n' >&2; return 2; fi
  if [ "$course_exit" -ne 0 ]; then printf 'STOP: live run failed\n' >&2; return 1; fi
  if [ ! -d "$EVIDENCE" ]; then printf 'STOP: evidence not created\n' >&2; return 1; fi
  "$PY" "$M/shared/case/verify_tool_proof.py" "$BASE/proof" "$BASE/run-token.txt" "$EVIDENCE"
  course_exit="$?"
  printf 'VERIFY_EXIT %s\n' "$course_exit"
  if [ "$course_exit" -eq 0 ]; then COURSE_PROOF_VERIFIED="$BASE"; fi
  return "$course_exit"
}
course_run_readiness
```

**Expected:** `READINESS_WORK`, `TOKEN_OUTSIDE`, `EVIDENCE_NOT_CREATED`, `LAUNCH_EXIT 0`, `READINESS CHECK PASS`, `VERIFY_EXIT 0`.

**Stop:** `LAUNCH_EXIT 2`, nonzero launch or verify exit, or STOP line.

**Recovery:** Keep the attempt. For key hold, re-enter and export in this window. For other prerequisite or failure, ask the owner with the first error from receipts. Do not edit files or reuse the attempt.

## 9. Save the setup report and read the result

The report checks prerequisites. It cannot replace the live readiness result. After the readiness passed, read the actual `from-omp.txt` bytes.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window.**

```bash
course_save_and_read() {
  if [ -z "${M:-}" ] || [ -z "${R:-}" ] || [ -z "${BASE:-}" ] || [ "${COURSE_PROOF_VERIFIED:-}" != "$BASE" ]; then
    printf 'STOP: readiness not passed in this terminal\n' >&2; return 1
  fi
  if [ -e "$BASE/setup-report.txt" ] || [ -L "$BASE/setup-report.txt" ]; then printf 'STOP: report exists\n' >&2; return 1; fi
  bash "$M/scripts/verify-setup.sh" "$R" "$BASE/setup-report.txt"
  local course_exit="$?"
  printf 'REPORT_EXIT %s\n' "$course_exit"
  [ "$course_exit" -eq 0 ] || return "$course_exit"
  if [ ! -f "$BASE/proof/from-omp.txt" ] || [ -L "$BASE/proof/from-omp.txt" ]; then printf 'STOP: result file missing or link\n' >&2; return 1; fi
  printf 'FILE %s\n' "$BASE/proof/from-omp.txt"
  cat -- "$BASE/proof/from-omp.txt" || return 1
  printf '\nEND OF FILE\n'
}
course_save_and_read
```

**Expected:** `SETUP CHECK PASS`, `REPORT_EXIT 0`, then the file path, `omp works <token>`, and `END OF FILE`.

**Stop:** Nonzero report exit, or STOP.

**Recovery:** Read the first FAIL in the report and correct only that. Keep the attempt for owner review. The readiness check remains the live proof.

## Set up local Obsidian

Obsidian lets you edit and link local notes for Module 2. Allow roughly 10 to 15 minutes. Use the signed Extra `obsidian` package from the approved full `pacman -Syu` transaction. It's the [Arch-maintained x86-64 package](https://archlinux.org/packages/extra/x86_64/obsidian/), not an AUR or vendor binary. Pacman checks signatures when it installs the package. Keep any existing profile and vaults.

If you skipped the package step even though Obsidian was missing, go back and run the approved full upgrade. Record the version pacman reports.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
pacman -Q obsidian
```

**Expected:** `obsidian` followed by the installed version (for example 1.13.7-2). **Stop:** Package missing or command fails. **Recovery:** Return to the owner-approved full-upgrade transaction.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
obsidian &
```

**Expected:** The Obsidian GUI opens in your desktop session. **Stop:** Launch error, missing display, or sandbox refusal. **Recovery:** Record `Obsidian HOLD` with the exact error. Do not add flags or change security controls.

### Open a fresh practice vault and follow its links

Use Obsidian to follow a note link, save an edit, and see a change made outside the app. Allow roughly 10 to 15 minutes. A **vault** is a local folder of notes. Use only the fresh practice folder; leave existing vaults and app profiles alone. You don't need an account, plugin, Sync, or MCP. This work makes no provider call.

Stay in the terminal where you set `PY`, `R`, and `M`. `OBS_ROOT` is outside the OMP attempt and checkout.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
course_initialize_obsidian() {
  [ -n "${PY:-}" ] && [ -n "${R:-}" ] && [ -n "${M:-}" ] || { printf 'HOLD: restore PY, R, M first.\n' >&2; return 1; }
  [ "$M" = "$R/AI_Harness_Bootcamp_2/module-00-setup" ] || return 1
  [ -f "$M/scripts/obsidian_readiness.py" ] && [ ! -L "$M/scripts/obsidian_readiness.py" ] || { printf 'HOLD: helper missing or linked.\n' >&2; return 1; }
  OBS_ROOT="$HOME/course-evidence/obsidian-arch-linux-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  "$PY" "$M/scripts/obsidian_readiness.py" initialize --root "$OBS_ROOT" || return 1
  printf 'OPEN EXACT VAULT: %s\n' "$OBS_ROOT/vault"
}
course_initialize_obsidian
```

**Expected:** `Created practice vault:` and `OPEN EXACT VAULT:` name the same absolute folder ending in `/vault`.

**Stop:** HOLD, error, existing destination, or missing variable.

**Recovery:** Keep the attempt. If the terminal closed, open a new one, paste the step 5 box to restore `PY`, `R`, and `M`, then set `OBS_ROOT` to the printed path without the final `/vault` (for example `OBS_ROOT="$HOME/course-evidence/obsidian-arch-linux-..."`). Do not initialize again. Ask the checkout owner for a missing helper.

**Window: Obsidian, ordinary desktop account.**

1. Open Obsidian (from the launch step above). If another vault opens, leave it alone. Open the vault switcher, choose **Manage vaults**, then **Open folder as vault → Open**. On a first launch, choose **Open folder as vault → Open** directly.
2. Select exactly the printed `OBS_ROOT/vault` folder. Use Ctrl+L and paste the absolute path. Do not select the checkout or an existing personal vault.
3. In Settings → Community plugins keep **Restricted mode** on. Under Core plugins turn **Sync** off. Note the app version in General, then close Settings.
4. Open `Start`. Use Ctrl+E for Reading view if needed. Click its **Token** link. Read the token shown.
5. Click **Reply**. Switch to editing view with Ctrl+E if needed. Paste only the token on one line. Press Ctrl+S.

**Expected:** Links open the notes; `Reply` shows the token you read.

**Stop:** Wrong vault, empty note created, settings not local/restricted, or cannot edit/save through GUI.

**Recovery:** Leave `Start` and `Token` unchanged. Reopen the exact printed vault and follow its existing links. Record `Obsidian HOLD` for policy or display failures. A text editor edit does not count.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"
```

**Expected:** `Token generation 1: ...` followed by `PASS: Obsidian file round-trip; GUI observation still required`.

**Stop:** HOLD or nonzero exit.

**Recovery:** If reply does not match, correct it in Obsidian and rerun. Keep all records.

### Observe an external change, save, and reopen

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
"$PY" "$M/scripts/obsidian_readiness.py" refresh --root "$OBS_ROOT"
```

**Expected:** `Source token rotated outside Obsidian; your saved reply was preserved.`

**Stop:** HOLD or error.

**Recovery:** Keep the attempt and error; ask owner for file/permission issues.

**Window: Obsidian, same practice vault.**

1. Return to `Token` (still open or reopen via link). Confirm the token changed from the one in `Reply`.
2. Follow **Reply**, replace the old line with the new token, press Ctrl+S. Do not run refresh again.
3. Close the vault window with its close control. Launch Obsidian again from the platform step. Reopen the exact `OBS_ROOT/vault` via Manage vaults if needed.
4. Open `Start`, follow **Token**, then **Reply**. Confirm the new token is still saved.

**Expected:** External change visible, new reply saved in Obsidian, same after reopen.

**Stop:** App does not show the change, edit lost, or wrong vault reopens.

**Recovery:** Record `Obsidian HOLD` with the exact action that failed. Shell match alone does not prove the GUI steps.

**Terminal: Arch Linux, Bash or Zsh, ordinary user, same window; no sudo.**

```bash
"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"
```

**Expected:** `Token generation 2: ...` and `PASS: ...`, plus record path.

**Stop:** HOLD, unrefrshed token, or GUI action not seen in the window.

**Recovery:** Correct the reply in Obsidian, save, close/reopen the vault, then check again.

### Record actual Obsidian readiness

Use an ordinary text editor to create `gui-observation.txt` beside the vault at the printed `OBS_ROOT`. Record date, OS/arch, app version, exact vault path, and the two disk-record paths. Describe following the links, first edit+save, seeing the external change, second edit+save, close and reopen. Note Restricted mode on and Sync off. You may add a screenshot of the vault but omit credentials.

Write `Obsidian READY` only if both disk checks passed **and** you saw every GUI action in the Obsidian window. Otherwise write `Obsidian HOLD` and name the missing action or error. A file or `.obsidian` folder alone does not prove use of the app. Keep this record separate from OMP and n8n results.

## Prepare local n8n for Module 7

n8n is the local workflow editor for Module 7. Staff prepare and qualify its two-service environment before you use it. Allow about 10 minutes to start it and check a saved workflow, plus staff-assisted restart. Keep n8n readiness separate from OMP, Obsidian, and Local model.

Staff own Docker installation, access, licensing, image versions, project identity, and persistence. Keep any existing installation and its data; do not install or migrate yourself. If staff have not prepared your environment, record **n8n HOLD** and contact the device/support owner.

### Start and inspect the prepared instance

Use the Arch terminal where step 5 set `PY` and `R`. In a new terminal, repeat the step 5 box first.

**Terminal: Arch Linux, Bash or Zsh, ordinary user.**

```bash
"$PY" "$M/scripts/n8n_local.py" start &&
"$PY" "$M/scripts/n8n_local.py" status
```

**Expected:** The helper reports the prepared n8n 2.41.5 instance and its external task runner, editor at `http://localhost:5678`.

**Stop:** The helper reports `HOLD`, the environment is not prepared, or the browser page does not open.

**Recovery:** Keep the first error and contact the device/support owner. Don't create another project or change Docker settings.

### Save and reopen a blank workflow

Open **http://localhost:5678**. On a fresh instance, complete local owner setup. On an existing instance, use its existing login. Skip optional offers and leave **Assistant** off. Don't enter your OpenRouter key until Module 7.

Select **Overview → Build a workflow** (or **Create workflow**). Name the blank workflow **Module 7 readiness** and press Enter. If that name already holds work, choose a distinct name. Leave the canvas blank and unpublished. Reload, return to the workflow list, and reopen it. Confirm its name, empty canvas, and unpublished state.

**Expected:** Named blank workflow survives reload.

**Stop:** Login fails, owner setup appears unexpectedly, or the saved workflow is missing.

**Recovery:** Preserve the instance and contact the support owner. Don't create another owner account over existing work.

### Observe staff-assisted persistence

Ask staff to stop and restart only this recorded course instance without removing data. Reopen the workflow after. Record **n8n READY** only if helper status, browser, reload/reopen, and staff-assisted persistence succeed. Otherwise **n8n HOLD**.

In later session, repeat the two helper lines in your shell. Do not run the staff stop procedure.

## Later sessions

After a restart, ask staff to start the approved Docker engine if it is stopped. Open a fresh terminal, repeat the step 5 box to set `PY`, `R`, and `M`, then run the two `n8n_local.py` commands above. Sign in with the existing local owner account and reopen your saved workflow.

## If a step stops

The list below is organized by the step that produced the first error. Keep the exact error, attempt folder, and last observed state. Ask the device or course owner with that evidence. Never delete, rename, or overwrite an existing attempt, checkout, vault, or n8n directory to "start fresh."

- Computer check or Python below 3.12: free space or ask owner for a supported Arch x86_64 desktop with ordinary account and current python package.
- Package transaction refused or conflicting: keep the exact pacman output; only the owner can approve the full `-Syu`.
- OMP install error: keep the installer’s message and check [omp.sh](https://omp.sh/). If `omp` is missing, follow the installer’s PATH instructions and restart the terminal.
- GitHub ls-remote or clone stop: keep the error. Network: owner. Credentials: use the gh subsection exactly once per failure mode. Invitation must come from the repository owner.
- New terminal shows `SET` or wrong paths: close it and open the next from the desktop menu. Never export in the diagnostic window.
- Key read or export fails to produce `SET`: re-paste the read box, then export. Treat any visible key as exposed per CREDENTIALS.md.
- Readiness launch or verify fails: keep the attempt folder and its receipts. The first printed failure is the one to correct. Do not edit `from-omp.txt` or reuse the folder.
- Report or read-back fails: the readiness check is still the live proof. Correct only the named prerequisite; do not clean the checkout.
- Obsidian package or launch: return to the approved pacman transaction or record HOLD with the GUI error. Never add `--no-sandbox` or overwrite an existing install.
- Obsidian GUI steps cannot be performed or observed: record `Obsidian HOLD` with the exact missing action. The disk checks alone are not sufficient.
- n8n helper, browser or persistence failure: keep the configuration and volumes and contact staff. Use only the recorded instance; don't delete data, stop another service or install another engine.

## Local model (capstone) readiness lane

Ask staff for the approved `hf` and `llama-server` paths, then [check local-model readiness](../../module-10-capstone/shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) before a download and again before launch. Quoted executable paths support spaces. Missing tools, insufficient capacity, an occupied endpoint, or an unresolved failed rehearsal mean **Local model HOLD**; preserve your other readiness results and contact the device/support owner.

See also [shared/TROUBLESHOOTING.md](../shared/TROUBLESHOOTING.md) and [shared/CREDENTIALS.md](../shared/CREDENTIALS.md) for cross-platform cases. Record every HOLD with the concrete symptom and the attempt path; a later prerequisite report cannot replace an earlier live check.