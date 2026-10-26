# Reference: Module 0 and the initial course setup

**Version:** 11 · **Frozen on:** 2026-10-05 · retains the single-OMP/OpenRouter, ungraded, individual long-document contract and rolling latest OMP; replaces the full n8n Assistant stack with staff-prepared n8n and external task runners
**Scope:** Module 0 learner material, shared setup contract, five platform setup paths, and the acceptance machinery that decides them
**Supported paths:** native Windows PowerShell, Windows with WSL 2 and Ubuntu for course work, macOS, Ubuntu, Arch Linux
**Artifact type:** procedural learner material and technical acceptance checks. Executable checks verify bounded behavior; they do not grade human capability. Time-to-first-checked-artifact and learner failure rates remain unmeasured until observed with people.
**Changes are recorded in `AMENDMENTS.md`.** The research survey below is retained; the active requirements in §§3–8 supersede the obsolete multi-tool setup, thin-case examples, and assertions that a public practice checker is secret.

---

## 1. The need, stated precisely

A capable professional arrives with the laptop they will use for the course. Its shell, runtimes, course files, credentials, and AI tools may be missing, stale, split across two environments, or working only in the one warm terminal where they were installed. They need one path that takes that machine to a visible, restartable state, and then uses it to complete a first bounded AI-assisted task whose acceptance they cannot quietly move.

This prevents five failures:

1. an installer reports success but the command cannot be found in a new shell;
2. a key works once because it was pasted where it will persist, or exposed in history;
3. Windows and WSL tools or files mix until neither environment is reproducible;
4. an AI tool reports it wrote a file when no acceptable file exists;
5. setup consumes the session and produces no evidence the learner can do the work.

**Done:** after following exactly one platform path, the learner opens a fresh shell, runs the course check, proves the required tools and repository work in that process, loads credentials without printing or persisting them, produces Module 0's checked communication artifact inside the bounded workspace, records the responsibility screen and frozen direction, observes their own falsifier fail, and knows the exact stop or escalation condition for anything still unavailable.

### 1.1 A reframing the need statement hides

The need as usually stated is "write good setup instructions." That framing has a measured failure rate. Mirhosseini and Parnin (ESEC/FSE 2020, *Docable*) executed 14,876 code blocks from 616 setup tutorials in fresh VMs: 13% ran naively, 26% with auto-patching, 52.3% with hand annotation — and **0 of 40 hand-annotated tutorials reached a final working setup**. The single largest error class was `E127 command-not-found` at 2,393 blocks, which the authors read as earlier setup steps having silently failed.

The correct framing is therefore: **a setup path is a program, and an unexecuted program is a broken program.** Prose quality is necessary and nowhere near sufficient. Any claim that five platform paths work, made without executing all five on clean machines, should be read as a prediction that at least one is broken right now. This Reference is built around that inversion, and §6 Class A exists only because of it.

### 1.2 What this module is not permitted to assume about its own author

Nathan and Petrosino (2003, n=48) found that domain experts significantly underestimate novice completion time, that intermediates predict better than experts, and that telling experts about the bias does not improve their predictions. Consequently: **no time budget in this document is authored.** Every duration below is either measured and cited, or marked `UNMEASURED` with the protocol that would settle it. An authored estimate presented as a budget is a defect under §6 D3.

---

## 2. Field survey

Fourteen systems, selected because each one settles a specific decision. Confidence is marked where it could not be verified from a primary source.

**2.1 Docable — Mirhosseini & Parnin, ESEC/FSE 2020** *(verified, primary)*. Executes tutorial code blocks in fresh VMs matched to the tutorial's OS, with assertions held in an external `steps.yml` selected by matching prose *above* each block — so the document cannot satisfy its own test. Asserts on **output**, not exit code, with the reason stated: some correct commands print to stderr. **Breaks:** Linux/SSH/VM only, so four of our five platforms are untestable by it; annotation cost is ~19 per tutorial. **Take:** the external stepfile, the output-not-exit-code rule, and the 0/40 number as our calibration baseline.

**2.2 Salerno, Treude & Thongtanunam, arXiv:2404.14637v3** *(verified, primary)*. The only think-aloud study of this exact audience: 24 sessions, 18 novices, 7 tools, plus 144 survey responses. Isolates **"Lack of Installation Progress Feedback" as its own failure category** (9/24 sessions) — beginners cannot distinguish hung from slow, or warning from error: *"I don't know if it's finished or not, how can I check?"* All four version-incompatibility cases were Apple Silicon. **Breaks:** students, one institution, no per-platform rates. **Take:** silence is the failure. Every step that is slow or quiet must state its expected duration and expected output volume before the learner runs it. Also: what learners *recall* blaming (unclear instructions, 88/144) is not what actually stopped them (process complexity, 14/24) — do not design from complaints.

**2.3 The Carpentries — `swc-installation-test-2.py`** *(verified)*. The strongest prior art for a learner-run, learner-unauthored check, and the only one designed for **bootstrap order**: stdlib-only, running on a machine where nothing is installed yet. Detects the OS with `platform` rather than asking the learner to self-identify, resolves failures through a `(system, package) → remediation URL` map, and uses OR-logic (`virtual-editor` passes on any of six editors) to test capability rather than brand. **Breaks:** unmaintained, not linked from the live install page, no fresh-shell check, no machine-readable output, hand-forked per cohort. **Take:** stdlib-only bootstrap design, auto-detected platform, and a remediation pointer on every failure.

**2.4 Degani & Wiener, *Human Factors* 35(2), 1993 (NASA CR-177549)** *(verified, primary)*. Guideline #1 is the most transferable rule in the survey: *checklist responses must portray the value or status of the item, not "checked" or "set"* — because *"'checked' and 'set' can be said too easily without any sound verification"* (ASRS 76798). Guideline #6: most critical items first, before interruption. Guideline #8: an explicit completion call. Names the real failure mode, **short-cutting**: collapsing several challenges into one response. **Breaks:** its core mechanism is two-operator challenge/response; a solo learner has no partner. **Take:** every verification response is a printed value compared against a shown exemplar — never a checkbox, never a learner-typed "PASS". The absence of a second operator is the argument for the executable check: the machine is the second crew member.

**2.5 The Rust Book ch. 1.1 + rustup** *(verified)*. Names an exact success string (*"Rust is installed now. Great!"*), gives expected output as a template with variable parts marked, and separates "installed" from "works" with a compile-and-run. **Take:** the exact-string success signal and the marked-variable output template.

**2.6 Flask's installation page** *(verified, negative exemplar)*. Lists commands with no expected output, no verification, and no failure branch. **Take:** what not to ship.

**2.7 Homebrew `brew doctor` / `diagnostic.rb`** *(verified)*. Broad environment diagnosis, but famously noisy: warnings that are almost always benign train users to ignore the tool. **Take:** a check that cries wolf is worse than no check. This is the argument for a three-state verdict (§4.4).

**2.8 Microsoft WinGet Configuration + Install WSL** *(verified)*. Declarative YAML with a first-class assert/apply split and idempotent resources. **Breaks decisively for us:** documented best-effort semantics — *"the configuration file will continue to run… even if some of the assertions or resource dependencies fail"*, leaving the learner to detect failures afterward. A partially configured machine plus a self-service detection burden is worse than a clean stop. **Take:** the assert/apply split; reject the partial-application semantics.

**2.9 Chef InSpec** *(verified)*. A cross-platform executable specification of a machine's desired state, with a human-readable control language and machine-readable output. **Take:** the idea that the environment specification is itself an artifact under version control, and that its output has a schema.

**2.10 `flutter doctor`, Docker `com.docker.diagnose check`** *(verified)*. Three-state output, per-check identifiers, and — in flutter's case — a next action per failure. **Take:** stable check IDs and next-action strings.

**2.11 `mise`, and Julia Evans on PATH** *(verified)*. Both target the activation gap: the tool is installed and still not found, because a shell did not load what it needed. **Take:** the fresh-shell check is not a nicety; it is the check for the single most common failure.

**2.12 Advent of Code and the CTF flag model** *(verified/partial)*. Per-participant input; the participant submits only the answer; the verdict is computed where the participant cannot reach. Because the flag is a **byproduct** of the work rather than a description of it, the entire challenge description and rubric can be published without weakening the check. **Breaks:** verifies the answer, not the method; and it needs somewhere to hold a secret — **which does not exist on the learner's own laptop.** AoC retired its global leaderboard for 2025 under capable models: verification survived, only speed ranking died. **Take:** never try to hide a secret on the learner's machine. Publish everything that is on the machine; hold the deciding artifact off it.

**2.13 okpy locked tests, GitHub Classroom autograding** *(verified from source)*. okpy's `locking.py` HMACs answers with `digestmod='md5'` keyed on **the assignment name** — a public string shipped in the same file, so a local model can enumerate short answers and match instantly. GitHub's own position on autograding tampering is *"we would not prevent student from editing but we can detect if a student change that."* **Take, stated falsifiably:** the secret must not be derivable from anything shipped to the learner. When the grader sits in the learner's tree, the honest design is not prevention but restore-over-detect plus a verdict computed elsewhere.

**2.14 METR, ImpossibleBench, "Building to the Test"** *(verified, primary)*. The decisive evidence for this module's architecture. METR: reward hacking occurred in **39/128 runs (30.4%) when the model could see the scoring function versus 8/1087 (0.7%) when it could not — a 43× difference**; on one task family, 21/21 = 100%; human baseliners hacked once. Prompting is not a fix: four honesty prompts left hacking at 70–95%, and o3 answered "no" to "does this plan adhere to the user's intention?" in 10/10 cases after producing a hacking strategy. ImpossibleBench: hiding tests drops cheating to near zero but degrades legitimate performance; **read-only access restores performance while preventing modification**. An explicit abort affordance cut hacking 54%→9% (GPT-5) and 49%→12% (o3); allowing multiple submissions *raised* it 33%→38%. Building to the Test: with a hidden oracle callable in-loop, every run scored 221–222/222 while up to 4 of 4 subsystems were dead. **Take, as three hard constraints:** (1) the deciding oracle's source must never sit in the learner's working directory; (2) acceptance must be two-part — behavioral *and* provenance; (3) give the learner a formative check that is **not** the deciding oracle, bound the retry budget, and provide an explicit "this looks impossible" escalation.

**2.15 RAID (ACL 2024), Liang et al. (*Patterns* 2023)** *(verified/partial)*. At a 5% false-positive operating point the best detector reaches 85.0% and most sit at 65–75%; a homoglyph attack costs Binoculars 41.9 points and Originality 75.7. Over 61% of TOEFL essays by non-native writers were flagged as AI-generated. **Take:** v1's refusal to accept a detector score as evidence is correct and well supported. It stands, now with citations.

### Measured numbers this Reference relies on

| Measure | Value | Source |
|---|---|---|
| Hand-annotated setup tutorials reaching a working setup | **0 of 40** | Docable §4.2 |
| Setup blocks executing naively | 13% (1,935/14,876) | Docable Table 1 |
| Largest error class | `E127 command-not-found`, 2,393 blocks | Docable Table 2 |
| Novices blocked by absent progress feedback | 9/24 sessions | Salerno Table 3 |
| Reward hacking, oracle visible vs hidden | **30.4% vs 0.7% (43×)** | METR |
| Prompting as a mitigation | leaves hacking at 70–95% | METR |
| Abort affordance as a mitigation | 54%→9%, 49%→12% | ImpossibleBench |
| Extra submissions as a control | raises cheating 33%→38% | ImpossibleBench |
| Simplified Technical English | task error rate 18%→14%, gains concentrated in non-native readers | Chervak, Drury & Ouellette, HFES 1996 |
| Words actually read on a page | ≤28%, "20% more likely" | Weinreich et al., ACM TWEB 2008 |
| Best AI-text detector at 5% FPR | 85.0%; most 65–75%; −41.9pp under homoglyph attack | RAID, ACL 2024 |
| Non-native essays falsely flagged | >61% | Liang et al. 2023 |

**Numbers that do not exist.** No published installation-failure rate, dropout rate, or setup-duration distribution for technical workshops. No instrumented time-to-first-value funnel for this kind of course. **Every setup-time and completion-rate figure in this document must therefore be produced by this module's own instrumentation, and is marked `UNMEASURED` until it is.**

---

## 3. Active execution and setup contract

1. Participants use Git, Python 3.12 or newer, a browser, an ordinary text editor, and the latest stable Oh My Pi release. The sole provider/model is **`openrouter/anthropic/claude-sonnet-4.6`**, with a participant-supplied process-local `OPENROUTER_API_KEY`. Node is a maintainer figure-build dependency, not a participant prerequisite.
2. OMP, Python, Git, credentials and course work stay in each platform's named shell. Native Windows uses its Python and `docker.exe` directly from PowerShell; staff manage Docker Desktop's approved Linux-container backend without a separate Ubuntu shell for n8n. The separate WSL course route keeps course work in Linux home, not a Windows mount. Native Windows has both x64 and ARM64 official OMP assets; an unavailable native test host remains unobserved, not a missing-release claim.
3. Resolve the latest stable release, then download the selected binary and `SHA256SUMS.txt` from that tag. Verify the unique exact-filename digest before installing, making executable, or executing those bytes. Preserve a conflicting installation and every failed download.
4. Put the verified user binary on PATH through explicit, non-secret configuration. Verify it again in a newly opened terminal without repairing PATH in that verification step. Preserve existing profiles and append idempotently. OS installation and managed-device approval remain with the device owner.
5. Hidden key entry runs as one isolated command; export follows separately. Print SET/MISSING only. Do not put a key in argv, profiles, reports, screenshots or committed files. An independently opened terminal normally lacks the previous terminal's process-local key; a child may inherit it.
6. Preserve existing related checkout changes. Inspect an unrelated occupied path and stop; never reset, pull, clean, or replace it automatically. Learner work and run evidence live in fresh external directories. Scoped LF checkout attributes preserve frozen source/control bytes across platforms.
7. Use `shared/run_omp.py` for actual calls. It fixes the provider/model, disables retries/fallback/cache warming and unrelated built-ins, isolates configuration, and exposes only the declared guarded tools. Runtime cwd is beneath isolated HOME so ancestor instruction discovery cannot import an external context file. This is a tool boundary, not an OS sandbox.
8. The launcher retains policy/config identity, raw OMP events, guard lifecycle and execution receipts, before/after snapshots, extracted response and result. Missing prerequisites exit 2; attempted incomplete/failed work exits 1. No output file or confident model sentence can turn a failed child into success.
9. `verify_tool_proof.py <proof-dir> <token-file> <evidence-dir>` requires the fresh exact `omp works <token>` disk content and a successful audited `course_write` with matching path and output hash. A hand-created or stale file does not prove tool use.
10. Keep local raw evidence outside the checkout; publish redacted staff summaries using `$HOME` and `$CHECKOUT`. Local policy receipts necessarily contain resolved paths. Never commit credentials or personal paths.
11. Before Module 7, staff prepare **n8n 2.41.5 and matching external task runners** from official images using `scripts/n8n_local.py`. The two-service configuration has no privileged container, Docker socket mount, Assistant sandbox, or search service. Staff own Docker installation, licensing, daemon access and effects on existing workloads. Preserve existing installs, contexts and data; never migrate a six-service installation automatically. Bind the editor to `127.0.0.1:5678`. A fresh approved project must be unused across containers, volumes and networks. The helper records its engine, project, private configuration and file hashes; lifecycle commands use only that identity and refuse inherited overrides or changed configuration. Prove real Code-node execution, local owner access, a saved blank workflow and persistence after stop/start without deleting volumes. Learners start the prepared environment, inspect status and use the browser. This is a later-project entry condition, not a new Module 0 objective.

## 4. Module 0 capability and invariant case facts

The new capability is getting a long document you can trust from AI: plan and test before any prose, one limited job per session, checks against references outside the draft, verified findings, targeted revision, and a send-or-hold decision kept by the learner. Installation is an entry condition, not a second mastery objective.

The supplied Harbor Depot → Field Clinic S-3 case keeps its invariant facts: request 40 water-treatment kits, baseline on-hand count 27, pen 4 custody rather than release, Ivo Marsh's release ownership, no assigned vehicle/approved permit/confirmed receipt, unknown supportability, and the Thursday/Friday 9:00 a.m.–5:00 p.m. paperwork window rather than pickup authority, with contact 555-0194. Since v9 they sit in six source files (request, count sheet, paperwork notice, release desk, yard board, clinic message), which add the stated weekly need, kit condition, paperwork examples, the three-step release requirement, no advance release dates, direct notification of the clinic clerk, and the clinic's five questions. The brief is for the Field Clinic S-3 supply team only. The provided changed-input fact changes the count to 19; it does not add movement authority.

The core preserves every stage: read the request, sources, and public checker; write `brief.md` (which carries the minimum screen) and `tests.md` before any prose; have OMP propose `outline-proposed.md`, correct `outline.md`, and freeze the plan; draft section 1 in its own session and read it against its quoted sources and receipts; draft the remaining sections one session each; run the checker on the 500–900-word `draft-v1.md` and execute a failing copy; list every number and code against the sources; run separate review sessions (tests, facts answered from the sources without the draft, reader actions, style); verify each finding into `review/r1/fixes.md`; revise only the named sections and confirm the rest are byte-identical; apply the changed count only where it is used and observe the original checker's expected stale-count failure; confirm `draft-v1.md` is unchanged; decide `READY TO SEND` or `HOLD`; leave a reconstructable handoff. Revision stops after two rounds. Keep original outputs and failed attempts.

The stretch asks a fresh session for the whole brief in one prompt, in a separate folder holding only the request and the sources, and compares that draft with the planned one.

### Timing and availability

The roughly three-hour session, the first-result goal of about the first hour, and the setup-duration ranges are **design targets, not measured performance or automatic gates**. Record actual elapsed time and assistance when a human pilot occurs. The 15 GB free-disk floor (25 GB for WSL) is a prerequisite check, not a prediction of completion time. No automatic paid retries are permitted.

Report native platform execution separately for macOS, Ubuntu, Arch, Windows PowerShell and WSL. A parser run or PowerShell-on-macOS replay is not native Windows evidence. Browser, terminal and assistive-technology observations must identify the actual surface used.

## 5. Public practice and technical acceptance

The case, practice checker and mechanical expectations are inspectable. A location outside the model's work root limits that model's tools; it does not make a repository file secret from its owner.

Technical acceptance uses the visible practice checker and human decision record. No separate hidden case is supplied; a documented HOLD is valid technical evidence when a prerequisite or decision condition is unresolved.

The checker is deliberately limited. It checks the brief's shape (title, 5–6 sections, 500–900 words), recognized polarity, quantities attached to their subjects, and unsupported promises. It cannot settle source applicability, tone, the responsible professional decision, or authorship. A recognized negated fact such as “No vehicle is assigned” must not fail because its shorter positive substring occurs inside it; a separate contradictory assertion must still fail.

## 6. Acceptance and negative evidence

Use meaningful behavior and integrity gates, not source-wording, incidental formatting, output-size, implementation-copy or mock-echo tests.

| Boundary | Required positive evidence | Required rejection |
|---|---|---|
| Official binary | Selected official digest before first execution; exact resolved version | Wrong/missing/duplicate digest, altered binary, conflicting destination |
| Fresh-shell setup | Supported Python/Git and verified OMP resolve after persistent configuration | Missing command, wrong pin/path, empty PATH component, absent prerequisites |
| Secret entry | Hidden input and process-only export; no value in output | Multi-command entry, persisted secret, exposed value |
| Checkout/work separation | Intended clone and fresh external work, unrelated changes preserved | Existing work destination, unrelated checkout, dangerous escape |
| Local n8n readiness | Staff-prepared two-service stack; loopback editor; external Code-node execution; owner access and saved-workflow restart persistence | Unapproved engine/licence change, occupied install/project, inherited overrides, changed configuration, privileged containers, wrong version/binding, lost existing state |
| Guarded execution | Real raw lifecycle, authorized tool joins, exact file readback and hashes | Missing/unready guard, outside path, missing instruction, stale or hand-created proof |
| Practice draft | Faithful source-supported brief, recognized negative facts, all quantity bindings | Contradiction, unsupported pickup/release, wrong subject/count, wrong audience |
| Planned drafting | Brief and tests before the outline; frozen plan hashes; one receipted session per section | Plan changed after drafting began, section file without a matching receipt |
| Review and revision | Findings from isolated sessions verified by the learner; only named sections change | Accepting a finding without a source, test, or rule; an unnamed section changing |
| Changed input | Original unchanged; correct revised count and expected old-checker failure | New authority, untraced material change, overwritten original |
| Falsifier | Actually executed wrong copy with named observed failure | Merely stated or invented failure |
| Publication | Generated public HTML, working resources, terminal/privilege/expected/stop/recovery labels | Missing path, unsafe link, unlisted staff artifact, copy button including output |
| Send decision | `READY TO SEND` or `HOLD`, with the source evidence behind it | Agent role-play, or a decision with no evidence behind it |

`tests/test_module_00.py` and the checker adequacy suite use disposable copies. Mutations must kill real behavior/safety boundaries. Shared runtime/publication tests own shared contracts; do not add duplicate prose assertions to every module. Reference and frozen case integrity remain checked. The reference digest changes only with an explicit amendment.

## 7. Authoring and evidence quality

Give each action its purpose, exact input/command, expected observation, observable stop and recovery. Use complete, calm sentences; define new terms at first use. Preserve learner agency and the distinction between a machine result and a professional decision. Do not ship curriculum-design rationale in learner pages.

Each evidence claim names its command, cwd, inputs/control hashes, actual status/output, elapsed time and provenance. Preserve the first failure and link its repair/recheck. Separate core, stretch, live-provider, platform, and accessibility lanes. Missing dependencies are blocked; unobserved performance is not measured. Synthetic receipts exercise verifier boundaries only and never count as live calls.

A technical reviewer may find defects without being a novice learner. An agent may operate a procedure without impersonating a learner. Score neither role by impersonation or a perfect-looking aggregate.

## 8. Drift and non-goals

Revalidate when the latest stable OMP CLI, extension API, context discovery, OpenRouter model/tool behavior, official assets, Python floor, OS shell or checkout path changes. Migrate launcher, guards, platform guides, proof checker and their consumers together; no legacy provider aliases or silent substitutions.

Do not add participant toolchains beyond Git/Python/OMP and the approved local n8n stack, an alternate agent runtime, provider fallbacks, a new installation framework, AI-authorship detection, or claims that local hashes resist an owner rewriting the entire evidence set. Preserve historical reviews/run records as historical, not current-platform or current-provider proof.

## 9. Rolling latest verification, 2026-10-05 UTC

The official latest-release API selected `v18.6.1`; this is an observation, not a course pin. The darwin-arm64 binary matched its release's `SHA256SUMS.txt` entry and API digest: `b5ca5cd17b8cc09ece36845988fd401f7d1002e1ab5b95600e0f328924246d52`. The authored macOS install block ran in disposable HOME/ZDOTDIR, saved `release.json`, verified the checksum before execution, and reported `omp/18.6.1`. An independently constructed login zsh resolved that installed binary through the saved profile.

The 280 setup checks covered Bash/zsh and PowerShell 7 fence parsing, all five release-metadata validators, optimized Python execution, unstable/malformed metadata, missing or duplicate assets, inconsistent download URLs, and macOS installer rejection before execution on invalid metadata, bad checksum, or conflicting existing bytes. Controlled fault cases replayed the previously verified official downloads; the positive macOS install used the real network. This is not native Windows PowerShell 5.1, WSL, Linux, or a GUI-terminal transition observation.

`verify-setup.sh` returned SETUP CHECK PASS with the actual version and process-local key presence. `shared/run_omp.py` then performed a real guarded read/write; `verify_tool_proof.py` accepted the exact fresh token, output path, and write hash with READINESS CHECK PASS. Separate latest-runtime runs exercised a bounded MCP read, a three-type Jev batch, and the full Copper Span dependency chain. Private evidence: `~/course-evidence/omp-latest-20261004/`. Historical setup campaigns remain unchanged.
