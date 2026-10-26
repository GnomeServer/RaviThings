# Core authoring guide

**Serves oracle:** S02, S04, S05, S06, S07, S08, S09, S10, S11, S12, S14, S15, S16, S17, S18, S19, S20, S21, S24, S25, S26

## Scope and responsibility

This guide governs the Reformation core and its runnable modules. Core files own the capability progression. Module sources own scenarios, commands, forms, practice data, and facilitator procedures. The published HTML is the learner surface.

The learner specifies task-specific behavior, configures bounded values in supplied controls, tests, interprets, and decides. The **adapter implements** executable mechanics, dynamic checks, and evidence export, and supplies every module's case. A builder owns general-purpose code, API/MCP, retrieval pipelines, agent runtimes, and deployment.

Adapter-supplied raw state carries a plain-language legend naming each field and state value. The legend labels; it does not interpret the result.

## Module contract

Every module declares once:

- `Serves oracle`
- `Primary objective`
- `Prerequisites`
- `Consumes`
- `Produces`
- `Rough time`
- `Performance stage`
- `Work surface`
- `Practical work`
- `Performance evidence`
- `Failure / HOLD`
- `Scope boundary`
- `Handoff`

Modules have independent supplied cases, not independent learning objectives. Each module assumes earlier capabilities and extends at least one of them. Every entry in `Consumes` is supplied from outside the module and carries the `VERIFY:` prefix: the learner confirms the supplied input or operating boundary before the attempt. `VERIFY:PREFLIGHT` and `VERIFY:CASE` are universal entry conditions.

No module consumes another module's product. Every token in `Produces` is named in that module's `Performance evidence` or `Check the work` section; the module's own result token records the observed behavior and its limits. A mention in `Handoff` alone does not establish that a product exists.

A module has one primary outcome. It leaves an evidence bundle describing work, observations, decisions, and unresolved limits. The bootcamp is ungraded: do not add exercise scores, learner pass/fail decisions, qualification ledgers, or reassessment requirements. Technical checks may report `PASS` or `HOLD`; those results describe the work, not the learner.

For each mastery claim, complete “Before this project, the learner could ___. After this project, the learner can ___.” A new file, scenario, tool installation, repetition count, or evidence log is not a new capability. Repeated skills are prerequisites or quality bars. Recover a missing prerequisite explicitly without relabeling it as the current objective.

### Module 02 contract

**Title:** Module 2 · Build and control a reusable second brain

**Mastery:** Using verified sources and bounded direction, control a learner-started AI judgment → knowledge build → fresh retrieval chain to create source-traceable reusable knowledge under an explicitly loaded saved instruction, then direct a meaningful correction in a new preserved revision.

Before this project, the learner could verify sources and give bounded direction. After this project, the learner can direct a fixed supplied helper's automatic AI judgments into provisional linked knowledge under an explicitly loaded saved instruction, perform independent source inspection, and direct a meaningful correction shown in a new preserved revision and fresh run. Source checking remains Module 01's inherited quality bar. Saved instructions, load proof, and controlled handoffs are newly taught here. Bounded multi-agent orchestration belongs to Module 05; checking a received local-model package from a fresh copy remains Module 10's.

**Consumes:** `VERIFY:PREFLIGHT`; `VERIFY:CASE`; `VERIFY:SUPPLIED_GUARD`

**Produces:** `SOURCE_AS_DATA_CONTROL`; `KNOWLEDGE_VAULT`; `RELOAD_RESULT`; `PO02_RESULT`

The independent Ledger Pike case retains all forty DN sources unchanged. Use Obsidian to inspect saved judgments, generated provisional knowledge, and source links, and to edit plain `Feedback.md`. Only the fixed helper writes generated Knowledge, judgment records, and navigation; versioned Knowledge remains immutable. Each learner-started run automatically continues through three paid sessions—judgment, build, and fresh retrieval—with local freezing between build and retrieval. No learner review, selection, approval, or note editing unlocks a pass. Each judging pass actually reads all forty originals, including on v2; v1 and v2 use six paid sessions in total.

Fresh retrieval reads only the helper-frozen navigation and versioned Knowledge notes; originals, judgments, feedback, and source-processing chat remain outside that read root. Keep the saved governing instruction outside every model read root and prove its explicit loading before each provider call. The learner independently traces answers through Knowledge and saved judgments to original support, then records a source citation, observed correction, and expected answer effect in `Feedback.md`. The next complete run consumes that feedback and preserves earlier revisions and evidence. Test missing-rule retrieval on v1 before restoring the same rule for v2, whose load receipts supply the restored-rule proof. A substantive focal change and actual fresh read and citation establish what changed and was used; independent source inspection determines whether the answer improved. Changed wording alone is insufficient. Local checks establish bytes, provenance, and boundaries, not semantic truth or human approval.

Legacy P4 is an authoring source only. Record adaptation provenance in Module 02's active staff reference; do not create a runtime dependency on the old checkout or change the frozen historical research reference.

### Module 05 contract

Before this project, the learner could direct and verify one bounded assistant run. After it, the learner can supervise a dependency-aware native OMP agent team, accept its handoffs, and recover a partial failure without discarding valid independent work. Use the three enabling objectives in `LEARNING_OBJECTIVES.md`: decomposition and complete delegation contracts; native fan-out/fan-in with dependent review and source adjudication; selective recovery with dependency invalidation.

The learner owns the work graph, assignment briefs, acceptance, and decision to use the combined result. OMP owns native child execution. The supplied adapter prepares resources, limits the tool surface, preserves native records, and checks evidence; it must not secretly replace delegation with a custom scheduler or prewritten outputs. Use read-only specialists and reviewer, one coordinator-owned output, bounded concurrency and depth, explicit stop conditions, and no implicit retry or model fallback. A task batch is not an ordered dependency graph.

**Consumes:** `VERIFY:PREFLIGHT`; `VERIFY:CASE`; `VERIFY:NATIVE_TASK`; `VERIFY:ORCHESTRATION_CONTROLS`

**Produces:** `WORK_GRAPH`; `AGENT_HANDOFFS`; `PARTIAL_RECOVERY`; `INTEGRATED_BRIEF`; `PO05_RESULT`

Native child completion and artifact presence are not acceptance. Join actual requests, child sessions, results, source identities and permitted effects. A missing input must produce an observed blocked attempt; a selective repair retains that attempt and identifies which prior work remains valid. Review consumes the actual candidate and source evidence after its prerequisites, not merely a request to “review the above.” A source or brief change invalidates its consumers and downstream integration. Keep model proposals, deterministic checks, and human acceptance separate. Historical renderer-repair evidence does not establish this replacement's behavior.


## Single ownership

| Sub-problem | Owner |
|---|---|
| Minimum screen, planned long-document drafting one session per section, separate review sessions with verified findings, targeted revision, bounded internal acceptance | 00 |
| Source verification and output discernment | 01 |
| Learner-started fixed helper AI handoffs to provisional knowledge, saved instruction and load proof, source-as-data control, fresh-session retrieval | 02 |
| MCP operation, AI classification judgment, limited tool authority proved by probes, revocation | 03 |
| Typed-question decomposition, read-only decision runs, measured confidence gates, code-owned routing | 04 |
| Native OMP team decomposition, evidence-bearing handoffs, dependent review, selective recovery | 05 |
 | Jev pattern configuration and comparison (fan-out, confidence, scoring, intent routing to lookup / deterministic comparison / human queue) inside native OMP controls | 06 |
| Model-driven tool use that produces a real structured-data artifact, with observed execution and downloaded-file inspection | 07 |
| Hallucination control with structured claim checks, isolated reviewer agents, correction, re-review and human disposition | 08 |
| Live-agent allow-list, write jail, planted-instruction refuse | 09 |
| Package local-runtime instructions/controls (no undeclared deps) for fresh-terminal structure verification | 10 |

## Responsibility before release

The minimum responsibility screen — source/data authority, sensitive-data boundary, affected audience or person, disclosure need, consequential authority, and human decision owner — is a standing rule applied in every module to its own supplied case. Modules 00–02 can make only bounded internal-acceptance decisions.

Module 03 owns MCP operation, judging an AI's classifications against stated rules, and limiting a tool's authority. A transcript in which the model never attempted a forbidden action does not show that a limit holds; a probe that attempts the action does. Every learner practices both the classification claim and the authority claim. Study a refusal to connect without treating it as evidence that a tool was operated.

## Evidence standard

Every bundle contains:

- work product or operated state;
- strongest independent result;
- learner decision and owner;
- observed result and its limits;
- failure or `HOLD` when applicable;
- substitution record when a named dependency was replaced — what was replaced, the same-state basis, who certified it, and the affected outcome;
- scope boundary; and
- handoff.

Independent evidence checks the producer’s claim against a separately inspectable source, deterministic rule, or observed state. Preserve inputs, check identities, and observed results so another person can inspect the comparison. Public practice files are inspectable. Authored fictional corpora and paired outputs are labeled practice data, not live OpenRouter receipts.

An executed tool claim requires the actual assistant call, execution result, guard decision, and disk effect. A refusal sentence is not a tool denial. Distinguish `DENIED_BY_GUARD`, `DENIED_BY_RUNTIME`, `NOT_ATTEMPTED`, and `VIOLATION`. Missing or incomplete receipts hold the affected claim. The OMP extension limits the tools exposed to the model; it is not an operating-system sandbox or a defense against malicious local processes.

## Nondeveloper and dynamic-check boundary

The learner specifies and configures bounded behavior in **supplied controls**: questions, thresholds, policies, and rules written in the formats those controls read. The adapter implements any new checker, router, or runner and owns its identity. If a needed behavior can't be expressed in a supplied control, record the behavior, implementation dependency, owner, and `HOLD`; do not claim the control was implemented. A model-backed control is pinned to one model and version, and its evidence records the build that answered.

The core includes bounded native OMP multi-agent orchestration and task-bounded automation, not agent-runtime development. Module 05 permits read-only specialists and a reviewer under one coordinator-owned output; learners configure supplied roles and briefs rather than build a scheduler. Module 07 connects one n8n agent to one spreadsheet-writing tool; it does not grant arbitrary file access or make a chat reply proof of an artifact. Module 08 adds a bounded learner-started read-only ensemble, run one stage at a time from prompts copied into the ordinary OMP coordinator: reviewers receive isolated inputs, the correction stage sees completed reviews as evidence, and fresh reviewers recheck the entire correction. The coordinator's conversation never enters a child's inputs. No model vote grants authority. The core also permits one narrow form of persistent knowledge: a local Markdown knowledge vault with learner-started automatic AI-processed provisional versions via the fixed supplied helper chain (judge → build → freeze → retrieve) and independent nonblocking source inspection. Neither AI success nor receipts represent human approval. Autonomous state updates, concurrent agent writes to shared knowledge, custom retrieval infrastructure, and MCP construction remain advanced. The fixed helper workflow is explicitly allowed.

## Deterministic and stochastic evidence

Exact blast-radius claims apply to deterministic outer state: input identity, route, status, field presence, policy version, receipts, and controlled deterministic fields. When probabilistic content materially affects acceptance, the run applies the pre-result variation rule below or routes the item to `HOLD`; one generated sample cannot establish exactness.

An output is **material** when a criterion named in the technical acceptance check depends on its content. Declare that classification before the run and apply the supplied control; the producer does not reclassify after seeing output.

Candidate evaluation declares before results one of:

- a deterministic case whose material result is mechanically fixed;
- repeated paired controls with run count and aggregation rule;
- a hard gate that any single violation defeats; or
- exclusion of the stochastic claim from the decision.

## Transfer practice

Clean-session restartability and the fresh-copy structure check are separate observations. Freeze the declared eleven-file bundle (`E/bundle-before.json`) and make a digest-checked copy into the fresh folder `F`. From a new terminal and a new ordinary OMP conversation rooted in `F`, have OMP run `scripts/check_package.py shared/PACKAGE.md` as an independent process and record the observed result. The structure check reads the package's named fields and confirms every file it names is inside `F`; it does not carry out the package's instructions. Record the check and unresolved limits in `E/close-out.md`.

## Publication check

Publish only when objective/map/module fields agree, every consumed token is supplied and prefixed, the first action can run from verified products alone, failure cannot be mistaken for pass, detailed implementation has not entered core, and every authoritative file names served oracle criteria.

Prefer the plain-language records a learner would recognize from ordinary work over internal product tokens, prefix tokens, or `PO` identifiers. When an identifier-shaped term helps the learner, such as an environment variable name, explain it at first use; the publisher does not scan learner pages for tokens. `PASS` and `HOLD` are ordinary words; see the recorded decision below.

## Recorded decisions

### Maintainer sources and HTML publication

Maintain existing instructional Markdown in its owning module and publish it through `scripts/build_course.py`. Do not add a second learner Markdown navigation path; additional canonical explanatory or reference pages, prompt sheets, and accessible or downloadable handouts belong under the owning module and are registered in `course.json`. Raw downloads are the exercise files learners operate on plus any registered resource that helps them. `course.json` owns the public allowlist; staff references, historical evidence, and answer keys stay outside `site/`.

Preserve command fence languages, terminal and privilege labels, separate expected output where present, stop conditions, link destinations, figure descriptions, and text alternatives. Run structural checks against the published HTML. Use ordinary complete sentences and define each new term at first use. Detailed explanations, behind-the-scenes discussion, orientation, recaps, worked examples, diagrams, screenshots, supplementary guides and handouts are allowed when they help the learner; choose the format for the task rather than a fixed template. Real authority, privacy, stop-condition, dependency-ownership and evidence distinctions remain.

The reader sources are `ui/course.css`, `ui/course.js`, and `ui/theme-init.js`. Keep Sirocco vendor files byte-identical; put course-specific changes in the application files. Declare every published UI asset individually in `course.json`; CSS dependencies must resolve inside the same allowlist. Do not copy a public directory recursively or add an external font/script dependency.

The manifest declares each page's `kind`, each module's exact `case_name` and capability `summary`, its learner-facing `outcomes` (optional object with optional `can` string of any length and/or optional `will` list of any number of nonempty strings), and one overview and lab route per module. Additional `reference` and `setup` pages may be registered. The publisher renders outcomes content when present and a device-local progress panel on pages that have steps; do not restate them in the Markdown. The home source contains exactly one `<div data-course-map></div>`; the publisher supplies its ordered links from that manifest.

`guide` is optional on every non-home page. Without it, the page keeps its authored H2/H3 hierarchy, prose, images, prompts, and disclosures unwrapped, with no step controls. An explicit object opts in; its only keys are `context_sections` and `optional_sections`, each a list of unique existing top-level H2 IDs, and `{}` groups every H2 as a step. A step group runs from its H2 to the next step, context, or optional boundary. Put explanatory H2s that are not actions (for example `before-you-stop` or `class-only-boundary`) in `context_sections` so they are not counted as steps. An optional top-level H2 belongs in `optional_sections` and must be followed by its `<details class="rf-stretch" markdown="1">` disclosure; a stretch disclosure has exactly one summary, and nested figure-text disclosures are not stretches. Each step gets a step number and a device-local done control, and module progress counts the explicit steps on every non-home page of that module. A guided page with no steps (only context sections, or no H2s) stays fully readable without progress or reader controls, and its outline says “On this page.” Never renumber or rename existing fragments to make a sequence look regular; new publisher-owned IDs use the reserved `rf-` prefix.

A fence without a shell language is ordinary copyable text, which suits prompts that learners copy into OMP. A `**Terminal: …**` label followed by a shell-language fence opts into a command card; a Bash card immediately followed by its PowerShell twin becomes one shell switch; paragraphs that begin with bold `Expected:`, `Stop:`, or `Recovery:` render as callouts. These are available presentations, not required rhetoric. Keep all core and context bodies visible in static HTML. Guided controls, search, copy, appearance, and resume are independent enhancements; their failure must not hide instructions or strand ordinary links. Read full page and printing expose optional work as well as core instructions. A section selection or “Last opened” label never establishes completion or a passed technical check.

Publication uses the existing environment from the repository root: `.venv/bin/python scripts/build_course.py`, then `.venv/bin/python scripts/check_course.py`, then `.venv/bin/python scripts/build_course.py --check`. The gate makes no paid model calls. Compare existing URLs, fragments, command bytes, labeled conditions, the class-only footer, and download/figure bytes when changing the reader. Exercise the actual HTML at root and prefixed mounts; keep visual, keyboard, clipboard, print, and fallback evidence outside the checkout. Do not put browser observations in the live-exercise ledger.


Use `shared/prepare_work.py` for Modules 02–10, Module 01’s starter for its fixed source boundary, and Module 00’s case copy (the request, the style rules, the checker, and six sources). Work and evidence stay outside the checkout. Refuse existing destinations and retain failed attempts. Only the documented restore operation may replace an authorized work-copy control.

Use the supplied OMP launchers rather than direct vendor logins or alternate harness branches. Require Git, Python 3.12+, the latest stable Oh My Pi release, a browser, and a text editor. Setup resolves one official latest release and verifies its binary against the same release's checksums. Record the actual OMP version in each attempt; audit saved identities without imposing a numeric course version. The exact model is `openrouter/anthropic/claude-sonnet-4.6`; the only participant credential is `OPENROUTER_API_KEY`. Node is a maintainer-only figure prerequisite. Module 03 also uses the free Obsidian desktop application to open its supplied vault; it needs no account, Sync, or community plugin, and the module states the requirement itself. Keep hashing, arithmetic, predicates, routing, and comparisons deterministic.

Module 02 also requires Obsidian to inspect generated Markdown and edit plain `Feedback.md`; learners do not edit generated Knowledge or navigation. Do not add community plugins, Sync, a REST API, or an MCP service to its core workflow. Reuse `shared/run_omp.py` and `shared/course_guard.mjs` unchanged.

Record observed exercise outcomes separately from editorial review. Keep live-provider and native-platform observations explicit. Preserve historical evidence without treating an old assessment policy as a current requirement. The 15-minute/eight-term orientation, 120-minute unaided-work limit, and first-result timing remain design targets until measured with people.

### `PASS` and `HOLD` are ordinary English, and they stay

The publication check above once banned any "claim-state word" from learner-facing material, while the frozen Module 0 Reference requires the learner to record `PASS` or `HOLD`, and both words appear throughout the learner surface. Two documents asserting opposite rules is worse than either rule.

Resolved in favour of `PASS` and `HOLD`. A check passes; work goes on hold. Both are words a competent professional already uses at work, and neither reveals anything about how the course is built. The requirement to map internal vocabulary to plain language is satisfied by plain-language forms such as `READY TO SEND / HOLD`.

One limit holds anyway. A recorded `PASS` is the outcome of a check, never the evidence for it — the verification response the learner sees must portray the observed value, so a learner typing `PASS` into a file cannot stand as proof that anything was verified. Other vocabulary follows the current authoring policy in `CLAUDE.md`: prefer plain language, explain an unfamiliar term at first use, and do not rely on a blacklist of identifier-shaped words.
