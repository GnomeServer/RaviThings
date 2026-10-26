# Reference: Module 7 — Automate a spreadsheet with an agent

**Revision 7:** 2026-10-07 — the lab now shows the n8n 2.41.5 editor for each construction step: Create workflow, the six-node line, node search, form trigger, extract, both Code bodies, Basic LLM Chain, the empty credential form, the pinned model id, the parser schema, Convert to File, and the Binary download. Those PNGs are captures of that editor. They are not the retired router figures.

**Revision 6:** 2026-10-07 — one unpublished workflow. Upload wave → Extract from File → One batch → Basic LLM Chain (`Fill the rows`) with OpenRouter and a Structured Output Parser → Rows → Convert to File. The AI Agent node requires a tool sub-node, and the file-writing tool was a second published workflow. That path is retired. Download `white-rack.xlsx` from Convert to File on the same execution. Do not publish the workflow.

**Revision 5:** 2026-10-05 — use the staff-prepared n8n plus external-runner stack. Publish only the internal three-node sheet tool during use, keep the form/agent workflow unpublished, and unpublish the tool at close. A live editor-form run on n8n 2.41.5 rejected Revision 4's unpublished database tool; the agent still claimed success. Require the tool result and downloaded file, not the parent execution's success flag.

**Revision 4:** 2026-10-04 — introduced the n8n AI Agent connected to OpenRouter and the tool that writes `white-rack.xlsx`. Revision 5 corrects its tool-publication constraint. Revision 3's 13-node router, its screenshots, and its exact-restore evidence are historical, not the active instructions.

**Active capability:** build one unpublished workflow on local n8n 2.41.5. A Basic LLM Chain calls OpenRouter with the learner's own key and returns one row per lot. Convert to File writes `white-rack.xlsx` on that same execution. The learner downloads the file and checks that it contains each source lot once. The key stays in the n8n credential store. Text in the model node is not the spreadsheet. Notes inside the batch are not rules.

The sections below through Revision 3 describe the retired router. Do not teach them as the current lab.

# Reference: Module 7 — Operate a fixed workflow through change

**Revision 3:** 2026-10-02 — native local n8n construction, exact comparisons, and verified export restoration.

**Scope:** two fictional 80-lot waves, about three hours. This is a planning estimate, not a measured learner-completion time. The course is ungraded.

**Capability delta:** a learner who can inspect sources and validate a bounded control can now assemble and operate a saved visual workflow, predict the complete effect of one policy change across batches, and recover the independently identified original workflow with byte-exact reruns. Earlier source inspection, prediction, validation, and evidence habits remain prerequisites, not new objectives.

## Active mechanism

Use local n8n **2.41.5**, the full approved official Docker stack, localhost-only browser access, and unpublished workflows. Assistant remains off. No provider key, model call, cloud account, production webhook, custom routing code, host-path upload, or completed learner router import is required.

The learner builds 13 nodes from blank:

1. Upload wave — Form Trigger 2.6, one required `.csv` file named `wave`, multiple files off.
2. Read CSV — Extract from File 1.1, headers and empty cells retained, erroneous records not skipped, Always Output Data on.
3. Pending rule — Edit Fields 3.5, retain inputs and add the fixed String `pending_status`.
4. Check batch — supplied Code 2 validator, Run Once for All Items.
5. Route lots — Switch 3.4, ordered case-sensitive String equality, first match only, extra fallback, type conversion off.
6. Rack hold — Edit Fields 3.5, `hold,RESOURCE_CONFLICT`.
7. Ready — Edit Fields 3.5, `pass,READY`.
8. Pending decision — Edit Fields 3.5, route expression and retained pending status.
9. Other permit — Edit Fields 3.5, `hold,OPEN`.
10. Collect routes — Merge 3.2, Append, four distinct inputs; branch Always Output Data stays off.
11. Original order — Sort 1, numeric `_row` ascending.
12. Receipt fields — Edit Fields 3.5, only `lot,route,status` in that order.
13. Make receipt — Convert to File 1.1, native CSV, header on, execution-specific filename.

Validation reads `$('Read CSV').all()` and `$input.all()`. It requires exactly five ordered original columns, unchanged source count/order/values, and only the appended policy field. Source-supplied `pending_status`, extra/missing/reordered columns, invalid dispositions/exceptions, cancelled lots without WITHDRAWN, duplicate/blank/unsafe lot IDs, and invalid or mixed policy values stop before routing. Lots exclude comma, quote, and ASCII controls. Unknown permit strings remain valid fallback data. `_row` and item linking preserve original order; validation does not route or repair inputs.

The separate supplied six-node checker uses Form Trigger 2.6, parallel Crypto 2 SHA256 hex hashes, a three-input Merge 3.2 by position, Code 2 comparison, and Convert to File 1.1 JSON. Upload comparison enters Merge input 1 directly; Hash baseline enters input 2 and Hash actual input 3. Crypto drops binary data, so the direct path preserves uploads. Code uses `this.helpers.getBinaryDataBuffer`, never a metadata/base64 shortcut. A successful green execution may contain a comparison HOLD.

Import adds nodes to the open canvas. The checker and restored router each require a **new blank workflow**. Restoration is not a manual reversal of the changed field.

## Case and protected expected effects

White Rack carries refrigerated reagent kits from Icehouse Depot to Clinic I-6. Lots are `LW-01`–`LW-80`. Source columns are `lot,permit,gate_window,input_disposition,resource_exception`.

Routing is exact and case-sensitive: RACK_CONFLICT first; otherwise AUTHORIZED; otherwise PENDING; otherwise fallback. Gate windows and dispositions are provenance only. CANCELLED requires WITHDRAWN but is not a routing branch. The saved policy changes only from `OPEN` to `NOT_AUTHORIZED`; every other parameter, wire, and input stays fixed.

- Both core waves: only `LW-12`, `LW-28`, and `LW-41` change from `hold,OPEN` to `reject,NOT_AUTHORIZED`; 77 serialized rows remain identical. `LW-19` and `LW-55` remain rack holds. Baseline wave receipts are byte-identical.
- Revised input with OPEN fixed: `LW-12`, `LW-44`, and `LW-60` change; 77 rows remain identical.
- Revised input fixed, policy changed: `LW-28`, `LW-41`, `LW-44`, and `LW-60` change; 76 rows remain identical.

These are staff answers, not learner downloads or pre-prediction demonstration content. Learners derive and freeze their own per-wave and optional revised-wave delta CSVs before routing. The checker contains no answer set.

## Exactness and restoration contract

An exact comparison requires complete file-byte equality. Predicted-change comparison accounts for every row and preserves count, order, header/BOM, quoting style, lot serialization, and record terminators. Every declared before/after pair must match and actually change; every undeclared serialized row remains identical. A header-only delta means zero changes, not a missing prediction. Malformed UTF-8/CSV, duplicate lots, missing/reordered rows, omitted/wrong predictions, and unpredicted byte changes HOLD. Files must not be normalized to pass.

Preserve the original export before the policy edit and retain its separate initial `file-identity` report. Initial equality yields `initial_record_only`; it is not restoration proof. Before import, supply the **original retained** SHA256 as `expected_sha256` and require `matched`. Equal replacement files cannot redefine the baseline. Preserve a separate changed export, then import the verified original into a new blank workflow and compare both reruns against their corresponding original receipts.

The retained native baseline is `native/router-baseline.json`; its original SHA256 is `3d02aef9cb8da98a61e992609375fd91b0fc5d8b7d9e903e9f681f354ccc67df`. `native/router-changed.json` differs in only Pending rule's node configuration; export version metadata also changes. These exports remain staff-only.

## Observed native evidence

`../evidence/native/runtime-proof.json` records native execution IDs, reports, node versions, boundaries, and limits. The same directory retains eight exact browser-downloaded receipts and 24 downloaded comparison/identity reports. Staff predictions are in `native/delta-core.csv`, `native/delta-revised-input.csv`, and `native/delta-revised-policy.csv`.

Observed on macOS arm64 Docker Desktop: Docker 29.7.2, Compose v5.4.0, n8n 2.41.5, managed Chromium, bind `127.0.0.1:5678`. The router was constructed through the UI, the original export hashed natively, both waves run under both policies, the original digest rechecked, and both restored receipts matched exactly. Revised-input and policy-only comparisons each accounted for all 80 rows. All four empty-branch cases preserved the expected rows and source order without fabricated records. Invalid CSV/schema/IDs/disposition/exception/cancellation/policy cases stopped before routing. Native comparison negatives held for unpredicted changes, missing/reordered/duplicate rows, wrong schema, BOM/newline/quoting changes, malformed CSV, wrong/omitted predictions, and a tampered replacement baseline.

The 40 published PNGs are actual n8n captures covering all 35 numbered construction/operation steps. Construction captures use verified native settings with execution output cleared where needed; they are not synthetic UI diagrams. Reports appear after the prediction instructions. Screenshots are context, not substitutes for retained downloaded bytes.

Browser automation input, clipboard, and download failures were corrected before final evidence. Native platform execution is limited to this Apple Silicon host. Windows/WSL, Intel macOS, Ubuntu, Arch, and Windows Arm remain unexecuted natively. Learner performance and completion times remain unobserved.

## Publication and history

The website publishes the owning overview/lab, their PNGs, and only five raw exercise files: three source CSVs, `validate-batch.js`, and `receipt-checker.json`. Completed routers, controls contracts, staff answers, reference/evidence, and historical fixtures are excluded by `course.json`. Module 7 preparation copies those same five inputs; it does not launch a Python router. Control regressions execute the shipped Code bodies, while native evidence establishes the real graph behavior.

Revision 1 (2026-08-23) used a thin three-lot case. Revision 2 (2026-09-30) introduced the 80-lot packet with a supplied Python router, RULE.md policy, and rule-file restore. Revision 3 retains the case facts but retires that executable mechanism, its callers, and its SVG figure specification. Existing `tests/expected/`, `reviews/`, and the older evidence transcripts remain historical; they are not native n8n proof or the active answer contract. Historical raw evidence is not rewritten to imply a current pass.
