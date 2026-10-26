# Cold Foundry staff reference

Scope: design rationale for Module 10, the local uncensored AI capstone. Frozen as staff material; learners see the lab, the service rules, and the package, never this file.

## 1. The need

The course's final capability is self-contained local-model operation and packaging. It extends earlier source-verification, bounded-control, and recovery skills to a real local runtime: an uncensored 27B model downloaded to and served from the learner's own laptop under OMP orchestration. The learner proves the live interaction and stop/restore behavior, then freezes the supporting instructions and controls into a package that carries everything except the weights. A separate fresh-copy structure check verifies named fields and local dependencies, not runtime behavior.

Three design decisions shape the module:

1. **A real model, not a fixture.** The pinned weights are a real Apache-2.0 release with a real identity. Size and digest checks are the learner's first verification behavior, exactly as in professional deployments.
2. **OMP as orchestrator, scripts as verifier.** OMP drafts the launch line and drives bring-up steps under learner approval — the same delegation pattern the course has taught since Module 00. The adapter scripts, not the model and not OMP, decide pass or hold: every claim in the package is checked against bytes and reachability.
3. **The uncensored model as the safety lesson.** The refusal direction is removed by the publisher. The module teaches that guardrails belong to the deployer: loopback bind only, weights that never leave the machine, prompts recorded by the harness, and a named personal boundary on the model's output.

## 2. Case

Pinned identity: `orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF`, a single 15.7 GB weight file `OrcaSAQ-2-27B-Uncensored.gguf` (15,676,553,472 bytes), repository pin `a0ebe1b5ad5c009cd382908585c04b7e9e0cf0c0`, blob `3312a8363a04f039c1825d8efe8c4c0314708a3c`, license Apache-2.0, base `orcarouter/Qwen3.8-27B-Uncensored`, gated `auto` on Hugging Face — login plus accepted conditions required before any download.

The stack: llama.cpp serves the weights loopback-only; OMP drives them through a generated provider overlay pointed at the loopback endpoint; the adapter verifies the pinned identity, generates the overlay, probes reachability, and proves the stopped state. The transfer package carries everything except the weights. Weights remain at the learner's original location for the live work; the kit supports the learner's own fresh-terminal structure check from a digest-checked copy.

The adverse cases are built in, not simulated: a hostile community note that argues for a `0.0.0.0` bind and a skipped digest check; the control file that must disable every command when turned off; the stop receipt that must name the port; and the deterministic re-wire whose bytes must compare equal after restore.

## 3. Transfer practice

What transfers: a bounded, verifiable bring-up procedure with an identity check, a live-interaction proof, a stopped-state proof, a restore comparison, and a package whose structure the check confirms from a fresh terminal copy without the author's chat history. Live runtime proofs (identity, loopback, interaction, stop/restore) are required and separate from the structure check. This is the professional shape of a local-AI deployment kit.

What does not transfer, and the module says so: no claim of production fitness (no serving beyond loopback, no concurrency, no safety stack); no model-quality claim (the quantization is not lossless; the publisher reports 94.4% top-1 agreement with the base); no claim that the model guards itself (it does not refuse, warn, or judge). The uncensored behaviour is the reason the boundary is the operator's, and the module teaches it by observation, not assertion.

If access, download, hardware, or time prevents a required step, preserve the observed evidence, record the affected work as `HOLD`, and close the attempt within the session. Unrun work remains unobserved; a demonstration by someone else is not the learner's operation, and no outside-session continuation is required.

## 2026-10-04 amendment — individual session, no recipient attempt

The owner directed on 2026-10-04 that all work is individual and completed within the session, with no graded exercise, homework, or handoff to another participant or instructor. The learner proves the live runtime, freezes and checks a fresh copy of the kit, and retains both kit and evidence. The weights stay at their original work location, and the structure-only copy check requires no second download or service launch. The package's `Next owner` field names the same learner. The gauntlet prompt and facilitator runbook follow this contract; historical evidence remains unchanged. The digest is recomputed for this amendment.
