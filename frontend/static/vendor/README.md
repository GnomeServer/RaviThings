# Vendor JS Bundles

Self-hosted copies of third-party JS/CSS so the app survives unpkg.com
outages and corporate proxies that block CDNs.

| Package | Version | Source | License |
|---|---|---|---|
| Leaflet | 1.9.4 | https://unpkg.com/leaflet@1.9.4/ | BSD-2-Clause |
| Leaflet.markercluster | 1.5.3 | https://unpkg.com/leaflet.markercluster@1.5.3/ | MIT |
| Leaflet.heat | 0.2.0 | https://unpkg.com/leaflet.heat@0.2.0/ | BSD-2-Clause |
| d3 | 7.9.0 | https://unpkg.com/d3@7.9.0/ | ISC |

Downloaded: 2026-04-07. To upgrade, re-run the curl commands in
`docs/plans/2026-04-07-robustness-cross-browser.md` Task 3 with the new
version pin and bump the version column above.
