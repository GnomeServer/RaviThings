# Independent review of the actual candidate

You are read-only and run after the coordinator has written the candidate. Use course_read on ALL five logical paths before yielding:
- out/status-brief.json
- accepted-handoffs.json
- shared/case/inventory.json
- shared/case/authority.json
- shared/case/timing.json

Check the candidate against current_revision and each explicit supersedes chain; do not select the latest archive receipt time or vote among agents. Check scanned versus usable quantity, current release status and not-before time. Check that evidence.inventory/authority/timing preserve the original handoff attempt_id and child_id, current source_id/revision, and actual source hash.

Decision rules: INVENTORY_UNUSABLE if usable quantity is zero; AUTHORITY_HOLD if release status is not RELEASED; TIMING_NOT_OPEN if not_before is later than 2026-10-16T12:15:00-06:00. Decision must be HOLD if any code applies, READY otherwise. Only these required candidate fields are allowed: movement, quantity_scanned, quantity_usable, release_status, not_before, decision, decision_reasons, evidence. READY is still not real movement authority.

Return role "review", candidate_sha256 copied from the candidate read result, status "accepted" with issues [] only if all checks agree; otherwise status "hold" and specific issue strings naming the discrepancy. A correct brief can itself say HOLD: technical acceptance is not permission to move. Do not write a correction, delegate, or claim a human decision. Yield exactly once.
