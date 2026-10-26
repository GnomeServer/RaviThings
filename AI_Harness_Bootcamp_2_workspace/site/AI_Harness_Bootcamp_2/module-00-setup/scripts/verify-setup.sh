#!/usr/bin/env bash
set -u

# Setup report for macOS, WSL, Ubuntu, and Arch Linux.
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
# the home directory with ~ and removes any credential embedded in a URL. No secret value
# is printed.
#
# No clean-tree requirement: git status is informational only. Unrelated changes are
# preserved; they do not trigger HOLD or advice to discard for QA.

SELF="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SELF")" 2>/dev/null && pwd -P)" || SCRIPT_DIR="."
MODULE_DIR="$(cd -- "$SCRIPT_DIR/.." 2>/dev/null && pwd -P)" || MODULE_DIR="$SCRIPT_DIR/.."

ROOT_INPUT="${1:-$PWD}"
ROOT="$(cd -- "$ROOT_INPUT" 2>/dev/null && pwd -P)" || ROOT="$ROOT_INPUT"

EVIDENCE_DIR="${AHB_EVIDENCE_DIR:-$HOME/course-evidence/module-00}"
mkdir -p "$EVIDENCE_DIR" 2>/dev/null || true
RESULTS="${2:-$EVIDENCE_DIR/setup-report-$(date -u +%Y%m%dT%H%M%SZ)-$$.txt}"
if [ -e "$RESULTS" ] || [ -L "$RESULTS" ]; then
  printf 'HOLD: report already exists; choose a new external report path.\n' >&2
  exit 1
fi

ERR_FILE="$(mktemp "${TMPDIR:-/tmp}/ahb-verify.XXXXXX")" || ERR_FILE=""
cleanup() { [ -z "$ERR_FILE" ] || rm -f "$ERR_FILE"; }
trap cleanup EXIT

pass_count=0
warn_count=0
fail_count=0
lines=()

# ---------------------------------------------------------------------------- reporting

HOME_MARK='~'
redact() {
  local s="${1-}"
  case "$s" in *://*@*) s="$(printf '%s' "$s" | sed -e 's#://[^/@[:space:]]*@#://***@#g')" ;; esac
  if [ -n "${HOME:-}" ]; then s="${s//"$HOME"/$HOME_MARK}"; fi
  printf '%s' "$s"
}

or_none() {
  if [ -n "${1-}" ]; then redact "$1"; else printf 'none'; fi
}

record() {
  local state="$1" name="$2" detail="$3" action="${4:-}"
  local line="[$state] $name: $detail"
  if [ "$state" != PASS ]; then
    [ -n "$action" ] || action="Save this line and stop at this boundary; the troubleshooting guide starts from the first failed check."
    line="$line
        NEXT ACTION: $action"
  fi
  lines+=("$line")
  printf '%s\n' "$line"
  case "$state" in
    PASS) pass_count=$((pass_count + 1)) ;;
    WARN) warn_count=$((warn_count + 1)) ;;
    *) fail_count=$((fail_count + 1)) ;;
  esac
}

# ------------------------------------------------------------------- version comparison

capture_version() {
  local name="$1" pattern="$2" cmd="$3"
  shift 3
  local resolved
  resolved="$(command -v "$cmd" 2>/dev/null)" || resolved=""
  if [ -z "$resolved" ]; then
    record FAIL "$name" "$cmd is not on PATH" \
      "Install $cmd with the step for it in your platform guide, open a new terminal, and run this check again."
    return
  fi
  local out
  if ! out="$("$cmd" "$@" 2>/dev/null)"; then
    record FAIL "$name" "$cmd could not run successfully" "Keep the failed command and repair this prerequisite before continuing."
    return
  fi
  out="${out//$'\r'/}"
  if [ -z "$out" ]; then
    record FAIL "$name" "$cmd returned no version" "Use the verified installation from the platform guide."
    return
  fi
  local shown
  shown="$(redact "$resolved") — $out"
  if [ -n "$pattern" ] && [[ ! "$out" =~ $pattern ]]; then
    record FAIL "$name" "unrecognized version at $shown" \
      "Install and verify the latest stable release, then re-run in a new terminal."
  else
    record PASS "$name" "$shown"
  fi
}

# ------------------------------------------------------------------ platform and machine

case "$(uname -s)" in
  Darwin) platform=macOS ;;
  Linux)
    if [ -n "${WSL_DISTRO_NAME:-}" ] || [ -n "${WSL_INTEROP:-}" ]; then
      platform=WSL
    else
      if command -v pacman >/dev/null 2>&1; then platform=Arch; else platform=Ubuntu; fi
    fi
    ;;
  *) platform=Unknown ;;
esac

arch="$(uname -m)"
platform_ok=yes
case "$platform" in
  macOS|Ubuntu|Arch|WSL) ;;
  *) platform_ok=no; record FAIL platform "unsupported: $platform" "Use a supported platform listed in README.md." ;;
esac
if [ "$platform_ok" = yes ]; then
  record PASS platform "$platform ($arch)"
else
  record FAIL platform "unsupported platform $platform ($arch)" "Use macOS, Ubuntu, Arch, or WSL 2 with Ubuntu."
fi

disk_floor_gb=15
[ "$platform" != WSL ] || disk_floor_gb=25
free_kb="$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2 {print $4}')"
if [ -z "${free_kb:-}" ]; then
  record WARN disk "could not determine free space" "Ensure at least ${disk_floor_gb} GB free under $HOME."
else
  free_gb=$((free_kb / 1024 / 1024))
  if [ "$free_gb" -ge "$disk_floor_gb" ]; then
    record PASS disk "${free_gb} GB free (want >= ${disk_floor_gb})"
  else
    record FAIL disk "${free_gb} GB free (want >= ${disk_floor_gb})" "Free space under $HOME and re-run."
  fi
fi

path_rest="${PATH:-}"
path_index=1
path_empty=""
while :; do
  part="${path_rest%%:*}"
  if [ -z "$part" ]; then
    path_empty="yes"
    break
  fi
  path_rest="${path_rest#*:}"
  [ "$path_rest" = "$part" ] && break
  path_index=$((path_index + 1))
done
if [ -z "$path_empty" ]; then
  record PASS path "no empty element"
else
  record FAIL path "empty element (current dir) in PATH" "Edit your shell startup to remove a leading/trailing/double colon in PATH."
fi

# ------------------------------------------------------------------------------- tools

capture_version git '' git --version

python_cmd=""
for candidate in python3.12 python3 python; do
  resolved="$("$candidate" -c 'import os, sys; sys.exit(1) if sys.version_info < (3, 12) else print(os.path.abspath(sys.executable))' 2>/dev/null)" || continue
  [ -x "$resolved" ] || continue
  "$resolved" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null || continue
  python_cmd="$resolved"
  break
done
if [ -z "$python_cmd" ]; then
  record FAIL python "Python 3.12+ not found on PATH" "Install Python 3.12+ and ensure it is on PATH in a new terminal."
else
  pyver="$("$python_cmd" --version 2>/dev/null | awk '{print $2}')"
  if [ -z "$pyver" ]; then
    record FAIL python "could not read version" "Install Python 3.12+."
  else
    major_minor="$(printf '%s' "$pyver" | awk -F. '{print $1"."$2}')"
    major=$(printf '%s' "$major_minor" | cut -d. -f1)
    minor=$(printf '%s' "$major_minor" | cut -d. -f2)
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 12 ]; }; then
      record PASS python "$pyver at $(command -v "$python_cmd")"
    else
      record FAIL python "want 3.12+, observed $pyver at $(command -v "$python_cmd")" "Install Python 3.12+."
    fi
  fi
fi
capture_version omp '^omp/[0-9]+\.[0-9]+\.[0-9]+$' omp --version

# ---------------------------------------------------------------------- course clone

if ! command -v git >/dev/null 2>&1; then
  record FAIL repo.clone "git not found" "Install Git with step 2 of your platform guide, open a new terminal, and run this check again."
else
  remote="$(git -C "$ROOT" remote get-url origin 2>/dev/null)" || remote=""
  revision="$(git -C "$ROOT" rev-parse --verify HEAD 2>/dev/null)" || revision=""
  dirty="$(git -C "$ROOT" status --porcelain 2>/dev/null)" || dirty=""
  if [ "$remote" = 'https://github.com/TheHolofex/AIHB_OCT_2026.git' ]; then
    record PASS repo.remote "$remote"
  else
    record FAIL repo.remote "want the course HTTPS origin, observed $(or_none "$remote")" \
      "Point origin at the course repository over HTTPS, or clone it again into a new directory, then run this check again."
  fi
  if printf '%s' "$revision" | grep -Eq '^[0-9a-f]{40}$'; then
    record PASS repo.revision "${revision:0:12}"
  else
    record FAIL repo.revision "no commit is checked out in $(redact "$ROOT")" \
      "Run git log -1 in the repository root and read the error it prints."
  fi
  if [ -z "$dirty" ]; then
    record PASS repo.clean "no changed or untracked paths"
  else
    dirty_count="$(printf '%s\n' "$dirty" | grep -c .)"
    record WARN repo.clean "$dirty_count changed or untracked paths; informational only" "Preserve these changes and continue in a separate external work folder."
  fi
fi

missing_module=""
for required in shared/MODULE_00_LAB.md shared/VERSIONS.md shared/case/verify_tool_proof.py platforms; do
  [ -e "$MODULE_DIR/$required" ] || missing_module="${missing_module:+$missing_module, }$required"
done
case "$MODULE_DIR" in
  "$ROOT"/*) module_in_root=yes ;;
  *) module_in_root=no ;;
esac
if [ -n "$missing_module" ]; then
  record FAIL repo.module "this clone is missing $missing_module under $(redact "$MODULE_DIR")" \
    "Preserve this checkout. Ask the course owner for the missing files or use a separate complete checkout; do not reset, clean, or pull over local work."
elif [ "$module_in_root" = no ]; then
  record FAIL repo.module "the checks you are running live in $(redact "$MODULE_DIR"), which is outside $(redact "$ROOT")" \
    "Run this check from the repository root you cloned, using the copy of the script inside that clone."
else
  record PASS repo.module "the course files for this session are present at $(redact "$MODULE_DIR")"
fi

# --------------------------------------------------------------- credentials and auth

if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  record PASS secret.openrouter 'SET in current process; value not printed'
else
  record FAIL secret.openrouter 'MISSING in current process' \
    'Enter the key again with the hidden-input step in your guide, in this same window, then run this check again.'
fi

if command -v omp >/dev/null 2>&1 && omp --version >/dev/null 2>&1; then
  record PASS config.omp "omp present and runnable"
else
  record FAIL config.omp "omp not present or not runnable" \
    "Install omp with the step in your platform guide, open a new terminal, and run this check again."
fi

# ------------------------------------------------------------------------------ verdict

if [ "$fail_count" -eq 0 ]; then
  verdict="SETUP CHECK PASS"
else
  verdict="SETUP CHECK HOLD"
fi

if ! (
  set -o noclobber
  {
    printf '%s\n' "${lines[@]}"
    printf '\n%s — report: %s\n' "$verdict" "$(redact "$RESULTS")"
  } >"$RESULTS"
); then
  printf 'HOLD: could not create the report without overwriting an existing file.\n' >&2
  exit 1
fi

printf '\n%s — report: %s\n' "$verdict" "$RESULTS"
if [ "$fail_count" -eq 0 ]; then
  exit 0
fi
exit 1
