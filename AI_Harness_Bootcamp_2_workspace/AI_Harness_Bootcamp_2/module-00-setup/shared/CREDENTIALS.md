# Run OMP with an API key, without provider sign-in

For the course exercises, use the OpenRouter key you were given for `openrouter/anthropic/claude-sonnet-4.6`. A newly installed OMP can use an API key directly: no `omp login`, `/login`, or model-vendor account is needed. The key must belong to the gateway you select, and that account must have access and credit for the model.

Keep the key in your approved password manager. Don't put it in a prompt, file, shell profile, Git setting, screenshot, chat, ticket, or evidence record. Supply it through `OPENROUTER_API_KEY` rather than an OMP command-line argument. The launcher reads it from this process's environment and gives OMP an isolated configuration; you don't need another provider login.

## Keep repository access separate from model access

Get each kind of access separately:

- The **hosted-course password** opens the website but does not give you GitHub repository access.
- Your **GitHub account** needs read permission for the private `TheHolofex/AIHB_OCT_2026` repository. Accept the owner's invitation with the account you plan to use.
- Your **OpenRouter key** lets you send model requests. It does not log you in to Git or GitHub.

In your platform guide, test read access to that exact repository with prompts disabled. If your approved Git credentials work, you don't need another login tool. Otherwise, follow the platform's GitHub CLI (`gh`) browser-login steps. GitHub CLI helps you reach the repository. It isn't another AI tool, and you don't need it to run OMP.

Before authorizing browser login, check the GitHub hostname, device code, and invited account. Then repeat the repository read check. Logging in alone doesn't grant permission. If the check fails, ask the owner to fix the invitation, organization approval, or network error. Don't log in again to try to gain permission.

[GitHub CLI prefers an operating-system credential store but can fall back to a plaintext file](https://cli.github.com/manual/gh_auth_login). Check which storage `gh auth status --hostname github.com` shows. Don't add `--show-token` or put authentication output in shared evidence. If device policy forbids that storage, stop and ask the device owner for approved storage or Git credentials. Don't use insecure storage. Only if fallback storage is needed and approved, follow the platform steps to set up `gh` as the Git credential helper for `github.com` alone.

## Enter the key through a hidden prompt

**Restart your terminal after installing OMP so PATH changes take effect.** Enter the key in the new terminal, then start OMP in that same window.

Choose your terminal's command. Paste only that command and press Enter. At the hidden prompt, type your OpenRouter key, which you enter in the terminal rather than save in a file, then press Enter. Don't paste the export or conversion commands while the prompt waits.

**Terminal: Bash or zsh, ordinary user.**

```bash
IFS= read -r -s OPENROUTER_API_KEY
```

**Terminal: PowerShell, ordinary user.**

```powershell
$secret = Read-Host 'OpenRouter key' -AsSecureString
```

**Expected:** The terminal accepts the key without displaying its value and returns to the ordinary prompt.

**Stop:** Characters are visible, the prompt is inaccessible with your access method, or you are unsure which program is receiving the input.

**Recovery:** Cancel input and close the terminal. If the key was exposed, revoke it in OpenRouter and get a replacement. Ask for an accessible approved input method; don't turn off masking.

## Make it available only to this process and its children

Wait until hidden input finishes. In PowerShell, the next block briefly converts the secure string to an environment value. It then clears and frees the temporary memory and disposes of the secure-string object.

**Terminal: Bash or zsh, ordinary user.**

```bash
export OPENROUTER_API_KEY
if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; else printf 'MISSING\n'; fi
```

**Terminal: PowerShell, ordinary user.**

```powershell
$bstr = [IntPtr]::Zero
try {
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
  $env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
  if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  if ($secret) { $secret.Dispose() }
  Remove-Variable secret,bstr -ErrorAction SilentlyContinue
}
if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) { 'MISSING' } else { 'SET' }
```

**Expected:** Only `SET` prints. The key is present in this process; this doesn't check validity, model availability, or a successful provider call.

**Stop:** The result is `MISSING`, conversion fails, or any key value appears in output.

**Recovery:** Re-enter the key through the hidden prompt. Revoke an exposed key first. Don't print the environment to troubleshoot.

## Start OMP directly with OpenRouter

After entering and exporting the key above, run `omp` in the same terminal from the folder where you want to work.

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

**Expected:** OMP opens with the selected model and replies to your message. Opening OMP alone does not validate the key. A model request can incur charges.

**Stop:** Missing credentials, HTTP 401, or a model-access or credit error.

**Recovery:** Check that the key belongs to OpenRouter and was entered in this terminal. Replace an invalid or revoked key with the issuer; check credit and model access with the account owner. Do not use provider sign-in to repair an API-key rejection.

For a one-message check without file tools or a saved session, run:

**Terminal: Bash or zsh, ordinary user, same window.**

```bash
omp --model openrouter/anthropic/claude-sonnet-4.6 --no-tools --no-session --no-title -p "Reply with exactly: OMP_API_KEY_OK"
```

**Terminal: PowerShell, ordinary user, same window.**

```powershell
omp --model openrouter/anthropic/claude-sonnet-4.6 --no-tools --no-session --no-title -p "Reply with exactly: OMP_API_KEY_OK"
```

**Expected:** `OMP_API_KEY_OK` and a successful process exit. This proves a live text reply, not tool operation. Use the course launcher for exercises that require bounded tools and receipts; direct OMP does not replace their readiness check.

**Stop:** An error, unsuccessful process exit, or no completed reply. A listed model or an open interface is not a successful request.

**Recovery:** Check the first error. For missing credentials, repeat the hidden input and export in this window. For HTTP 401, replace the key with a valid OpenRouter key; for credit or model-access errors, ask the account owner. Keep the selected model unchanged.

## If your key is issued by Kilo instead

Kilo and OpenRouter are separate gateways. A Kilo-issued key belongs in `KILO_API_KEY`, with a `kilo/` model selector, not in `OPENROUTER_API_KEY`. This direct OMP route does not change the course launchers' OpenRouter requirement.

**Terminal: Bash or zsh, ordinary user. Paste this command alone, press Return, then paste your Kilo key at the hidden prompt and press Return again.**

```bash
IFS= read -r -s KILO_API_KEY
```

**Terminal: PowerShell, ordinary user. Paste this command alone, press Enter, then enter your Kilo key at the hidden prompt.**

```powershell
$secret = Read-Host 'Kilo API key' -AsSecureString
```

After the hidden prompt returns, make the key available to OMP:

**Terminal: Bash or zsh, ordinary user, same window.**

```bash
export KILO_API_KEY
```

**Terminal: PowerShell, ordinary user, same window.**

```powershell
$bstr = [IntPtr]::Zero
try {
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
  $env:KILO_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
  if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  if ($secret) { $secret.Dispose() }
  Remove-Variable secret,bstr -ErrorAction SilentlyContinue
}
```

Run a live one-message check. It can incur charges:

**Terminal: Bash or zsh, ordinary user, same window.**

```bash
omp --model kilo/anthropic/claude-sonnet-4.6 --no-tools --no-session --no-title -p "Reply with exactly: OMP_API_KEY_OK"
```

**Terminal: PowerShell, ordinary user, same window.**

```powershell
omp --model kilo/anthropic/claude-sonnet-4.6 --no-tools --no-session --no-title -p "Reply with exactly: OMP_API_KEY_OK"
```

**Expected:** `OMP_API_KEY_OK` and a successful process exit. Then use `omp --model kilo/anthropic/claude-sonnet-4.6` for interactive work in that terminal.

**Stop:** HTTP 401 or `INVALID_TOKEN`, even if the error text says to sign in again. The gateway rejected the key; this is not a requirement to sign in to Anthropic.

**Recovery:** Get a valid replacement Kilo key from the account owner. Do not paste it into a chat or command argument. Close the terminal after work to discard its environment, or use `unset KILO_API_KEY` in Bash/zsh or `Remove-Item Env:KILO_API_KEY -ErrorAction SilentlyContinue` in PowerShell. Already-running child processes can retain an inherited copy.

## Check a separately opened terminal

Open a new terminal independently of the one where you entered the key. It should report `MISSING`. A child shell started from the first terminal can inherit its environment, so it isn't an independent check. `SET` alone doesn't mean the key was saved in a profile or leaked.

**Terminal: Bash or zsh, ordinary user, independently opened window.**

```bash
if [ -n "${OPENROUTER_API_KEY:-}" ]; then printf 'SET\n'; else printf 'MISSING\n'; fi
```

**Terminal: PowerShell, ordinary user, independently opened window.**

```powershell
if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) { 'MISSING' } else { 'SET' }
```

**Expected:** `MISSING` in an independent window. Enter the key again there when you need another model turn.

**Stop:** If a new terminal window unexpectedly shows `SET`, find out why before describing the key as process-only.

**Recovery:** Check how the terminal started and whether an approved parent supplied the variable. Don't put profile or environment values in evidence. Revoke the key if you find an exposed or unauthorized saved copy.

## End access when you finish

Close the terminal to remove its process environment, or remove the variable from the current process:

**Terminal: Bash or zsh, ordinary user.**

```bash
unset OPENROUTER_API_KEY
```

**Terminal: PowerShell, ordinary user.**

```powershell
Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
```

**Expected:** The presence-only check now reports `MISSING` in that process.

**Stop:** A child process may still have an inherited copy. Removing the variable doesn't revoke the provider key.

**Recovery:** Close those processes. Revoke the provider key if access must end everywhere or the value was exposed.

Record the provider/model identity, observed `omp/<semver>`, whether the check showed `SET` or `MISSING`, and redacted run outcomes. Never save any part of the key. The current process environment limits persistence but doesn't shield it from other processes under your account.

Sources: [OpenRouter key settings](https://openrouter.ai/settings/keys), [Sonnet 4.6 through OpenRouter](https://openrouter.ai/anthropic/claude-sonnet-4.6), [OMP provider environment variables and credential precedence](https://github.com/can1357/oh-my-pi/blob/v18.6.1/docs/providers.md), [OMP model resolution](https://github.com/can1357/oh-my-pi/blob/v18.6.1/docs/models.md), and [Kilo Gateway authentication](https://kilo.ai/docs/gateway/authentication).
