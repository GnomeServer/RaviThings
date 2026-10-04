# OSINT Atlas

OSINT Atlas is a macOS investigation workbench for the DOE contractor catalog on Google Photorealistic 3D Tiles. Find an entity, inspect its evidence and nearby context, and retain findings in a local Case.

## Run

### Standalone macOS app

Use the standalone app when you do not need live code updates. From the repository root:

```bash
cd desktop
npm install
npm run tauri build -- --bundles app
open "src-tauri/target/release/bundle/macos/OSINT Atlas.app"
```

The app includes Cesium's runtime, geometry workers, terrain-height data, and widget assets. It does not need the Vite development server. Google 3D Tiles and enabled live services still need network access.

### Development

Keep the development command running while you use the app:


```bash
cd desktop
npm install
npm run tauri dev
```

Cesium loads some worker files and data only when you select a site. If you stop the development server while leaving a development app window open, those requests can fail and stop map rendering. Relaunch with the command above, or use the standalone app.

## Investigate

1. Press **Cmd/Ctrl+K** to find an entity or command. Search examples include `Hope Gas`, `risk critical`, `port 3389`, and `cve CVE-2007-2768`. The palette also opens Settings, Case, Shared CVEs, and Critical sites. Search uses the existing catalog queries, not natural-language analysis.
2. Open a dossier to read **Exposure**, **Nearby**, or **Kill chain**. Exposure starts with the catalog-derived score, federal obligation, contract count, observed hosts, and recorded CVEs. Use **Overview**, **Findings**, **Brief**, **Network**, **Sources**, and **Profile** to jump to the corresponding evidence. Additional CVEs, host services, certificate subdomains, and ASN hosts remain available in expandable lists. CVE and supported port actions open their corresponding catalog results, with both the returned count and the actual total.
3. In Nearby, choose a type and a 25, 50, or 100 km radius. Connections represent **geographic proximity**, not an inferred network relationship. The map draws the nearest eight named targets, plus an explicit ninth of the same type. A preview and Frame keep the origin selected; **Open dossier** selects the endpoint.
4. Use **Pin** or **Pin step** to retain the entity and its note in Case. Case is stored locally and survives reloads. It deduplicates entities and keeps the latest 12 pins, replacing the oldest when full. Remove deletes one pin; Clear requires confirmation. A failed save leaves the existing pins unchanged.

On the map, national-scale counts group contractors. Click a group's circle or count to frame its members at regional scale and see individual markers. This movement starts without waiting for a surface-height lookup and does not start an orbit. Hover for identity, category, location, and catalog exposure where available; click a marker to open its dossier. A selected entity keeps a labeled map marker and a summary card with **Inspect**, **Nearby**, and **Pin** actions. Contractor cards include recorded evidence totals and collection status; facility cards show geographic identity and operator details without assigning a contractor exposure score. The lower-right sector controls hide other categories. CVE filters keep nonmatching markers dimmed and selectable.

**Evidence sources** distinguishes successful collection, no results, errors, uncollected data, and records that need refreshing after a domain change. Missing or failed collection is not shown as a zero observation. Source dates describe stored observations, not live checks; the latest successful date does not imply every source is current. Source errors and conflicting domain observations are called out in the dossier and selection card.

As you zoom, the map loads the 3D tiles needed for the current view. Contractor markers and Nearby radius outlines follow the surfaces already loaded, without requesting maximum-detail tiles for every location. Their height updates run in small batches after movement stops and when tiles finish loading, leaving the map responsive while detail resolves. Image detail still depends on Google's coverage and your connection.

The compact attribution strip uses **Google Maps** text instead of a logo, as permitted for space-constrained layouts by the [Map Tiles API attribution policy](https://developers.google.com/maps/documentation/tile/policies#logo). **Data attribution** opens the viewport's provider credits over the app window, including when the dossier is expanded. Cesium ion branding is omitted because Atlas uses Google's API directly, with no ion assets or geocoder; this does not remove Google's or other data providers' attribution.

**Hide** closes the workspace without clearing the selection, filter, or results. The map's selection card and filter chips restore their corresponding views. **Back** returns to the preceding workspace. The separate Clear selection and Clear filter actions remove only their respective state.

### Analysis and progress

To follow a **Kill chain** or **Step detail** request, read its progress record. It appears immediately with the request type and subject. It shows reported stages, the model when reported, elapsed time, output character count, and when model data last arrived. Stages include preparing, connecting, waiting, streaming, parsing, and verifying. Completion shows **Complete**; an error shows **Failed** with its message.

The provisional answer preview shows only the last 1,200 characters of streamed output. It is separate from the final validated result shown in the dossier. It contains no private model reasoning, estimated finish time, or invented percentage. To read without the text changing, focus the preview or scroll up. The preview text pauses while progress counters continue. Return to the end and move focus out of the preview to resume the live tail. This pauses only the display; the model continues working.

Changing selection or collapsing a step does not cancel its model request. Each concurrent request keeps its own subject and progress, with the newest active request first. An earlier result cannot attach to a new dossier or a different step. History retains the latest three finished records plus a finished record that still has focus. To remove a finished record, use **Dismiss**.

Ask, filter, CVE, and port queries have their own busy, result, and error feedback. Catalog queries can run while analysis is active. Camera preparation has separate feedback and remains stoppable with **Stop**.

### Building footprints

Selecting an entity looks up its street address with Google Geocoding. An unambiguous building outline is highlighted in gold with a translucent fill over the 3D map. Hide keeps it; changing or clearing the selection removes it. Nearby previews keep the origin's outline.

The **Building footprint** chip opens **Google source and match** in the dossier. Use **Frame building** to focus the matched building at its 3D surface height and begin one 40-second orbit. This does not change the catalog location or the origin of Nearby results.

A building footprint is **not a parcel or ownership boundary**. If the catalog has no street address, a returned building must contain the mapped point. Ambiguous destinations, campus grounds, nearby landmarks, missing outlines, and lookup failures are not replaced with guessed rectangles or proximity circles.

The existing Google key must have **Geocoding API** enabled and allowed by its API restrictions, separately from Map Tiles API. See [Google's destination lookup documentation](https://developers.google.com/maps/documentation/geocoding/search-for-destinations). After enabling the API, use **Retry footprint**; changing the saved Maps key still requires Reload map.

The workspace docks beside the map on wide windows and becomes a bottom sheet below 1100 px. **Expand** reserves a 72 px map-and-credits strip; **Collapse** restores the map area. Short bottom-sheet windows open expanded so the dossier remains readable. The native minimum window size is 480×560.

### Inspect and orbit

Use **Inspect** or **Frame building** for a close-up followed by one gentle, 40-second aerial revolution. **Orbit** explicitly starts another revolution after either close-up action. These views use the interactive Google Photorealistic **3D Tiles**, not the prerecorded Google Aerial View video API.

Inspect and Orbit target the selected building footprint when a match is already available; otherwise they use the selected coordinates. Close-up and Site views use the actual Google tile surface height. If that height is unavailable, camera motion stops and a message explains the failure. Site, Region, and Nearby endpoint framing use the requested coordinates; a Nearby endpoint does not inherit the origin's building outline.

Surface preparation first uses the Google geometry already rendered on the map. If the target surface is not rendered yet, preparation waits up to 10 seconds for detailed tiles. If the lookup fails or times out, motion stops and a message tells you to wait for the tiles to load before trying again. **Stop** cancels preparation immediately; a late tile response cannot restart the camera.

While the camera is preparing or orbiting, **Stop** is directly available beside the map. In an expanded workspace, it moves to the workspace header so the map attribution stays clear. You can also stop by pressing **Escape**, pressing or touching the map, or scrolling over it. Your first map gesture still works normally. Stopping keeps your dossier, connections, and selection open; another Escape follows the dismissal order below.

Another camera command, changing or clearing the selection, opening the command palette, enabling reduced motion, or unloading the map also cancels current and pending camera movement. The orbit ends after one revolution and never resumes automatically after interruption. Selecting an entity, using Site or Region, zooming closer, loading tiles, or receiving a footprint match does not start an orbit. With reduced motion enabled, close-up actions focus the subject without orbiting.

### Keyboard

| Key | Action |
| --- | --- |
| Cmd/Ctrl+K | Open the command palette. |
| Up/Down, Home/End, Enter | Choose a palette option while keeping input focus. |
| Escape | Stop current or pending camera motion first. Otherwise dismiss the palette, visible step detail, proximity preview/connections, workspace, or selection, in that order. |
| 1 / 2 / 3 | Select Exposure / Nearby / Kill chain in a visible dossier. |
| Left/Right, Home/End | Move between dossier tabs when a tab has focus. |
| p / f | Pin the selected entity / frame its site. |
| [ / ] | Cycle the nearby radius. |
| j / k | Move between generated steps in the visible Kill chain tab. |

Dossier shortcuts do not run while typing in a field. Search, result lists, and Nearby rows provide alternatives to selecting map symbols.

## Services and unavailable states

The Google Maps key is resolved from Keychain service `google-maps-api` (accounts `api-key`, `default`, `key`), then `GOOGLE_MAPS_API_KEY`, then the repo `.env`. Map Tiles API must be enabled. `--no-keychain` skips Keychain. The app does not embed a key and does not request CARTO, Protomaps, or OpenFreeMap.
Enter keys for the five services in **Settings**. They are stored in the app support `config.json`; env vars and `.env` are still honored. Blank fields keep saved keys. Failed saves retain the draft and do not report success. After changing the Maps key, use the explicit reload action to rebuild the map.

Catalog and map readiness are separate. A missing Maps key or tile failure does not prevent catalog search and dossiers. Layers shows the actual source, count, age, and availability of each overlay. Sector filters do not enable overlays; **Show mobility overlays** explicitly enables flights, earthquakes, and satellites. Generated analysis requires configured OpenRouter access.


AIS uses `AIS_API_KEY` (Datalastic). FIRMS uses `FIRMS_API_KEY`, falling back to `FIRMS_MAP_KEY`. With either feed on, the app plots vessels owned or operated by the in-view contractor families (at most eight) and fires within 25 km of those families' sites. Selecting a contractor narrows both feeds to that family. The feeds do not download the camera box.

GodsEyeView layers are read from `GEV_ROOT` (default `/Users/ravistarzl/Documents/GitHub/gods-eye-view`). Dams and data centers are contextual search/proximity results, not a standing facility field. Missing sources and failed requests have separate states from a successful query with no matches.

## Development checks

From `desktop`, check the Svelte/TypeScript frontend, run the evidence-summary regression tests, and build its assets:

```bash
npm run check
npm run test:insights
npm run build
```

The browser development page can exercise the shell and CSS, but catalog, service, and map verification requires the native Tauri application. Catalog tests, from the repository root:

```bash
cd desktop/src-tauri
cargo test
```

## Local interface assets

Sirocco 1.0.0 CSS, fonts, grain, and the 18 used SVG icons are vendored unchanged under `src/lib/vendor/sirocco`. The interface does not load fonts or icons from a CDN or depend on an external Sirocco checkout. Atlas-specific layout and domain styles remain outside the vendor files.

Original private package metadata and the four font OFL notices are included in `static/licenses/sirocco`, which is copied to `build/licenses/sirocco` for distribution. Google Tiles and enabled live services still require their respective network access.
