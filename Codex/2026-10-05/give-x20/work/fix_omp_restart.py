from pathlib import Path

root = Path('/home/dow_admin/Documents/AIHB_OCT_2026/AI_Harness_Bootcamp_2/module-00-setup')
updates = {}
for path in sorted((root / 'platforms').glob('*.md')):
    text = path.read_text()
    old = '**Restart your terminal after installing OMP so PATH changes take effect.** Follow any PATH instructions the installer prints, then close and reopen your terminal before starting OMP or entering your API key.'
    new = '**Restart your terminal after installing OMP so PATH changes take effect.** Follow any PATH instructions the installer prints, complete Step 4 in this window, then close and reopen your terminal as directed in Step 5 before starting OMP or entering your API key.'
    assert text.count(old) == 1, path
    text = text.replace(old, new)
    old = '**Recovery:** Check the installer\'s error or PATH instructions, then reopen the terminal and try `omp --version` again.'
    new = '**Recovery:** Check the installer’s error. For `omp` not found, use [PATH recovery](../shared/TROUBLESHOOTING.md#if-omp-is-not-found-after-restarting), then reopen the terminal and try `omp --version` again.'
    assert text.count(old) == 1, path
    updates[path] = text.replace(old, new)

path = root / 'shared/TROUBLESHOOTING.md'
text = path.read_text()
heading = '## If omp is not found after restarting\n'
assert heading not in text
section = '''## If omp is not found after restarting

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

'''
marker = next(line for line in text.splitlines() if line.startswith('## ') and line != '## Choose the next action from the observed failure')
updates[path] = text.replace(marker + '\n', section + marker + '\n', 1)
for path, text in updates.items():
    path.write_text(text)
    print(path.relative_to(root))
