# AIHB_OCT_2026 — Reformation

**Serves oracle:** S02, S05, S06, S07, S09, S12, S13, S19, S20, S21, S24, S26

This course is in its own repository: <https://github.com/TheHolofex/AIHB_OCT_2026>. The standard checkout is `~/Documents/AIHB_OCT_2026`. You'll find the course sources, publishing tools, and required reference files here; you don't need a parent checkout.

## Course identity

Reformation is an **ungraded bootcamp** for a **professional domain user** doing accountable AI-assisted work without more operating complexity than the work needs. It builds professional AI-user and **harness operator** skills, not builder or software-engineering skills. Exercises produce work and observations, not learner scores or qualification decisions.

A harness is everything around a model that shapes and records its work: direction, context, sources, tools, permissions, working artifacts, saved controls, feedback, checks, and traces. The learner sets limits on the model's behavior, configures supplied controls, inspects evidence, and owns consequential decisions. An **adapter** builds and protects the executable mechanics and supplies each module's case. A builder owns APIs, MCP, retrieval pipelines, agent runtimes, and deployment.

The core targets a **nondeveloper** who can use workplace files and applications and inspect plain-language configuration. A ready accessible environment, checked in advance, supplies the mechanics.

The learner course is published under [`site/`](site/). Existing Markdown in [`AI_Harness_Bootcamp_2/`](AI_Harness_Bootcamp_2/) is maintainer source, not a second learner reading path. [`MISSION_THREAD_SCENARIOS.md`](MISSION_THREAD_SCENARIOS.md) holds the independent case specifications. [`evidence/exercise-runs.json`](evidence/exercise-runs.json) records observed exercise outcomes and explicit unverified lanes; design budgets are not pilot evidence.

## Core promise

The first-result target is about an hour to a frozen plan and a first AI-drafted section checked against its sources. It's a design target, not a measured promise about how long learners take. Before releasing anything consequential, the learner applies a minimum responsibility screen. Across the core, the learner gets a long document they can trust from AI, verifies sources, controls context, operates MCP tools under limited authority, decides with typed questions, orchestrates a bounded OMP agent team, configures and compares decision-model patterns inside OMP, has an agent write a spreadsheet, controls hallucinations through structured checks and independent agent review, and transfers the method.

The core runs on **four teaching days, Monday through Thursday, instructor-led and hands-on throughout**. Most modules take about three hours, including Slope Brief and Cold Foundry. Chalk Line takes about two and a half hours; Night Desk takes a little over two hours. These are rough estimates, not measured times. Each module has one outcome and its own supplied case, and produces **one evidence bundle per module**.

The day order, with each module's case, is:

| Day | Cases, in order |
|---|---|
| Monday | North Shelf (00), Cold Lantern (01) |
| Tuesday | Ledger Pike (02), Kiln Hold (03), Chalk Line (04) |
| Wednesday | Copper Span (05), Blue Gauge (06), White Rack (07) |
| Thursday | Slope Brief (08), Night Desk (09), Cold Foundry (10) |

The clocks and break points are in [COURSE_MAP.md](COURSE_MAP.md).

## Target sequence

| ID | Case | Module | Primary capability |
|---:|---|---|---|
| 00 | North Shelf | Get a long document you can trust from AI | Screen responsibility, plan and test a long document before any prose, have AI draft it one section at a time from six sources, check it against references outside it, revise only what's flagged, and decide whether to send it. |
| 01 | Cold Lantern | Verify sources and outputs | Produce and challenge research/source work with independent evidence. |
| 02 | Ledger Pike | Build and control a reusable second brain | Direct automatic AI judgments into source-traceable provisional knowledge, prove saved-rule loading and fresh retrieval, and correct a subsequent preserved revision through source-backed feedback. |
| 03 | Kiln Hold | Operate MCP tools under limited authority | Connect a supplied MCP server, research a folder of notes, check the assistant's markings against the written rules, prove each limit including actions the model never tries, and remove the connection with proof. |
| 04 | Chalk Line | Decide with typed questions | Decompose a desk decision into atomic typed questions, run a model once as a read-only decision function, validate and measure its answers against frozen labels, and route in code with gates set from the measurement. |
| 05 | Copper Span | Orchestrate an OMP agent team | Decompose independent work and dependent joins, accept source-bearing native child results, and recover partial failure without discarding valid work. |
 | 06 | Blue Gauge | Use Jev inside Oh My Pi | Use Jev inside Oh My Pi to configure and compare four decision-model patterns, choosing how answers become routes, priorities, and calls to record lookup, deterministic record comparison, or human queue. |
| 07 | White Rack | Automate a spreadsheet with an agent | Connect a local n8n AI Agent to OpenRouter with the learner's key, have it write a spreadsheet from the supplied batch, download that file, and check it against the source lots. |
| 08 | Slope Brief | Control hallucinations | Run three typed Jev checks across a whole brief, then independent agent reviews; correct only what the evidence supports, and keep unknowns visible in the human decision. |
| 09 | Night Desk | Constrain agent behavior | Enforce a live agent's declared tool boundary and distinguish observed denial from a prohibited call never attempted. |
| 10 | Cold Foundry | Stand up and package a local uncensored AI | Stand up the pinned uncensored model on the learner's own laptop under OMP, prove a live loopback-only interaction, stop and restore it, package the supporting kit of instructions and controls (weights excluded) so a fresh-terminal structure check passes, and close out by separating live runtime proof from structure-only evidence. Thursday's session is individual work. |

Cases and evidence bundles are **independent**: no gate relies on a product from an earlier module. Skills build on one another, but earlier skills are assumed rather than retaught as new objectives. The authoritative sequence and supplied inputs are in [COURSE_MAP.md](COURSE_MAP.md). Outcomes are in [LEARNING_OBJECTIVES.md](LEARNING_OBJECTIVES.md). [AUTHORING_GUIDE.md](AUTHORING_GUIDE.md) defines the module contract.

### Module 02 mastery

Using verified sources and bounded direction, control a learner-started AI judgment → knowledge build → fresh retrieval chain to create source-traceable reusable knowledge under an explicitly loaded saved instruction, then direct a meaningful correction in a new preserved revision.

Module 01 already established source checking as a quality bar, and bounded direction is also an earlier skill. Module 02 adds saved-rule load proof, controlled automatic AI handoffs, persistent knowledge, and correction. The supplied helper runs a fixed judge → build → freeze → retrieve chain after one learner start; independent human source inspection can occur during or after processing and never unlocks a pass. AI-processed knowledge and machine receipts are provisional, not human approval. Its separate Ledger Pike case keeps all forty DN sources. Bounded multi-agent orchestration belongs to Module 05; checking a received local-model package from a fresh copy remains Module 10's.

Each complete run uses three paid sessions: judgment, build, and fresh retrieval; freezing is a local helper operation between build and retrieval. The v1 and v2 runs use six paid sessions in total. Each judging pass actually reads all forty originals. Only the helper writes the generated, immutable versioned Knowledge notes, judgment records, and navigation. The learner examines saved judgments and original source support independently, writes the observed correction in plain `Feedback.md`, and starts v2 without editing generated Knowledge. Test the missing-rule stop on v1 before restoring the same rule for v2. Local checks establish bytes, provenance, and executed reads, not truth or improvement.
## Core and advanced boundary

The core includes bounded native OMP multi-agent orchestration and task-bounded automation. Module 05 uses read-only specialists and a reviewer with one coordinator-owned output, explicit dependencies, and bounded recovery. Module 07 uses one n8n agent and one spreadsheet-writing tool. Module 08 adds a bounded, human-started, read-only review ensemble: agents work in isolated sessions, and a person starts each fixed stage and owns acceptance. The core permits one narrow form of persistent knowledge: a local Markdown knowledge vault with learner-started automatic AI-processed provisional versions via the fixed supplied helper chain (judge → build → freeze → retrieve) and independent nonblocking source inspection. Neither AI success nor receipts represent human approval. Autonomous state updates, concurrent agent writes to shared knowledge, unattended or recursively expanding teams, adaptive flow, and custom retrieval infrastructure remain advanced work. The fixed helper workflow is explicitly allowed. Typed calibration belongs to Module 04, native teams to Module 05, ensembles to Module 08.

The core requires zero programming objectives. Dynamic checker implementation, API/MCP construction, custom RAG, agent-runtime development, and deployment remain adapter or builder work.

## Evidence and operating limits

- A person owns consequential acceptance, release, refusal, authority expansion, and residual risk.
- A material acceptance uses independent evidence from a source, deterministic check, or observed state. Public practice files are inspectable.
- Keep input and check identities the same across a comparison. Authored practice data, hashes, model authorship, and agent role-play don't prove how a person performed.
- Every learner makes decisions and operates the tools. A supported `no-use`, `no-release`, or `no-tool` decision is professional performance: record and study it, but don't treat it as proof of operation.
- Keep evidence of a material failure before repairing it. Finding the fault alone is held, not completed recovery.
- A file's presence or a written refusal doesn't prove execution. Keep actual tool calls, execution results, guard records, and disk snapshots. A technical replay proves only the behavior it exercised.
- `PASS` and `HOLD` describe technical checks and work decisions, not grades. Keep the failed attempt, fix its cause, and keep later attempts separate.
- A clean-session check proves only the behavior exercised. Module 10's fresh-terminal structure check, run from a new OMP conversation in a fresh terminal on the copied package, confirms the named fields and the presence of every listed file inside the kit; it does not execute instructions or show that the kit can be operated by another person.
- Each module bundle contains the artifact/state, decisive evidence, decision, claim result, failure or `HOLD`, scope boundary, and handoff.

## Authoritative files

- [Course map](COURSE_MAP.md)
- [Learning objectives](LEARNING_OBJECTIVES.md)
- [Authoring guide](AUTHORING_GUIDE.md)
- [`modules/core/`](modules/core/)
- [Mission-thread scenario memory](MISSION_THREAD_SCENARIOS.md) — staff specs for session projects; not a lab

Detailed scenarios, commands, forms, answer keys, fixtures, and platform procedures remain outside the core skeleton. Only allowlisted public pages and exercise files enter `site/`; staff references, historical reviews, and answer keys stay outside publication.

## Reader UI and manifest

The allowlisted instructional destinations share the local Sirocco reader. Edit `ui/course.css` for composition, `ui/course.js` for progressive enhancement, and `ui/theme-init.js` for the before-paint appearance preference. `ui/vendor/sirocco/` contains the byte-identical selected reference assets and their font licenses; course overrides belong outside that vendor directory. The reader requires no JavaScript bundler, package installation, CDN, or external font service.

`course.json` remains the single publication registry:

- Each page has a `kind`: `home`, `overview`, `lab`, `setup`, or `reference`. Each module declares `case_name`, `summary`, `nav_summary`, `outcomes`, and exactly one overview and lab page. Additional `reference` and `setup` pages may be registered per module. `summary` describes the work on the homepage card; `nav_summary` concisely names the main tool or skills beneath the case name in the desktop rail, mobile Course menu, and no-JavaScript navigation. `outcomes`, if present, is an object containing only optional `can` (string, any length) and/or optional `will` (list of any number of nonempty strings). The publisher accepts any length and count; it rejects wrong types or unknown keys. Keep these labels grounded in the module's distinct learning objectives.
- `guide` is optional on every non-home page. An explicit object with keys only `context_sections` and/or `optional_sections` (lists of unique nonempty H2 IDs) opts in; `{}` means all-H2 guided grouping. Other page kinds and omitted guide keep the authored hierarchy. Zero-step pages show “On this page” with no progress or reader controls. Module progress aggregation counts explicit steps on every non-home page belonging to the module. Unlabeled or non-shell fences are ordinary copyable text. A recognizable **Terminal:** label plus shell fence opts into a command card; adjacent Bash/PowerShell may pair.
- `ui_assets` explicitly maps each UI source to its published destination. Local CSS dependencies must also be declared. The publisher rejects missing dependencies, external CSS resources, unsafe paths, and unexpected output files.
- Figure entries accept SVGs and PNGs. PNGs use standard-library IHDR validation for intrinsic dimensions and the same full-size dialog as SVGs. Instructional PNGs live under the owning module's `shared/figures/`; their complete generation prompts and provenance stay unpublished in that module's `figures/RASTER_PROMPTS.md`, which is never listed in `course.json`. Keep authentic n8n captures under the owning module's `shared/figures/` as well. Do not feed screenshots or instructional PNGs into the SVG renderer.
- The homepage hero is the first `.webp` in `ui_assets`. Optional photo bands map an id to a declared `.webp` under the top-level `home_bands` key, and each id appears exactly once on the home page as an empty `<div data-photo-band="ID"></div>`. An unknown, repeated, unused, non-empty, or non-home placeholder fails the build. Bands render as decorative, lazy-loaded figures outside search, the outline, and the figure dialog. The publisher reads WebP dimensions from the file header and emits the intrinsic width/height. Fixed pixel sizes are not required for publication. Course-owned photographs live in `ui/images/`, not in the vendored Sirocco directory; `ui/images/ART_DIRECTION.md` holds their style guidance, exact prompts, encode budgets, and provenance for the shipped images.
- The generated `assets/search-index.json` contains instructional prose and heading targets, not fenced commands, raw exercise contents, staff sources, or evidence. Search loads it only when opened.

Search defaults to **Whole course**, with **This module** and **This page** scopes where applicable. Exact headings and phrases rank above scattered body words; equal-ranked results retain document order. Results show their true total and add 20 at a time through **Show more**. Queries and reading history are not transmitted; the only search fetch is the same-origin allowlisted index. Index failure exposes Retry and Course map recovery.

Keep keyboard navigation, figure text, alt text, link and anchor correctness, sanitization, private-source exclusion, symlink rejection, and technical checks. Standalone accessibility or equivalent-inspection pages and callouts are allowed when they help the learner.

Every module overview and lab has an **Overview / Lab** switch immediately below its title. Both links come from the module's manifest routes; `aria-current="page"` marks the active page. Keep the switch visible on overview pages as well as labs, at narrow and wide widths, and without JavaScript.

H2/H3 targets feed both navigation presentations. The desktop section rail is used only at widths of at least 1280px and heights of at least 720px. Otherwise a sticky **On this page** disclosure stays available while reading; the homepage always uses that disclosure. Passive scrolling changes its current-section label and `aria-current`, never focus, saved position, or completion. Explicit navigation reveals the owning section, aligns native and scripted fragment offsets, and focuses the heading or its disclosure control. Without JavaScript, the native outline links and full reading remain available.

Guided reading, shell cards, paired shells, and callouts are available enhancements, not requirements. When a **Terminal:** label plus shell fence is present the publisher may render it as a command card with copy. Expected, Stop, and Recovery paragraphs whose first bold text matches are turned into callouts when authored. Numbered steps carry step numbers and a "Mark done" control when a guide is active; the rail stepper mirrors them when present. Read full page exposes all procedure bodies and optional/transcript disclosures. Without JavaScript, core instructions, shells when present, outcomes when present, and the static stepper when applicable remain visible, and navigation uses ordinary links and native disclosures. Existing heading fragments remain valid.

Appearance, reading mode, shell choice, explicitly selected reading positions, and step completion use only `reformation-ui:v1:{course-root-pathname}` in local storage (state version 2; version 1 preferences migrate). Progress is per device and per module: the overview panel, the header bar, and the home course map count done steps out of the explicit steps on the module's guided pages. Pages without steps show no progress. "Reset progress on this device" clears positions and completion but keeps appearance, reading mode, and shell choice. These preferences store no work, credentials, or check results, and a done mark never establishes a passed technical check. Root and prefixed publications use separate keys.


## Runtime and publication

Participants need Git, Python 3.12+, the **latest stable Oh My Pi release**, a browser, and an ordinary text editor. Setup uses the official one-line installer from [omp.sh](https://omp.sh/), followed by a terminal restart and an `omp --version` check. Each run records the actual `omp --version` output; there is no course-specific OMP version number. Live cloud-model OMP runs still select **`openrouter/anthropic/claude-sonnet-4.6`** as the main chat model, with `OPENROUTER_API_KEY` supplied to the current process. Module 05 uses its native-task orchestration launcher. Module 06 starts ordinary `omp`, installs the TypeSafe skill, and calls `jev-1.13` through OpenRouter with that same key. Other recorded OMP agent runs use `shared/run_omp.py`, directly or inside a supplied module helper; those launchers create fresh runtime state, bound the model's tools, and disable retries and model fallback. In Modules 08–10 learners copy natural-language prompts into an ordinary OMP conversation, the coordinator, which runs the supplied helpers and mechanical operations while the learner inspects evidence and authorizes sensitive actions; the coordinator is not a recorded child. Module 09's coordinator launches the constrained child through `shared/run_omp.py` with the declared policy, and Module 10's coordinator starts and stops its own managed `llama-server` service after the learner approves.

Resolve latest when installing or updating, not while auditing saved evidence. Checks compare each attempt's recorded runtime identities, so a later OMP release does not relabel an earlier run. Complete a dependent Module 05 chain with the same verified runtime; after an upgrade, start a fresh chain. Provider and model pins remain unchanged.

Module 02 also uses Obsidian to inspect the local Markdown vault and edit plain `Feedback.md`, not generated Knowledge or navigation. It requires no community plugin, Sync account, REST API, or MCP service.

Module 06 uses ordinary Oh My Pi as the chat agent. Learners install the TypeSafe skill and have it write code that calls `jev-1.13` through OpenRouter with `OPENROUTER_API_KEY`. There is no separate TypeSafe key and no Oh My Pi judge role. Do not start `scripts/blue_gauge.py`.

Modules 02–10 use `shared/prepare_work.py`; Module 01 keeps its nine-source starter and Module 00 copies its request, style rules, checker, and six sources. Helpers refuse existing work/output attempts. A missing key or unavailable pinned provider/model holds the live lane without replacing it with a different model or unlabeled fixture.

Module 05 runs native `task` children rather than a second scheduler. Its three read-only specialists feed a coordinator-owned brief and a dependent read-only review. The first missing-input attempt remains on record; selective repair can reuse only still-valid independent results. The module checker joins requested assignments to native child records, source identities and permitted effects. A parent summary, finished task, or fixture transcript cannot substitute for accepted live handoffs.

Module 7 uses local **n8n 2.41.5 and matching external task runners** in a staff-prepared two-service Docker environment. The [staff runbook](AI_Harness_Bootcamp_2/module-00-setup/facilitator/RUNBOOK.md#local-n8n-readiness) owns provisioning; learners use `n8n_local.py start|status` and the browser. The stack has no privileged container, Docker socket, Assistant sandbox or search service. Native PowerShell uses `docker.exe` directly without an Ubuntu n8n bridge. The learner connects an AI Agent to OpenRouter with their own key and downloads the spreadsheet that agent creates. The key must not appear in an export, prompt, or note. Run `python3 AI_Harness_Bootcamp_2/module-00-setup/tests/test_n8n_local.py`, `python3 AI_Harness_Bootcamp_2/module-07-batch-workflow/tests/test_sheet.py` and `node --test AI_Harness_Bootcamp_2/module-07-batch-workflow/tests/test_controls.mjs`.

Module 10 has a separate **Local model** readiness lane. Learners use ordinary OMP prompts to resolve tool paths, run readiness, authorize the download and each launch, start the managed service under a unique handle, prove that the attempt owns the listener before the health probe, capture a local response, stop the owned handle, validate the stop receipt with `local_ai.py stop` after the actual stop, disable and restore the control, and repeat the owned lifecycle. Staff provision only missing tools using [the capstone runbook](AI_Harness_Bootcamp_2/module-10-capstone/facilitator/RUNBOOK.md); [VERSIONS](AI_Harness_Bootcamp_2/module-00-setup/shared/VERSIONS.md) distinguishes pinned candidates from actually rehearsed combinations. The published `check_readiness.py` observes approved tool paths/flags, work and Xet-cache volume capacity, installed/available RAM, and the declared `127.0.0.1:8080` endpoint before authentication/download and again before launch. Its 35 GiB download policy is total free space, not an additional model allocation. A planning-floor result does not establish model performance or a completed lifecycle. An occupied endpoint remains HOLD; do not reuse or stop someone else's service. The final structure check runs the checker from a new OMP conversation in a new terminal on the copied package; the checker validates named sections and file presence.

The child working directory is inside its redirected, fresh HOME. The historical OMP 18.3.5 replay showed that `--no-rules` did not disable [ancestor context-file discovery](https://github.com/can1357/oh-my-pi/blob/v18.3.5/packages/coding-agent/src/discovery/helpers.ts): placing cwd beside HOME allowed an outside ancestor's instructions to load. That offline replay observed the leak before the placement fix and its absence afterward, with zero provider requests. The isolated HOME/cwd boundary remains in place.

`.gitattributes` keeps text checkouts at LF so frozen source/control digests survive Git's automatic line-ending conversion. Native Windows setup also disables `core.autocrlf` for the clone command only. Do not renormalize or reset an existing dirty checkout to repair a hash failure; keep the mismatch and use an intact fresh copy.

Native OMP can exit 0 after an extension preparation error. Shared one-shot launchers still hold an attempt without exactly one completed terminal turn, the expected model identity, complete guard lifecycle, and matching tool/disk receipts. Module 06 is an ordinary interactive session, not that launcher audit. An offline host-invoked guard smoke verifies extension APIs and allow/deny behavior; it is not a model tool call or provider evidence. Runtime evidence files are local audit records, not cryptographic proof against an operator who can rewrite the whole evidence directory.

The saved-evidence audit joins each successful call to its authorization, independent execution check, tool/path identity, and filesystem effect. It also binds `response.md` to the final assistant event; changing only the extracted answer cannot change the recorded model response.

The MCP cutover retires the `hash_tool` policy field. Historical receipts containing that field require the launcher revision that produced them; the current auditor rejects the obsolete schema. Keep those receipts unchanged rather than removing fields to make an old run pass a new auditor.

Maintainers need Python 3.12+, Node.js 22, Bash, Zsh, POSIX sh, and a PowerShell parser to run every offline gate. Provision missing local parsers through an owner-approved native route; a missing parser is HOLD, never a skipped success. From the repository root, create the Python environment once if it does not already exist:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

Reuse that environment for publication and checks. `node scripts/render_figures.mjs --check` verifies every local image link in the module pages. No module currently has a spec-owned SVG figure; the script renders a `figures/spec.json` only if one is added. Instructional PNGs are not rendered by that script. A reader UI change does not require regenerating figures.

```bash
.venv/bin/python scripts/build_course.py
.venv/bin/python scripts/check_course.py
.venv/bin/python scripts/build_course.py --check
.venv/bin/python -m http.server 8766 --bind 127.0.0.1 --directory site
```

On native Windows, use `.venv\Scripts\python.exe` for the virtual-environment interpreter. Reuse the environment during correction loops. `check_course.py` never starts paid model calls; live verification is explicit and separately recorded. Serve only `site`, not the repository or staff source tree.

`check_course.py` requires `tests/test_command_syntax.py` and `scripts/check_command_syntax.py`. The syntax inventory covers allowlisted instructional Markdown, the eleven active facilitator runbooks, and named root maintainer procedures; it excludes immutable evidence, reviews, generated HTML, and archives. Each fence is parsed independently without execution or profiles. Output records source hashes, headings, fence/source-line locations, parser paths/versions, and fence/parser totals. An unclosed fence, failed self-check, missing parser, or syntax error holds the gate. `--report PATH` on `check_command_syntax.py` writes a new JSON receipt; keep it outside the checkout.

PowerShell 7 syntax is not Windows PowerShell 5.1 proof. Before release, run the same current PowerShell-fence inventory with native `powershell.exe` (or its approved explicit path via `--powershell`) and retain its source-bound parser results. Exercise the native package probe and copied-package structure check on that native machine as well. A parser pass cannot prove invocation, encoding, installation, or server operation. Native platform, process ownership, UTF-8, and path-with-spaces qualification remain a staff rehearsal lane.

The publisher reports instructional pages, raw downloads, and UI/generated assets separately. `--check` is read-only and compares exact bytes, including search and styles. After a UI change, exercise the built pages in a real browser in Dark and Sand, on narrow and wide viewports, with keyboard navigation, full reading, no JavaScript, print, and a prefixed mount. Keep screenshots and first-failure records outside the checkout. Browser proof is not native-platform, assistive-technology, provider, or learner-performance evidence.

`site/` is generated output and is not committed. On a fresh clone, install the pinned build dependency and run the publication commands above before serving or deploying. Publish the contents of `site/` as a static site; do not point a host at the repository root. The generated site needs no application server or provider credentials.

The GitHub repository is private. Give participants repository read access before they use the clone instructions; access to a hosted course page does not grant access to the source repository. Each setup route checks existing HTTPS access first. Only failed access enters the official `gh` browser-login fallback. `gh` is a conditional repository-access helper, not a harness or model credential. Its preferred OS credential store can fall back to plaintext; device policy must permit the reported storage before configuring the Git helper for `github.com`.

## Setup maintenance and verification

The five owning procedures are under `AI_Harness_Bootcamp_2/module-00-setup/platforms/`. Keep their commands aligned with the shared credential, version, troubleshooting, and source pages. The supported routes are native Windows PowerShell 5.1; Windows plus WSL 2 Ubuntu 24.04/26.04; macOS 15+ on Apple Silicon or Intel; Ubuntu 24.04/26.04 on x86-64/ARM64; and official Arch x86-64. Intel Homebrew is Tier 3, not equivalent support. Arch package installation is a full upgrade, never a partial `pacman -Sy`.

Keep the setup boundaries: install only missing prerequisites; verify the exact OMP checksum before execution; keep conflicting installs, profiles, and dirty checkouts; check saved PATH in an independent terminal without repairing it inside the check; and keep the prerequisite report separate from the live readiness check and actual disk readback. Both report helpers execute Python candidates until a usable 3.12+ interpreter is found. The native helper also tries the Python launcher's version selectors and rejects Store aliases/reparse paths.

Call the setup activity a **readiness check**. Its verifier reports `READINESS CHECK PASS` or `READINESS CHECK HOLD`; the executable remains `verify_tool_proof.py`. The name does not change the token, receipt, identity, or disk-content acceptance checks.

Windows execution policy is not a blanket setup prerequisite. Leave an already permitted policy unchanged. Managed restrictions, signing requirements, and intentional local restrictions require the device owner's approved route. The optional unmanaged-default recovery is explicitly consented, Process-only `RemoteSigned`; closing that PowerShell process ends it.

### Earlier verification receipts (historical)

The counts and execution limits below describe earlier revisions. They do not establish current-source PASS; the active campaign and its byte-exact previous-report reference are in [`evidence/exercise-runs.json`](evidence/exercise-runs.json).

The hands-on language/setup revision passed all 28 offline gates and publication checks for 32 instructional pages, 663 raw downloads, and 38 UI/generated assets. Actual OMP 18.3.5 installation/checksum and no-key launcher boundaries were exercised in a disposable Apple Silicon home and an Ubuntu 24.04 x86-64 container, including Bash/zsh interactive and login startup. The Ubuntu route also exercised the official prerequisite and `gh` packages. PowerShell 7 parsing and controlled command-boundary checks are not Windows PowerShell 5.1 evidence.

Release evidence remains incomplete: native Windows/WSL, Intel macOS, the other Ubuntu combinations, independent desktop-terminal transitions, GitHub browser authentication, and authorized paid readiness checks remain unobserved for the revised routes. The emulated Arch container could not initialize pacman's syscall sandbox; no sandbox bypass was used to claim an upgrade. A representative nondeveloper's homepage/setup attempt is also unobserved. Browser navigation, clipboard, saved place, keyboard, search, no-script reading, print, and prefixed publication were exercised; narrow DOM checks passed, but narrow screen capture failed in the browser tooling. Keep those limits separate from passed checks. Preserve transcripts and visual evidence outside the checkout; do not describe the five routes as natively verified or the revision as unqualified “S-tier.”

The native Module 7 cutover passed all 27 current scoped gates: 32 instructional pages, 692 raw downloads, and 38 UI/generated assets. n8n 2.41.5 ran in the approved isolated six-service stack on Apple Silicon Docker Desktop. Native form submissions produced both 80-row baselines, the predicted three-lot policy change, and byte-identical restored receipts; independent downloaded checker reports also cover revised inputs, malformed batches, empty routes, and tampered evidence. See `AI_Harness_Bootcamp_2/module-07-batch-workflow/evidence/REVIEW_VERDICT.md` for execution IDs and limits. Bash/zsh and PowerShell parsing plus controlled shell-boundary checks cover all five authored setup routes; they are not native Windows/WSL/Linux runs.

### Current navigation/readiness campaign

`20261005T002550Z-navigation-main-integration` records the integration with the newer module designs and retains **HOLD for unobserved evidence lanes**. The earlier `20261004T105600Z-course-navigation-readiness` campaign and incoming main report are archived byte-for-byte. The user authorized committing, merging, pushing, and removing the task branch/worktree despite those gaps. That publication authorization is not native-platform, human, live-model, or billing evidence. Earlier passes are not inherited by redesigned or changed sources.

The coordinator must confirm T and the cohort machine inventory and collect actual pilot, facilitator and technical-peer observations separately from automated verification. The mandatory macOS/Apple Silicon, native Windows PowerShell 5.1, and clean Arch routes are not proved by an incomplete cohort inventory. The [Module 00 staff register](AI_Harness_Bootcamp_2/module-00-setup/facilitator/RUNBOOK.md) owns T−7/T−3/T−1 duties and separate access, approval, licensing, tool, application, and local-model records. A completed procedure or checklist is not an observed participant attempt. The current Cold Foundry assignment is individual work completed within its session; the earlier campaign's recipient requirement is historical.

This staff verification campaign has one US$25 total authorization. Paid admission remains HOLD until its private budget register establishes the required enforcement, settlement, funding, and owner controls. No paid trial is used to discover whether that bound holds. The provisional US$40 learner allowance is separate future logistics, not an enforced cap or additional campaign spending authority. The user's publication override authorizes Git integration and publication, not additional spending or a change from unobserved to PASS.

The publisher reports current page, download, and asset counts. Detailed checks and evidence hashes belong in the ledger rather than being inferred from those counts. The Module 7 work-folder helper copies only the current batch, sheet rules, and spreadsheet checker; unpublished files stay out, and missing or linked inputs stop preparation before destination creation. The Module 02 path-safety name scan uses directory-entry strings instead of constructing a `Path` for every sibling; symlink/junction, traversal, and case-collision checks remain enforced.

### Rolling latest OMP verification — 2026-10-05 UTC

The official latest-release lookup selected `v18.6.1` for this verification, not as a new course pin. The authored macOS installer downloaded and verified that release in a disposable home; a separate login zsh resolved it from the saved profile. All 280 setup syntax, release-selection and failure-boundary checks passed, including optimized Python metadata validation and preservation of conflicting installed bytes.

The real latest binary passed the setup report, token-and-write readiness check, one bounded MCP read, a bool/choice/score Jev batch, and Copper Span's four native stages. Fanout produced the expected missing-Timing HOLD; selective repair dispatched only Timing; integration and review passed their independent saved-evidence checks. Existing provider/model pins did not change. Private records are under `~/course-evidence/omp-latest-20261004/`; the affected module references record run IDs and scope. These checks do not establish native Windows/WSL/Linux installs, GUI-terminal transitions, full MCP/Blue Gauge lab outcomes, or learner performance.

The generated setup pages were exercised in an isolated Chromium browser at desktop and 390-pixel widths. macOS and Windows copy controls returned the authored installer commands, and the version table showed the rolling latest requirement. Screenshots and clipboard observations are retained with the private evidence. The automation browser required explicit clipboard read/write permissions after a clipboard read left subsequent writes denied; no course code was changed to bypass that browser state.

Before integration, all manifest module gates, the additional Module 01 content check, shared launcher/guard tests, publication/build tests, and figure check passed individually. Module 02's eight-mutation adequacy run required an extended deadline: its first run hit 600 seconds, and the isolated rerun passed in 823 seconds. That branch retained the previously documented Module 07 core-contract HOLD.

Integration preserved main's independently committed Module 02 path-check optimization and Module 07 contract corrections. The combined `scripts/check_course.py` then passed all 30 scoped gates with its normal per-command deadlines, and publication passed byte-for-byte checking: 35 instructional pages, 419 raw downloads and 40 UI/generated assets. The first combined run had three failures caused by an ignored, bytecode-only directory under the retired Module 06 name; that cache was preserved outside the checkout, without changing source or weakening discovery checks. Both combined-run logs remain with the private evidence.

The final remote integration retained the new Module 0 long-form lesson and repository README. All 31 scoped gates passed, and publication passed byte-for-byte checking with 35 instructional pages, 435 raw downloads and 40 UI/generated assets. Three generated files retired by the new manifest were preserved outside `site/` before rebuilding. Chromium confirmed overview-to-macOS navigation, the latest-release installer at 390 pixels without document overflow, and the rendered latest-stable requirement. The new long-form adapter also accepted the retained real `omp/18.6.1` readiness receipt; this is receipt compatibility evidence, not a new full long-form exercise run.

### Integrated latest OMP verification — 2026-10-05 UTC

After integrating the current long-form Module 0 changes, the publisher rebuilt 35 instructional pages, 435 raw downloads, and 40 UI/generated assets. The complete `scripts/check_course.py` run passed all 31 scoped gates in 255 seconds with a dedicated `TMPDIR`; the 600-second per-command deadline was unchanged. This supersedes the earlier combined-gate limitation above. The copied worktree's untracked, cache-only retired Module 06 directory was preserved outside the checkout before verification.

The entire generated site, including search data and downloads, contains no `18.3.5` reference, numeric OMP release requirement, or hard-coded OMP release URL. Browser checks covered all five setup routes; the final merged version table shows `latest stable release`. A fresh macOS install verified the official release checksum and resolved `omp/18.6.1` in a new login shell. A fresh, read-only MCP run passed the independent saved-receipt audit after restoring the result's required MCP metadata; all 32 shared runtime tests passed. The observed executable version is evidence, not a new pin. Logs, the regression's failing/passing runs, and desktop/mobile browser proof are retained under `~/course-evidence/omp-latest-site-check-1791162031193/`. Native Windows/WSL/Linux installation is not claimed.

### Module 02 automatic AI handoffs — 2026-10-06

Module 02 now runs one bounded judge → build → freeze → fresh-retrieval sequence without human admission between stages. Learners inspect the answer-to-source trail in Obsidian and give source-backed feedback for a preserved new revision. All 34 offline course gates passed after the cutover, including behavioral regressions, mutation checks, shared-runtime checks, and byte-for-byte publication. Chromium verification covered the generated walkthrough, shell switching, command copying, figure viewing, and 1440-pixel and 390-pixel layouts. Native Obsidian source inspection was observed on this macOS host; other platforms and learner completion remain unobserved.

**Two-revision live result: UNVERIFIED at initial publication.** Two live judge attempts read all forty sources but reached the 300-second session deadline before returning judgments; neither reached build or retrieval. Both attempts are preserved under `~/course-evidence/module02-ai-handoffs-20261006T030026Z/`. The helper now requests OMP's supported low-thinking mode for each Module 02 phase, with the same pinned model, deadline, and no-retry policy. The user authorized publication in this state, then six fresh sessions after the website is live (eight sessions total). Offline passes are not evidence that those live revisions completed.

**Post-publication verification:** Live v1 completed judge, build, freeze, and fresh retrieval with stdin unavailable and no human approval between stages. The judge read all forty sources; the remaining stages consumed the validated judgments and frozen notes. The missing-rule run stopped before a model session, and restoring the rule left v1's preservation check passing.

All eight authorized sessions have now been used, including the two pre-publication attempts. The final session exercised the v2 judge: it read all forty sources, feedback, and both prior records, then added the requested road-versus-gate qualification. A private authorization guard stopped before v2 build; no v2 notes or answers were published. **Complete live v1/v2 proof remains UNVERIFIED.** The v2 rationale also counted a qualification of the gate condition as a fifth independent deficiency; this semantic finding remains visible rather than being treated as a successful human review.

Post-publication fixes require contiguous verbatim excerpts, derive source-to-claim membership from validated citations instead of asking the model to duplicate that index, and link each answer citation only to judgments matching its source passage. The final runtime passed all 35 scoped course gates in 215.94 seconds, with six Module 02 mutations killed and none surviving. A separate real-CLI smoke completed v1 and v2 with explicitly synthetic receipts and verified both preserved revisions. Publication checked 35 pages, 407 downloads, and 40 assets byte-for-byte.

The final answer renderer was also exercised against the genuine saved v1 outputs in a separate preview vault; native Obsidian navigation reached answer → Knowledge → judgment → original source. The original live receipts and helper were not rewritten to make that rendering check look like another live run. Source identities, observed failures, the capped v2 attempt, and screenshots remain under the private evidence root above.

### Simplified local n8n verification — 2026-10-06 UTC

The active runtime is staff-prepared n8n 2.41.5 plus matching external task runners, without Assistant's sandbox/search infrastructure. All five learner routes use the same Python start/status helper; learners verify editor access, saved work and staff-assisted persistence rather than administer Docker. Staff preparation and recovery are in the Module 00 runbook.

The two-service stack ran on Apple Silicon Docker Desktop in an isolated project and on loopback port `15679`, preserving the existing instance on `5678`. A real external-runner Code task, stopped-container recovery, volume-preserving recreation, four persisted workflows and a working retained credential passed. The current Module 7 agent downloaded an 80-lot XLSX with no route/status mismatches. Its first live tool failure exposed a publication requirement: publish only the internal sheet tool during use, keep the agent/form unpublished, then unpublish the tool at close. Both UI exports were key-free. The two live agent runs increased observed key-level OpenRouter usage by US$0.13572; no per-generation billing receipt is claimed.

All 35 scoped course gates passed, including 19 helper boundary tests. Publication passed byte-for-byte checking for 35 instructional pages, 437 downloads and 40 assets. Chromium checks covered 11 pages, three widths and both themes without document overflow; all five platform copy controls returned the authored commands. Direct course screenshot capture timed out; inspected wide Sand and narrow Dark visuals are screen-media PDF renders. This is not native Windows/WSL/Linux/Intel Mac qualification or measured human learner performance. The existing navigation/readiness campaign's unobserved lanes remain HOLD.

The Module 00 and Module 07 `evidence/REVIEW_VERDICT.md` files record the observed failures, corrections and limits. The `local_n8n_simplification` revision record in `evidence/exercise-runs.json` binds the private source and evidence manifests under `~/course-evidence/reformation-qa/20261006T021456Z-simplify-local-n8n/`.

Integration retained the newer Module 02 revision `bb936d1`. The combined course passed all 35 scoped gates in 421 seconds, and byte-exact publication passed for 35 pages, 428 downloads and 40 assets. The nine generated downloads retired by that incoming revision were preserved outside `site/` before rebuilding. The n8n helper and Module 7 exercise bytes were unchanged by the merge; the rebuilt setup and lab were also inspected in Chromium. Both disposable n8n projects were removed after their evidence was saved, including their test volumes; the preexisting instance retained its identity, running state and loopback binding.

## Netlify deployment

The hosted course is at [reformation-aihb-oct-2026.netlify.app](https://reformation-aihb-oct-2026.netlify.app). Native Netlify builds use the existing GitHub App connection to the private repository and publish successful pushes to `main`.

Root `netlify.toml` selects Python 3.12 and Node.js 22, then runs `scripts/bootstrap_parsers.sh` around the dependency install, publisher, and mandatory course gate. The bootstrap requires Ubuntu 24.04 x86-64 and its declared compiler/native dependencies; it downloads official PowerShell 7.6.6 and Zsh 5.9.2 artifacts with pinned SHA-256 verification into a private build-only directory. Their PATH applies to the exact child build command. No sudo, global installation, parser-result cache, cross-build cache, or cache plugin is used. Only `site/` is published; any failed command blocks publication. Pretty URLs remain disabled.

Manage the shared password in [the Netlify project](https://app.netlify.com/projects/reformation-aihb-oct-2026) under **Project configuration → General → Visitor access → Project visibility**. Keep **Password** selected with **Production and previews** scope. This protects pages, assets, downloads, and immutable deploy URLs. Keep credentials out of Git and build environment variables; the local `NETLIFY_PAT` stays in ignored `.env`.

To reconnect GitHub, open **Project configuration → Developer settings → Continuous deployment → Repository → Manage repository → Link to a different repository** and select `TheHolofex/AIHB_OCT_2026` through the existing Netlify GitHub App. Keep existing App repository grants. After relinking, confirm `main`, the `netlify.toml` build settings, private deploy logs, and all-deploy password protection. Push a deployment-owned change and confirm the published production deploy's commit matches that push; a successful clone or a build started by relinking does not prove push notifications work.

In the native deploy log, confirm `build.command from netlify.toml`, the pinned parser versions, the final all-scoped-gates PASS, and the byte-for-byte publication check. Then check the live password gate and an authenticated download; a ready deploy alone does not verify access protection.

If a private-repository push appears missing, check **Deploys** for **Pending Review** before relinking. Netlify can hold an unrecognized Git author as `unverified-committer`, and the ordinary deploy-list API can omit that request; the site's builds API still lists it. For an author who is already a team member, use **Start approval process → Further action required → Approve and match with existing team member**, select that person, and confirm the match. Do not enable team-wide auto-approval to resolve one author's identity.
