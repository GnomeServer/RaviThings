# Module 10 — Stand up and package a local uncensored AI

**Serves oracle:** S04, S09, S10, S14, S20, S21, S22, S23  
**Primary objective:** PO-10 — Stand up and package a local uncensored AI
**Prerequisites:** Earlier source verification, bounded controls, and recovery skills; a preflighted environment; and this module's supplied task. Establish Hugging Face account access and accept the model's conditions during the session.
**Consumes:** VERIFY:PREFLIGHT; VERIFY:CASE; VERIFY:TRANSFER_TASK  
**Produces:** LOCAL_MODEL_SERVICE; PO10_RESULT  
**Rough time:** about 3 hours  
**Performance stage:** Transferred  
**Work surface:** A real local-model service on the learner's own laptop, operated through prompts copied into ordinary OMP (the coordinator); the learner approves access, download, each launch and each stop, and OMP starts and stops its own managed service  
**Practical work:** Stand up the pinned uncensored model on the learner's own laptop under OMP orchestration (account, download, live bring-up under an owned managed service, interaction, stop/restore), freeze a digest-checked eleven-file kit copy excluding weights, and run the package structure check from a fresh terminal and new OMP conversation. ~180 min Thursday allocation (unmeasured). All individual in-session work on own laptop.
**Performance evidence:** Verified weights identity, loopback-only service proof, live-interaction transcript, stop/restore receipts, byte-identical restore comparison, frozen bundle record, digest-checked copy, fresh-terminal structure check, and close-out.
**Failure / HOLD:** Hold the affected work for gated access not accepted, wrong-size or wrong-hash weights, insufficient hardware, a bind beyond loopback, public exposure, or a forced pass. If access, download, hardware, or time prevents completion, record the reason and close the attempt within the session; no outside-session continuation is required.
**Scope boundary:** Live identity, interaction, and stop/restore evidence proves only the local runtime behavior exercised. The separate structure check confirms named files and fields in the fresh copy; it does not execute commands or prove runtime behavior. Neither establishes production fitness, safety-stack completeness, or model quality.
**Handoff:** The learner retains the kit and evidence. The package's `Next owner` field names the same learner, not another participant or instructor.
**Case family:** [CASE_FAMILY.md](../../CASE_FAMILY.md). This module runs real software under its own bounded-use rule instead of a fictional logistics movement; its independence rule is unchanged. This module's gate does not consume another module's product.  

## Why

Saved artifacts are the claim. A local uncensored model is finished when it runs live on the learner's machine under verified identity, survives stop/restore without conversational memory, and the supporting kit of instructions and controls (everything except weights) passes structure check from a fresh terminal copy without the author's chat history.

## Enabling objectives

1. Operate the local model end-to-end under OMP (live identity, interaction, stop, restore).
2. Package the local-runtime instructions and controls so the kit has no undeclared dependencies and the structure check passes from a fresh terminal.
3. Distinguish live runtime proof from structure-only evidence in the close-out.

## Check the work

A clean individual session uses the learner's work folder. The learner copies prompts into ordinary OMP. OMP executes the mechanical steps. The learner freezes the declared eleven-file bundle, makes a digest-checked copy to fresh location `F`, opens a new terminal and a new ordinary OMP conversation in `F`, runs `scripts/check_package.py shared/PACKAGE.md`, records the observed result. The structure check reads named fields and confirms files inside `F`; it does not run commands. PO10_RESULT records verified identity, live interaction, stop/restore receipts, byte-identical restore comparison, frozen bundle, digest-checked copy, fresh-terminal structure check, and unresolved limits.

## Supplied-case domain (adapter)

The pinned model is `orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF`: a single 15.7 GB weight file, Apache-2.0, abliterated (uncensored) base, access-gated on Hugging Face. llama.cpp serves it loopback-only; OMP drives it through a generated provider overlay; the adapter scripts verify the pinned identity, wire the overlay, probe reachability, and prove the stopped state. A bind beyond loopback and an unserved capability claim are the core adverse cases. The transfer bundle carries everything except the weights. Weights stay at the learner's original location; no re-download for the structure check. The learner answers the "Next owner" field by recording retention of ownership.
