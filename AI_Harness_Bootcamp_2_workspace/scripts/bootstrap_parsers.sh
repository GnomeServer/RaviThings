#!/usr/bin/env bash
# Ubuntu 24.04 x86_64 build-only parsers. Run the build command in this PATH;
# never modify global installations, shell profiles, the publish tree or caches.
set -euo pipefail

fail() { printf 'HOLD: parser bootstrap: %s\n' "$*" >&2; exit 1; }
[[ $# -gt 0 ]] || fail 'supply the build command and its arguments'
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || fail 'requires the qualified Ubuntu 24.04 x86_64 build environment'
[[ -r /etc/os-release ]] || fail '/etc/os-release is unavailable'
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || fail 'requires Ubuntu 24.04; qualify a changed build image before use'
for tool in curl tar xz sha256sum cc make bash sh; do
    command -v "$tool" >/dev/null || fail "missing build dependency: $tool"
done

PS_VERSION=7.6.6
PS_SHA256=ddbc4a2d113bbd46d283cfedcbcd117a70caefd7673f41f2b4e0000badf103bc
PS_URL="https://github.com/PowerShell/PowerShell/releases/download/v${PS_VERSION}/powershell-${PS_VERSION}-linux-x64.tar.gz"
ZSH_VERSION=5.9.2
ZSH_SHA256=36fa734374b44783582cec09bcd67822e2f992c779ec1624ab5596df078d2f81
ZSH_URL="https://www.zsh.org/pub/zsh-${ZSH_VERSION}.tar.xz"

TOOLS="$(mktemp -d "${TMPDIR:-/tmp}/course-parsers.XXXXXXXX")"
trap 'rm -rf -- "$TOOLS"' EXIT
mkdir "$TOOLS/bin" "$TOOLS/powershell" "$TOOLS/source"
printf 'PARSER SOURCE %s sha256=%s\n' "$PS_URL" "$PS_SHA256"
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$PS_URL" --output "$TOOLS/powershell.tar.gz"
printf '%s  %s\n' "$PS_SHA256" "$TOOLS/powershell.tar.gz" | sha256sum --check --strict -
tar -xzf "$TOOLS/powershell.tar.gz" -C "$TOOLS/powershell"
chmod +x "$TOOLS/powershell/pwsh"
ln -s "$TOOLS/powershell/pwsh" "$TOOLS/bin/pwsh"

printf 'PARSER SOURCE %s sha256=%s\n' "$ZSH_URL" "$ZSH_SHA256"
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$ZSH_URL" --output "$TOOLS/zsh.tar.xz"
printf '%s  %s\n' "$ZSH_SHA256" "$TOOLS/zsh.tar.xz" | sha256sum --check --strict -
tar -xJf "$TOOLS/zsh.tar.xz" -C "$TOOLS/source"
(
    cd "$TOOLS/source/zsh-$ZSH_VERSION"
    ./configure --prefix="$TOOLS/zsh"
    make -j2
    make install.bin
)
ln -s "$TOOLS/zsh/bin/zsh" "$TOOLS/bin/zsh"
export PATH="$TOOLS/bin:$PATH"
export POWERSHELL_TELEMETRY_OPTOUT=1 POWERSHELL_UPDATECHECK=Off
hash -r
[[ "$(pwsh --version)" == "PowerShell $PS_VERSION" ]] || fail 'PowerShell version/dependencies did not match'
[[ "$(zsh --version)" == "zsh $ZSH_VERSION"* ]] || fail 'Zsh version did not match'
printf 'PARSER PATH %s\n' "$TOOLS/bin"
bash --version
zsh --version
pwsh --version
"$@"
