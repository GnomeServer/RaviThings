# Figure prompts and provenance — module-03-mcp-research

Staff-only record. Not published (absent from `course.json`).

- Generator: `codex-cli 0.154.0` (`codex exec`, built-in `image_gen`). No reference images attached.
- Style: flat light instructional diagram (warm off-white ground, white boxes, thin neutral borders, one ochre accent, muted red only for stop/HOLD, muted green only for allowed). Sentence-case titles and plain-language labels.
- Post-processing: composited onto the opaque `#FAF7F0` ground and saved as lossless RGB PNG at native size; no other pixel changes.
- Run evidence (all attempts, prompts, logs): `~/course-evidence/image-remake-20261003T204449`
- These figures replace an earlier set that used dark, glowing styling and slogan-style labels.

## m03-aggregation

- Title: When combined elements make a product STAFF
- Native size: 1536×1024; published SHA-256: `a1f7e2d249247a97697b64055be90282e338aa9b4b3957836bfd956fb0f1ca37`
- Accepted attempt: 02 of 2
- Earlier attempts were rejected in review for relationship or layout defects; the last revision requirements are included at the end of the prompt.

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional diagram. Do not write code or SVG. Return the absolute saved PNG path.

VISUAL STYLE (strict):
- Flat, clean technical diagram like a figure in a professional training manual or consulting report (think McKinsey/Stripe documentation). 1536x1024 landscape.
- Opaque solid warm off-white background #FAF7F0. No texture, no grid, no vignette, no gradients, no glow, no shadows, no 3D, no shine, no decorative icons, no illustrations.
- Boxes: white fill #FFFFFF, 1.5px solid border #C9C1B0, small 6px corner radius. Header strips or emphasis: deep ink #2B2A27 text; one accent colour, muted ochre #9A7B3C, for arrows and key borders; muted red #A23B2C only for stop/blocked items; muted green #4E6B3A only for allowed items. Arrows thin (2px), solid, simple arrowheads.
- Typography: one clean sans-serif (Inter or Helvetica style), sentence case everywhere (no ALL CAPS except code tokens and status words like HELD/BREACHED), title 44px semibold at top-left, labels 26-30px regular, generous padding, consistent spacing, aligned grid.
- Render every text string exactly as given, once, spelled correctly. Add no other words, numbers, logos or captions.

TITLE (top-left): "When combined elements make a product STAFF"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Movement elements (any three of the four count)"
- "Location grid"
- "Time with zone letter"
- "Named route"
- "Quantity or lot"
- "One product, such as a single summary note"
- "Holds at least 3 of the 4 elements"
- "Handling: STAFF at minimum"
- "Even when every source is OPEN or PARTNER"
- "Separate notes, one element each, kept apart"
- "Not one product, so this rule does not apply"

LAYOUT AND RELATIONSHIPS:
Top band, left: a group box headed 'Movement elements (any three of the four count)' holding four equal text chips. Three of the chips have straight arrows, meaning 'goes into', to a single central product box labelled 'One product, such as a single summary note', which contains the line 'Holds at least 3 of the 4 elements'. The fourth chip is drawn the same as the others and is not greyed out. An arrow from the product box leads to a result box, 'Handling: STAFF at minimum', with 'Even when every source is OPEN or PARTNER' as a sub-line beneath it. Bottom band, below a divider: three small separate note boxes labelled together 'Separate notes, one element each, kept apart', with no arrows between them or to STAFF, and the caption 'Not one product, so this rule does not apply'. No shape icons and no real grid, time, route or lot values.

REVISION REQUIREMENTS (a previous attempt was rejected; fix all of these):
- In attempt-01 the bottom band shows three large blank rectangles (each about a third of the width and about 130 px tall) with nothing inside. They read as empty form fields or unfinished placeholders, not as 'small separate note boxes'. Nothing marks them as notes holding one element each, so the band looks unfinished. Fix: replace them with three small note icons drawn as flat outlines, each about chip-sized (about 180×110 px) with a folded top-right corner and two or three short grey hairlines for text. Space them evenly under the heading 'Separate notes, one element each, kept apart', with no text inside, no arrows, and the caption 'Not one product, so this rule does not apply' centred beneath. Keep the top band as it is.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m03-authority-layers

- Title: Where a call stops, and what records it
- Native size: 1536×1024; published SHA-256: `e268230609096b2e5956e55e9010b7a52975edda8ceec17dbb0ebc95d7cbbf3a`
- Accepted attempt: 01 of 1

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional diagram. Do not write code or SVG. Return the absolute saved PNG path.

VISUAL STYLE (strict):
- Flat, clean technical diagram like a figure in a professional training manual or consulting report (think McKinsey/Stripe documentation). 1536x1024 landscape.
- Opaque solid warm off-white background #FAF7F0. No texture, no grid, no vignette, no gradients, no glow, no shadows, no 3D, no shine, no decorative icons, no illustrations.
- Boxes: white fill #FFFFFF, 1.5px solid border #C9C1B0, small 6px corner radius. Header strips or emphasis: deep ink #2B2A27 text; one accent colour, muted ochre #9A7B3C, for arrows and key borders; muted red #A23B2C only for stop/blocked items; muted green #4E6B3A only for allowed items. Arrows thin (2px), solid, simple arrowheads.
- Typography: one clean sans-serif (Inter or Helvetica style), sentence case everywhere (no ALL CAPS except code tokens and status words like HELD/BREACHED), title 44px semibold at top-left, labels 26-30px regular, generous padding, consistent spacing, aligned grid.
- Render every text string exactly as given, once, spelled correctly. Add no other words, numbers, logos or captions.

TITLE (top-left): "Where a call stops, and what records it"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Tool offer (allow-list)"
- "Guard"
- "Server scope"
- "Read-only and create-only limits"
- "Files on disk"
- "Not sent"
- "Blocked before the server"
- "Denied by the server; no file changed"
- "Allowed"
- "Evidence: harness or probe record"
- "Evidence: server audit and disk check"
- "Server boundary"
- "The server cannot audit a call it never received."

LAYOUT AND RELATIONSHIPS:
A horizontal request path of four boxes left to right, joined by plain arrows meaning 'passes to': Tool offer (allow-list) → Guard → Server scope, with 'Read-only and create-only limits' as a sub-line inside Server scope → Files on disk. The arrow into Files on disk is labelled 'Allowed'. Each of the first three boxes has its own downward muted-red refusal branch, which ends with no onward arrow: 'Not sent', 'Blocked before the server', and 'Denied by the server; no file changed'. Each refusal box then leads by a neutral arrow, meaning 'check', to the evidence box below it: 'Evidence: harness or probe record' under Not sent and under Blocked before the server, and 'Evidence: server audit and disk check' under the server denial. Files on disk has a neutral arrow down to a second 'Evidence: server audit and disk check'. A dashed vertical divider between Guard and Server scope is labelled 'Server boundary' at the top. The footer sentence sits under the divider, beside the two harness-record boxes. No refusal passes through a later layer.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m03-contract-authority

- Title: Reading a server's contract before you connect
- Native size: 1536×1024; published SHA-256: `d260edc7a437701d7a05bbc6e79ab46bb33ba7ce865603797f2371e88b671228`
- Accepted attempt: 01 of 1

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional diagram. Do not write code or SVG. Return the absolute saved PNG path.

VISUAL STYLE (strict):
- Flat, clean technical diagram like a figure in a professional training manual or consulting report (think McKinsey/Stripe documentation). 1536x1024 landscape.
- Opaque solid warm off-white background #FAF7F0. No texture, no grid, no vignette, no gradients, no glow, no shadows, no 3D, no shine, no decorative icons, no illustrations.
- Boxes: white fill #FFFFFF, 1.5px solid border #C9C1B0, small 6px corner radius. Header strips or emphasis: deep ink #2B2A27 text; one accent colour, muted ochre #9A7B3C, for arrows and key borders; muted red #A23B2C only for stop/blocked items; muted green #4E6B3A only for allowed items. Arrows thin (2px), solid, simple arrowheads.
- Typography: one clean sans-serif (Inter or Helvetica style), sentence case everywhere (no ALL CAPS except code tokens and status words like HELD/BREACHED), title 44px semibold at top-left, labels 26-30px regular, generous padding, consistent spacing, aligned grid.
- Render every text string exactly as given, once, spelled correctly. Add no other words, numbers, logos or captions.

TITLE (top-left): "Reading a server's contract before you connect"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Tool: manage_tags"
- "Read-only mark: yes"
- "Description: "Add or remove tags on a note""
- "The mark and the description disagree. Check what the tool changes."
- "Server instructions"
- "Can steer the model"
- "Cannot grant permission"
- "Cannot enforce the connection's limits"

LAYOUT AND RELATIONSHIPS:
Top panel: a plain tool card (not a fake app window) with the tool name 'Tool: manage_tags' (manage_tags in monospace) and two lines, 'Read-only mark: yes' and the quoted description. A bracket spans both lines and leads to a muted amber callout box holding the disagreement sentence. Bottom panel, below a divider: a 'Server instructions' box with one arrow, meaning 'can do', to 'Can steer the model'. Next to it, a separate muted box lists 'Cannot grant permission' and 'Cannot enforce the connection's limits' with no arrow from the instructions box, so instructions are never drawn connected to permission. Light background, no ≠ disc, no glow.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m03-effective-handling

- Title: How to work out a note's effective handling
- Native size: 1536×1024; published SHA-256: `5b05d9860c14f1dccfb4543984f1e3058e968994a02d2756278d914048a8eb7e`
- Accepted attempt: 01 of 1

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional diagram. Do not write code or SVG. Return the absolute saved PNG path.

VISUAL STYLE (strict):
- Flat, clean technical diagram like a figure in a professional training manual or consulting report (think McKinsey/Stripe documentation). 1536x1024 landscape.
- Opaque solid warm off-white background #FAF7F0. No texture, no grid, no vignette, no gradients, no glow, no shadows, no 3D, no shine, no decorative icons, no illustrations.
- Boxes: white fill #FFFFFF, 1.5px solid border #C9C1B0, small 6px corner radius. Header strips or emphasis: deep ink #2B2A27 text; one accent colour, muted ochre #9A7B3C, for arrows and key borders; muted red #A23B2C only for stop/blocked items; muted green #4E6B3A only for allowed items. Arrows thin (2px), solid, simple arrowheads.
- Typography: one clean sans-serif (Inter or Helvetica style), sentence case everywhere (no ALL CAPS except code tokens and status words like HELD/BREACHED), title 44px semibold at top-left, labels 26-30px regular, generous padding, consistent spacing, aligned grid.
- Render every text string exactly as given, once, spelled correctly. Add no other words, numbers, logos or captions.

TITLE (top-left): "How to work out a note's effective handling"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "1. Header marking"
- "A missing marking means STAFF."
- "2. Latest valid notice"
- "Apply the latest valid notice, if any, by Zulu time."
- "3. Inheritance"
- "At least as restricted as any note it draws on"
- "4. Aggregation"
- "A product with 3 of 4 movement elements is at least STAFF."
- "Effective handling"
- "A valid notice is a marking-change notice from the Release Authority,"
- "naming a note that exists and setting a permitted level."
- "Standing rules"
- "New notes written by the AI start at STAFF."
- "A proposed marking or a body claim changes nothing."
- "Only a valid Release Authority notice changes a marking."

LAYOUT AND RELATIONSHIPS:
One straight row (or column) of four numbered step boxes in the order 1→2→3→4. Each box has a bold header and one body line. Plain arrows between the steps mean 'then apply'. Step 4 leads to a result box, 'Effective handling'. Under step 2, a small footnote marker leads to the two-line valid-notice definition. To the side or below, set apart by a divider, a panel headed 'Standing rules' holds its three lines as bullets. No arrow joins the standing-rules panel to the steps or to the result, and no arrow comes from 'proposed marking' to any level. One font throughout and no ≠ symbol.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m03-phase-scope-revoke

- Title: Each phase gets its own reach
- Native size: 1536×1024; published SHA-256: `f739d301bcbfe1463826e5fd32d0f39d073b261a50bd7fcd6aa6b476f78f3649`
- Accepted attempt: 03 of 3
- Earlier attempts were rejected in review for relationship or layout defects; the last revision requirements are included at the end of the prompt.

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional diagram. Do not write code or SVG. Return the absolute saved PNG path.

VISUAL STYLE (strict):
- Flat, clean technical diagram like a figure in a professional training manual or consulting report (think McKinsey/Stripe documentation). 1536x1024 landscape.
- Opaque solid warm off-white background #FAF7F0. No texture, no grid, no vignette, no gradients, no glow, no shadows, no 3D, no shine, no decorative icons, no illustrations.
- Boxes: white fill #FFFFFF, 1.5px solid border #C9C1B0, small 6px corner radius. Header strips or emphasis: deep ink #2B2A27 text; one accent colour, muted ochre #9A7B3C, for arrows and key borders; muted red #A23B2C only for stop/blocked items; muted green #4E6B3A only for allowed items. Arrows thin (2px), solid, simple arrowheads.
- Typography: one clean sans-serif (Inter or Helvetica style), sentence case everywhere (no ALL CAPS except code tokens and status words like HELD/BREACHED), title 44px semibold at top-left, labels 26-30px regular, generous padding, consistent spacing, aligned grid.
- Render every text string exactly as given, once, spelled correctly. Add no other words, numbers, logos or captions.

TITLE (top-left): "Each phase gets its own reach"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Phase 1: Research"
- "Reads: Handbook/ and Sources/"
- "New writes only in: Drafts/research/"
- "Phase 2: Partner"
- "Reads only: Estimate/Releasable/"
- "New writes only in: Drafts/partner/"
- "Phase 3: Revoked"
- "Server map: mcpServers: {}"
- "No server is started"
- "A fresh run is offered no tools"
- "Nothing carries over from one phase to the next."

LAYOUT AND RELATIONSHIPS:
Three equal columns left to right in time order under one thin plain timeline rule, which carries no text. Each column has a header (Phase 1/2/3) and the same two rows in the same vertical positions. Research and Partner: row 1 is the 'Reads' line and row 2 is the 'New writes only in' line. Revoked: row 1 is 'Server map: mcpServers: {}' and row 2 holds 'No server is started' above 'A fresh run is offered no tools'. Show paths and mcpServers: {} in monospace. Draw no arrows between columns, because an arrow would read as data or permission carrying forward; the phase numbers give the order. The Revoked header is darker, with the same neutral palette and no red. Put the 'Nothing carries over…' sentence as a single footer line spanning all three columns. No empty bottom band and no server-denial node.

REVISION REQUIREMENTS (a previous attempt was rejected; fix all of these):
- The spec says 'Show paths and mcpServers: {} in monospace'. In attempt-02 only 'mcpServers: {}' is monospace. Handbook/, Sources/, Estimate/Releasable/, Drafts/research/ and Drafts/partner/ are in the proportional sans, so code tokens are styled inconsistently across the three columns. In the Revoked column, 'A fresh run is offered no tools' is also in a condensed face that is smaller than 'No server is started' directly above it. Fix: set the five folder paths in the same monospace as mcpServers: {}, keeping the prefixes 'Reads:', 'Reads only:' and 'New writes only in:' in the sans. Set 'A fresh run is offered no tools' in the same face and size as 'No server is started'. Keep layout, palette and all strings.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m03-probe-proof

- Title: Probe results for open and bounded connections
- Native size: 1536×1024; published SHA-256: `6cb935fa8524685b990c3a17e67646d3691e1344296b5e662d87addc97d52aa0`
- Accepted attempt: 02 of 2
- Earlier attempts were rejected in review for relationship or layout defects; the last revision requirements are included at the end of the prompt.

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional diagram. Do not write code or SVG. Return the absolute saved PNG path.

VISUAL STYLE (strict):
- Flat, clean technical diagram like a figure in a professional training manual or consulting report (think McKinsey/Stripe documentation). 1536x1024 landscape.
- Opaque solid warm off-white background #FAF7F0. No texture, no grid, no vignette, no gradients, no glow, no shadows, no 3D, no shine, no decorative icons, no illustrations.
- Boxes: white fill #FFFFFF, 1.5px solid border #C9C1B0, small 6px corner radius. Header strips or emphasis: deep ink #2B2A27 text; one accent colour, muted ochre #9A7B3C, for arrows and key borders; muted red #A23B2C only for stop/blocked items; muted green #4E6B3A only for allowed items. Arrows thin (2px), solid, simple arrowheads.
- Typography: one clean sans-serif (Inter or Helvetica style), sentence case everywhere (no ALL CAPS except code tokens and status words like HELD/BREACHED), title 44px semibold at top-left, labels 26-30px regular, generous padding, consistent spacing, aligned grid.
- Render every text string exactly as given, once, spelled correctly. Add no other words, numbers, logos or captions.

TITLE (top-left): "Probe results for open and bounded connections"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Normal probe"
- "Open connection"
- "Bounded connection"
- "Read outside scope"
- "Overwrite a source note"
- "Create a note outside the write folder"
- "Delete a source note"
- "BREACHED"
- "HELD"
- "HELD (allow-list)*"
- "* Deletion is off the allow-list, so the call is never sent."
- "server.outcome: NOT_SENT. This does not test the server's response."
- "Permitted reads and the new-note write must still show WORKS."
- "Stretch: server-only probe"
- "--ignore-allow-list on the bounded connection"
- "The delete call reaches the server"
- "Evidence: the server's denial and unchanged files on disk"

LAYOUT AND RELATIONSHIPS:
Upper panel headed 'Normal probe': a plain table with two column headers ('Open connection', 'Bounded connection') and four row headers in this order: Read outside scope, Overwrite a source note, Create a note outside the write folder, Delete a source note. Rows 1–3: 'BREACHED' (muted red fill) under Open and 'HELD' (muted green/neutral fill) under Bounded, so BREACHED and HELD each appear three times. Row 4: 'HELD (allow-list)*' in both columns in a neutral grey tint. Directly under the table, the two-line footnote ('* Deletion is off…' then 'server.outcome: NOT_SENT…', with NOT_SENT and server.outcome in monospace). The last line inside the normal-probe panel is the WORKS note. Below it, a separate lightly tinted panel headed 'Stretch: server-only probe' has three boxes left to right joined by plain arrows meaning 'then': '--ignore-allow-list on the bounded connection' (flag in monospace) → 'The delete call reaches the server' → 'Evidence: the server's denial and unchanged files on disk'. No arrow connects the stretch panel to the table. Read order: table, footnote, WORKS note, stretch panel.

REVISION REQUIREMENTS (a previous attempt was rejected; fix all of these):
- In attempt-01 the two delete-row cells hold the same result, but in the Open column 'HELD' is bold and in the Bounded column it is regular weight. In a results table that suggests the two outcomes differ, yet the page says deletion is HELD by the allow-list in both configurations. The WORKS line and the three stretch-panel boxes are also set in a narrower condensed face than the table rows and footnote, so the figure mixes two sans families. Fix: render 'HELD (allow-list)*' identically in both cells (same weight, regular or bold, same grey tint), and use the table's sans face for the WORKS line and the stretch-box text. Keep monospace only for server.outcome, NOT_SENT and --ignore-allow-list. Strings and layout are otherwise correct.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

