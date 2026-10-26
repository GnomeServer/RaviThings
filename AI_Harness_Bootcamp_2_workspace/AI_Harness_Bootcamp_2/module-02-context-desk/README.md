# Module 2 · Build and control a reusable second brain

Turn forty source notes into reusable knowledge without losing their evidence or limits. You start a bounded chain of AI judgments, knowledge organization, and fresh retrieval. The helper saves the results as a provisional revision. You inspect every material answer back to its original sources, then use source-backed feedback to direct a substantive correction in a second, preserved revision.

Plan for about three hours (a rough estimate). Two complete runs use six paid OMP sessions: three for v1 and three for v2, using `openrouter/anthropic/claude-sonnet-4.6`. The missing-rule test and snapshot checks are local. There are no automatic paid retries or ongoing background updates. The exercise is ungraded.

## Start here

Open the [Module 2 lab](shared/MODULE_02_LAB.md). Use the Python, OMP, and local Obsidian you already checked in Module 00.

## Capabilities

- Direct claim-granular AI judgments across the supplied sources into linked, provisional knowledge while preserving evidence, conflicts, unknowns, and source-as-data limits.
- Prove that each AI pass loaded the saved rule and consumed the validated preceding handoff, and that fresh retrieval used only frozen navigation and Knowledge notes, not the source-processing chat or raw packet.
- Give source-backed feedback on one substantive weakness and show its correction in a new content revision and fresh answer that reads and cites the focal note.

Keep applying the source-verification practices from Module 01. AI-processed notes, answers, and machine receipts are not human approval. Your source inspection is independent of the automatic handoffs; no per-note selection or approval unlocks a pass.

## The working files

Forty notes hold fictional paperwork for crate C-44 and vehicle QP-17. The originals stay unchanged in `vault/Sources`. Each revision has its own `Knowledge/REV/` notes, so an old answer's links still reach the old note bytes.

Open `vault` in Obsidian. The AI has only the read-only `course_read` tool and returns structured judgments, a build plan, and answers. Only the helper writes the generated Knowledge, `Reviews/REV-judgments.md`, `Reviews/REV-answers.md`, frozen snapshots, and navigation. You edit `Feedback.md`, not the generated records.

Judgment reads a staged copy of all forty sources. On a revision it also reads frozen prior judgments, the prior build, and your feedback as data. Build reads the validated new judgments and, for a revision, the prior build. Fresh retrieval can read only the chosen frozen `MOC.md` and versioned Knowledge notes—not Sources, feedback, prior processing chat, or judgment files.

The launcher explicitly loads the saved rule from outside each read root before contacting the model. The local file screen flags instruction-like wording; it does not decide which facts are true. The rule keeps quoted orders, generated text, and feedback from granting authority or overriding the evidence boundary.

## Class-only boundary

The names, crates, offices, and quoted blocks are fictional. Results are for class use only. They don’t authorize a release, assignment, dispatch, or real movement.
