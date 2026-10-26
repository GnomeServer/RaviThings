# Module 7 facilitator runbook

The learner builds one unpublished n8n workflow. It reads the White Rack batch, asks a model for one row per lot, and writes a spreadsheet. The downloaded file is the result. Text in the model node is not. The sheet does not authorize a real movement.

## Prepare the room

Allow about three hours on Wednesday. If the run cannot finish, preserve the execution and record `HOLD`. Do not type the spreadsheet for the learner, publish the workflow, or switch them to n8n Cloud.

Confirm n8n 2.41.5 and its matching external task runner on the [staff-prepared two-service stack](../../module-00-setup/facilitator/RUNBOOK.md#local-n8n-readiness), localhost-only access, actual Code-node execution and saved-workflow persistence. Keep n8n Assistant off. Assistant is not the workflow. The OpenRouter key goes only into the n8n credential form. It must not appear in a prompt, export, screenshot, or note. If an export contains the key, the learner deletes that copy and revokes the key.

Learners need `wave1.csv`, `SHEET_RULES.md`, and `scripts/check_sheet.py` from the lab.

## What to watch

One workflow: Upload wave → Extract from File → One batch → Fill the rows → Rows → Convert to File. Fill the rows is a Basic LLM Chain with an OpenRouter chat model and a Structured Output Parser. Do not let them add an AI Agent node. That node requires a tool, and a tool is a second workflow.

The model chooses the row values. Convert to File writes `white-rack.xlsx`. A green model node is not the file. Download from Convert to File on the same execution. The workflow stays unpublished.

The checker prints `PASS: sheet has the 80 source lots` when the download has each source lot once. REVIEW lines and the learner's notes cover rows the rules reject. A note inside the batch is not a rule.

## Close

Look for the attempt folder, the workflow name, the execution the file came from, the download, the checker output, and a note naming wrong rows. No score. An unfinished run stays `HOLD`.

## Operational readiness notes

See Module 00 facilitator runbook for shared staff operational procedures, T-relative schedule, privacy-safe register, platform matrix, and evidence collection. This module: one unpublished workflow, the downloaded sheet, and checker PASS.

Record machine, source hashes, outcomes, and HOLDs for the published controls. No blind provider retry.
