# Cold Foundry review verdict — 2026-10-03

## Commands and evidence

Offline:
- `python3 tests/test_module_10.py` — 93 behavior checks, 0 failures.
- `python3 tests/test_adequacy.py` — 20 mutations, 0 survivors, 0 unapplied.
- `node scripts/render_figures.mjs --check` — 70 figures byte-identical, links resolve.
- `python scripts/check_course.py` — all 29 scoped gates pass; `build_course.py --check` verifies the published site byte-for-byte.

Real-weights lane (operator account `TheHolofex`, gated conditions accepted):
- Download: `hf download orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF` — exactly 15,676,553,472 bytes.
- Real SHA-256 recorded into the shipped `model-card.json`: `4ab6bdf8a9008869abf1630fb92d04b5439805f96b56692962fa240b1d439977`.
- Adapter `verify` on the real weights: `PASS: pinned weight identity verified`.
- `wire`: loopback-only overlay (no non-loopback address in any output).
- llama-server bring-up on `127.0.0.1` at 32K context; model loads (262,144-token trained context confirmed); probe `PASS: local service reachable on loopback`.
- One real OMP interaction: provider `llama.cpp`, model `OrcaSAQ-2-27B-Uncensored`, `stopReason: stop`, real reply text.
- Stop: service killed, probe `HOLD: service is not reachable` (exit 1), stop receipt naming the port, `PASS: service is stopped and unreachable on loopback`.
- Restore: relaunch, probe `PASS`, wire outputs byte-identical (overlay identical byte-for-byte; launch JSON identical modulo the work-dir path). Final stop-state proof repeated after teardown.
- The operator's own pre-existing llama-server on port 8080 was never touched; the validation used a separate port and was torn down after the run. The user's OMP models configuration was restored to its original content and verified registering `llama.cpp` and `ochi` as before.

Small-model lane (Qwen2.5-0.5B stand-in, earlier session): every mechanism independently reproduced end to end.

## Review outcomes

| Dimension | Verdict | Evidence |
|---|---|---|
| Runtime/security | EXCELLENT | Loopback constant pinned; 3-second probe bound; atomic exclusive publication; control checked before and during every action; path confinement intact; banned tokens enforced |
| Curriculum/voice | EXCELLENT | Zero banned tokens across learner surfaces; zero meta commentary; every command-bearing section carries Expected/Stop/Recovery in both shells |
| Publication/UI | EXCELLENT | All command blocks labeled; 29/29 gates green; site byte-for-byte; figures regenerated and verified |
| Transfer honesty | EXCELLENT | Technical replay and independent-person attempt recorded separately; unobserved ≠ passed in every surface |
| Uncensored-boundary honesty | EXCELLENT | No self-guarding claim anywhere; guardrails assigned to the operator in rules, lab, package, and reference |
| HOLD discipline | EXCELLENT | Every refusal path names its specific reason; no silent exits; no residue |
| Real-model identity | EXCELLENT | Pinned size + digest enforced and now exercised against the real 15.7 GB weights |

## Limits

Class F and the human panel remain unmeasured. The independent-recipient attempt remains unobserved until a real person operates the kit; per course doctrine that is not a pass.
