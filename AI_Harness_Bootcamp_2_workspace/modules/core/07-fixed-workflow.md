# Module 07 — Automate a spreadsheet with an agent

**Serves oracle:** S04, S08, S13, S14, S17, S19  
**Primary objective:** PO-07 — Automate a batch into a spreadsheet  
**Prerequisites:** Source verification, bounded tool use, typed-output inspection, failure preservation, and local n8n readiness; this module's supplied batch and sheet rules  
**Consumes:** VERIFY:PREFLIGHT; VERIFY:CASE; VERIFY:BATCH_WORKLOAD  
**Produces:** AGENT_SHEET; PO07_RESULT  
**Rough time:** about 3 hours (planning estimate, unmeasured)  
**Performance stage:** Adversarial  
**Work surface:** Structured-data/batch work  
**Practical work:** Connect an AI Agent in local n8n to OpenRouter, give it one spreadsheet-writing tool, run the supplied batch, download the actual XLSX file, and inspect the file against the source and sheet rules.  
**Performance evidence:** AGENT_SHEET includes the downloaded spreadsheet and its source batch, unpublished agent and tool workflow exports without key material, the tool-call and download execution identity, the structure-check result, and observations identifying any incorrect routes or statuses. PO07_RESULT records what the run produced, the learner's decision, and unresolved limits.  
**Failure / HOLD:** Missing local runtime, wrong model or tool, no observed tool call, absent download, missing or invented source lots, key material in an artifact, or unsupported routing. A chat reply and a green execution are not evidence that the spreadsheet exists or is correct. Preserve failed executions and downloads, except exposed key material, which must be removed and the credential revoked.  
**Scope boundary:** One human-started agent workflow and one supplied-purpose file-writing tool. No programming objective, cloud n8n deployment, published production workflow, arbitrary host-file access, autonomous collaboration, or multi-agent writing. The model chooses row values; the converter does not prove their correctness.  
**Handoff:** Keep the source batch, actual download, execution identity, checker result, observations, and secret-free exports. Record wrong rows instead of hand-editing the model's spreadsheet into a passing result.
**Case family:** [CASE_FAMILY.md](../../CASE_FAMILY.md). White Rack is independent of other modules' cases and consumes none of their products.

## Capability added

Before this project, the learner can bound a tool's authority, inspect model outputs, and check claims against sources. After it, the learner can connect a model's tool call to the production of a real structured-data artifact, then distinguish the observed file and its correctness from what the model says it produced. Source checking and credential hygiene remain prerequisites, not new objectives.

## Enabling objectives

- Compose an agent, a pinned chat model, and one callable tool workflow so a supplied batch produces a downloadable spreadsheet rather than a chat-only answer.
- Trace the observed tool call through the sub-execution to the downloaded artifact, keeping the credential in the local n8n credential store.
- Inspect complete lot coverage separately from route and status correctness, using the source batch and first-match rules to identify model errors without repairing the evidence by hand.

## Active execution contract

Use local n8n 2.41.5, localhost browser access, and unpublished workflows. The agent uses OpenRouter's `anthropic/claude-sonnet-4.6` with the learner's own credential. n8n Assistant remains off; it is not the AI Agent node.

The agent workflow is Upload wave → Extract from File → One batch → AI Agent. One batch collects all extracted rows into a single item. The agent has an OpenRouter Chat Model and a Call n8n Workflow Tool connected to a separate unpublished workflow. That tool accepts `sheet_csv`, parses it with the supplied Code body, and uses Convert to File to produce `white-rack.xlsx`. The learner pastes the supplied bodies; writing a new parser or runtime is not an objective.

The instruction requests one tool call containing every lot. Inspect intermediate steps to establish what actually happened; the request alone does not prove one call occurred. Download the XLSX from that sub-execution. Docker-hosted n8n does not place it directly in the learner's Documents folder. Retain each execution and download separately.

## Artifact and evidence contract

The supplied `wave1.csv` contains 80 White Rack lots, `LW-01`–`LW-80`, carrying refrigerated reagent kits from Icehouse Depot to Clinic I-6. The spreadsheet columns are `lot,route,status,reason`. Apply the first matching rule from `shared/SHEET_RULES.md`: exact RACK_CONFLICT holds with RESOURCE_CONFLICT; otherwise exact AUTHORIZED passes with READY; otherwise exact WITHDRAWN rejects with NOT_AUTHORIZED; every other permit holds with OPEN. Batch notes, gate-window text, and input dispositions do not override those rules. The rack pair stays held; this exercise does not choose which cold lot travels.

Run the supplied `scripts/check_sheet.py` against the downloaded file and the unchanged source batch. Its PASS establishes that each source lot is present once, not that the routes and statuses are correct. The learner compares those fields with the rules and records incorrect rows in `observations.md`. If XLSX reading is unavailable, preserve the original download and check a CSV copy exported from it; identify that copy rather than claiming it is the original binary.

The retired 13-node deterministic router, policy-change comparisons, and exact restoration remain historical evidence. They are not current requirements or products. No result from this fictional case authorizes a real movement, and no learner score or peer sign-off is required.
