# Required tool identities

Use the latest stable Oh My Pi release and the exact provider/model pair in your run policy. Install OMP with the official one-line command from [omp.sh](https://omp.sh/) and retain its reported version with the run evidence. A similarly named model is not a substitute.

| Component | Required value | Check |
|---|---|---|
| Oh My Pi | latest stable release from the official installer | In a restarted terminal, `omp --version` reports `omp/<semver>`; record the resolved command path and actual version. |
| Provider/model | `openrouter/anthropic/claude-sonnet-4.6` | The launcher and actual run receipts agree on OpenRouter and Sonnet 4.6. |
| Jev for Module 6 | `jev-1.13` through OpenRouter | The agent calls it with `OPENROUTER_API_KEY`. No separate TypeSafe key. Jev is not the chat model. |
| Credential | `OPENROUTER_API_KEY` | A presence-only check reports `SET` in the process that launches OMP. |
| Python | 3.12 or newer | Resolve its absolute executable path and inspect its version. |
| Obsidian | Local desktop app required for Module 2; fresh reference 1.13.7 | Keep an existing version; record it, and watch the full GUI workflow in the Obsidian window separately from the disk check. |
| n8n | 2.41.5, staff-prepared two-service local (n8n + external runners) | Use the common helper start/status in the platform shell; check editor, reload workflow, and staff-assisted persistence. |
| Docker and Compose | Approved local engine and modern `docker compose` plugin | `docker info` and `docker compose version` succeed as the ordinary user in the intended new shell; version 5 is acceptable. |
| Git | Git 2 from your platform guide's official route: Git for Windows, Apple's Command Line Tools or Homebrew, or the Ubuntu or Arch `git` package | `git --version` prints `git version 2.` followed by more numbers, and the intended checkout is readable. |
| Browser and text editor | An accessible combination you can operate | You can read instructions, edit plain-text work files, and inspect actual outputs. |

You need read access to the private course repository on GitHub. If your existing approved Git credentials work, you don't need another login tool. Otherwise, follow the platform steps to log in through your browser with [GitHub CLI (`gh`)](https://cli.github.com/manual/gh_auth_login). The package is `GitHub.cli` in WinGet, `gh` in Homebrew and Ubuntu Universe, and `github-cli` in Arch's official repositories. GitHub CLI helps you reach the repository; you don't need it to run the AI tools.

Use the macOS/Linux installer inside macOS, Linux, or WSL Ubuntu. Use the PowerShell installer for native Windows. Follow any PATH instructions the installer prints, then restart your terminal before running OMP or entering the API key. The installer chooses its installation location; confirm `omp` is available in the new terminal.

## Match the package route to the operating system

| Setup route | Operating-system and shell boundary |
|---|---|
| Native Windows OMP | Windows PowerShell 5.1 on an owner-supported Windows installation with WinGet; x64 or ARM64. PowerShell on macOS/Linux is a different environment. n8n uses the prepared two-service environment with Docker Desktop Linux backend (staff-managed); native OMP stays in PowerShell. |
| Windows with WSL 2 | Windows 10 build 19041+ or Windows 11 is the technical floor for Microsoft's install command; Obsidian needs the higher WSLg floor of Windows 10 build 19044+ or Windows 11. The host must also remain supported under the device owner's policy. Use Ubuntu 24.04 or 26.04 in WSL 2 and run course commands in Ubuntu Bash. |
| macOS | Bash or zsh on Apple Silicon or Intel. Homebrew's current supported-install requirements are macOS 15+; Intel is Tier 3. An OMP download for Intel doesn't mean Homebrew supports Intel equally. |
| Ubuntu | Ubuntu 24.04 or 26.04 on x86-64 or ARM64, using Bash or zsh and the distribution's Python package. |
| Arch Linux | Current official Arch Linux on x86-64, using Bash or zsh. Arch Linux ARM is a separate distribution, not this package route. |

Check your OS and architecture before installing. A binary may be available even when your operating system is not supported. Keep a suitable tool you already have, and do not replace system Python or add a package source just to get past a version hold.

The launcher keeps the runtime configuration separate, makes only the named course tools available, and turns off automatic retries, model fallback, cache warming, unrelated extensions, skills, and persistent sessions. Use it for exercises instead of your personal OMP profile. A prerequisite report shows what is set up, not what happened during a model turn; check the readiness receipts to see whether those controls worked.

You don't need another model-provider key or agent CLI. For Module 2, you need local Obsidian with Sync off and community plugins restricted, but you don't need an account, plugin, or MCP service. For Module 7, you need local n8n and a local instance-owner login, but not n8n Cloud signup or an Assistant key. If the latest OMP release, pinned n8n release, or specified model is unavailable, keep the failure and put that part of setup on hold. Don't use an unreviewed substitute to get a passing label.

## Local Obsidian for Module 2

Keep any existing installation, its profile, and personal vaults. Record the version you have, then complete the same workflow and check what happens in the app; do not upgrade or downgrade just to match the reference. For a fresh vendor installation, use **1.13.7**. The asset names and SHA-256 values come from an approved record of the [official release metadata](https://api.github.com/repos/obsidianmd/obsidian-releases/releases/tags/v1.13.7), and downloads come from the [official v1.13.7 release](https://github.com/obsidianmd/obsidian-releases/releases/tag/v1.13.7). Check the selected download before running it.

| Fresh route | Official asset | Exact SHA-256 |
|---|---|---|
| macOS, Apple Silicon or Intel | [Obsidian-1.13.7.dmg](https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/Obsidian-1.13.7.dmg) | `05daa54f5e1a4458f75da29f8faaa17e8e37ae16998432537f674c626db99bce` |
| Native Windows, x64 or ARM64 | [Obsidian-1.13.7.exe](https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/Obsidian-1.13.7.exe) | `f233dc24896b3f2d5f9e4b01111181a561d0760b2105f0a474024c5f3143a9bc` |
| Ubuntu/WSLg x86-64 | [obsidian_1.13.7_amd64.deb](https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/obsidian_1.13.7_amd64.deb) | `17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0` |
| Ubuntu/WSLg ARM64 | [Obsidian-1.13.7-arm64.AppImage](https://github.com/obsidianmd/obsidian-releases/releases/download/v1.13.7/Obsidian-1.13.7-arm64.AppImage) | `e286fd2bb2a5d346a35a577bd764c73fd5537dddec2b99a1a3e5e35974085203` |

On Arch x86-64, install the signed [Arch Extra `obsidian` package](https://archlinux.org/packages/extra/x86_64/obsidian/) through the guide's approved `pacman -Syu` full upgrade. The reference package version was **1.13.7-2**. Arch maintains this package; it is not from AUR or a vendor download. Record the version you installed and check that the app is ready. Do not apply the vendor hashes to this package, downgrade Arch, or run a partial upgrade. See [Arch's full-upgrade guidance](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported).

WSLg runs Linux Obsidian inside your existing Ubuntu distribution, using the same Linux home as OMP. To show the app window, it [needs Windows 10 build 19044+ or Windows 11 and WSL 2](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps). Builds 19041–19043 can run the earlier CLI steps while Obsidian stays on HOLD. Keep the distribution and any active Docker workloads; get an owner-approved window for updates or restarts. Do not open a WSL UNC vault in native Windows Obsidian or move course files to `/mnt/c`.

On Ubuntu 24.04/26.04 ARM64, follow the guide's approved package step to run the AppImage: `libfuse2t64` for FUSE, and `zlib1g-dev`, which supplies the `libz.so` name the ARM64 AppImage's starter loads ([AppImage issue 964](https://github.com/AppImage/AppImageKit/issues/964)). Keep FUSE 3, and do not install obsolete `fuse` instead. The [AppImage FUSE guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html) explains the compatibility library is needed. The vendor's [AppImage launch instructions](https://github.com/obsidianmd/obsidian-help/blob/master/en/Getting%20started/Download%20and%20install%20Obsidian.md) use `chmod u+x` and `./Obsidian-1.13.7-arm64.AppImage --no-sandbox`. The second command turns off Chromium's renderer sandbox for this app, so you need separate device-owner approval. It does not add to or replace the course tool boundary. Without approval, Obsidian stays on HOLD; do not change kernel-wide security settings, permissions, or privileged sandbox files to force it to launch.

The Obsidian app window has been checked only with **Obsidian 1.13.7 on Darwin arm64**. On Ubuntu (x86-64 and ARM64), Arch, and Ubuntu in WSL, the install steps ran and the app started in Linux test machines with a virtual display, but nobody looked at its window there. The app window on native Windows, WSLg, Intel macOS, Ubuntu, and Arch has not been checked here. Having an asset, a command that parses, or a disk PASS from the helper does not show that the app works on those systems. On each device, follow the link/edit/save/refresh/reopen practice in its [platform guide](../README.md#set-up-local-obsidian), using local files, Restricted community plugins, and Sync off.

## Local n8n stack contract

Staff provision the two-service environment using the official n8nio/n8n:2.41.5 and ghcr.io/n8n-io/runners:2.41.5 images. The learner uses the Python helper `n8n_local.py start/status` in the ordinary shell. See the [task runner configuration](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners.md) and [Docker Compose install options](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose.md).

The editor port is 127.0.0.1:5678. Assistant remains off. A named blank unpublished workflow must survive reload and a staff-assisted stop/start of the recorded instance (volumes preserved). Existing instances and data remain owner-controlled; no learner migration or deletion.

Staff check the Docker installation, image versions, external Code-node execution and retained workflow data before class. If the prepared instance is missing or a check fails, record **n8n HOLD** and contact the device/support owner. Use your platform guide to start and inspect the instance; don't edit its configuration or install another stack.

## Local model readiness lane (Module 10)

Keep existing tools and ask the device owner to approve any missing installation. Record the actual executable paths, version/help output and platform/architecture; a matching version is not proof that the model fits or runs.

The official Hugging Face CLI candidate is **huggingface-hub 2.1.1**, installed into an isolated per-user Python environment. The [official universal wheel](https://files.pythonhosted.org/packages/33/23/885b3a3b510c305f1d84421913935e19b6a48b93d173a0541674c1e88c2a/huggingface_hub-2.1.1-py3-none-any.whl) has SHA-256 `d76fa1d8e6a59e01f012b1d88da604c099c7a0f2e26b1cc7d708f0a4283bd2a2`. Retain the installation report's resolved dependency versions, URLs and hashes. [CLI reference](https://huggingface.co/docs/huggingface_hub/guides/cli).

The llama.cpp candidate is official prerelease **b11146**, commit `7fe450e19305b828c199d602c23a8337aaa1f03b`. Select the archive for the actual OS and architecture; do not substitute a GPU build or another release merely to get a passing startup. These immutable file identities are from the [official release metadata](https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b11146). The upstream tag is not marked immutable; verify the retained digest before extracting.

| Runtime | Official archive | SHA-256 |
|---|---|---|
| macOS ARM64 | [llama-b11146-bin-macos-arm64.tar.gz](https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-macos-arm64.tar.gz) | `1ad3f9eff80edb9dbef4259ad564d1720612ef7eea48fa4afed0e54f5f3d5711` |
| macOS x86-64 | [llama-b11146-bin-macos-x64.tar.gz](https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-macos-x64.tar.gz) | `305f0e3a17d2c01eb205cd0a62128357f1ec3b55329cb084d94e5ec0115d7a3b` |
| Windows ARM64, CPU | [llama-b11146-bin-win-cpu-arm64.zip](https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-win-cpu-arm64.zip) | `1727d241f3bf6d27360e984e851cf013928fd655bf89f8628e70da027f377b7d` |
| Windows x86-64, CPU | [llama-b11146-bin-win-cpu-x64.zip](https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-win-cpu-x64.zip) | `14cf1303ca9ac3abd94816850532f9f9a69ac66fbaca3776fc6f9061c2fac1d1` |
| Linux ARM64, CPU | [llama-b11146-bin-ubuntu-arm64.tar.gz](https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-ubuntu-arm64.tar.gz) | `4aeda6fe68831547e49b7fa87607383ca5352b3d72ca5f70d52ed265f58c131f` |
| Linux x86-64, CPU | [llama-b11146-bin-ubuntu-x64.tar.gz](https://github.com/ggml-org/llama.cpp/releases/download/b11146/llama-b11146-bin-ubuntu-x64.tar.gz) | `c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410` |

Archive availability is not platform qualification. Full current native model rehearsals for these candidates remain **unobserved/HOLD**; an installed-host version or a Linux container cannot establish native Windows, Arch or another machine's operation. Keep the exact resolved environment after its rehearsal; do not call an untested combination qualified.

Before a new weight download, require **35 GiB total free** on the actual work/download volume and every separately configured cache volume that may hold the full weight allocation. This conservative policy allows two model-sized allocations plus roughly 5 GiB margin; it is not a vendor minimum or additional space above 35 GiB. The pinned file is 15,676,553,472 bytes, approximately 14.60 GiB. The separate base setup thresholds remain 15/25 GiB.

The fixed `--local-dir weights` route stores download metadata under that directory and bypasses the Hub file cache. Its capacity check covers the actual destination and HF Xet cache, not an unused `HF_HUB_CACHE` volume. [Local-directory download behavior](https://huggingface.co/docs/huggingface_hub/v2.1.1/en/package_reference/file_download#huggingface_hub.hf_hub_download).

Use **24 GiB installed RAM** as a provisional planning floor, not a speed guarantee. At least 16 GiB but less than 24 GiB is conditional on the complete exact-model rehearsal at context 32768. Below 16 GiB, or after a failed rehearsal, arrange an owner-approved qualified machine. Machines at or above 24 GiB still need that rehearsal. Record available RAM and competing workload. Linux `MemTotal` excludes reservations: retain the device owner's installed-capacity inventory separately, plus any VM/container limit.

[Check local-model readiness](../../module-10-capstone/shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) in a fresh terminal before HF authentication/download and immediately before launch. The endpoint must be free at `127.0.0.1:8080`; never use another service's health response as this attempt's evidence. The check neither downloads nor starts a model.

Retain actual evidence of verified weights, an owned loopback listener, context 32768, health after listening, a real OMP reply, stop/unreachable, disabled-control refusal, digest-checked restore and byte comparison, frozen copy, cold replay, and final stop. None of the capacity or identity checks promises answers, refusals, warnings, or interactive speed.
