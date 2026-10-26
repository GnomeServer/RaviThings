# Figure prompts and provenance — module-00-setup

Staff-only record. Not published (absent from `course.json`).

- Generator: `codex-cli 0.154.0` (`codex exec`, built-in `image_gen`). No reference images attached.
- Style: flat light instructional diagram (warm off-white ground, white boxes, thin neutral borders, one ochre accent, muted red only for stop/HOLD, muted green only for allowed). Sentence-case titles and plain-language labels.
- Post-processing: composited onto the opaque `#FAF7F0` ground and saved as lossless RGB PNG at native size; no other pixel changes.
- Run evidence (all attempts, prompts, logs): `~/course-evidence/image-remake-20261003T204449`. The long-form rewrite of 2026-10-04 added `m00-longform-loop`, `m00-plan-first`, and `m00-critique-passes`, regenerated `m00-falsifier` and `m00-change-isolation`, and retired `m00-bounded-direction` and `m00-responsibility-screen`; evidence in `~/course-evidence/image-remake-20261004T235455Z-longform`.
- These figures replace an earlier set that used dark, glowing styling and slogan-style labels.

## m00-change-isolation

- Title: Change only the sections that use the new fact
- Native size: 1536×1024; published SHA-256: `83b4fdf3038550a8a6a29f428c4e18d78a0524da4d2a7f727ecae20622ae8aae`
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

TITLE (top-left): "Change only the sections that use the new fact"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "New fact: 19 kits on hand"
- "Find the sections whose Facts line uses the on-hand count"
- "Rewrite only those sections"
- "Copy every other section unchanged"
- "Compare versions: unchanged sections match byte for byte"
- "The checker still expects 27"
- "So the new version fails that one check"
- "Do not edit the checker to hide the failure"

LAYOUT AND RELATIONSHIPS:
Top row, left to right, joined by ochre arrows: 'New fact: 19 kits on hand' -> 'Find the sections whose Facts line uses the on-hand count', which then splits with two orthogonal ochre arrows into two boxes stacked on the right: upper 'Rewrite only those sections' and lower 'Copy every other section unchanged'. Both of those feed one box further right: 'Compare versions: unchanged sections match byte for byte'. Bottom row, separate and read right to left with muted red arrows: 'The checker still expects 27' -> 'So the new version fails that one check' -> 'Do not edit the checker to hide the failure' (this last box has a muted red outline). One muted red arrow runs from the compare box down to 'The checker still expects 27'.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-claim-check

- Title: Trace each claim to its source
- Native size: 1536×1024; published SHA-256: `f91738908ac89da930ff06ad89a6fffd22d705be4a52d18a84e10e291571ca06`
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

TITLE (top-left): "Trace each claim to its source"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Material claim"
- "Source and locator (line or paragraph)"
- "Quoted support"
- "What the quote establishes"
- "What it does not establish"
- "An action a reader might infer"
- "Not supported"
- "Mechanical checks"
- "Human interpretation"

LAYOUT AND RELATIONSHIPS:
Top chain, left to right, 'then' arrows: 'Material claim' → 'Source and locator (line or paragraph)' → 'Quoted support'. From 'Quoted support', an orthogonal fork down to two side-by-side boxes: 'What the quote establishes' (left) and 'What it does not establish' (right). From 'What it does not establish', a dashed red connector ending in a perpendicular stop bar, with the small label 'Not supported' at the bar, leads toward 'An action a reader might infer' at far right. This is a blocked link, not an arrow. Both fork boxes feed down by straight arrows into 'Human interpretation' (bottom centre). A separate lower-left box, 'Mechanical checks', has one straight arrow into 'Human interpretation' only, and no connection to the inferred-action box. Even spacing; no S-bends.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-critique-passes

- Title: Check the draft against something outside it
- Native size: 1536×1024; published SHA-256: `0ae963fd610e9d4e7e8dbe2b9a9a4fad25c7bc44ed37d48f5ba8f4bea2a17245`
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

TITLE (top-left): "Check the draft against something outside it"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Check"
- "Compares the draft with"
- "Checker"
- "Required facts and banned promises"
- "Number list"
- "Every number and code, and the source that has it"
- "Tests pass"
- "Your tests.md"
- "Facts pass"
- "Questions from the draft, answered from the sources without the draft"
- "Reader pass"
- "What the clinic clerk would do after reading it"
- "Style pass"
- "The rules in STYLE.md"
- "Each finding quotes the sentence, names the rule or source, and proposes a fix"
- "You verify every finding before anything changes"

LAYOUT AND RELATIONSHIPS:
A two-column table with header row 'Check' | 'Compares the draft with'. Six rows in this order: Checker | Required facts and banned promises; Number list | Every number and code, and the source that has it; Tests pass | Your tests.md; Facts pass | Questions from the draft, answered from the sources without the draft; Reader pass | What the clinic clerk would do after reading it; Style pass | The rules in STYLE.md. The first two rows (Checker, Number list) share a thin left bracket in neutral grey; the last four rows share a thin left bracket in ochre. Below the table, separated by a rule, two plain footer lines stacked: 'Each finding quotes the sentence, names the rule or source, and proposes a fix' and then 'You verify every finding before anything changes'. No arrows, no icons, no checkmarks.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-falsifier

- Title: Test the checker on a copy
- Native size: 1536×1024; published SHA-256: `2bbbd1a117d6dfb43c231adf0a2c30eaabc6801667bca456aa7f670bf0a7ffc6`
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

TITLE (top-left): "Test the checker on a copy"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Original: draft-v1.md"
- "Keep the original unchanged"
- "Record its hash"
- "Later, confirm the hash is unchanged"
- "Test copy: checker-test.md"
- "Make a separate copy"
- "Add one deliberate error"
- "Run the same checker"
- "Expected result: the checker rejects the copy"
- "A rejection shows the check catches this error"
- "It does not show the original is correct"

LAYOUT AND RELATIONSHIPS:
Two columns separated by a thin vertical rule. Left column headed 'Original: draft-v1.md' with three stacked boxes joined by downward ochre arrows: 'Keep the original unchanged' -> 'Record its hash' -> 'Later, confirm the hash is unchanged'. Right column headed 'Test copy: checker-test.md' with four stacked boxes joined by downward ochre arrows: 'Make a separate copy' -> 'Add one deliberate error' -> 'Run the same checker' -> 'Expected result: the checker rejects the copy'. Centered under both columns, two plain lines: 'A rejection shows the check catches this error' and 'It does not show the original is correct'. No arrow crosses the vertical rule.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-longform-loop

- Title: Get a long document you can trust
- Native size: 1536×1024; published SHA-256: `edcacec30c265d97f272021233d7e35806e6ca28b2d6da35012bf605a5d0602a`
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

TITLE (top-left): "Get a long document you can trust"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "1. Plan before any prose"
- "brief.md, tests.md, outline.md"
- "2. Draft one section at a time"
- "Each section: one job, its facts, a word budget"
- "3. Check in separate passes"
- "Checker, number list, four review sessions"
- "4. Verify every finding"
- "You accept or reject each one against the sources"
- "5. Fix only the flagged sections"
- "The other sections stay byte for byte"
- "6. Decide"
- "READY TO SEND or HOLD"
- "At most two rounds"

LAYOUT AND RELATIONSHIPS:
Six numbered step boxes in reading order, left to right across two rows: row 1 holds steps 1, 2, 3; row 2 holds steps 4, 5, 6, read left to right. Each box has its bold step label and, under it, its plain sub-line: '1. Plan before any prose' / 'brief.md, tests.md, outline.md'; '2. Draft one section at a time' / 'Each section: one job, its facts, a word budget'; '3. Check in separate passes' / 'Checker, number list, four review sessions'; '4. Verify every finding' / 'You accept or reject each one against the sources'; '5. Fix only the flagged sections' / 'The other sections stay byte for byte'; '6. Decide' / 'READY TO SEND or HOLD'. Thin ochre arrows connect 1 to 2 to 3, then 3 down to 4, then 4 to 5 to 6. One additional thin dashed ochre arrow returns from box 5 back up to box 3, labelled 'At most two rounds' beside the dashed arrow. Box 6 has a muted green outline; all other boxes are neutral. No icons.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-plan-first

- Title: Write the plan before the AI writes prose
- Native size: 1536×1024; published SHA-256: `4bf65a9b663be87cfe89ff21466125c103e0956db605cd1556637944819f13c7`
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

TITLE (top-left): "Write the plan before the AI writes prose"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "brief.md"
- "Reader and purpose"
- "Sources it may use"
- "What it can't authorize"
- "Who decides it goes out: you"
- "tests.md"
- "What it must say"
- "What it must never say or imply"
- "Questions a reader must answer from it"
- "outline.md"
- "One job per section"
- "The facts each section may use"
- "A word budget sized to those facts"
- "OMP proposes the outline. You correct it."
- "Freeze the plan before drafting"

LAYOUT AND RELATIONSHIPS:
Three equal tall cards side by side, each headed by a monospace file name: 'brief.md', 'tests.md', 'outline.md'. Under 'brief.md' list four plain lines: 'Reader and purpose'; 'Sources it may use'; 'What it can't authorize'; 'Who decides it goes out: you'. Under 'tests.md' list three lines: 'What it must say'; 'What it must never say or imply'; 'Questions a reader must answer from it'. Under 'outline.md' list three lines: 'One job per section'; 'The facts each section may use'; 'A word budget sized to those facts'. Under the outline.md card only, a small note box reads 'OMP proposes the outline. You correct it.' Below all three cards, a full-width bordered bar with an ochre border reads 'Freeze the plan before drafting'. Thin ochre lines drop from the bottom of each card into the bar. No other arrows.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-readiness-lanes

- Title: Check each tool separately
- Native size: 1536×1024; published SHA-256: `446f4d4f9e806beb162ab65de14aceb7af8798fa25508b80d6bdd8262f4eb1bb`
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

TITLE (top-left): "Check each tool separately"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "OMP prerequisites"
- "Read the prerequisite report in a new terminal"
- "Live OMP check"
- "A live call writes from-omp.txt"
- "Read the file from disk"
- "verify_tool_proof.py checks the file and its receipt"
- "Obsidian"
- "Check the files on disk"
- "Check the same changes in the app window"
- "n8n"
- "Check the running stack"
- "Check the workflow survives reload and restart"
- "A passing prerequisite report does not replace the live check"
- "A result for one tool does not clear another"

LAYOUT AND RELATIONSHIPS:
Four equal-width vertical lanes side by side, each with a heading at the top: 'OMP prerequisites', 'Live OMP check', 'Obsidian', 'n8n'. Lane 1: one box, 'Read the prerequisite report in a new terminal'. Lane 2: three boxes top to bottom joined by downward 'then' arrows: 'A live call writes from-omp.txt' → 'Read the file from disk' → 'verify_tool_proof.py checks the file and its receipt'. Lane 3: two boxes stacked with no arrow between them (both checks are required, neither replaces the other): 'Check the files on disk', 'Check the same changes in the app window'. Lane 4: two boxes stacked the same way: 'Check the running stack', 'Check the workflow survives reload and restart'. Thin vertical rules separate the lanes. No line crosses between lanes and no lane feeds a shared all-clear box. A plain two-line footer spans the width: 'A passing prerequisite report does not replace the live check' (placed under lanes 1–2) and 'A result for one tool does not clear another'. No red banner, no tail dots.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m00-recovery-loop

- Title: Recover from a failed step
- Native size: 1536×1024; published SHA-256: `fab611f950c431908f7f8c613f4b1f55bb4e0fcb01476315cc8ab696c87df29d`
- Accepted replacement: 01 of 1, generated with Codex CLI 0.154.0 through its built-in `image_gen` tool.
- Reference image: the prior `m00-recovery-loop.png` at commit `c87f7d9`, SHA-256 `fc46cc117a748cabf0422e40d4b4c1057e722ce22ef4edf89931d011e467f999`.
- Review: all thirteen labels are present and correctly spelled. The Yes branch returns new evidence to the harness; the No branch records the result. The existing light course-figure style is retained.

### Final prompt

````text
$imagegen
Use the built-in image_gen tool to generate exactly ONE PNG instructional flow diagram. Do not write code or SVG. Save the finished PNG as /tmp/aihb-m00-recovery.VPoavF/recovery-loop.png and return that absolute path. Do not edit repository sources. Do not run tests, builds, linters, or formatters.

This is a revision of the attached course diagram, not a new visual identity. Preserve the existing course figure's light, clean style. The subject is a learner using an AI harness to solve a setup error. Teach the work itself: no curriculum rationale, making-of commentary, grades, scores, or qualification claims.

VISUAL STYLE:
- 1536x1024 landscape, opaque warm off-white background #FAF7F0.
- Match the attached figure: white panels #FFFFFF, thin border #C9C1B0, small corner radius, deep ink text #2B2A27, muted ochre #9A7B3C arrows and key borders. No new style, scene, photographic effects, decorative icons, gradients, texture, glow, shadows, 3D, logos, or invented data.
- One clean sans-serif; sentence case; title 44px semibold at top-left; labels 26-30px, generous padding, aligned layout. Make every label legible.
- Render every label below exactly once, except that Yes and No label their respective decision edges. Do not invent, abbreviate, or add any labels.

TITLE:
"Recover from a failed step"

LABEL SET:
Main instruction panel:
"Ask the harness"
"Copy and paste the error"
"Describe what you were doing"
"Describe what you are trying to accomplish"
"Fix this issue."
Other flow nodes:
"Review and apply the fix"
"Run the same check again"
"Still failing?"
"Paste the new error and describe what you tried"
"Record the result"
Decision edges:
"Yes"
"No"

LAYOUT AND RELATIONSHIPS:
The dominant panel occupies the upper-left half. Its heading is Ask the harness; the next three lines are equally readable supporting instructions; Fix this issue. is the final emphasized line inside that same panel. Do not draw arrows between the lines: they are parts of one request, not separate actions.
A single right-pointing arrow leaves this panel to Review and apply the fix in the upper-right. A down arrow leads to Run the same check again, then another down arrow to the diamond Still failing?. The Yes edge leaves the LEFT vertex of the diamond for a lower-left box reading Paste the new error and describe what you tried; a clear return arrow from that box goes back to the main Ask the harness panel. This is the learner returning with new evidence. The No edge leaves a DIFFERENT vertex for Record the result, at the lower-right, with no return arrow from success. Place Yes and No on their own distinct edges. Keep connectors outside boxes, uncrossed, and away from text. Use the available canvas evenly with generous margins.

Do not retain any old labels such as Change one thing, Use the recovery guidance, or Neither outcome starts an automatic retry. The revised diagram must visibly include the full error + action + goal + explicit fix request, not just generic troubleshooting advice.

Before returning, inspect all labels and arrows. Every stated label must appear, spelled exactly. The two decision edges must be unambiguous. Do not report an image as completed without actually generating it.
````

## m00-tool-layers

- Title: What each layer of the tool shows
- Native size: 1536×1024; published SHA-256: `e17c92f9c131167a1c787858a62ef33666712f5b353e8b420f50f4873448b17e`
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

TITLE (top-left): "What each layer of the tool shows"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Layer"
- "What it gives you as evidence"
- "Model"
- "Text it generated"
- "Interface"
- "File written to disk"
- "Harness"
- "Enforced permissions and run receipts"
- "Person"
- "Interpretation and the decision to use the result"
- "Generated text is not a verified fact"
- "A receipt shows what ran, not that the result is right"
- "Record one observed capability"
- "Record one observed limit"

LAYOUT AND RELATIONSHIPS:
Two-column table, four equal-height rows read top to bottom, with column headers 'Layer' and 'What it gives you as evidence'. Rows: Model | Text it generated; Interface | File written to disk; Harness | Enforced permissions and run receipts; Person | Interpretation and the decision to use the result. No arrows between rows, so no row passes its result to the next. Two small italic notes sit in the right margin at row boundaries, each with a short tick to its boundary: 'Generated text is not a verified fact' on the Model/Interface boundary; 'A receipt shows what ran, not that the result is right' on the Harness/Person boundary. Below the table, one neutral bracket spans all four rows and splits into two equal side-by-side outcome boxes: 'Record one observed capability' and 'Record one observed limit'. Meaning: evidence from any row can support either record. Draw no stub above the first row and no joint dots.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````
