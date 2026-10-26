# Prose panel review — Technical beginner

Reviewer kind: language model
Role: Technical beginner
Module revision: Reference 49c5910af76e, panel round 1, 2026-08-14
Rubric: reference/REFERENCE.md section 6 Class F (eight dimensions, 0–4, acceptance 32/32)
Total: 23/32
Result: REJECT

> **This is not the review the Reference requires.** Section 6 Class F specifies a three-person
> panel — one technical beginner, one experienced cross-platform operator, one professional
> editor. This reviewer is a language model asked to read from that seat. It did not experience
> confusion, did not run a command on any of the five platforms, and cannot stand in for the
> person. Every claim about what a learner would not know is inference from the text.
> Class F remains UNMEASURED until three people score it.


## Scores

| Dim | Dimension | Score | Cited sentence | Where |
|---:|---|---:|---|---|
| 1 | Sounds like someone who has done the task | **3** | - `XAI_API_KEY: SET in current process`, and the key value itself printed nowhere; | `README.md:70` |
| 2 | States purpose before action | **3** | ## 5. Clone and inspect the course | `platforms/arch-linux.md:122` |
| 3 | Ordinary complete sentences | **3** | **You should see:** a version of `5` `1` or higher in the `Major` and `Minor` columns. | `platforms/windows-powershell.md:22` |
| 4 | Exact, concrete detail without display | **2** | **You should see:** a maintained macOS release, `arm64` or `x86_64`, at least 15 GB free, and either a Command Line Tools path or no path yet. | `platforms/macos.md:16` |
| 5 | Treats failure as diagnostic evidence | **3** | **Stop here if:** a command path from the earlier steps is missing, `TOOL PROOF PASS` does not appear, n8n does not answer, `obsidian-vault-config` is | `platforms/macos.md:393` |
| 6 | No generic encouragement, hype, throat-clearing, or repeated summary | **3** | Setup runs in the same ten stages on every platform: | `README.md:44` |
| 7 | Preserves the learner's agency | **3** | For this case, use only the supplied source packet. The draft stays with named course participants, contains no personal data, and is never published. | `shared/MODULE_00_LAB.md:205` |
| 8 | Reads aloud without sounding generated | **3** | A tool saying “done” is not the same as a file on disk. A version string is not the same as an authenticated write. The checks make those differences  | `README.md:79` |

## Making-of findings

1. PUBLIC_RUBRIC.md:7 — 'A working environment is the entry condition for the session. It is not part of the result and is not scored here.' This explains a scoping decision about the course's assessment scheme. Apply the discriminator: a mentor teaching the same craft would never say it, because there would be nothing to score and no session. F2 violation.
2. PUBLIC_RUBRIC.md:30 — 'Additional practice runs on your own machine cannot change either one.' The whole Reassessment section (lines 28-30) is course grading policy: what is preserved, what is reassessed, against which rubric. None of it survives outside an institution. F2 violation.
3. shared/MODULE_00_LAB.md:304 — 'Passing the practice check does not pass the module, and failing it is evidence, not a verdict.' The first clause is meta-commentary about the course's own assessment machinery. The real lesson underneath it ('a mechanical check passing is not the same as the work being acceptable') would survive a book or a mentor; 'does not pass the module' would not. Reframe rather than cut.
4. shared/MODULE_00_LAB.md:3 — 'You will use one AI command-line tool to draft a short email from a supplied set of facts. You will check that draft yourself, prove your own check is capable of failing, change one supplied fact and rerun, and decide whether anyone may read the result.' This is 'what we'll cover' — the artifact previewing the artifact. Each clause is a heading in the same file.
5. README.md:44-55 — 'Setup runs in the same ten stages on every platform:' followed by the ten section headings. A table of contents for documents the reader has not opened. Meta-commentary about the shape of the material, not instruction.
6. README.md:3 — 'Plan for 1–3 hours of machine setup, then one three-hour class session.' Session scheduling. Marginal: the reader genuinely needs to reserve time, and the Reference (§4.6) fixes the 180/120 split, so this is Reference-mandated logistics rather than an authoring lapse. Flagged, not charged.
7. shared/MODULE_00_LAB.md:9-25 — the Timebox table allocating minutes per part is session scheduling by the discriminator's own definition. Also Reference-mandated (D3 requires the lab timebox to sum to 120), so it cannot be a deduction against this Reference; noted so the tension is visible rather than hidden.
8. Not a violation, examined and cleared: macos.md:79 ('The append starts with a blank line on purpose: when the last line of a file has no newline after it, appending joins two commands into one broken line…') and arch-linux.md:116 explain why the guide's own command is shaped that way, not why the course is. That is craft — the missing-trailing-newline trap is real outside any course — and it should stay.

## Sentences that read as generated

1. README.md:79 — 'A tool saying “done” is not the same as a file on disk. A version string is not the same as an authenticated write. The checks make those differences visible.' Two parallel 'X is not Y' clauses plus a summarizing third: the antithesis triad.
2. shared/NEXT_MODULE.md:9 — 'A tool reporting "done" is not a file on disk, and a fluent sentence is not a verified one.' The same figure, doubled inside one sentence.
3. shared/TROUBLESHOOTING.md:12 — 'A tool saying "done" is not evidence.' Third instance of the same construction in a third file.
4. shared/ACCESSIBILITY.md:3 — 'Reading a screenshot aloud is not equivalent to operating the control.' Fourth instance, fourth file.
5. shared/MODULE_00_LAB.md:304 — 'failing it is evidence, not a verdict.' Antithesis used as an aphoristic closer.
6. platforms/macos.md:303 — 'Everything that survives a restart is configuration; everything that does not is a secret you re-enter on purpose.' Balanced-semicolon aphorism that instructs nothing and is not true as a general claim; the actual instruction is the preceding sentence, 'Quit Terminal completely and reopen it.'
7. platforms/ubuntu.md:289 — 'A tool that works only in the terminal where it was installed is not installed.' and platforms/windows-wsl.md:281 — 'A tool that only works in the window where it was installed is not installed; this is where that shows up.' The same sentence opening the same section in two guides, differing by two words.
8. shared/MODULE_00_LAB.md:325 — 'A check that has never failed tells you nothing.' This is REFERENCE.md:221's governing principle ('a check that has never failed proves nothing') transplanted into learner prose. It is redeemed by the two sentences after it, which do instruct, but it arrives as a design-document epigram.
9. platforms/windows-wsl.md:248 — 'Nothing appears; that is the point.' Fragment-adjacent emphasis clause. Mild; the surrounding paragraph earns it.

## Verifications that assert rather than observe

1. platforms/macos.md:60 — 'Confirm it names the `Homebrew/brew` repository on GitHub, that it targets macOS, and that it installs into `/opt/homebrew` on Apple Silicon or `/usr/local` on Intel.' Three assertions about a several-hundred-line script, with no line number, no search string, and no exemplar of what any of the three looks like. The same instruction recurs at ubuntu.md:60, arch-linux.md:170, windows-wsl.md:101, windows-wsl.md:197 and windows-powershell.md:194. This is the module's own defence against Reference invariant 4 (no blind remote execution), and for the stated audience it resolves to pressing q and asserting. windows-powershell.md:200 is the only one that supplies an exemplar ('a PowerShell script whose download URL points at `github.com/aaif-goose/goose` and which names `windows` and `x86_64`') and is the model the other five should follow.
2. platforms/arch-linux.md:318 — `printf 'obsidian_vault_path=%s\nobsidian_file_count=%s\n' 'the path Obsidian shows' 'the count Obsidian shows' > "$run/obsidian.txt"`. Run verbatim, this records the literal words 'the path Obsidian shows'. Nothing downstream validates it: step 10 (arch-linux.md:338) cats the file straight into the report. The learner asserts, and the assertion is never compared with anything.
3. platforms/windows-wsl.md:357 — the placeholder values `'1234'` and `'\\wsl$\Ubuntu\home\yourname\course\AI_Harness_Bootcamp'` are written as the observed record, and the 'You should see' at line 364 ('a recorded vault path that ends in `course\AI_Harness_Bootcamp`') is satisfied by the placeholder itself. Step 10's gate at line 381 is `test -s`, non-empty. A learner who pastes the block unchanged passes the Obsidian check without looking at Obsidian.
4. platforms/windows-powershell.md:385-386 — `Read-Host 'Vault name Obsidian shows'` and `Read-Host 'File count Obsidian shows'`, validated at line 415 by `-notmatch 'AI_Harness_Bootcamp'` and `-notmatch '\d'`. Any typed string containing that name and any digit passes. Better than the two above because it must be typed, but still a learner-typed claim rather than a printed value compared against an exemplar (Reference §2.4, Degani & Wiener guideline 1).
5. platforms/macos.md:374 — `IFS= read -r obsidian_files` records a file count that is never compared to anything. macOS partly redeems this at lines 381-385 by testing for the `.obsidian` directory, which is a real machine-side observation, and the accompanying sentence at line 389 says so honestly. Ubuntu is the only path that fully closes the loop: ubuntu.md:385 computes the expected count from the clone and ubuntu.md:398 refuses to write the record unless the two match. Ubuntu's treatment is the standard the other four should meet.
6. platforms/windows-wsl.md:22 — '**You should see:** a supported Windows build and at least 25 GB free.' 'Supported' is a judgment the learner is asked to make with no list of supported builds anywhere in the module. macos.md:16 has the same problem with 'a maintained macOS release'.
7. platforms/arch-linux.md:22 — '**Stop here if:** … package databases are in a broken state.' Step 1 runs no command that reports database state, so this stop condition asks the learner to certify something they were given no way to observe. Reference F4 requires every 'Stop here if' to name an observable condition.

## Evidence for the scores that were not deducted

platforms/windows-powershell.md:73-83. "Windows ships a placeholder named `python.exe` that opens the Microsoft Store instead of running Python. It sits in a folder called `WindowsApps` and is zero bytes long, so the path and the size tell you which one you have." Then the command, then: "**You should see:** a path like `C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python312\\python.exe` and a size of at least 90000 bytes." Then: "**Stop here if:** the path contains `\\WindowsApps\\` or the size is `0`. That is the Store placeholder, not Python. Open **Settings › Apps › Advanced app settings › App execution aliases**, switch off the entries named `python.exe` and `python3.exe`, close PowerShell, open a new window, and run the check again." This is the whole rubric in eleven lines: it names a failure that only someone who has been bitten by it knows exists, states the mechanism before the command, gives two numeric observables a stranger can read off the screen with no judgment involved, treats the bad result as information rather than defeat, and ends with a repair specific enough to follow without understanding any of it. Every other verification in the module should be measured against this one.

## Verdict

REJECT — 23/32 against a 32/32 bar. This is unusually good procedural writing; the deductions are specific, not atmospheric, and most are repairable without rewriting anything. Ranked by what would stop a learner soonest.

FIRST PLACE I WOULD BE STUCK, reading as the assigned persona: no file in the module tells me how to run a command block. I am shown fenced blocks of ten or more lines containing `if`, `else` and `fi`. Nothing says whether to copy the whole block and paste it once, paste line by line, or type it; nothing says not to type the ``` marks or the word `zsh`. The first mention of pasting anywhere in the module is macos.md:260 — step 7, credential entry — which presupposes I have been pasting whole blocks for six steps. That is a bootstrap gap of the Carpentries kind the Reference praises at §2.3, and it precedes every other finding here.

WHAT I WOULD NOT KNOW, IN ORDER OF APPEARANCE (unexplained on first use):
- "CLI" — README.md:24, "Codex CLI", and README.md:30, "The AI CLIs make short provider-billed proof calls." Never expanded anywhere in any learner file; I ran the grep.
- "shell" — README.md:11, "Windows, no Linux shell." Never defined in any learner file, though the entire module is about one.
- "repository" — README.md:21; "clone" — README.md:48 and the section-5 heading of macos.md:166 and arch-linux.md:122. Defined only on the PowerShell path (windows-powershell.md:124) and partly on WSL (windows-wsl.md:152).
- "PATH" — README.md:47. Defined at each guide's step 4 and at TROUBLESHOOTING.md:25, but the README uses it first and defines nothing. Reference F1 requires first use.
- "process" — README.md:70 "current process", macos.md:305 "new process". Never defined, and it carries the module's whole session-only-secret lesson.
- "package manager" — defined well at macos.md:46, undefined at TROUBLESHOOTING.md:9 and on the Ubuntu and Arch paths.
- "pager" — macos.md:60 and ubuntu.md:60 say "Press `q` to leave the pager" without saying what one is. windows-powershell.md:194 and windows-wsl.md:101 both explain it; the two Unix guides do not.
- Shell startup files — macos.md:79 writes to `~/.zprofile` and ubuntu.md:101 to `~/.bashrc` with no gloss. windows-wsl.md:75 gets it right ("the small files Ubuntu reads each time you open a terminal") and arch-linux.md:78 explains the mechanism.
- "sudo" and the invisible password — ubuntu.md:25 and :48 use `sudo` with no explanation that the password prompt shows nothing while you type. windows-wsl.md:42 and :83 explain both. On the Ubuntu path, the first thing that happens is a prompt that appears frozen.
- "prefix" (npm) — ubuntu.md:104-117 and arch-linux.md:104-118 build a whole stop condition on it, undefined. "root" — ubuntu.md:37. "TLS", "PPA" — ubuntu.md:87. "AUR" — arch-linux.md:22. "AppImage" — ubuntu.md:209. "elevation" — windows-powershell.md:47. "port" — TROUBLESHOOTING.md:19. "health endpoint" — ubuntu.md:349, ACCESSIBILITY.md:69. "absolute path" — README.md:68, ubuntu.md:372.
- "sandbox" — MODULE_00_LAB.md:399 requires the learner to write down "What the product around it did (the command-line tool, its sandbox, its file writing)". The graded deliverable asks for an analysis of a term the module never defines. PUBLIC_RUBRIC.md:18 compounds it by grading "model output, product surface, harness control, and human decision" with no gloss on three of the four.

WHERE I COULD NOT TELL WHETHER IT WORKED: macos.md:104 (three brew installs, no expected output); macos.md:200 and ubuntu.md:158 and arch-linux.md:152 and windows-wsl.md:184 (npm global installs, no expected output — only windows-powershell.md:160 supplies one); ubuntu.md:179 and arch-linux.md:179 and macos.md:220 (the goose installer run has neither a duration annotation nor an expected result, though windows-wsl.md:204 and windows-powershell.md:204 both supply one, so Reference A9 is met unevenly).

WHERE I COULD NOT TELL WHETHER WAITING WAS NORMAL: everywhere, past sixty seconds. Five guides promise "Silence for a minute at a time is normal"; no file anywhere states a threshold past which silence means something is wrong, and TROUBLESHOOTING.md's fifteen-row table has no row for it. Against Reference §2.2 — the one failure category the survey isolates as its own — this is the module's largest gap.

WHERE I WOULD FEAR I HAD BROKEN MY LAPTOP: arch-linux.md:52, "Running the rest against a half-replaced kernel or C library produces errors that no later step can explain" — the condition is a package list that scrolled past during a forty-minute upgrade, and no way to recover it after the fact is given. And macos.md:92, which appends to a login file I have never been told exists.

WHAT TO FIX FIRST, IF THE PANEL IS RECONVENED: (1) add a "how to run a command block" paragraph before step 1 of all five guides; (2) add a hang threshold and a TROUBLESHOOTING row for it; (3) give macos.md:60, ubuntu.md:60, arch-linux.md:170 and windows-wsl.md:197 the exemplar sentence that windows-powershell.md:200 already has; (4) make the Obsidian record on the Arch and WSL paths a compared value the way ubuntu.md:398 does; (5) fix README.md:70 to quote a string that some script actually prints; (6) cut PUBLIC_RUBRIC.md:7 and the Reassessment section, and reframe MODULE_00_LAB.md:304; (7) stop giving away the step-5 screen and the step-12 prediction in the instructions for making them.
