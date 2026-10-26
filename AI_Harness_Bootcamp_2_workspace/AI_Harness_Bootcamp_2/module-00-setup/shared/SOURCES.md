# Primary setup sources


## Windows and WSL

- [WinGet overview](https://learn.microsoft.com/en-us/windows/package-manager/winget/)
- [Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Set up a WSL development environment](https://learn.microsoft.com/en-us/windows/wsl/setup/environment)
- [PowerShell environment variables](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables)
- [Windows PowerShell 5.1 execution policies and scopes](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1)
- [Official GitHub CLI Windows installation](https://raw.githubusercontent.com/cli/cli/trunk/docs/install_windows.md)
- [Python on Windows](https://docs.python.org/3/using/windows.html)
- [Git for Windows](https://git-scm.com/downloads/win)

## macOS

- [Homebrew](https://brew.sh/)
- [Apple command-line tools through Homebrew prerequisites](https://docs.brew.sh/Installation)
- [Homebrew support tiers, including Intel](https://docs.brew.sh/Support-Tiers)
- [Apple Gatekeeper · Open a blocked app](https://support.apple.com/en-us/102445)
- [Install Git on macOS: Homebrew or Apple's Command Line Tools](https://git-scm.com/install/mac)

## Ubuntu and Arch

- [Ubuntu package management](https://documentation.ubuntu.com/server/how-to/software/package-management/)
- [Ubuntu 24.04 Python package](https://packages.ubuntu.com/noble/python3)
- [Ubuntu 26.04 Python package](https://packages.ubuntu.com/resolute/python3)
- [Ubuntu GitHub CLI package in Universe](https://packages.ubuntu.com/noble/gh)
- [Official Arch Linux platform definition](https://archlinux.org/about/)
- [Arch Linux pacman](https://wiki.archlinux.org/title/Pacman)
- [Arch Linux Python](https://wiki.archlinux.org/title/Python)
- [Arch GitHub CLI package](https://archlinux.org/packages/extra/x86_64/github-cli/)
- [Install Git on Linux with the distribution's package manager](https://git-scm.com/install/linux)

## Shared tools

- [Git installation](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Clone a GitHub repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
- [GitHub CLI browser login and credential storage](https://cli.github.com/manual/gh_auth_login)
- [GitHub CLI authentication status](https://cli.github.com/manual/gh_auth_status)
- [GitHub CLI host-scoped Git credential helper](https://cli.github.com/manual/gh_auth_setup-git)
- [Oh My Pi releases (latest stable)](https://github.com/can1357/oh-my-pi/releases/latest)
- [OMP CLI reference](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
- [OMP model resolution](https://github.com/can1357/oh-my-pi/blob/main/docs/models.md)
- [OMP approval policy](https://github.com/can1357/oh-my-pi/blob/main/docs/approval-mode.md)
- [OMP extension API](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- [Sonnet 4.6 through OpenRouter](https://openrouter.ai/anthropic/claude-sonnet-4.6)
- [OpenRouter authentication](https://openrouter.ai/docs/api-reference/authentication)
- [Python downloads](https://www.python.org/downloads/)

## Local Obsidian

- [Official Obsidian 1.13.7 release](https://github.com/obsidianmd/obsidian-releases/releases/tag/v1.13.7) and [release API metadata with asset digests](https://api.github.com/repos/obsidianmd/obsidian-releases/releases/tags/v1.13.7): the downloads for a fresh install and their exact SHA-256 values are in [Required tool identities](VERSIONS.md#local-obsidian-for-module-2). Keep any installed version and profile, then record the result of the same workflow.
- [Official installation instructions](https://github.com/obsidianmd/obsidian-help/blob/master/en/Getting%20started/Download%20and%20install%20Obsidian.md): universal macOS/Windows installers, AppImage execute permission, and launching with `--no-sandbox`. Get separate device-owner approval for that renderer-sandbox exception; it does not allow you to change system-wide security.
- [Local Markdown storage and external-change refresh](https://github.com/obsidianmd/obsidian-help/blob/master/en/Files%20and%20folders/How%20Obsidian%20stores%20data.md): open only the practice `vault` folder. Use local storage with Restricted community plugins and Sync off; no Obsidian account, community plugin, or MCP service needed.
- [Microsoft WSL GUI requirements](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps): Windows 10 build 19044+ or Windows 11, WSL 2, and working GUI support. Run Linux Obsidian in the existing Ubuntu Linux home beside OMP; do not use a native Windows app on a WSL UNC vault.
- [AppImage FUSE guidance](https://docs.appimage.org/user-guide/troubleshooting/fuse.html) and [Ubuntu `libfuse2t64`](https://packages.ubuntu.com/noble/libfuse2t64): on Ubuntu ARM64, keep FUSE 3 and add only the approved compatibility library. The older `fuse` package is not a replacement.
- [Arch Extra Obsidian package](https://archlinux.org/packages/extra/x86_64/obsidian/) and [Arch full-upgrade requirement](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported): use the signed distribution package in your existing approved `pacman -Syu` transaction. The package was 1.13.7-2 when checked; do not downgrade to match it.
- [Supplied readiness helper](../scripts/obsidian_readiness.py): `initialize`, `refresh`, and `check` take `--root` for a fresh attempt outside the checkout. A disk PASS from this helper still needs a separate check in the Obsidian window and does not show OMP or n8n ready.

The Obsidian window was checked only on **Obsidian 1.13.7, Darwin arm64**. It hasn't been checked on native Windows, WSLg, Intel macOS, Ubuntu, or Arch. Complete **Set up local Obsidian** in your [platform guide](../README.md#set-up-local-obsidian) and check links, edits, saves, refreshed files, and reopening on your own device before recording Obsidian READY. Official documentation and available binaries show how to set it up, but not whether it works on your machine.

## Local n8n (staff-prepared two-service)

- [n8n task runners and external Code execution](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners.md)
- [Install using Docker Compose (official images)](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose.md)
- [Advertised webhook URLs and `N8N_WEBHOOK_URL`](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/configure-webhook-urls-with-reverse-proxy.md)
- [Docker Desktop for macOS](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Docker Desktop WSL integration](https://docs.docker.com/desktop/features/wsl/)
- [Docker Desktop licensing](https://docs.docker.com/subscription/desktop-license/)
- [Compose down without volumes](https://docs.docker.com/reference/cli/docker/compose/down/)

Staff prepare local n8n 2.41.5 with its matching external task runner. Follow your platform guide to start it with the supplied [Python helper](../scripts/n8n_local.py), open **http://localhost:5678**, and confirm that a blank unpublished workflow survives reload and a staff-assisted restart. Keep Assistant off. Preserve existing instances and data.

Use the prepared configuration rather than running the upstream full-stack installer or changing Compose files. Check the actual browser and saved workflow on your own device before recording **n8n READY**.

## Source hierarchy

Start with documentation for the release you're using, then check operating-system documentation and the official package source. A community post may explain a symptom, but check the official source for required command. A post cannot grant permission to bypass device policy.
