# Copper Span figure prompts and provenance

Staff-only record. Not published by `course.json`.

## Generation and review

- Replaced the renderer-repair figures on 2026-10-04 for native OMP orchestration.
- Generator: Codex CLI 0.154.0, built-in `image_gen`, session `01a1082f-55fd-7a61-b036-5be7356fbb6c`.
- Existing course style retained: warm off-white ground, white boxes, neutral borders, ochre connectors, red only for blocked work. These are conceptual diagrams, not screenshots or measured runs.
- The generator rejected an initial work-graph image for a dark background and an incorrect arrow into review. Network failures during generation did not produce accepted evidence. Final images were separately opened and inspected by the maintainer assistant.
- No pixel post-processing. Files copied from the generated PNGs; native dimensions independently checked with `sips`.
- Work graph: all labels present, including four `Read-only` labels; three independent branches join at acceptance; the join leads to the single-writer brief, then independent review, then a human decision. No shortcut or line crosses text.
- Recovery: original inventory and authority evidence feed separate conditional-reuse paths; blocked timing leads only to corrected assignment and timing rerun; all three valid paths feed downstream recheck. No automatic retry loop or rerun of unaffected specialists.

| File | Native dimensions | SHA-256 |
|---|---|---|
| `m05-work-graph.png` | 1536 × 1024 | `4cccf0456593d9cf51aa4f3df3256e6f71ebb031100b771d57f96ae31561ba2a` |
| `m05-partial-recovery.png` | 1536 × 1024 | `ef3497003e760edb181908348cb229ff199ce5a4624e8d4c2d8dcdb71567f847` |

## Shared generation instructions

```text
Use the built-in image_gen tool to generate TWO separate PNG instructional diagrams, each 1536x1024 landscape. Do not write drawing code or SVG. Save the finished images exactly as /tmp/copper-span-omp.Pjp27n/m05-work-graph.png and /tmp/copper-span-omp.Pjp27n/m05-partial-recovery.png. Do not edit repository sources or run tests/builds. Generate actual images, inspect them, and return the two absolute paths. These are conceptual workflow diagrams, not screenshots or measured execution results.

EXISTING COURSE STYLE — applies to both figures. Preserve this established publication style rather than introducing the dark Starzl defense style: flat, clean instructional figure on an opaque solid warm off-white #FAF7F0 ground, white #FFFFFF boxes, thin #C9C1B0 borders, deep ink #2B2A27 text. Muted ochre #9A7B3C for important connectors and boundaries; muted red #A23B2C only for blocked work; muted green #4E6B3A only for accepted/reusable work. No scene, people, computer chrome, decorative icon, texture, grid, vignette, gradient, glow, shadow, 3D or fabricated statistic. One Inter/Helvetica-like sans serif. Sentence case. Title about 42px, labels 26–30px, notes at least 24px. Thin, clearly directed arrows outside boxes and away from text. Small 6px box corners, aligned rows and generous padding. Use the full canvas with safe outer margins. Render only the exact label sets below; do not add step numbers, fake timestamps, PASS claims, logos or extra captions.
```

## m05-work-graph

```text
FIGURE 1 — native independent work followed by dependent review.
Title at top left: "Run independent work together"
Top centered node: "Coordinator" with smaller line "Complete briefs".
Second row has three equal independent nodes: "Inventory", "Authority", "Timing". Each has the exact smaller line "Read-only" (three occurrences total). Branch from Coordinator into each node; no arrows between specialist nodes.
Third row centered, emphasized join box: "Accept all required handoffs". Each specialist has its own directed arrow INTO that box. There is no shortcut around the join.
Bottom row, left to right, three nodes: "Combined brief" (smaller line "One writer"), "Independent review" (smaller line "Read-only"), "Human decision" (smaller line "Use, revise or hold"). A clean routed arrow leads from the join box to Combined brief, then Combined brief → Independent review → Human decision. Do not draw a join-to-review shortcut. The reviewer waits for the actual combined brief.
Bottom footnote, exactly: "A task batch does not define the order of dependent work."
Layout suggestion: title y70; Coordinator y185; three specialists y350; join y540; bottom three nodes y775; note y965. Keep branch/join arrows noncrossing and with adequate vertical spacing. Read-only appears FOUR times total, once at each specialist and once at independent review.
```

## m05-partial-recovery

```text
FIGURE 2 — selective recovery and downstream invalidation.
Title at top left: "Recover only the affected work"
Three vertical lanes left column: "Inventory result", "Authority result", "Timing blocked". The first two have smaller line "Preserve evidence"; Timing blocked has smaller line "Missing input" and a muted-red border. These are conceptual states, not a live receipt.
Middle column: top two boxes align with Inventory and Authority, both labeled "Reuse if unchanged" (two occurrences). Each initial result points only to its corresponding reuse box. Below them, "Correct the assignment" leads DOWN to "Rerun Timing only". Timing blocked points to Correct the assignment. There is no arrow returning to Inventory or Authority.
Right column: one emphasized box labeled "Recheck the combined brief" with second line "and its review". Both reuse boxes and Rerun Timing only feed this box through distinct noncrossing rightward routes joining on its left. No arrow from the blocked state directly to integration.
Bottom left standalone note: "Keep the original blocked attempt."
Bottom footer exactly: "Changed inputs invalidate the work that used them and every result built from that work."
Suggested layout: initial nodes at x260, y300/465/645; reuse/correction nodes at x745, same y positions; rerun below correction at y795; downstream box at x1240, y520. Reserve footer y925–995. Route the three arrows to the downstream box around, not through, other boxes. Do not duplicate Inventory, Authority or Timing rerun boxes. Do not show an automatic retry loop.

Before returning, inspect every label, confirm all arrows follow the specified dependency direction, confirm no line crosses a box/text, and verify every stated label appears with the specified repeat counts. If necessary regenerate to correct structural defects. Do not report completion without actually generating both images.
```
