# Combine accepted handoffs

You are the sole writer of the fictional CS-2 combined brief. The required specialist handoffs have already passed the independent saved-evidence checks. Do not delegate or schedule review.

Use course_read on ALL four logical paths before writing:
- accepted-handoffs.json
- shared/case/inventory.json
- shared/case/authority.json
- shared/case/timing.json

For each source, follow current_revision and explicit supersedes, not the greatest recorded_at. Reconcile each handoff against its current source. The accepted-handoffs object is keyed by specialist; each entry preserves attempt_id, child_id, report and fingerprint. Do not replace these identities with your own run identity.

Write one JSON object, using course_write exactly once to out/status-brief.json. No Markdown, extra keys or other output files. Required fields:
- movement: "CS-2"
- quantity_scanned and quantity_usable: current inventory integers
- release_status: current authority release_status
- not_before: current timing ISO value
- decision: "HOLD" if any rule below holds, otherwise "READY" (class-only, never real authorization)
- decision_reasons: each applicable code, once: INVENTORY_UNUSABLE if quantity_usable is zero; AUTHORITY_HOLD if release_status is not RELEASED; TIMING_NOT_OPEN if not_before is after the shared decision time
- evidence: object keyed inventory, authority and timing. Each value has exactly attempt_id and child_id from that original handoff, source_id and revision from its report, and sha256 from its report.source_sha256.

If a required input is unavailable or contradicts its accepted handoff, stop without writing and report the concrete discrepancy. Do not manufacture missing facts. After a successful write, state that independent review and a human use decision remain required.
