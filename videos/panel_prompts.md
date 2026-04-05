# OSINT Atlas — Section 1 Pipeline Visualization Panels

4 quad-panel images (2x2 grid) covering all 14 pipeline layers. Generate each as 16:9 (1920x1080).
Place generated images in `videos/panels/` as: `panel1_discovery.png`, `panel2_infrastructure.png`, `panel3_classification.png`, `panel4_synthesis.png`

---

## Visual Framework (apply to ALL panels)

Dark navy background (#0a0e1a). Cyan accent (#00e5ff). JetBrains Mono monospace font for all text. Tactical HUD aesthetic — DARPA command center, not consumer dashboard. Minimal, clean, high contrast. No people. No stock-photo feeling. Technical precision. 16:9 aspect ratio. Thin cyan dividing lines between quadrants. Each quadrant has a small layer number badge in the top-left corner.

---

## Panel 1: DISCOVERY & VALIDATION (Layers 01-04)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 1: DISCOVERY & VALIDATION" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (01, 02, 03, 04) in the top-left corner.

TOP-LEFT (01 DOMAIN DISCOVERY): A cascading list of company names on the left paired with domain names resolving on the right. Thin cyan connection lines between them. Green checkmarks on successful resolutions, red X marks on failures. Counter badge: "2,214 targets / 1,227 resolved".

TOP-RIGHT (02 AI RESEARCH): Split panel — left side shows a contractor record with a yellow warning triangle on a mismatched domain, right side shows web search results and news articles feeding into a corrected domain with a green checkmark. Cyan arrow connecting the correction. Badge: "987 domains corrected".

BOTTOM-LEFT (03 DOMAIN VERIFICATION): A dimly visible website behind a scanning overlay grid. Side panel shows verification signals as indicator lights: "SSL Certificate: VALID" (green), "Name Match: FOUND" (green), "Parking Page: NO" (green). Circular confidence gauge showing 92%.

BOTTOM-RIGHT (04 DNS INTELLIGENCE): Terminal window with DNS record output in green monospace text. MX and SPF records visible. A DMARC record field glowing red with "p=none" highlighted. Below the terminal: summary dashboard with badges — "Email: Google Workspace", "DNS: Cloudflare", "DMARC: NOT CONFIGURED" in red.

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast against the dark background.

---

## Panel 2: INFRASTRUCTURE MAPPING (Layers 05-08)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 2: INFRASTRUCTURE MAPPING" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (05, 06, 07, 08) in the top-left corner.

TOP-LEFT (05 CERTIFICATE TRANSPARENCY): A radial tree diagram with a root domain node at center. Branches extend outward to discovered subdomains labeled vpn.*, auth.*, dev.*, staging.*, api.*, mail.*. VPN endpoints glow red, authentication portals glow orange, dev servers glow yellow. Thin cyan connection lines. Certificate icon on the root node. Counter: "42 subdomains discovered".

TOP-RIGHT (06 WEB FINGERPRINTING): A layered X-ray view showing three stacked layers — bottom: "Ubuntu 22.04" (operating system), middle: "nginx 1.24" (web server), top: "WordPress 6.4" (CMS). To the right, a security headers checklist: HSTS (green check), CSP (red X), X-Frame-Options (green check), X-Content-Type (red X). Score badge: "2/4". Faded HTTP response headers visible in background.

BOTTOM-LEFT (07 SHODAN ORG SEARCH): A dark world map with glowing cyan dots representing discovered hosts. Shodan search bar at top: org:"Battelle Memorial Institute". Results list on the right side showing IP addresses with colored port badges — red for 445/3389, yellow for 22, green for 443. Dots pulse like radar pings. Counter: "430 hosts / 1,247 open ports".

BOTTOM-RIGHT (08 PER-IP ENRICHMENT): A detailed host profile card. Large IP address in cyan monospace at top. Service table below showing rows: port 443/HTTPS "nginx 1.24", port 22/SSH "OpenSSH 8.9", port 3306/MySQL "MySQL 5.7.38" — each row with a colored severity dot. Right panel: SSL certificate details (issuer, expiry). Bottom: CVE badges in red and orange. Corner badge: "HOSTED: AWS". Timestamp: "Scanned: 2d ago".

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast.

---

## Panel 3: NETWORK CLASSIFICATION (Layers 09-12)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 3: NETWORK CLASSIFICATION" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (09, 10, 11, 12) in the top-left corner.

TOP-LEFT (09 ASN ENUMERATION): Network topology diagram with large translucent circles representing autonomous systems, labeled "AS13335", "AS16509", "AS14618". Inside each circle, smaller dots represent IP addresses. Thin lines connect IPs to their ASN. One ASN circle highlighted in cyan with label "CONTRACTOR-OWNED", others labeled "CLOUD PROVIDER" in gray. Faint routing table in background.

TOP-RIGHT (10 ON-PREMISES CLASSIFICATION): Split visualization. Left half labeled "ON-PREMISES" in red text — showing an abstract building icon with server rack connected to red-dotted IP addresses. Right half labeled "CLOUD" in cyan — showing abstracted cloud infrastructure connected to cyan-dotted IPs. Center horizontal bar shows the split: "34% ON-PREM" (red section) / "66% CLOUD" (cyan section).

BOTTOM-LEFT (11 SERVICE RISK CLASSIFICATION): Side-by-side comparison panels. Left panel titled "NAIVE" with a red strikethrough: "Port 1433 → MSSQL (critical)" with red badge. Right panel titled "BANNER-AWARE" with cyan checkmark: "Port 1433 / Banner: OpenSSH 6.0p1 → SSH (medium)" with yellow badge. Below: row of dangerous service icons — RDP, SMB, FTP, Telnet — each with severity coloring.

BOTTOM-RIGHT (12 NVD CVSS SCORING): Horizontal bar chart showing CVE severity distribution — Critical bar (dark red, labeled "127"), High (orange, "312"), Medium (yellow, "891"), Low (green, "45"). To the right, a featured CVE card: "CVE-2023-38408" with "CVSS 9.8" displayed large in red, subtitle "OpenSSH / Unauthenticated RCE / Public Exploit".

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast.

---

## Panel 4: INTELLIGENCE SYNTHESIS (Layers 13-14 + Summary)

A dark command center quad-panel visualization (2x2 grid with thin cyan dividing lines). Dark navy background (#0a0e1a), cyan accent (#00e5ff), JetBrains Mono monospace font. Title bar across top: "PHASE 4: INTELLIGENCE SYNTHESIS" in small cyan letters with a thin horizontal rule below. Each quadrant has a small layer number badge (13, 14, greek-sigma, #) in the top-left corner.

TOP-LEFT (13 ENTITY EXTRACTION): A paragraph of text from an intelligence brief with named entities highlighted in different colors — technologies in cyan, facilities in green, processes in orange, materials in red. Thin lines connect each highlighted entity to a categorized sidebar listing: "TECHNOLOGY: SCADA, PLC", "FACILITY: Pantex Plant", "MATERIAL: enriched uranium". Counter: "6,134 entities / 2,211 briefs".

TOP-RIGHT (14 KNOWLEDGE GRAPH): A large-scale network graph visualization with dense clusters of nodes connected by relationship lines. Node colors by type: recipients (cyan), technologies (green), facilities (orange), materials (red). Visible clustering — national labs in one cluster, nuclear facilities in another. Query bar at bottom: "vector + keyword + graph + relationship → RRF → reranker". Stats: "24,706 nodes / 72,064 relationships".

BOTTOM-LEFT (PIPELINE OVERVIEW): A vertical flow diagram showing all 14 layers as numbered horizontal bars connected by downward arrows. Bars color-coded by phase — Discovery (cyan), Infrastructure (green), Classification (orange), Synthesis (red). Layer names abbreviated next to each bar. Clean schematic, technical blueprint style.

BOTTOM-RIGHT (SCALE): Large typography displaying key statistics stacked vertically: "2,214 CONTRACTORS", "51 STATES", "$127.6B OBLIGATIONS", "14 LAYERS", "24,706 NODES", "72,064 EDGES". Each number in bold cyan, labels in muted gray. Minimal, impact-driven.

Tactical HUD aesthetic throughout. Minimal. Technical precision. No people. 16:9 aspect ratio. High contrast.
