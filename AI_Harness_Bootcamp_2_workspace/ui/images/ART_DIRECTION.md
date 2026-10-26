# Homepage imagery: art direction and provenance

Maintainer record for the photographs in this directory. It is not published: the publisher ships only the files that `course.json` allowlists (`ui_assets`, `home_bands`). Course-owned photographs live here, never in the vendored `ui/vendor/sirocco/` directory.

## Files

| File | Size | Use | Scene |
|---|---|---|---|
| `home-hero.webp` | 1672×941, 142,250 B | Homepage hero (the first `.webp` in `ui_assets`) | A convoy of unmarked cargo trucks passes a scan portal at a forward supply-base gate at golden hour. One pallet waits behind a taped hold line. |
| `home-band-custody.webp` | 1672×716, 120,678 B | Band `custody` | A night receiving yard under amber light towers: staged pallet rows, a scan portal, a refrigerated container. |
| `home-band-route.webp` | 1672×716, 112,092 B | Band `route` | Four cargo trucks climb desert switchbacks at dusk toward a clinic in the valley. |
| `home-band-clinic.webp` | 1672×716, 110,536 B | Not placed | A field clinic receiving point at warm dusk, with the delivered stack confirmed. |

Custody and route are the placed bands: cargo received into custody, then the vehicle moves. They are decorative (`alt=""`), lazy-loaded, and placed on the home page with `<div data-photo-band="ID"></div>`. The clinic photograph is kept here and is not on the home page.

## Style guidance

Same lineage as the Starzl field photographs in `$HOME/Documents/GitHub/SE_Website/public/assets/` (`starzl-desert-operations`, `starzl-alt-pnt-network`, `starzl-ew-multidomain-range`; these were attached to every generation as style references and are not reproduced).

- Photoreal 35 mm documentary look, fine film grain, warm earthen grade with slight desaturation. The site CSS adds `sepia(.35) saturate(.8) brightness(.8) contrast(1.05)` and a scrim, so deliver a cleanly exposed photograph and keep overlay colors warm.
- Specific military logistics: palletized cargo under netting, transit cases, a refrigerated ISO container with generator, unmarked six-wheel cargo trucks, a scan portal, sandbag and barrier walls, tan clinic tents. No comms-only scenes.
- No people, no weapons, no readable text, numbers, logos, insignia, flags, or emblems (cargo markings are blank bars). No cool-colored glow, neon, code rain, hologram panels, lens flare, volumetric rays, or heavy depth of field.
- Palette tokens only: `#0D0906`, `#17110C`, `#A58650`, `#C8A96A`, `#C8B78A`, `#655337`, `#4F5634`, `#8FA15A`, `#B43A2F`, `#2D3030`, `#FFF8E7`.

### The cyberspace trace layer

One vocabulary, composed into the photograph at about 20–30% strength, photograph first:

1. Route traces: thin dotted arcs and vectors in light gold `#C8A96A` that follow real geometry, with small circular waypoint nodes.
2. Manifest brackets: thin L-shaped corner brackets (the UI's HUD-corner motif) over three to six real objects, with no legible characters.
3. Survey mesh: a faint translucent survey grid with topographic contour lines draped on the ground in perspective (the design system's survey grid and dune contours made spatial).
4. State nodes: olive `#8FA15A` = cleared or confirmed, gold = in transit, brick red `#B43A2F` = hold, at most one per image.

### Composition (current treatment)

- Hero: 16:9, subject mass in the right 55%, calm left 40% (the headline sits there), horizon 45–66% down, detail in the upper 75%.
- Band: generate 16:9 at 1672×941 and crop the vertical center to 1672×716. Keep all key content inside the central 68% of the height.

These ratios and crops are recommendations for the current visual treatment. The publisher reads and emits intrinsic dimensions; fixed pixel sizes are not a publication requirement.
## Generation

Codex's built-in image tool through `codex exec` (ChatGPT login; no API key). One call produces one image, in about 80–100 seconds. Attach the three style references with `-i`. The session id printed on stderr names the output folder under `$HOME/.codex/generated_images/`; never pick "the newest file", because parallel runs share that folder.

```
codex exec --skip-git-repo-check -s workspace-write -C <work-dir> \
  -i <starzl-desert-operations.png> -i <starzl-alt-pnt-network.png> -i <starzl-ew-multidomain-range.png> \
  -o <work-dir>/last-message.txt - < prompt.md
```

Prompt wrapper (prepended to each spec):

> Use the built-in image_gen tool (Codex's imagegen skill in its default built-in mode) to generate exactly ONE image. Do not use the CLI fallback, do not write code to produce the image, and do not copy or edit the attached reference images as the output. The attached images are STYLE references only: photographic realism, warm earthen grade, golden-hour light, hardware realism, film grain, and the thin dotted arc-trace idiom. Do not reproduce their subjects. Generate one image, then state the absolute path of the saved PNG file. Do not generate more than one image.

## Encoding

```
cwebp -quiet -q 66 -m 6 -sns 100 -f 50 -segments 4 -resize 1672 941 master.png -o home-hero.webp
cwebp -quiet -q 66 -m 6 -sns 100 -f 50 -segments 4 -crop 0 112 1672 716 master.png -o home-band-NAME.webp
```
Budgets and sizes are recommendations for the current treatment, not hard release caps. Hero at most 170 KB (soft target), band at most 130 KB. Plain `-q 80` produced 228 KB on the hero. Decode the sky and check for banding after encoding. The publisher reads WebP dimensions from the file header and emits the actual width/height for the shipped assets. The exact 1672×941 / 1672×716 sizes, byte counts, generation dates, and prompts below are the records for the images that were accepted and published; they are not requirements for future images.
## QA rubric

Accept only if every point holds, checked on the full image and on native-resolution crops of tablet screens, container panels, crate faces, tent flaps, and vehicle doors:

1. Photoreal, in the lineage's warm grade.
2. Specifically military logistics.
3. Trace layer present, subtle, warm, physically integrated; at most one brick-red hold marker; no cool glow.
4. No readable text or numbers, no people, no weapons, no emblems.
5. Composition rule for hero or band holds (after the crop, for bands).
6. No garbled hardware, duplicated objects, or watermark.

## Provenance

Generated on 2026-10-02 with Codex CLI 0.154.0 (built-in image tool). Every shipped image was accepted on its first generation. The hero was chosen from three candidates by previewing each inside the real page with the course CSS: the convoy-at-the-gate scene read strongest and kept its red hold node visible beside the left scrim. Residual defect, accepted: a blurred 30×8 px smudge on the hero portal beam is not legible at any display size. These are AI-generated images, not photographs of real events or equipment; they contain no real people, units, or markings.

## Prompts (exact text of each accepted generation)

### home-hero.webp

```
Use case: photorealistic-natural
Asset type: full-bleed website hero photograph, 16:9 landscape, 1672x941. A headline will sit over the left 40% of the frame, so that side must stay calm.
Primary request: A photoreal documentary wide shot of a military logistics convoy staging at the gate lane of a forward supply base in high desert at late golden hour, about to depart for a distant field clinic, with a restrained cyberspace trace layer woven into the scene like an instrumented digital manifest.
Scene/backdrop: flat desert with a graded dirt road running from the right foreground back toward the center of the horizon; low sandbag berms and concrete barrier segments flank the lane; a tall light tower; layered brown mountains on the horizon; the low sun is behind and to the left, glowing through thin dust; far on the horizon a small cluster of tan clinic tents.
Subject (right 55% of the frame): three unmarked tan and olive six-wheel cargo trucks nose-to-tail receding along the road, their loads of netted pallets under tarps; the lead truck passes under a simple steel scan-portal frame spanning the road with small antennas; beside the road, a staging line of netted pallets and olive-drab and tan transit cases; at the far right edge a camouflage-netted 20-foot refrigerated ISO container with reefer unit and generator; a rugged tablet open on a case in the lower right foreground showing only an abstract amber route graph.
Cyberspace layer (about 25-30% strength, photograph first): one continuous thin light-gold (#C8A96A) dotted route trace running along the road from the convoy toward the distant clinic tents, with small circular waypoint nodes; a few dotted arcs rising from the truck loads into the sky; thin gold L-shaped corner brackets floating over each truck's load and over two roadside pallets as manifest tags, with no legible characters; a faint translucent survey grid with topographic contour lines draped on the terrain either side of the road, fading with distance; olive (#8FA15A) nodes on the cleared truck loads; exactly one brick-red (#B43A2F) node over a single pallet set apart at the roadside behind a taped hold line, in the right-middle ground.
Composition/framing: eye-level, slightly low, 35mm; horizon about 55% down; the left 40% is calm sky, open desert and the far road with minimal detail; all important detail within the upper 75% of the frame.
Lighting/mood: backlit late golden hour, long soft shadows toward the viewer, warm dust glow around the tires, warm shadows, quiet and exacting.
Style/medium: photograph, 35mm documentary look, natural film grain, naturalistic slightly desaturated warm grade.
Color palette: sandstone and tan (#C8B78A), olive drab (#4F5634), warm near-black shadows (#0D0906), gold accents (#A58650, #C8A96A); no cool colors anywhere.
Constraints: no people, faces or hands; no weapons; no readable text, numbers, logos, insignia, flags or emblems anywhere (all markings are blank bars or abstract marks); no red cross or red crescent emblem; no watermark.
Avoid: neon; cyan, blue, purple or green glow; Matrix code rain; hacker wall; holographic panels with text; lens flare; volumetric god rays; bloom; heavy depth of field; HDR look; waxy, plastic, CGI, 3D-render, cartoon or stock-photo look; garbled machinery.
```

### home-band-custody.webp

```
Use case: photorealistic-natural
Asset type: wide website mood strip. Generate 16:9 landscape 1672x941; it will be cropped to a 21:9 strip from the vertical center, so keep ALL key content within the central 68% of the frame height. No headline overlay.
Primary request: A photoreal documentary night shot of a forward military logistics depot receiving yard under amber light: cargo received into custody, staged but not yet released, with a restrained cyberspace trace layer.
Scene/backdrop: a gravel and hardpan receiving yard at night; the sky is warm brown-black with a few faint stars and NO blue cast, lit only by two or three tall sodium-amber light towers and amber vehicle marker lights; a low sandbag berm and concrete barrier wall in the distance; a line of tan frame tents far away glowing faintly amber.
Subject: neat rows of shrink-wrapped, netted medical pallets and olive-drab and tan transit cases staged on dunnage across the yard, receding toward the distance; a 20-foot ISO reefer container with its unit and a diesel generator under a light tower at the right; an unmarked tan cargo truck waiting at the lane; a simple tripod scan portal with small antennas at the lane in the center; a rugged tablet open on a transit case in the foreground showing only an abstract amber graph.
Cyberspace layer (about 25-30% strength, photograph first): many small gold node points, one on each pallet in the rows, like an inventory ledger; thin light-gold (#C8A96A) dotted traces linking the rows to the scan portal and onward toward a faint clinic glow on the horizon; thin gold L-shaped corner brackets around six to eight pallets as manifest tags, with no legible characters; a faint translucent survey grid with topographic contour lines draped across the yard in perspective; olive (#8FA15A) nodes on a few cleared pallets nearest the truck; exactly one brick-red (#B43A2F) node over a single pallet set apart behind a taped hold line in the middle ground.
Composition/framing: low wide angle, 35mm, vanishing point slightly right of center; key content within the central 68% of the frame height; sky and foreground gravel may be plain.
Lighting/mood: pools of warm amber light with long soft shadows, thin dust haze in the light, deep warm shadows in the #0D0906 family, quiet.
Style/medium: photograph, 35mm documentary look, natural film grain, naturalistic slightly desaturated warm grade.
Color palette: sandstone and tan (#C8B78A), olive drab (#4F5634), warm near-black shadows (#0D0906), gold accents (#A58650, #C8A96A); no cool colors anywhere.
Constraints: no people, faces or hands; no weapons; no readable text, numbers, logos, insignia, flags or emblems anywhere (all markings are blank bars or abstract marks); no red cross or red crescent emblem; no watermark.
Avoid: neon; cyan, blue, purple or green glow; Matrix code rain; hacker wall; holographic panels with text; lens flare; volumetric god rays; bloom; heavy depth of field; HDR look; waxy, plastic, CGI, 3D-render, cartoon or stock-photo look; garbled machinery.
```

### home-band-route.webp

```
Use case: photorealistic-natural
Asset type: wide website mood strip. Generate 16:9 landscape 1672x941; it will be cropped to a 21:9 strip from the vertical center, so keep ALL key content within the central 68% of the frame height. No headline overlay.
Primary request: A photoreal documentary elevated wide shot of a military logistics convoy of four unmarked tan and olive six-wheel cargo trucks climbing a graded desert switchback road at dusk, loads covered under tarps, dust trails glowing gold in the low sun, amber marker lights on, headed toward a distant valley where a small cluster of tan clinic tents glows with warm light. The cyberspace trace layer follows the route.
Scene/backdrop: arid ridges and mountains layered in warm haze receding to a glowing horizon; the road snakes diagonally through the middle of the frame with several switchbacks; plain warm sky above and a plain rocky slope in the foreground.
Cyberspace layer (about 25-30% strength, photograph first): a thin continuous light-gold (#C8A96A) dotted route trace following the road with small circular waypoint nodes at each switchback as checkpoints; thin gold L-shaped corner brackets floating over the lead truck and the third truck as manifest tags, with no legible characters; a faint translucent survey grid with topographic contour lines draped across the mountain slopes in perspective, fading into the haze; olive (#8FA15A) nodes on checkpoints already passed; a gold node on the lead truck (in transit); a single olive node at the distant clinic tents (arrival). No red marker in this image.
Composition/framing: elevated vantage looking down a valley, 35mm; the road and convoy occupy the central 68% of the frame height; sky and foreground slope are plain.
Lighting/mood: low dusk sun behind the ridges, long soft shadows, gold dust trails, warm haze, warm shadows, quiet and exacting.
Style/medium: photograph, 35mm documentary look, natural film grain, naturalistic slightly desaturated warm grade.
Color palette: sandstone and tan (#C8B78A), olive drab (#4F5634), warm near-black shadows (#0D0906), gold accents (#A58650, #C8A96A); no cool colors anywhere.
Constraints: no people, faces or hands; no weapons; no readable text, numbers, logos, insignia, flags or emblems anywhere (all markings are blank bars or abstract marks); no red cross or red crescent emblem; no watermark.
Avoid: neon; cyan, blue, purple or green glow; Matrix code rain; hacker wall; holographic panels with text; lens flare; volumetric god rays; bloom; heavy depth of field; HDR look; waxy, plastic, CGI, 3D-render, cartoon or stock-photo look; garbled machinery.
```

### home-band-clinic.webp

```
Use case: photorealistic-natural
Asset type: wide website mood strip. Generate 16:9 landscape 1672x941; it will be cropped to a 21:9 strip from the vertical center, so keep ALL key content within the central 68% of the frame height. No headline overlay.
Primary request: A photoreal documentary shot of a field clinic receiving point at warm dusk: cargo delivered and the usable quantity confirmed. Unloaded medical transit cases and netted pallets are stacked on a staging mat at the entrance of tan frame tents lit warm from within; an unmarked tan cargo truck pulls away in the background with amber taillights; a rugged tablet sits open on a case beside a simple scan post. The cyberspace trace layer shows the movement closing.
Scene/backdrop: flat desert at dusk with a warm glowing sky near the horizon and a warm brown-dark upper sky with NO blue cast; plain tan tents with no emblems or markings, soft warm light spilling from their open flaps; a string of warm bulbs along the tent line; a graded dirt road leading away to the horizon.
Cyberspace layer (about 25-30% strength, photograph first): thin light-gold (#C8A96A) dotted traces arriving from the distance along the road and curving down to end at the received stack; the trace ends in a single olive (#8FA15A) confirmation node over the stack, with a thin gold L-shaped corner bracket around it; a few more thin gold L-shaped corner brackets around other unloaded cases as manifest tags, with no legible characters; a faint translucent survey grid with topographic contour lines draped on the ground in perspective, strongest in the mid-distance and fading out; small olive nodes on cleared cases. No red marker in this image.
Composition/framing: eye-level, 35mm; the stacked cases and tent entrance sit in the central 68% of the frame height, slightly right of center; plain sky above and plain ground below.
Lighting/mood: warm dusk, soft pools of warm tent light on the ground, thin dust haze, deep warm shadows in the #0D0906 family, quiet.
Style/medium: photograph, 35mm documentary look, natural film grain, naturalistic slightly desaturated warm grade.
Color palette: sandstone and tan (#C8B78A), olive drab (#4F5634), warm near-black shadows (#0D0906), gold accents (#A58650, #C8A96A); no cool colors anywhere.
Constraints: no people, faces or hands; no weapons; no readable text, numbers, logos, insignia, flags or emblems anywhere (all markings are blank bars or abstract marks); no red cross or red crescent emblem; no watermark.
Avoid: neon; cyan, blue, purple or green glow; Matrix code rain; hacker wall; holographic panels with text; lens flare; volumetric god rays; bloom; heavy depth of field; HDR look; waxy, plastic, CGI, 3D-render, cartoon or stock-photo look; garbled machinery.
```
