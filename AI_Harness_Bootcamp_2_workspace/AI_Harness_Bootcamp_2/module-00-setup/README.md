# Module 0 · Set up the harness and get a long document you can trust

Install and check your tools, then have Oh My Pi plan, draft, check, and revise a North Shelf status brief one section at a time. You write the plan and the tests first, check the draft against the sources in separate review sessions, and decide whether you'd send it.

Start with one platform guide. Install what's missing, open a new terminal, and run the OMP readiness check. In that check, the model reads a fresh token and writes a real file through the course launcher. Check local Obsidian before Module 2 and local n8n before Module 7; keep those results separate from the status brief.

Plan for about one to three hours for setup (a rough estimate). Downloads, desktop readiness, or owner approvals may take longer. Plan for about three hours for the [status brief](shared/MODULE_00_LAB.md) (a rough estimate).

## Start here

Choose one platform path and stay in it. A **terminal** is the text window where you enter commands; the **shell** is the program, such as PowerShell or Bash, that runs them.

| Your machine | Use this guide |
|---|---|
| Windows, native PowerShell | [Windows · PowerShell OMP and local n8n](platforms/windows-powershell.md) |
| Windows with or willing to install WSL 2 | [Windows · WSL 2 with Ubuntu](platforms/windows-wsl.md) |
| Mac | [macOS](platforms/macos.md) |
| Ubuntu desktop | [Ubuntu](platforms/ubuntu.md) |
| Arch Linux desktop | [Arch Linux](platforms/arch-linux.md) |

Choose PowerShell to keep OMP, Python, Git, credentials, and course work native to Windows. Choose WSL if your organization permits it and you want to do that work inside Ubuntu. Staff prepare local n8n for your chosen shell using the approved Docker Desktop Linux backend. You don't need a separate Ubuntu window for n8n on the PowerShell route. If device policy blocks the backend, keep your OMP result and record **n8n HOLD** until the owner resolves it. Don't complete both OMP routes.

## What you will install

- Install [Git](#install-git) and get a **checkout**, your local copy of the private course repository.
- Install Python 3.12 or newer.
- Install Oh My Pi (`omp`) from the latest stable release (the setup prints the observed `omp/<semver>`).
- Before Module 2, install local Obsidian. A **vault** is a folder of linked Markdown notes on your laptop. For a fresh install, use release **1.13.7**; if it's already installed, keep it and record its version.
- Before Module 7, use the prepared local n8n environment. Staff own the two-service setup and persistence qualification. Follow your platform guide's n8n steps and run the common helper.

**Restart your terminal after installing OMP so PATH changes take effect.** Close the installation window and open a new terminal before starting OMP or entering your API key. **PATH** is the list of folders your shell searches for commands.

Get GitHub read access to `TheHolofex/AIHB_OCT_2026`; the hosted-course password doesn't grant it. Your guide checks approved Git credentials first. Use GitHub CLI (`gh`) for browser login only if that fails; you don't need it to run the AI.

For the live readiness check, use `shared/run_omp.py` with OpenRouter and the fixed model `openrouter/anthropic/claude-sonnet-4.6`. Use your own [OpenRouter key](shared/CREDENTIALS.md), which you enter in the terminal rather than save in a file. If you lack account or repository access, ask its owner before continuing.

Module 7 uses the local visual workflow editor. You don't need n8n Cloud. Keep Assistant off and keep workflows unpublished during setup. In Module 7 you put your OpenRouter key into an n8n credential for the agent. Don't put that key in a file, a workflow export, a prompt, or your notes.

## Install Git

**Git** is a version-control tool. It copies the course files from GitHub to your computer and records exactly which version you have. Your platform guide uses Git in step 4 to make your checkout, so Git comes first.

Step 1 of your guide reports whether Git is missing. Step 2 installs it from your operating system's official source, the same routes the [Git project lists](https://git-scm.com/downloads):

| Your machine | Where Git comes from | Install step |
|---|---|---|
| Windows, PowerShell route | Git for Windows, which WinGet installs as `Git.Git` | [Install Git and Python](platforms/windows-powershell.md#2-install-git-and-python) |
| Windows with WSL | Ubuntu's `git` package, installed inside Ubuntu | [Install Git and the other missing packages](platforms/windows-wsl.md#2-install-git-and-the-other-missing-packages) |
| Mac | Apple's Command Line Tools, which the Homebrew installer adds, or Homebrew's `git` | [Install Git and Python](platforms/macos.md#2-install-git-and-python) |
| Ubuntu | Ubuntu's `git` package | [Install Git and the other missing packages](platforms/ubuntu.md#2-install-git-and-the-other-missing-packages) |
| Arch Linux | Arch's `git` package, in a full system upgrade | [Install Git and the other missing packages](platforms/arch-linux.md#2-install-git-and-the-other-missing-packages) |

Git is ready when `git --version` prints `git version 2.` followed by more numbers. Each guide's **Confirm Git works** box runs that check right after the install. If an installer is blocked, or asks for approval you can't give, stop and ask the device owner. Don't download Git from any other website.

## Before the first command

- Keep at least 15 GB free; WSL should have 25 GB.
- Get administrator approval for operating-system packages.


## Start OMP with your OpenRouter key

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

**Expected:** OMP replies to `hello`.

**Stop:** `omp` is not found or the provider rejects the request.

**Recovery:** Use [PATH recovery](shared/TROUBLESHOOTING.md#if-omp-is-not-found-after-restarting) for a missing command, or the [credential guide](shared/CREDENTIALS.md#start-omp-directly-with-openrouter) for a rejected request.

## When a step fails

Copy and paste the error into the harness. Describe what you were doing when the error appeared and what you are trying to accomplish, then ask it to fix the issue:

```text
I'm trying to: [describe the outcome you want].
I was doing this when the error appeared: [describe the command or action].
Here is the error:
[paste the error message]

Fix this issue.
```

Review and apply the fix, then rerun the failed check. If it still fails, paste the new error into the same conversation and explain what you tried. If the harness itself cannot start, use [When setup stops](shared/TROUBLESHOOTING.md).

![Give the harness the error, what you were doing, and your goal. Ask it to fix the issue, then check the result.](shared/figures/m00-recovery-loop.png)

*Give the harness the error, what you were doing, and your goal. Ask it to fix the issue, then check the result.*

<details markdown="1">
<summary>Figure text</summary>

Copy and paste the error into the harness, describe what you were doing and what you are trying to accomplish, and ask “Fix this issue.” Review and apply the fix, then run the same check again. If it still fails, return to the harness with the new error and what you tried. If it succeeds, record the result.

</details>

## Ready means observable

Open a new terminal after the last install. Check these OMP setup results:

![The prerequisite report, live tool write, and two application checks each show something different. One check cannot stand in for another.](shared/figures/m00-readiness-lanes.png)

*The prerequisite report, live tool write, and two application checks each show something different. One check cannot stand in for another.*

<details markdown="1">
<summary>Figure text</summary>

Check each tool on its own. In a new terminal, inspect the prerequisite report. A live OMP call must write a file and produce a receipt; open the file from disk to check it. A setup report marked PASS cannot replace that live check. For Obsidian, check both the files on disk and what you see in the app window. For n8n, check both the running stack and whether the workflow stays saved in the browser. A result for one tool cannot clear another.

</details>

- `origin` reports `https://github.com/TheHolofex/AIHB_OCT_2026.git`, and `git rev-parse HEAD` reports a 40-character id (the setup check prints the first 12). `git status --short` is informational; keep unrelated changes. They don't block setup or QA;
- the platform resolver selects an absolute Python executable reporting 3.12 or higher and saves it as `PY` (`$PY` in PowerShell);
- the setup check prints the observed `OMP_VERSION omp/<semver>` and the absolute command path;
- the key check shows `SET` in that terminal without printing the key;
- the tool writes `from-omp.txt` through the course launcher, and you read the file from disk;
- the expected absolute tool path works in that new terminal without repairing PATH; and
- the setup report stays outside the checkout and contains no key, token, or password.

The setup report shows PASS, WARN or FAIL for version, path, repository, and key presence. Run `verify_tool_proof.py` separately on the tool-written file, token, and saved run record; it reports `READINESS CHECK PASS` or `READINESS CHECK HOLD`. Even a passing setup report cannot replace the live check.

A **receipt** records a run's inputs, tool calls, results, and file effects. Keep receipts and your **work folder** (the editable exercise copy) outside the checkout. That way, corrections won't overwrite supplied inputs or earlier attempts.

Open and read the result file from disk before accepting it. A tool saying “done” doesn't prove the file exists.

## Set up local Obsidian

Obsidian is the note app for Module 2. A **vault** is a folder of notes on your laptop. Do this before Module 2, in the platform guide you already chose. You don't sign in to Obsidian, and you don't use your key here.

Open **Set up local Obsidian** in that guide and follow only those steps:

- [Windows PowerShell](platforms/windows-powershell.md#set-up-local-obsidian)
- [Windows with WSL](platforms/windows-wsl.md#set-up-local-obsidian)
- [Mac](platforms/macos.md#set-up-local-obsidian)
- [Ubuntu](platforms/ubuntu.md#set-up-local-obsidian)
- [Arch Linux](platforms/arch-linux.md#set-up-local-obsidian)

The guide installs the app if you don't have it, then has you practice in one new vault. If Obsidian is already installed, keep that copy and your existing notes. Don't mix steps from another platform.

You're done when the guide's checks pass and you saw the practice in the Obsidian window. Write **Obsidian READY** or **Obsidian HOLD** as the guide tells you. That result stays separate from your Oh My Pi and n8n results. If a step stops, use [Obsidian troubleshooting](shared/TROUBLESHOOTING.md#when-local-obsidian-stops).

## Local n8n readiness for Module 7

Staff prepare the two-service n8n environment (n8n + external task runner images) and qualify persistence before class. Use the common Python helper in your platform's ordinary shell. Keep n8n separate from OMP, Obsidian, and Local model results.

In your chosen platform guide, follow only the n8n steps:

- [Windows PowerShell](platforms/windows-powershell.md#prepare-local-n8n-for-module-7)
- [Windows with WSL](platforms/windows-wsl.md#set-up-local-n8n-for-module-7)
- [Mac](platforms/macos.md#prepare-local-n8n-for-module-7)
- [Ubuntu](platforms/ubuntu.md#prepare-local-n8n-for-module-7)
- [Arch Linux](platforms/arch-linux.md#prepare-local-n8n-for-module-7)


Open **http://localhost:5678**. On a fresh instance, complete local owner setup; on an existing instance, use its existing login. Leave Assistant off and don't enter your provider key until Module 7. Create a blank, unpublished workflow named **Module 7 readiness**, choosing a different name if it already exists. Reload and reopen it to confirm that it was saved.

Ask staff to stop and restart only the recorded course instance without removing its data. Reopen the same workflow afterward. Record **n8n READY** only when helper status, browser access, reload/reopen, and staff-assisted persistence all succeed. Otherwise record **n8n HOLD** with the first failure.

Existing instances and data remain owner-controlled. If staff have not prepared your environment, contact the device/support owner. Complete the checks on your own device; an OMP pass does not establish n8n readiness.

## Local model readiness for Module 10

Staff provision the capstone tools before class. Run the checks in a fresh terminal on the machine you'll use for Module 10. Keep results separate from OMP, Obsidian, and n8n readiness.

[Check local-model readiness](../module-10-capstone/shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) before any download or launch, using the approved [tool identities](shared/VERSIONS.md#local-model-readiness-lane-module-10). The pre-download policy requires 35 GiB total free space on the actual destination and applicable cache volumes. A 24 GiB installed-RAM planning floor does not establish performance; every machine needs a complete exact-model rehearsal.

Record the platform, architecture, tool paths/versions, free space (bytes and GiB), RAM, port status, and device-owner approval. A base setup PASS does not clear capstone capacity. Unmeasured platform or architecture combinations remain unobserved until exercised on a qualifying machine.
