# OSINT Atlas — Video Demo Scripts

**Format:** 5 videos, each 2-3 minutes, scenario-driven.
**Goal:** Viewers come away thinking "Oh my god."
**Classification:** UNCLASSIFIED — all data from public OSINT sources.

---

## Video 1: "The Scale" (2 min)

**Opening shot:** Black screen → map loads → 2,214 contractors appear.

**Sequence:**
1. Map at full zoom-out (US overview) — hold 3 seconds
2. Threat dashboard visible: 1,464 internet-exposed, 534 with critical CVEs, 976 with no DMARC
3. Slowly zoom toward Tennessee → Oak Ridge cluster comes into focus
4. Click CONSOLIDATED NUCLEAR SECURITY, LLC [3] — detail panel opens
5. Risk score appears: show the number, the factors
6. Scroll to AI Research Brief: "manages Y-12 National Security Complex and Pantex Plant"
7. Pull back to full map view

**Narration concept:**
"This is every DOE contractor in the United States. 2,214 organizations. $127.6 billion in federal obligations. We mapped their entire internet-facing attack surface from public sources. Every port. Every vulnerability. Every expired certificate. This is what an adversary already knows about the DOE supply chain."

**Key "oh my god" moment:** The sheer scale of the threat dashboard numbers appearing over the dark map. 1,464 internet-exposed. 534 with critical CVEs.

---

## Video 2: "The Command Console" (3 min)

**Opening shot:** Console open, cursor blinking.

**Sequence:**
1. Type: "show me contractors with critical exposed services"
   → Map filters → red/orange markers remain → "Filtered to N contractors"
2. Type: "which one has the most vulnerabilities"
   → Map flies to contractor → detail panel opens → risk score, vuln count
3. Type: "show me contractors within 50 miles"
   → Radius circle appears → nearby contractors highlighted
4. Type: "compare those two" [pick 2 from radius]
   → Comparison table renders inline in chat
5. Type: "export as CSV"
   → Download triggers
6. Close with a natural language question: "what's the biggest risk in Tennessee?"
   → LLM answers with specific data, flies to location

**Narration concept:**
"No buttons. No menus. Just tell the system what you want. It searches, filters, compares, and exports — from natural language. The AI doesn't just answer questions. It drives the entire map."

**Key "oh my god" moment:** The radius circle appearing and filtering contractors spatially, followed immediately by a comparison table — all from typing English sentences.

---

## Video 3: "The Intelligence Brief" (2 min)

**Opening shot:** Click on CENTERRA GROUP, LLC [45] — $419M obligation.

**Sequence:**
1. Detail panel opens → AI Research Brief section
2. Status badge: ACQUIRED (amber)
3. Domain correction callout: ~~gsaelibrary.gsa.gov~~ → constellis.com (validated)
4. Brief text: describes acquisition by Constellis Holdings
5. Clickable sources below
6. Scroll to a second contractor: WEST PUBLISHING CORPORATION [400]
7. Status: ACQUIRED → parent: Thomson Reuters → domain: west.com → thomsonreuters.com
8. Click "Research" on a third contractor → watch SSE stream in real time:
   "Searching: company + DOE..." → "Found 12 results" → "Synthesizing..." → brief appears

**Narration concept:**
"DNS probing found gsaelibrary.gsa.gov as Centerra's domain. That's a government catalog site — completely wrong. The AI researched the company, found it was acquired by Constellis Holdings, and corrected the domain to constellis.com. Then it re-ran all downstream scans against the real domain. 987 domains were corrected this way — automatically."

**Key "oh my god" moment:** The domain correction callout — old domain struck through, new domain in green. The realization that the platform self-corrected its own data using AI reasoning.

---

## Video 4: "The Kill Chain" (3 min)

**Opening shot:** Console query: "show me the highest risk Research & Labs contractor"

**Sequence:**
1. Console filters → flies to THE REGENTS OF THE UNIVERSITY OF CALIFORNIA [7]
2. Detail panel opens → CRITICAL RISK score (76+)
3. Exposed services visible: MSSQL:1433, MySQL:3306, RDP:3389, PostgreSQL:5432, Redis:6379
4. Five dangerous services exposed to the internet on a $3 billion DOE contractor
5. Click "Kill Chain" → MITRE ATT&CK steps generate
6. Walk through steps:
   - Initial Access: exposed MSSQL (T1190)
   - Credential Access: database with cleartext creds
   - Lateral Movement: via shared database infrastructure
   - Exfiltration: data staging through exposed services
7. Click a step → detailed analysis with specific IPs and ports
8. Close on: "This is a $3 billion contractor with three exposed database engines."

**Narration concept:**
"This contractor manages nuclear research for DOE. Three billion dollars in federal obligations. And right now, five of their services — MSSQL, MySQL, RDP, PostgreSQL, and Redis — are directly accessible from the public internet. 191 known vulnerabilities. Here's what an attack path looks like."

**Key "oh my god" moment:** The console says "This appears to be the most exposed and vulnerable research lab contractor in the entire DOE dataset" — followed by the MITRE ATT&CK kill chain with real IPs and ports. Not theoretical — actual infrastructure.

---

## Video 5: "The Supply Chain" (2 min)

**Opening shot:** Heat map toggle → geographic risk concentration glows.

**Sequence:**
1. Heat map shows risk concentration in DC/Maryland/Virginia corridor
2. Type: "show me contractors in Maryland with high risk"
   → Filters → several contractors appear
3. Click on ALLIANCE TECHNOLOGY GROUP, LLC [1915] — risk score 91
4. 166 exposed hosts, 337 vulnerabilities, DMARC=not_set
5. Scroll to correlation section — show any shared IP infrastructure
6. Type: "compare the top 3 riskiest contractors in Maryland"
   → Comparison table: side by side risk scores, vulns, services
7. Toggle back to heat map — show how risk clusters geographically
8. Close with: "Supply chain risk isn't abstract. It has IP addresses."

**Narration concept:**
"Risk concentrates geographically. The DC-Maryland-Virginia corridor has the highest density of DOE contractors — and the highest density of exposed infrastructure. These contractors share IP ranges, mail providers, and DNS infrastructure. Compromise one, you're inside the network neighborhood of dozens."

**Key "oh my god" moment:** The heat map showing risk concentration, then the realization that these contractors are physically and digitally co-located.

---

## Production Notes

**Pacing:** Let the map animate. Don't narrate over typing — let the viewer read the queries. Add narration over results.

**Music:** Low ambient, dark. Match the tactical HUD aesthetic.

**Resolution:** 1440p or 4K. The dark theme with cyan accents is sharp at high res.

**Viewing order:** 1 → 2 → 4 → 3 → 5

**Sizzle reel:** 90-second cut of the best moments from all 5:
- Map loading (3s)
- Threat dashboard numbers (3s)
- Console query → map animates (5s)
- Kill chain steps appearing (5s)
- Domain correction callout (3s)
- Radius circle + comparison table (5s)
- Heat map glow (3s)
- Close on: "UNCLASSIFIED. All public sources."
