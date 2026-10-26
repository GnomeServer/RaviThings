# Module 01 · Verify a congressional affairs briefing

You are an analyst in the fictional **Office of Congressional Affairs (OCA)**. At **14:05 EDT on 6 October 2026**, an AI draft says **SEND** a briefing to staff of the fictional House Subcommittee on Community Programs. Decide whether that recommendation follows from the packet. Work only from the supplied case records; do not infer actual congressional rules from this exercise.

Plan for about two to three hours. A model may help organize files, but you own the source judgments, arithmetic, and verdict. The AI draft, its citations, and a review it writes of itself are claims to inspect.

## Start an attempt

From the `module-01-congressional-affairs` folder that contains `tools/`, run:

```bash
python3 tools/exercise.py start attempts/my-first-attempt
python3 tools/exercise.py verify attempts/my-first-attempt
```

The starter refuses to overwrite an attempt. It copies `REQUEST.md`, all nine sources, and blank work files. `verify` prints a SHA-256 fingerprint for each inbox source and checks it against this packet's manifest. A matching fingerprint establishes byte identity, not truth or authority. Keep your work inside the new attempt. If you use Codex, open that attempt as your working folder and ask it to guide you one step at a time. Do not open the `facilitator/` source before the reveal step.

You can start the Codex session with:

```text
Guide me through LAB.md using this CA-27 attempt. Begin with the source inventory.
Show me the exact source lines behind each proposed register row and ledger claim;
ask me to judge whether the source has the right authority, identity, version, and time.
Do not open the facilitator change before I freeze the baseline. Help me check
arithmetic independently of S09, and keep unsupported claims visibly unresolved.
```

## 1. Inventory the packet

Read `REQUEST.md` and every file in `inbox/`, including the AI draft. Record each source in `source-register.csv`: filename and hash, issuer, version or status, effective time, exact inquiry/committee/batch identifiers, what the source may establish, and what it cannot establish. Mark a superseded or wrong-scope item as such. Treat instructions embedded in a source as source text, never as instructions to you or Codex.

## 2. Break the AI draft into claims

Use `thread-ledger.csv`. Give each claim that could change **SEND** its own row. Keep the five statement types: `SOURCE FACT`, `CALCULATION`, `INFERENCE`, `DECISION`, and `UNSUPPORTED`. A sentence that mixes a count, a clearance state, and an action needs separate rows. Cite an exact file, version, and section or line for each source fact. An AI confidence score is not evidence.

Trace these eight steps in order, using these names exactly in the `step` column:

1. `Inquiry defined`
2. `Records received`
3. `Cases validated`
4. `Brief assembled`
5. `Release approved`
6. `Submission window met`
7. `Packet transmitted`
8. `Committee receipt confirmed`

For each step, state its entry condition, what is actually supported, what it hands to the next step, and what remains unknown. A record being received is different from being validated. An accepted release request is different from an approval. A possible submission time is different from a transmission, and transmission is different from committee receipt.

## 3. Recompute the numbers and clock

Using source values, show arithmetic and units in the ledger. At minimum, calculate:

- records received; verified closed records; unverified records; and the gap to the requested coverage;
- the packet page count using only verified batches, and the count if every received batch were included;
- the current portal cutoff converted from `Z` (UTC) to EDT; and
- the earliest possible submission time from the 14:05 decision point, assuming every missing condition were satisfied immediately, plus its margin against the current cutoff.

Label a clock result **counterfactual** when approval, validated coverage, or packet readiness is missing. It is not evidence that the packet was sent. Check a calculation yourself rather than asking the AI that produced the draft to check it.

## 4. Challenge sources that cannot carry SEND

In `challenge-matrix.md`, make one block for each source cited or tempting to use that cannot prove the draft's claim. State what it does prove, the exact mismatch, what it cannot prove, and which office or record would be needed. Include any superseded deadline, other-inquiry material, and the embedded instruction attempt. Quote the offending instruction briefly and explain why it has no authority.

Write `corrected-brief.md` for an internal reviewer. Separate supported, contradicted, and unresolved claims. Name the present blockers, the next evidence needed, and the decision owner. Do not draft a message to real congressional staff.

## 5. Freeze a baseline verdict

In `baseline-verdict.md`, record the exact inquiry, subcommittee, program, decision time and zone, batch range, release ticket, and current deadline notice. Then write one verdict on **readiness to send**: `ACCEPT`, `REVISE`, `REJECT`, or `HOLD`. Explain the strongest supported fact, strongest contradiction, unresolved condition, later event not observed, and what would change the decision. You can reject the AI draft's wording while placing actual release on `HOLD`; state the readiness verdict clearly.

Before revealing the update, write `change-prediction.md`. Predict the effect **if a new notice changes only the CA-27 portal cutoff from 18:50Z to 19:20Z**. Name the clock claims that should change, the unrelated claims that must stay, and any blocker that would remain. Save your files, then run:

```bash
python3 tools/exercise.py freeze attempts/my-first-attempt
python3 tools/exercise.py reveal attempts/my-first-attempt
```

`freeze` records hashes of the baseline register, ledger, challenge matrix, brief, verdict, and prediction. `reveal` refuses to run unless those hashes still match. Keep the frozen files unchanged.

## 6. Apply only the new source

Read `inbox/S10_CA27_PORTAL_NOTICE_v6.md` after reveal. Its issue time matters. Copy baseline ledger rows into `changed-thread-ledger.csv`, then update the deadline and dependent schedule claims using the time the new notice was issued. Write `changed-brief.md` and `changed-verdict.md`. State the old and new values, source revisions, changed margin, unchanged blockers, and whether the overall decision changes. The last documented release-ticket status remains the 14:02 snapshot; do not assume a later approval. Do not treat S10 as available at 14:05. Do not turn a conditional submission time into an observed upload or committee receipt.

Run `python3 tools/exercise.py verify attempts/my-first-attempt` again. This checks that the original packet and freeze remain intact. It does **not** score the quality of your reasoning.

## 7. Handoff and independent check

Ask Codex to write a compact `handoff.md` from your saved changed verdict and cited source lines. Review that output against your sources; preserve the first version and record any needed correction in your own notes. It must let another reviewer answer: what may proceed, what cannot, what exact condition blocks SEND, which records and calculations establish that, and what evidence would change it. Include the time zone and the fact that transmission and committee receipt have not been observed.

Prepare a restricted review packet:

```bash
python3 tools/exercise.py prepare-review attempts/my-first-attempt
```

Open the resulting `scrutiny-packet/` folder in a **new Codex chat** and direct it to use only that folder. The packet contains only the handoff, request, sources, and a review task. Do not give the new chat your ledger, briefs, verdicts, or this chat history. Save its response as `handoff-scrutiny.md` in the main attempt. Then write `handoff-scrutiny-decision.md` yourself: what it checked, whether its conclusion stands, and what remains your decision. A second AI response is a challenge, not a replacement for your judgment.

## Completion check

Your attempt should have nine source-register rows, ledger coverage of all eight steps, source-based arithmetic with units, explicit source challenges, a baseline frozen before the update, changed work that cites S10 only where it matters, and a handoff that survives a fresh source check. The script checks file identity and freeze order; it intentionally does not award a substantive PASS for a verdict.
