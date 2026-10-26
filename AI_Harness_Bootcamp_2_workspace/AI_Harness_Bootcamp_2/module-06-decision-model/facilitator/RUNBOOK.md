# Facilitator runbook — Module 6 Blue Gauge

The learner opens ordinary Oh My Pi in the module directory. Oh My Pi remains the chat agent. They paste the TypeSafe skill install prompt, then tell the agent to call `jev-1.13` through OpenRouter with the existing `OPENROUTER_API_KEY`. They do not create a TypeSafe key, set an Oh My Pi judge role, or start `scripts/blue_gauge.py`.

## Before class

1. Confirm Oh My Pi starts and `omp --version` prints `omp/<semver>`.
2. Confirm `OPENROUTER_API_KEY` is set and can reach `typesafe/jev-1.13`. If the key or model is missing, hold the live Jev calls. Do not create a TypeSafe key or substitute `jev-latest`.
3. Keep reference materials to yourself.

## Route

| Clock (approx.) | Work | Observable |
|---|---|---|
| 0:00–0:20 | Start Oh My Pi and install the TypeSafe skill | Session open; skill loaded; OpenRouter `jev-1.13` agreed; key not printed |
| 0:20–1:00 | Section 1, speculative fan-out | One multi-question API call per message; ignored answers marked |
| 1:00–1:30 | Section 2, confidence-gated routing | Two gates on saved answers; no new API call for the comparison |
| 1:30–2:10 | Section 3, composite scoring | New order from saved scores; no new API call |
| 2:10–2:25 | Section 4, intent routing | Lookup, comparison, and human path are distinct; approvals come to the learner |
| 2:25–2:40 | Section 5, hallucination check | Missing quote needs no Jev call; a found quote is supports, contradicts, or says nothing |
| 2:40–3:00 | Section 6, keep the chat model off closed decisions | Five notes compared from API usage; gate change adds no call; lookup does not call the chat model; missing cost is not recorded |

Clock marks are planning guides. The day's clock is in `COURSE_MAP.md`.

## Coaching boundary

You may point to a desk rule, a source file, or the skill install prompt. Do not write the questions for them, set the Oh My Pi judge role, or start the Python launcher. Record assistance as an observation, not a learner score.

## Hold

- The OpenRouter key is missing, or `jev-1.13` is rejected: hold the live Jev calls.
- The agent asks for a TypeSafe key, uses `jev-latest`, makes Jev the chat model, prints the key, or writes the key into a file: stop that path and return to the lab.
- A route, score, handler result, or token count is treated as cargo clearance, flight acceptance, or dispatch: stop and return to the desk rules.
- The notes are pasted into the chat, Jev is used as the chat model, or a missing cost is written as zero: stop that path and return to the lab.
