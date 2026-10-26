# Module 00 — Get a long document you can trust from AI

**Serves oracle:** S04, S06, S07, S08, S09, S10, S19  
**Primary objective:** PO-00 — Get a long document you can trust from AI  
**Prerequisites:** Preflighted accessible environment and this module's supplied case  
**Consumes:** VERIFY:PREFLIGHT; VERIFY:CASE; VERIFY:SUPPLIED_ACCEPTANCE  
**Produces:** MIN_SCREEN; FROZEN_PLAN; SECTION_DRAFTS; REVIEW_FINDINGS; TARGETED_REVISION; PO00_RESULT  
**Rough time:** about 3 hours  
**Performance stage:** Guided to Independent  
**Work surface:** Multi-section status brief drafted through the shared OMP launcher, one session per job  
**Practical work:** Write the brief (which carries the minimum screen) and the tests before any prose; have OMP propose an outline, then correct and freeze it; have OMP draft one section per session; run the supplied practice checker and make it fail on a known-bad copy; list every number and code against the sources; run separate review sessions for tests, facts (questions answered from the sources without the draft), reader actions, and style; verify each finding; revise only the flagged sections; apply one changed fact only where it is used; decide send or hold.  
**Performance evidence:** brief.md and tests.md that predate the outline; outline-proposed.md beside the corrected outline.md; plan.json hashes; per-section receipts; checker results and checker-test.md; number lists; review/r1 files with fixes.md; SAME/CHANGED section comparisons for each revision; change-fixes.md; decision.md and handoff.md.  
**Failure / HOLD:** Hold when preflight, the supplied case, permission, a source, the decision owner, the affected audience, or the acceptance control is missing; when a screen line can't be answered; when the plan changes after drafting starts; when a session's file doesn't match its receipt; when a material finding remains after two revision rounds; or when a reader could take the brief as a release, a pickup time, or a delivery promise. Public practice checks are inspectable.
**Scope boundary:** Proves planned, checked AI drafting of a long document for bounded internal use; it does not authorize consequential release. Structured claim admission, typed judgments, and reviewer ensembles remain Module 08's.  
**Handoff:** Give the next owner the plan, every version, the review findings and decisions on them, the checks run, the observed AI capability and limit, and the send-or-hold decision.
**Case family:** [CASE_FAMILY.md](../../CASE_FAMILY.md). The adapter supplies a self-contained case in that family. This module's gate does not consume another module's product.


## Why

A long document fails quietly: a fact with no source, a section that repeats another, a sentence that promises what nothing supports. One prompt for the whole document hides those failures in fluent prose, and asking the drafting session whether its draft is good mostly returns approval. Planning before prose, one limited job per session, checks against references outside the draft, verified findings, and targeted revision keep each failure visible and fixable.

## Enabling objectives

1. Apply the minimum screen and write a brief, tests, and a corrected outline with facts and word budgets before any drafting, then have the AI draft one section per session within that plan.
2. Check the draft against references outside it — a checker shown to fail on a known error, a number list, and separate review sessions — and accept only findings that rest on a source line, a test, or a style rule.
3. Revise only flagged sections, confirm unchanged sections stay byte-identical, apply one changed fact only where it is used, and decide send or hold from the evidence.

## Check the work

Inspect whether brief.md and tests.md predate the outline, the corrected outline differs from the proposed one where the proposal was wrong, each section stays within its facts, the checker failed on the known-bad copy, every NOT IN SOURCES number was resolved, each accepted finding cites its source line, test, or rule, rejected findings give reasons, only named sections changed in each revision, the changed fact moved only where it was used, and the decision cites files in the work folder. Record these observations in PO00_RESULT. Any unresolved screen item is `HOLD`; polished output can't override it.

## Supplied-case domain (adapter)

A 500–900-word, five- or six-section status brief from the Harbor Depot inventory clerk to the Field Clinic S-3 supply team. It answers the clinic's five questions from six source files: the request, the pen 4 count, the paperwork notice, the release desk status, the yard board, and the clinic's message. It states custody, what a release needs, and what the clinic must not do yet. Not the GO brief.
