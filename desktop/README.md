# OSINT Atlas

OSINT Atlas is a macOS investigation workbench for the DOE contractor catalog on Google Photorealistic 3D Tiles. Find an entity, inspect its evidence and nearby context, and retain findings in a local Case.

## Run

```bash
cd desktop
npm install
npm run tauri dev
```

## Investigate

1. Press **Cmd/Ctrl+K** to find an entity or command. Search examples include `Hope Gas`, `risk critical`, `port 3389`, and `cve CVE-2007-2768`. The palette also opens Settings, Case, Shared CVEs, and Critical sites. Search uses the existing catalog queries, not natural-language analysis.
2. Open a dossier to read **Exposure**, **Nearby**, or **Kill chain**. Exposure retains the source evidence and its view limits. CVE and supported port actions open their corresponding catalog results. Results show both the returned count and the actual total.
3. In Nearby, choose a type and a 25, 50, or 100 km radius. Connections represent **geographic proximity**, not an inferred network relationship. The map draws the nearest eight named targets, plus an explicit ninth of the same type. A preview and Frame keep the origin selected; **Open dossier** selects the endpoint.
4. Use **Pin** or **Pin step** to retain the entity and its note in Case. Case is stored locally and survives reloads. It deduplicates entities and keeps the latest 12 pins, replacing the oldest when full. Remove deletes one pin; Clear requires confirmation. A failed save leaves the existing pins unchanged.

**Hide** closes the workspace without clearing the selection, filter, or results. The map's selection and filter chips restore their corresponding views. **Back** returns to the preceding workspace. The separate Clear selection and Clear filter actions remove only their respective state.

### Building footprints

Selecting an entity looks up its street address with Google Geocoding. An unambiguous building outline is highlighted in gold with a translucent fill over the 3D map. Hide keeps it; changing or clearing the selection removes it. Nearby previews keep the origin's outline.

The **Building footprint** chip opens **Google source and match** in the dossier. Use **Frame building** to center the camera on the matched building at its 3D surface height. This does not change the catalog location or the origin of Nearby results.

A building footprint is **not a parcel or ownership boundary**. If the catalog has no street address, a returned building must contain the mapped point. Ambiguous destinations, campus grounds, nearby landmarks, missing outlines, and lookup failures are not replaced with guessed rectangles or proximity circles.

The existing Google key must have **Geocoding API** enabled and allowed by its API restrictions, separately from Map Tiles API. See [Google's destination lookup documentation](https://developers.google.com/maps/documentation/geocoding/search-for-destinations). After enabling the API, use **Retry footprint**; changing the saved Maps key still requires Reload map.

The workspace docks beside the map on wide windows and becomes a bottom sheet below 1100 px. **Expand** reserves a 72 px map-and-credits strip; **Collapse** restores the map area. The native minimum window size is 480×560.

### Keyboard

| Key | Action |
| --- | --- |
| Cmd/Ctrl+K | Open the command palette. |
| Up/Down, Home/End, Enter | Choose a palette option while keeping input focus. |
| Escape | Dismiss the palette, visible step detail, proximity preview/connections, workspace, selection, or orbit, in that order. |
| 1 / 2 / 3 | Select Exposure / Nearby / Kill chain in a visible dossier. |
| Left/Right, Home/End | Move between dossier tabs when a tab has focus. |
| p / f | Pin the selected entity / frame its site. |
| [ / ] | Cycle the nearby radius. |
| j / k | Move between generated steps in the visible Kill chain tab. |

Dossier shortcuts do not run while typing in a field. Orbit requires Inspect first; reduced motion disables Orbit and stops one already running. Search, result lists, and Nearby rows provide alternatives to selecting map symbols.

## Services and unavailable states

The Google Maps key is resolved from Keychain service `google-maps-api` (accounts `api-key`, `default`, `key`), then `GOOGLE_MAPS_API_KEY`, then the repo `.env`. Map Tiles API must be enabled. `--no-keychain` skips Keychain. The app does not embed a key and does not request CARTO, Protomaps, or OpenFreeMap.
Enter keys for the five services in **Settings**. They are stored in the app support `config.json`; env vars and `.env` are still honored. Blank fields keep saved keys. Failed saves retain the draft and do not report success. After changing the Maps key, use the explicit reload action to rebuild the map.

Catalog and map readiness are separate. A missing Maps key or tile failure does not prevent catalog search and dossiers. Layers shows the actual source, count, age, and availability of each overlay. Sector filters do not enable overlays; **Show mobility overlays** explicitly enables flights, earthquakes, and satellites. Generated analysis requires configured OpenRouter access.


AIS uses `AIS_API_KEY` (Datalastic). FIRMS uses `FIRMS_API_KEY`, falling back to `FIRMS_MAP_KEY`. With either feed on, the app plots vessels owned or operated by the in-view contractor families (at most eight) and fires within 25 km of those families' sites. Selecting a contractor narrows both feeds to that family. The feeds do not download the camera box.

GodsEyeView layers are read from `GEV_ROOT` (default `/Users/ravistarzl/Documents/GitHub/gods-eye-view`). Dams and data centers are contextual search/proximity results, not a standing facility field. Missing sources and failed requests have separate states from a successful query with no matches.

## Development checks

From `desktop`, check the Svelte/TypeScript frontend and build its assets:

```bash
npm run check
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
