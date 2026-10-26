# Module 5 · Orchestrate an OMP agent team

Three specialists can finish three assignments without producing one usable answer. The missing work is often at the join: an input nobody received, a source revision nobody reconciled, or a review that ran before the candidate existed.

For fictional Copper Span, vehicle CS-2 carries IV fluid cases from Basin Depot to Clinic F-9. Inventory, release authority and timing belong to separate records. Direct a read-only specialist for each, preserve their source identities, and give one coordinator ownership of the combined brief. A separate reviewer checks the actual candidate before your use decision.

[Run the Copper Span workflow](shared/MODULE_05_LAB.md) · [Native OMP orchestration reference](shared/ORCHESTRATION_GUIDE.md)

## What changes when you direct a team

- Separate work that can run independently from work that must wait. Give every child a complete brief, exact inputs, explicit limits and an acceptance condition.
- Operate native OMP fan-out and dependent fan-in. Trace requested work to actual child execution and returned evidence; resolve disagreements through sources, not votes.
- Preserve partial success. Repair only invalidated assignments, retain attributable unchanged results, and recheck the work that depends on the repair.

Bring the source-verification, saved-instruction and single-assistant permission practices you already use. The additional responsibility is the dependency and ownership boundary **between** agents.

## One graph, explicit joins

![Coordinator dispatches three read-only specialists. Required handoffs join before one writer combines the brief; independent review precedes the human decision.](shared/figures/m05-work-graph.png)

<details markdown="1">
<summary>Figure text</summary>

“Run independent work together.” Coordinator, Complete briefs, branches to Inventory, Authority and Timing, each Read-only. All feed Accept all required handoffs. Then Combined brief, One writer; Independent review, Read-only; Human decision, Use, revise or hold. “A task batch does not define the order of dependent work.”

</details>

The first native wave contains a real missing-input boundary. Two specialists can return usable work while the third remains blocked. Finishing the batch is not permission to integrate an incomplete set.

## Repair without erasing the first attempt

![Inventory and Authority results remain reusable if unchanged. Blocked Timing leads to a corrected assignment and Timing-only rerun, followed by downstream rechecks.](shared/figures/m05-partial-recovery.png)

<details markdown="1">
<summary>Figure text</summary>

“Recover only the affected work.” Inventory result and Authority result each say Preserve evidence and lead to Reuse if unchanged. Timing blocked, Missing input, leads to Correct the assignment and Rerun Timing only. All valid paths feed Recheck the combined brief and its review. “Keep the original blocked attempt.” “Changed inputs invalidate the work that used them and every result built from that work.”

</details>

An unchanged report retains its original producing attempt and child identity. A new timestamp is not evidence of new work. A changed source or assignment invalidates its consumer and dependent results—not unrelated analysis.

## A checked brief is not movement authority

The specialist reports, combined brief and independent review remain distinct artifacts. A technically accepted brief can correctly say HOLD. Keep your human use decision separate from the agent's completion message and the checker's PASS.

All names, quantities, times and decisions are fictional. No result plans or authorizes a real movement.
