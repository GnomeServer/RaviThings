# OSINT Atlas — Section 1 Pipeline Visualization Panels

4 quad-panel images (2x2 grid) covering all 14 pipeline layers. Generate each as 16:9 (1920x1080).
Place generated images in `videos/panels/` as: `panel1_discovery.jpg`, `panel2_infrastructure.jpg`, `panel3_classification.jpg`, `panel4_synthesis.jpg`

All examples are real data from the DOE contractor dataset.

---

## Visual Framework (apply to ALL panels)

Dark navy background (#0a0e1a). Cyan accent (#00e5ff). JetBrains Mono monospace font for all text. Tactical HUD aesthetic — DARPA command center, not consumer dashboard. Minimal, clean, high contrast. No people. No stock-photo feeling. Technical precision. 16:9 aspect ratio. Thin cyan dividing lines between quadrants. Each quadrant has a small layer number badge in the top-left corner.

---

## Panel 1: DISCOVERY & VALIDATION (Layers 01-04)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 1: DISCOVERY & VALIDATION" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (01, 02, 03, 04) in the top-left corner.

TOP-LEFT (01 DOMAIN DISCOVERY): A cascading list of real DOE contractor names on the left — "BATTELLE MEMORIAL INSTITUTE", "BECHTEL NATIONAL INC", "TRIAD NATIONAL SECURITY LLC", "UT-BATTELLE LLC", "FOUR RIVERS NUCLEAR PARTNERSHIP" — each paired with a domain resolving on the right: "battelle.org", "bechtel.com", "triadns.org", "ut-battelle.org", "fourriversnuclear.com". Thin cyan connection lines between them. Green checkmarks on successful resolutions, red X on a few failures. Counter badge: "2,214 targets / 2,196 resolved".

TOP-RIGHT (02 AI RESEARCH): Split panel — left side shows a contractor record "CENTERRA GROUP LLC" with a yellow warning triangle on domain "gsa.gov/elibrary" (wrong — that's a government catalog). Right side shows AI research: web search results, news articles about Constellis Holdings acquisition, corrected domain "constellis.com" with green checkmark. Cyan arrow connecting the correction. Badge: "987 domains corrected / 2,211 briefs generated".

BOTTOM-LEFT (03 DOMAIN VERIFICATION): A verification interface for "battelle.org". SSL padlock icon showing valid certificate. Scanning overlay checking page content for "Battelle Memorial Institute" — match highlighted in cyan. Side panel shows signals as indicator lights: "MX: Microsoft 365" (green), "Domain Name Match" (green), "AI Research: 95% confidence, 3 sources" (green). Verdict: "LIKELY" at 60% confidence. Counter: "511 verified".

BOTTOM-RIGHT (04 DNS INTELLIGENCE): Terminal window with DNS record output for "triadns.org" in green monospace text. MX records visible pointing to mail servers. SPF record showing authorized senders. A DMARC record field glowing red: "v=DMARC1; p=none" — or better, completely empty with "NO RECORD FOUND" in red. Below: summary badges — "Mail: Unknown", "DNS: Unknown", "DMARC: NOT SET" in red. Second example below: "battelle.org" with "Mail: Proofpoint", "DNS: Cloudflare", "DMARC: reject" in green.

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast against the dark background.

---

## Panel 2: INFRASTRUCTURE MAPPING (Layers 05-08)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 2: INFRASTRUCTURE MAPPING" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (05, 06, 07, 08) in the top-left corner.

TOP-LEFT (05 CERTIFICATE TRANSPARENCY): A radial tree diagram with "battelle.org" as the root domain node at center. Branches extend outward to real subdomains and associated domains: "pnnl.gov", "pnl.gov", "labworks.org". A second cluster shows UC domain with subdomains: "vpn.*", "auth.*", "optiputer.net", "ucsd.edu". Certificate icon on root nodes. Thin cyan connection lines. Counter: "465,109 certificates analyzed / 19,874 subdomains discovered".

TOP-RIGHT (06 WEB FINGERPRINTING): A layered X-ray view for "battelle.org" showing the web stack — server layer: "Cloudflare" (CDN/proxy), with security headers checklist: HSTS (green check), X-Frame-Options (green check), CSP (red X), X-Content-Type (red X). Score badge: "2/4". Second smaller example: "fourriversnuclear.com" showing score "4/4" — all green checks. Faded HTTP response headers visible in background.

BOTTOM-LEFT (07 SHODAN ORG SEARCH): A dark world map with glowing cyan dots. Shodan search bar at top: org:"Battelle Memorial Institute". Results cascade on the right: top ports — 443 (155 hosts), 80 (144 hosts), 161 (41 hosts). Top services listed: "BigIP (138)", "ntpd (33)", "OpenSSH (17)". Domains found: "pnnl.gov, pnl.gov, battelle.org". Counter: "430 hosts / 3 ASNs / 20 CVEs". Dots pulse like radar pings.

BOTTOM-RIGHT (08 PER-IP ENRICHMENT): A detailed host profile card for a Battelle host. IP address in cyan monospace. Organization: "Pacific Northwest Division". Service table showing rows with real data: port 443/HTTPS, port 80/HTTP, port 161/SNMP — each with product and version from banners. Right panel: SSL certificate details. Bottom: CVE badges. Corner badge: "HOSTED: On-Premises" in red. Timestamp: "Scanned: 3d ago". Counter: "9,586 hosts enriched across fleet".

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast.

---

## Panel 3: NETWORK CLASSIFICATION (Layers 09-12)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 3: NETWORK CLASSIFICATION" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (09, 10, 11, 12) in the top-left corner.

TOP-LEFT (09 ASN ENUMERATION): Network topology diagram with real ASN data. Large translucent circles: "AS3428" (Battelle), "AS32513" (PNNL), "AS10796" (Battelle Energy). A second cluster: "AS26397" and "AS46985" (UC system). Inside each ASN circle, smaller dots represent IP addresses. Lines connect IPs to their ASN. Battelle ASNs highlighted cyan — "CONTRACTOR-OWNED". Faint routing table in background.

TOP-RIGHT (10 ON-PREMISES CLASSIFICATION): Split visualization using real Battelle data. Left half labeled "ON-PREMISES" in red — showing IPs "192.101.x.x" series with server rack icon. Right half labeled "CLOUD" in cyan — showing "104.18.x.x" and "172.64.x.x" (Cloudflare). Second example below: Four Rivers showing single IP "192.169.x.x" classified as on-prem via GoDaddy. Counter: "1,585 contractors with on-premises infrastructure identified".

BOTTOM-LEFT (11 SERVICE RISK CLASSIFICATION): Side-by-side comparison using real UC Regents data. Left panel titled "NAIVE (Port-Based)" with red strikethrough: "Port 1433 → MSSQL (critical)" and "Port 3306 → MySQL (critical)". Right panel titled "BANNER-AWARE" with cyan checkmark: "Port 1433 / Banner: OpenSSH 6.0p1 → SSH-on-:1433 (medium)" and "Port 3306 / Banner: OpenSSH 6.0p1 → SSH-on-:3306 (medium)". Below: real Four Rivers dangerous services — "SMB: EternalBlue/WannaCry vector", "MySQL: weak auth", "RDP: BlueKeep/brute force", "FTP: cleartext". Badge: "227 contractors at critical severity".

BOTTOM-RIGHT (12 NVD CVSS SCORING): Vulnerability display using real data. Featured CVE card: "CVE-2023-38408 / CVSS 9.8 / OpenSSH 6.0p1 / Unauthenticated RCE / Public Exploit Available" — the UC Regents finding. Below: fleet-wide stats as horizontal bars — "Battelle: 20 CVEs", "UC Regents: 20 CVEs". Counter: "237 contractors with known CVEs on exposed hosts".

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast.

---

## Panel 4: INTELLIGENCE SYNTHESIS (Layers 13-14 + Summary)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 4: INTELLIGENCE SYNTHESIS" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (13, 14, greek-sigma, #) in the top-left corner.

TOP-LEFT (13 ENTITY EXTRACTION): A real text excerpt from the Battelle AI research brief: "Battelle Memorial Institute is a major nonprofit research organization that manages DOE national laboratories, including Pacific Northwest National Laboratory in Richland, WA, and Oak Ridge National Laboratory..." with named entities highlighted — "Battelle Memorial Institute" (organization, purple), "Pacific Northwest National Laboratory" (facility, green), "Richland, WA" (location, yellow), "Oak Ridge National Laboratory" (facility, green), "DOE" (organization, purple). Lines connecting to categorized sidebar. Counter: "6,134 entities / 2,211 briefs".

TOP-RIGHT (14 KNOWLEDGE GRAPH): A large-scale network graph. Visible clusters with real labels — a "National Laboratories" cluster containing nodes for PNNL, ORNL, LANL, Sandia, LLNL. A "Nuclear Weapons Complex" cluster with Pantex, Y-12, Savannah River. Technology nodes: SCADA, enrichment, plutonium processing. Relationship lines connecting facilities to their management companies (Battelle→PNNL, Triad→LANL, UT-Battelle→ORNL). Stats: "24,706 nodes / 72,064 relationships". Query bar: "vector + keyword + graph + relationship → RRF → reranker".

BOTTOM-LEFT (PIPELINE OVERVIEW): A vertical flow diagram showing all 14 layers as numbered horizontal bars connected by downward arrows. Bars color-coded by phase — Discovery layers 1-4 (cyan), Infrastructure layers 5-8 (green), Classification layers 9-12 (orange), Synthesis layers 13-14 (red). Real layer names abbreviated: "Domain Disc.", "AI Research", "Domain Verify", "DNS Intel", "CT Logs", "Web FP", "Shodan Org", "Shodan IP", "ASN Enum", "On-Prem", "Svc Risk", "NVD CVSS", "Entity Ext.", "Knowledge Graph".

BOTTOM-RIGHT (SCALE): Large typography displaying real statistics stacked vertically: "2,214 CONTRACTORS", "51 STATES & TERRITORIES", "$127.6B OBLIGATIONS", "2,196 DOMAINS RESOLVED", "465,109 CERTIFICATES", "9,586 HOSTS ENRICHED", "24,706 GRAPH NODES", "72,064 RELATIONSHIPS". Each number in bold cyan, labels in muted gray. Minimal, impact-driven.

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast.
