# Figure prompts and provenance — module-04-typed-decisions

Staff-only record. Not published (absent from `course.json`).

- Generator: `codex-cli 0.154.0` (`codex exec`, built-in `image_gen`). No reference images attached.
- Style: flat light instructional diagram (warm off-white ground, white boxes, thin neutral borders, one ochre accent, muted red only for stop/HOLD, muted green only for allowed). Sentence-case titles and plain-language labels.
- Post-processing: composited onto the opaque `#FAF7F0` ground and saved as lossless RGB PNG at native size; no other pixel changes.
- Run evidence (all attempts, prompts, logs): `~/course-evidence/image-remake-20261003T204449`
- These figures replace an earlier set that used dark, glowing styling and slogan-style labels.

## m04-answer-types

- Title: Three answer types
- Native size: 1536×1024; published SHA-256: `5618453533ecc141d1a04adb471bf3d5334ffa05034a7f78a55384c440db4379`
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

TITLE (top-left): "Three answer types"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Yes-or-no question"
- "Answer: p, the probability that the answer is yes"
- "Choice question"
- "Answer: one listed option, plus declared confidence"
- "quantity: one of the message's candidate IDs, or NONE"
- "replaces: an earlier message ID, or NONE"
- "Score question"
- "Answer: one level index from an ordered list, plus declared confidence"
- "An answer can fit its type and still come from a misreading."

LAYOUT AND RELATIONSHIPS:
Three equal cards side by side, left to right: Yes-or-no, Choice, Score. Each card has a header and one 'Answer:' line. Inside the Choice card only, below its Answer line, two indented example lines (quantity and replaces, with field names and NONE in monospace), shown as parallel bullets and not chained to each other. Below all three cards, a full-width plain note bar (neutral fill, no red, no ≠) holds the closing sentence. No connectors are needed.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m04-final-confidence

- Title: The final confidence check
- Native size: 1536×1024; published SHA-256: `176f5bb0ac54ed88b701d9007b8b67147b039f2064c92ee56516b93c78c12f3b`
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

TITLE (top-left): "The final confidence check"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Requests that passed rules 1–8"
- "request"
- "authority"
- "instructs_desk"
- "Yes-or-no answers: confidence = abs(2p - 1)"
- "line"
- "quantity"
- "Choice answers: declared confidence"
- "Weakest of the five confidences"
- "Below min_confidence"
- "REVIEW"
- "At or above min_confidence (equality passes)"
- "PICK"
- "To exclude an observed wrong answer, set min_confidence strictly above its confidence."
- "Replacement-link confidence is not part of this check."

LAYOUT AND RELATIONSHIPS:
Left: entry box 'Requests that passed rules 1–8'. An arrow leads to two stacked input groups. Group A has the three monospace field names request, authority and instructs_desk, all passing through the conversion box 'Yes-or-no answers: confidence = abs(2p - 1)'. Group B has line and quantity, passing through 'Choice answers: declared confidence'. Both groups feed one central node, 'Weakest of the five confidences', with clean orthogonal connectors and no kinks. Two branches leave the node: 'Below min_confidence' → REVIEW chip, and 'At or above min_confidence (equality passes)' → PICK chip, with chip colours consistent with m04-routing-order. Two footnote lines at the bottom: the strict-threshold rule, then the replacement-link exclusion. No icons and no glow.

REVISION REQUIREMENTS (a previous attempt was rejected; fix all of these):
- In attempt-01 REVIEW is a saturated red filled chip and PICK is a saturated green filled chip with white text. The spec requires chip colours consistent with m04-routing-order. That figure uses neutral outlined monospace chips, and its spec forbids an approval green on PICK. Green PICK suggests approval or dispatch, which the page explicitly denies ('PICK … does not authorize dispatch'). Red REVIEW suggests failure. Fix: draw REVIEW and PICK as the same neutral chips used in m04-routing-order: white fill, thin warm-grey outline, dark monospace text, same size. Keep all other boxes, connectors and the two footnotes unchanged.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m04-freeze-measure

- Title: Freeze your labels before the model runs
- Native size: 1536×1024; published SHA-256: `5eaaa29c340f96e70df9b6301f4eb1ae9e88d86b7cad4fae9e6e97eb546c006e`
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

TITLE (top-left): "Freeze your labels before the model runs"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Before the run"
- "Ten-message sample"
- "Write your labels for 4 questions"
- "Freeze: record the digest and UTC time"
- "The run starts only after the freeze"
- "Run the model once on all 40 messages"
- "320 typed answers (8 questions × 40 messages)"
- "Compare on the 10 sample messages and 4 labeled questions"
- "Adjudicate each disagreement"
- "The model's declared confidence is not measured agreement."
- "Agreement on a 10-message sample is not a general reliability rate."

LAYOUT AND RELATIONSHIPS:
Two horizontal lanes. Upper lane, headed 'Before the run': Ten-message sample → Write your labels for 4 questions → Freeze: record the digest and UTC time. A dashed time connector labelled 'The run starts only after the freeze' goes from the Freeze box down to the lower lane's first box; it is a time order, not a data feed. Lower lane: Run the model once on all 40 messages → 320 typed answers (8 questions × 40 messages). Solid arrows from Freeze and from 320 typed answers converge on 'Compare on the 10 sample messages and 4 labeled questions' → 'Adjudicate each disagreement'. No arrow runs from model output back to the labels. The two caution sentences sit in a muted note box at the bottom, with no warning icons and no ≠. No decorative icons.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m04-routing-order

- Title: Routing rules, checked in order
- Native size: 1536×1024; published SHA-256: `10ee3efb2e1fbf8a52aea3a405122f92fb9765503d06b74fd7d2bab100b92f7c`
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

TITLE (top-left): "Routing rules, checked in order"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "The first rule that matches sets the route; otherwise, try the next."
- "1"
- "Target of a recorded replacement"
- "SUPERSEDED"
- "2"
- "Instructs the desk"
- "REFER"
- "3"
- "Endpoint of an uncertain replacement link"
- "REVIEW"
- "4"
- "Not a request"
- "IGNORE"
- "5"
- "Line answer is MIXED (two sizes)"
- "6"
- "Size or quantity missing"
- "CLARIFY"
- "7"
- "Quantity does not convert to a positive whole number of boxes"
- "8"
- "Insufficient authority"
- "9"
- "Otherwise: final confidence check"
- "REVIEW or PICK"
- "PICK adds boxes to the requirement line; it does not authorize dispatch."

LAYOUT AND RELATIONSHIPS:
Two columns of numbered rows: 1–5 on the left and 6–9 on the right. One down-arrow enters row 1 from the instruction line under the title, and no other arrow enters the list. Each row is a numbered condition box with a short horizontal arrow on its right to its route chip, meaning 'if this matches, route here'. A short down-arrow between rows means 'no match, try the next rule', with one turn arrow from row 5 to row 6. Route chips: 1 SUPERSEDED, 2 REFER, 3 REVIEW, 4 IGNORE, 5 REVIEW, 6 CLARIFY, 7 CLARIFY, 8 REFER, 9 'REVIEW or PICK'. Use neutral chips, or one muted colour per route used consistently with m04-final-confidence; PICK must not get an approval green. Put the PICK sentence as a small footnote under the right column. MIXED and the route tokens are in monospace.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m04-state-and-questions

- Title: Where the model sits in the decision flow
- Native size: 1536×1024; published SHA-256: `eaf1d0f7f76585d1e548481673d9401c8710299527cb2d68fa01c3a3287dc143`
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

TITLE (top-left): "Where the model sits in the decision flow"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "State built by software"
- "Catalog, desk rules and messages"
- "Quantity candidate IDs"
- "Questions"
- "7 supplied questions and 1 of your own"
- "Model"
- "Returns typed answers only; changes nothing"
- "Typed answers"
- "Validate"
- "Measure against your labels"
- "Code sets the route"
- "People make consequential decisions"
- "The model has no path to dispatch."

LAYOUT AND RELATIONSHIPS:
Upper left: two input boxes stacked vertically. Box 1 is 'State built by software', with the sub-line 'Catalog, desk rules and messages' and an attached inset 'Quantity candidate IDs'. Box 2 is 'Questions', with the sub-line '7 supplied questions and 1 of your own'. Plain arrows, meaning 'given to', run from both boxes into a central 'Model' box with the sub-line 'Returns typed answers only; changes nothing'. One arrow leaves Model to 'Typed answers', then continues down to a left-to-right row of four boxes joined by arrows meaning 'then': Validate → Measure against your labels → Code sets the route → People make consequential decisions. Draw no edge, crossed or dashed, from Model to anything except Typed answers. The no-dispatch sentence is a footnote under the row. No dot nodes or glow.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

## m04-supersession

- Title: How the router handles proposed replacement links
- Native size: 1536×1024; published SHA-256: `ec39bbf76c6eb4b68b44b3fd4a1410d0b4f0ae6fca5b0fbc6b481d514521d3ba`
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

TITLE (top-left): "How the router handles proposed replacement links"

TEXT ELEMENTS (each exactly once unless the layout says a token repeats; verbatim):
- "Proposed replaces link"
- "Is the link NONE, or is the replacer referred?"
- "Yes"
- "No"
- "Ignore the link"
- "Is link confidence below min_confidence?"
- "Mark both endpoints uncertain"
- "Record the replacement; the target is superseded"
- "Both results go to the routing rules, which apply in order."
- "Uncertain flags do not set a route by themselves."
- "Referred replacer: its instructs_desk p meets its gate,"
- "or its request p meets its gate and authority p does not."

LAYOUT AND RELATIONSHIPS:
Top-down flowchart. Start box 'Proposed replaces link' (replaces in monospace) → diamond 1 'Is the link NONE, or is the replacer referred?'. A Yes branch goes right to a neutral grey end box 'Ignore the link', which has no further arrow; the No branch goes down. → diamond 2 'Is link confidence below min_confidence?'. Yes branch right → 'Mark both endpoints uncertain'; No branch down → 'Record the replacement; the target is superseded'. Both of these outcome boxes have arrows into one bottom box, 'Both results go to the routing rules, which apply in order.', with the line 'Uncertain flags do not set a route by themselves.' directly beneath it. Each diamond has exactly one Yes and one No label. A footnote panel, bottom right and set off by a thin rule, holds the two-line referred-replacer definition. Neutral fills with a muted accent on outcomes, and no route tokens such as REVIEW in the flow.

Before returning, check every text element is present, spelled exactly, and nothing else was added.
````

