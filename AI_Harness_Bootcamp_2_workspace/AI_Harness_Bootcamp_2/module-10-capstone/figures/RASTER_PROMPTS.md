# Figure prompts and provenance — module-10-capstone

Staff-only record. Not published (absent from `course.json`).

- Generator: `codex-cli 0.154.0` (`codex exec`, built-in `image_gen`). No reference images attached.
- Style: flat light instructional diagram (warm off-white ground, white boxes, thin neutral borders, one ochre accent, muted red only for stop/HOLD, muted green only for allowed). Sentence-case titles and plain-language labels.
- Post-processing: composited onto the opaque `#FAF7F0` ground and saved as lossless RGB PNG at native size; no other pixel changes.
- Run evidence (all attempts, prompts, logs): `~/course-evidence/image-remake-20261003T204449`
- Run evidence (both prompt-first regenerations, all attempts, prompts, logs): `~/course-evidence/image-remake-20261008T010638Z-m10-prompt-first`
- These two figures were regenerated for the prompt-first redesign.
- These figures replace an earlier set that used dark, glowing styling and slogan-style labels.

## m10-evidence-boundaries

- Title: What each check supports
- Native size: 1536×1024; published SHA-256: `196a278794e2c3ca812b02c4d7b5aac4271663d1962785b9ef555f76ddb733e2`
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

TITLE (top-left): "What each check supports"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Evidence"
- "Supports"
- "Size and digest"
- "Identity of the weight file"
- "Health probe"
- "Service reachable at the time of the probe"
- "Live transcript"
- "One recorded interaction"
- "Structure check"
- "Named fields and local paths present"
- "None of these checks establishes:"
- "Safety, model quality, production readiness or independent transfer"

LAYOUT AND RELATIONSHIPS:
A two-column table with the headers 'Evidence' and 'Supports'. Four equal rows, unnumbered and unranked: Size and digest / Identity of the weight file; Health probe / Service reachable at the time of the probe; Live transcript / One recorded interaction; Structure check / Named fields and local paths present. Use a plain thin arrow or just a column rule between the cells; no icons, or one minimal flat glyph per evidence cell. Below the table, separated by a rule, a single footer box with a thin red outline: the heading 'None of these checks establishes:' over the line 'Safety, model quality, production readiness or independent transfer'. No arrow or line from any row reaches the footer. No checkmarks or PASS stamps.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m10-launch-approval

- Title: You approve; OMP starts the server
- Native size: 1536×1024; published SHA-256: `496479a7e923baf4dd5be1b568bd9389791fd2c2acd03f053f13d5cb609abedb`
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

TITLE (top-left): "You approve; OMP starts the server"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Checked weight file"
- "Loopback configuration"
- "OMP drafts the launch line"
- "Your check: 127.0.0.1, context 32768, nothing that widens the boundary"
- "Wrong: reject the line and ask OMP for a new draft"
- "Approved: OMP starts the server"
- "Health probe: is the service reachable?"
- "Unreachable: HOLD"
- "A drafted line is not a running service"

LAYOUT AND RELATIONSHIPS:
Row 1, read left to right: two input boxes stacked, 'Checked weight file' and 'Loopback configuration', each with an arrow into 'OMP drafts the launch line' (grey outline, marked as OMP's step). An arrow goes to a decision box, 'Your check: 127.0.0.1, context 32768, nothing that widens the boundary', with a solid outline marked as the operator's step. From the check, the 'Wrong' exit drops to a red-outlined box 'Wrong: reject the line and ask OMP for a new draft'. A short dashed return arrow goes from that box straight back to 'OMP drafts the launch line', a direct short return with no wraparound; nothing from this box reaches the server. Row 2: the 'Approved' exit drops to 'Approved: OMP starts the server' (OMP's step after your approval). After a visible gap, an arrow to a separate box 'Health probe: is the service reachable?', then a red-outlined exit 'Unreachable: HOLD'. A footnote under row 1, attached to the draft box by a thin line: 'A drafted line is not a running service'. Monospace for 127.0.0.1 and 32768. No terminal window, command text or PASS readout.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m10-operator-boundary

- Title: What the local boundary does and does not limit
- Native size: 1536×1024; published SHA-256: `730d77514354a0e9d8a2fc0898e6485692e8743a74f3b0bfc641f8939f79a0f4`
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

TITLE (top-left): "What the local boundary does and does not limit"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Service bound to 127.0.0.1 only"
- "One operator"
- "Local weights"
- "Requests and replies"
- "Prompts and replies are recorded"
- "Operator reviews output before any use"
- "Blocked at the boundary: no shared endpoint, no traffic from other people"
- "Identity check confirms the weight file only, not its safety or accuracy"

LAYOUT AND RELATIONSHIPS:
Centre-left: a rectangle outlined as the service boundary, labelled 'Service bound to 127.0.0.1 only' (127.0.0.1 in monospace). Inside it are two boxes, 'One operator' and 'Local weights', joined by a two-way arrow labelled 'Requests and replies'. Along the inner bottom edge is a strip 'Prompts and replies are recorded', with nothing crossing it. One arrow leaves the boundary on the right to a box outside it: 'Operator reviews output before any use'. There is no arrow from that box onward and no arrow anywhere toward publishing or other people. On the boundary's outer edge (top or right) is a short red barred segment with the list 'Blocked at the boundary: no shared endpoint, no traffic from other people', written as an edge annotation, not as destinations. A small separate grey callout, 'Identity check confirms the weight file only, not its safety or accuracy', attaches by one thin line to 'Local weights'. It does not cross the recording strip and does not enclose the boundary. No shield, lock, port number or model name.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m10-stop-restore

- Title: Service stop and control restore are separate
- Native size: 1536×1024; published SHA-256: `eba9634945575cfe011c43e1276f1bb86d0f3541c4d9759a6b5bde33000b0ca8`
- Accepted attempt: 02 of 2

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

TITLE (top-left): "Service stop and control restore are separate"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Stop (previous step)"
- "OMP stops its owned process"
- "Probe reports unreachable"
- "Stop receipt"
- "Adapter verifies the stopped state"
- "Control"
- "Control disabled"
- "Every adapter command returns HOLD: control disabled"
- "This refusal is not evidence that the service stopped"
- "Validate the baseline digest"
- "Restore the control from the baseline"
- "Restoring the control does not restart the service"
- "To claim it is running again: launch it, then probe"

LAYOUT AND RELATIONSHIPS:
Two horizontal swimlanes in separate bordered panels with a clear gap between them; no line crosses between the lanes. Top lane, header 'Stop (previous step)', left to right with arrows: 'OMP stops its owned process' (tagged as OMP's step) → 'Probe reports unreachable' → 'Stop receipt' → 'Adapter verifies the stopped state' (tagged as the adapter's check; no power or kill icon). Bottom lane, header 'Control', with two sub-sequences separated by a gap. First: 'Control disabled' → a red-outlined box 'Every adapter command returns HOLD: control disabled', which is a dead end, with the small note 'This refusal is not evidence that the service stopped' directly beneath it. Second: 'Validate the baseline digest' → 'Restore the control from the baseline' → a terminal note box 'Restoring the control does not restart the service'. A separate grey box beside that terminal note, with no incoming arrow, reads 'To claim it is running again: launch it, then probe'. No decorative bars, people, hands or shields.

FIX NOTE FOR THIS REGENERATION: Render every box label entirely in deep ink #2B2A27, with no colored or bold words. Show the actor only through the label text itself: no colored tags, badges or pills. Keep all existing labels, arrows, lanes and spacing unchanged.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

