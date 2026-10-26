# Module 4 — Decide with typed questions

**Serves oracle:** S04, S07, S09, S14, S18, S19  
**Primary objective:** PO-04 — Decide with typed questions  
**Prerequisites:** Preflighted accessible environment and this module's supplied case  
**Consumes:** VERIFY:PREFLIGHT; VERIFY:CASE; VERIFY:QUESTION_SET; VERIFY:DECISION_CONTROLS  
**Produces:** TYPED_ANSWERS; LABEL_AGREEMENT; CONFIDENCE_GATES; ROUTED_REQUIREMENT; PO04_RESULT  
**Rough time:** about 2½ hours  
**Performance stage:** Independent  
**Work surface:** Typed question set, read-only decision run, and code-owned router  
**Practical work:** Build the state from the supplied case, read the seven typed questions and state which judgment each isolates, add one yes-or-no question of your own and check the file, label a fixed ten-message sample and freeze it, run the pinned model once as a read-only decision function with the contract as the saved instruction, validate every typed answer against the question set, measure agreement with the frozen labels and adjudicate every disagreement against the desk rules, set the routing gates from the measurement, route all forty messages in the supplied router, decide the REFER, REVIEW, and CLARIFY queues, and hand off a requirement line that names the messages each count rests on. The stretch runs the function a second time and measures flipped answers.  
**Performance evidence:** TYPED_ANSWERS validated from a read-only receipt, the labels digest frozen before that run, LABEL_AGREEMENT with adjudicated disagreements and the highest declared confidence among wrong answers, CONFIDENCE_GATES set from that measurement, ROUTED_REQUIREMENT recomputable from the answers and the gates on disk, a handoff that addresses every queued message, and the verifier's joined result.  
**Failure / HOLD:** Hold when a supplied case file, the contract, the prompt, or a supplied question was edited; when the run had write authority, started before the labels were frozen, saw different labels on disk, or skipped the state or question file; when a reply strays from the answer sets and is edited instead of preserved; when labels change after the freeze; when gates change after the last routing; when a queued message is missing from the handoff; or when the handoff states more than one decision.  
**Scope boundary:** Proves that typed answers from one run were validated, measured, and routed in code for bounded internal use; it does not establish the model's accuracy beyond the labeled sample, does not calibrate declared confidence, and does not authorize a pick, a dispatch, or a change in who may approve.  
**Handoff:** Give the desk lead the requirement line with its source messages, the three queues with the clerk's proposed handling, the agreement table and gate settings, the authority change as the lead's decision, and the limit that declared confidence is the model's claim.  
**Case family:** [CASE_FAMILY.md](../../CASE_FAMILY.md). The adapter supplies a self-contained case in that family. This module's gate does not consume another module's product.

## Why

Volume desk work needs judgments software can act on. A broad question answered in prose hides several judgments behind one answer and leaves the decision inside the model. Atomic typed questions expose each judgment, let code combine them with rules a person can read, and make the model's answers measurable against a person's own.

## Enabling objectives

1. Work with atomic questions with fixed answer sets: say which judgment each supplied question isolates, and add one that isolates a judgment the set does not cover.
2. Run a general model as a side-effect-free decision function under a saved contract, with receipts that show what it read and that it wrote nothing.
3. Validate typed answers mechanically and preserve a reply that strays, instead of repairing it.
4. Measure declared confidence against labels written before the run, and set a gate from the measurement rather than from the declaration.
5. Route in code, and name the decisions that stay with a person.

## Check the work

Confirm from the receipt that the run was read-only, read the state and the question file, and carried the contract as its saved instruction. Confirm that the labels digest predates the run and that the agreement file is the comparison of those labels with the validated answers. Recompute the routing from the answers and the gates on disk and compare. Read the handoff for every REFER, REVIEW, and CLARIFY message and for the authority change recorded as the desk lead's decision. Record the result in PO04_RESULT. No pick, dispatch, or authority change is claimed.

## Supplied-case domain (adapter)

Chalk Line is a vehicle resupply of sterile surgical gloves from Ferry Depot to Clinic K-3 on vehicle CL-9, leaving at 15:00 MDT on 8 October 2026. Messages CL-001 through CL-040 are the shift's intake pile. The catalog has four lines by glove size; a box is the unit of issue and a case is ten boxes. Only the Clinic K-3 administrative officer's approval, or a K3-REQ reference, carries authority.

The question set asks seven questions per message: is it a request, which line, which quantity candidate, how urgent, does the administrative officer's own message carry authority, does it instruct the desk, and which earlier message it replaces; the learner adds an eighth yes-or-no question that the router ignores. Quantity candidates are found by software, so a quantity is chosen, never typed. The router applies supersession (counted only from messages that are not themselves referred and only when the link's declared confidence reaches the gate), the instruction gate, the request gate, usability, the authority gate, and a confidence gate, in that order.

The pile holds one hostile note that calls itself approved and asks to be hidden, one legitimate change to who may approve that still belongs to the desk lead, twelve supersession links, three unit traps, two messages for another clinic, one Zulu timestamp, one quoted request inside a no-action message, and three locally true messages that are not requirements. The staff key stays outside every learner download.
