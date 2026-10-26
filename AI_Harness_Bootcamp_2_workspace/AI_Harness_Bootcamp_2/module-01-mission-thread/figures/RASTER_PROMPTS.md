# Figure prompts and provenance — module-01-mission-thread

Staff-only record. Not published (absent from `course.json`).

- Generator: `codex-cli 0.154.0` (`codex exec`, built-in `image_gen`). No reference images attached.
- Style: flat light instructional diagram (warm off-white ground, white boxes, thin neutral borders, one ochre accent, muted red only for stop/HOLD, muted green only for allowed). Sentence-case titles and plain-language labels.
- Post-processing: composited onto the opaque `#FAF7F0` ground and saved as lossless RGB PNG at native size; no other pixel changes.
- Run evidence (all attempts, prompts, logs): `~/course-evidence/image-remake-20261003T204449`
- These figures replace an earlier set that used dark, glowing styling and slogan-style labels.

## m01-atomic-ledger

- Title: One material claim per row
- Native size: 1536×1024; published SHA-256: `ab0764e37073de1b8b1ee8230740b7a8bffb219ecd3b44f620f2d4dffde25242`
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

TITLE (top-left): "One material claim per row"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Compound assertion from the AI brief"
- "Count claim"
- "State claim"
- "Decision claim"
- "Source, version and locator"
- "Statement kind"
- "Warrant"
- "Units and calculation, if any"
- "Dependency and handoff"
- "Uncertainty"
- "Stop at a fact, calculation, assumption, HOLD or human decision"

LAYOUT AND RELATIONSHIPS:
Top left: one box 'Compound assertion from the AI brief' with no case text inside. Three straight branches (meaning 'splits into') go from it to the three row labels of a plain table below: 'Count claim', 'State claim', 'Decision claim'. The table has one header strip with six column headings in single lines: Source, version and locator | Statement kind | Warrant | Units and calculation, if any | Dependency and handoff | Uncertainty. Cells are empty, with ordinary thin table rules; no lines or dots run through the cells. One plain sentence sits under the table: 'Stop at a fact, calculation, assumption, HOLD or human decision'. Title left-aligned or centred to match the rest of the set.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-broken-handoff

- Title: What each true state still needs
- Native size: 1536×1024; published SHA-256: `7dd1d578a87802d0baef40c1bf2401d10d2c987d5d3d344e49949659a7f1d27a`
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

TITLE (top-left): "What each true state still needs"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "True at this step"
- "Does not supply"
- "Still needs its own evidence"
- "Recorded custody"
- "Release"
- "Permit received"
- "Approval of the permit"
- "Expected arrival"
- "Delivery evidence"
- "Delivered"
- "Confirmation of usable quantity"
- "Each state can be true without meeting the next requirement"

LAYOUT AND RELATIONSHIPS:
Three columns with headings: left 'True at this step', a narrow middle gap column 'Does not supply', right 'Still needs its own evidence'. Four independent rows: Recorded custody | Release; Permit received | Approval of the permit; Expected arrival | Delivery evidence; Delivered | Confirmation of usable quantity. Left boxes have solid neutral outlines. Right boxes have dashed outlines, meaning separate evidence is needed; they do not mean the evidence is missing. In the middle column each row has a short connector broken by a gap with a small neutral bar, with no arrowhead and no X. Rows are not linked to each other. Footer: 'Each state can be true without meeting the next requirement'.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-byte-identity

- Title: Identify the file, then check it applies
- Native size: 1536×1024; published SHA-256: `4a7046fb2c6b13f2e46053d38d1502e083d6cb39159a8a847d0f633a74386d9e`
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

TITLE (top-left): "Identify the file, then check it applies"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Identity check"
- "File bytes"
- "Hash"
- "Byte identity: these exact bytes"
- "Applicability check"
- "Issuer"
- "Version and time"
- "Exact entity"
- "Allowed use"
- "Fits the claim"
- "Traceable evidence"
- "A hash does not establish truth or authority"

LAYOUT AND RELATIONSHIPS:
Two horizontal lanes separated by a thin rule. Upper lane, headed 'Identity check': 'File bytes' → 'Hash' → 'Byte identity: these exact bytes' (arrows mean 'produces'). The note 'A hash does not establish truth or authority' sits on the dividing rule under the identity lane. Lower lane, headed 'Applicability check': four separate parallel boxes stacked or in a row ('Issuer', 'Version and time', 'Exact entity', 'Allowed use'), each with its own evenly spaced arrow into 'Fits the claim'. They are not chained to each other. The 'Byte identity' box and the 'Fits the claim' box each send one straight arrow right into a single box, 'Traceable evidence'. No trust badge, no glow.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-change-isolation

- Title: Predict the change before you see it
- Native size: 1536×1024; published SHA-256: `330128301ea51d3bce0f257e57e774aa2afd0befd9c94e784294d7088cf0f2f7`
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

TITLE (top-left): "Predict the change before you see it"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Freeze the baseline verdict"
- "Write change-prediction.md"
- "What should change"
- "What must not change"
- "Reveal the source update"
- "Update only the dependent claims"
- "Keep unrelated blockers visible"
- "Recompute the verdict"
- "New evidence does not produce a GO automatically"

LAYOUT AND RELATIONSHIPS:
Left to right, 'then' arrows: 'Freeze the baseline verdict' → 'Write change-prediction.md'. The prediction box forks into two parallel horizontal lanes: upper lane starts with 'What should change', lower lane with 'What must not change'. Both lanes pass through one shared vertical box, 'Reveal the source update', the same size as the other boxes, which spans both lanes and marks the point after which the update is seen. After the reveal, the upper lane continues to 'Update only the dependent claims' and the lower lane to 'Keep unrelated blockers visible'. The lanes do not cross. Both lanes converge into 'Recompute the verdict'. A plain footer line sits directly under that box: 'New evidence does not produce a GO automatically'. One neutral connector colour throughout; no source values, no verdict shown.

REVISION REQUIREMENTS (a previous attempt was rejected; fix all of these):
- The whole diagram sits in a band at about y 360–680 of a 1024 px canvas, leaving the top and bottom thirds empty. Box text is about 20 px tall and the footer about 16 px, so at 800 px wide the footer drops to about 8 px and is hard to read. The footer 'New evidence does not produce a GO automatically' also runs wider than 'Recompute the verdict' and reaches about 1518 px of the 1536 px canvas, almost cut off at the right edge. The connectors are a pale grey that almost disappears against the background. Regenerate with these changes: (1) scale the diagram to fill about 80% of the canvas height below the title, with box text at least 26 px. (2) Use the same mid-tone connector colour as the other figures. (3) Centre the footer under 'Recompute the verdict', at body-text size, with at least 40 px of right margin; wrap it inside that column or move the column left if needed. Keep all labels and the lane structure unchanged.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-recompute-feasibility

- Title: Recompute, then check feasibility
- Native size: 1536×1024; published SHA-256: `c3c24b19446df18bebba368f92460e75fb3e26b8abdc85f3711df50c7471f4bb`
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

TITLE (top-left): "Recompute, then check feasibility"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Source values"
- "Units"
- "Are the premises supported?"
- "Yes"
- "No"
- "UNSUPPORTED: hold the claim"
- "Show the operation yourself"
- "Your independent result"
- "Do not copy the producer's result"
- "Are the required entry conditions met?"
- "Counterfactual: valid only if the blocked condition were met"
- "Feasible at this step only"
- "Delivery is not yet observed"

LAYOUT AND RELATIONSHIPS:
Left: 'Source values' and 'Units' as two small stacked boxes whose arrows join into the diamond 'Are the premises supported?'. 'No' (down) goes to a red-outlined box 'UNSUPPORTED: hold the claim', which ends there. 'Yes' (right) goes to 'Show the operation yourself' → 'Your independent result'. The note 'Do not copy the producer's result' is attached as a sub-line directly under the result box. The result box feeds the second diamond, 'Are the required entry conditions met?'. 'No' (down) goes to 'Counterfactual: valid only if the blocked condition were met'. 'Yes' (right) goes to 'Feasible at this step only', with the sub-line 'Delivery is not yet observed'. Each diamond's Yes and No labels sit on their own edges (Yes/No are drawn twice, once per diamond). No edge loops back. Clean aligned orthogonal connectors; no glow.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-source-authority

- Title: Which source can establish which claim
- Native size: 1536×1024; published SHA-256: `cd5296357ba5c9f60a505b87201d6ff9db2dca96ac9ef4e78bab028cf26b67bf`
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

TITLE (top-left): "Which source can establish which claim"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Source"
- "Can establish"
- "Warehouse"
- "Custody of scanned totes"
- "Quality office"
- "Which lots are released"
- "Fleet Engineering"
- "Payload and required equipment"
- "Road Authority"
- "Gate window"
- "Movement Registry"
- "Permit status"
- "Warehouse record used for release: wrong authority"
- "For every claim, also check exact entity and current version"

LAYOUT AND RELATIONSHIPS:
A five-row, two-column table with headers 'Source' and 'Can establish'. In each row, a straight horizontal arrow (meaning 'is the authority for') runs from the source cell to its claim cell: Warehouse → Custody of scanned totes; Quality office → Which lots are released; Fleet Engineering → Payload and required equipment; Road Authority → Gate window; Movement Registry → Permit status. Rows are separate and do not link to each other. Below the table, a separate callout box holds a short arrow drawn as blocked (struck through with a perpendicular bar) and the text 'Warehouse record used for release: wrong authority'. No line from the callout crosses the table. A single footer sentence spans the width: 'For every claim, also check exact entity and current version'. Sources in Title Case as proper names; claim cells in sentence case.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-statement-types

- Title: Five kinds of statement
- Native size: 1536×1024; published SHA-256: `5c2bf67f88bf4e36bb0a5c3790c4cccf858f808f2bad0418628e4eabf437695f`
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

TITLE (top-left): "Five kinds of statement"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Mixed sentence"
- "SOURCE FACT"
- "An applicable source states it directly"
- "CALCULATION"
- "Supported values and units produce it"
- "INFERENCE"
- "An interpretation with a stated reason"
- "DECISION"
- "A named person owns the choice"
- "UNSUPPORTED"
- "No applicable source or sound calculation supports it"
- "Split until each row has one kind"

LAYOUT AND RELATIONSHIPS:
Left: one box labelled 'Mixed sentence' with no case text inside. Five thin branches fan from it to the left edge of five equal-height rows stacked on the right. Each row has two cells: the kind token in monospace caps (SOURCE FACT, CALCULATION, INFERENCE, DECISION, UNSUPPORTED) and its support in sentence case. Every row has the same neutral border and fill; no colour ramp, no ordering cue, and no arrows between rows (these are parallel categories, not steps toward approval). Footer, same contrast and size as body text: 'Split until each row has one kind'.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-supported-verdict

- Title: What a defensible verdict must show
- Native size: 1536×1024; published SHA-256: `625b3e90ee3810ccfc5cf73e889d6bced591d1718569551e2b70a1a0fa88392e`
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

TITLE (top-left): "What a defensible verdict must show"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Each claim, including the producer's rebuttal"
- "Supported"
- "Contradicted"
- "Unresolved"
- "Exact sources and calculations for each finding"
- "Class-only decision"
- "ACCEPT"
- "REVISE"
- "REJECT"
- "HOLD"
- "Current blockers"
- "Next evidence and who can supply it"
- "The rebuttal is another claim to check, not proof"

LAYOUT AND RELATIONSHIPS:
Top box 'Each claim, including the producer's rebuttal' fans down from its bottom edge into three separate, equal boxes: 'Supported', 'Contradicted', 'Unresolved'. A small note attached under the top box reads 'The rebuttal is another claim to check, not proof'. All three category boxes feed down into one box, 'Exact sources and calculations for each finding' (arrows mean 'is backed by'). That box feeds one bordered panel headed 'Class-only decision', which contains four separate token boxes in one row, ACCEPT, REVISE, REJECT, HOLD. All four tokens get the same neutral style, none selected, none coloured. Below them in the same panel: 'Current blockers' and 'Next evidence and who can supply it'. A direct single-line orthogonal connector also runs from 'Unresolved' down the right side to 'Next evidence and who can supply it'. All connectors are single strokes; no doubled lines.

REVISION REQUIREMENTS (a previous attempt was rejected; fix all of these):
- The rebuttal note 'The rebuttal is another claim to check, not proof' is drawn as a box under the top claim box, and the three-way fan to Supported/Contradicted/Unresolved starts from the bottom of that note box. The note therefore becomes a step in the flow, as if every claim passes through 'the rebuttal is another claim' before it is sorted. The spec says the fan leaves the top box's bottom edge and the note is attached. Regenerate with the fan starting directly from the bottom edge of 'Each claim, including the producer's rebuttal'. Put the note as plain small text, with no box and no connector into the fan, either to the right of the top box or directly beneath it but offset so the fan does not pass through it. Keep all other text, the neutral tokens and the Unresolved → 'Next evidence and who can supply it' connector unchanged.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m01-thread-handoffs

- Title: The eight steps of the Cold Lantern thread
- Native size: 1536×1024; published SHA-256: `d23b2a23e023e0d1ba9616d6310155f1ccf538a2abef6a944d9af53dfc332379`
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

TITLE (top-left): "The eight steps of the Cold Lantern thread"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "1 Requirement defined"
- "2 Cargo received"
- "3 Cargo released"
- "4 Vehicle made ready"
- "5 Movement authorized"
- "6 Route window met"
- "7 Cargo delivered"
- "8 Usable effect confirmed"
- "Each step's output must meet the next step's entry condition"
- "Decision point"
- "Not yet observed"
- "Arrows show required handoffs, not completed checks"

LAYOUT AND RELATIONSHIPS:
Two rows of four equal numbered boxes; the number sits inside each box before the name. Row 1, left to right: 1 → 2 → 3 → 4. One clean orthogonal connector goes down from box 4 and wraps left to box 5 at the start of row 2. Row 2, left to right: 5 → 6 → 7 → 8. Every arrow means 'hands its output to'. The sentence 'Each step's output must meet the next step's entry condition' sits centred in the band between the two rows, clear of the wrap connector. Between boxes 6 and 7, a dashed vertical line has a gap where the 6→7 arrow passes, so it does not cut the arrow. 'Decision point' is labelled above that line. A neutral bracket over boxes 7 and 8 reads 'Not yet observed'; boxes 7 and 8 have dashed outlines. Footer line: 'Arrows show required handoffs, not completed checks'. No check marks or status colours on any step.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

