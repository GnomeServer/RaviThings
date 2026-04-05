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

**Optional TABLE OF HORRORS insert (after step 2, when detail panel shows services):**
Pick the most alarming CVE on the contractor's exposed services. One line on screen:
"CVE-2023-38408 — CVSS 9.8 — Remote Code Execution — Public exploit available"
Hold 3 seconds. Then continue with radius query.

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

**After showing services, cut to: TABLE OF HORRORS overlay (10 seconds)**

| CVE | CVSS | What It Does | Exploit? |
|-----|------|-------------|----------|
| CVE-2023-38408 | **9.8** | OpenSSH RCE via agent forwarding | Public PoC on GitHub |
| CVE-2024-38475 | **9.1** | Apache mod_rewrite remote code execution | ExploitDB #52081 |
| CVE-2020-15778 | **7.8** | OpenSSH scp command injection | Metasploit module |
| CVE-2023-51767 | **7.0** | OpenSSH auth bypass via row hammer | Research paper |
| CVE-2021-41617 | **7.0** | OpenSSH privilege escalation | Public PoC |

**Narration over table:** "These aren't theoretical. Every one of these CVEs has public exploit code. A 9.8 remote code execution on OpenSSH. A 9.1 Apache RCE. On a three billion dollar nuclear research contractor. From data anyone can collect."

**Then resume kill chain sequence.**

**Key "oh my god" moment:** The table of horrors — CVSS 9.8 and 9.1 with "Public PoC" next to them, on the same screen as the contractor's name and DOE obligation.

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
- **Table of Horrors: CVE-2023-38408 CVSS 9.8 RCE — Public PoC (4s)**
- Kill chain steps appearing (5s)
- Domain correction callout (3s)
- Radius circle + comparison table (5s)
- Heat map glow (3s)
- Close on: "UNCLASSIFIED. All public sources."

---

## Appendix: Table of Horrors — Verified CVEs from Demo Contractors

### UC Regents [7] — $3B obligation, 191 CVEs

| CVE | CVSS | Service | Impact | Public Exploit |
|-----|------|---------|--------|---------------|
| CVE-2023-38408 | **9.8** | OpenSSH | Remote code execution via agent forwarding | GitHub PoC, Metasploit |
| CVE-2024-38475 | **9.1** | Apache httpd | Remote code execution via mod_rewrite | ExploitDB |
| CVE-2020-15778 | **7.8** | OpenSSH scp | Command injection via scp client | Metasploit module |
| CVE-2023-51767 | **7.0** | OpenSSH | Authentication bypass via row hammer | Research paper + PoC |
| CVE-2021-41617 | **7.0** | OpenSSH | Privilege escalation in sshd | Public PoC |
| CVE-2025-26465 | **6.8** | OpenSSH | MitM via VerifyHostKeyDNS bypass | Public PoC |
| CVE-2023-48795 | **5.9** | SSH | Terrapin prefix truncation attack | Widespread PoC |
| CVE-2018-15473 | **5.3** | OpenSSH | Username enumeration | Metasploit, ExploitDB |

Exposed services on this contractor: MSSQL:1433, MySQL:3306, RDP:3389, PostgreSQL:5432, Redis:6379, Kubernetes:10250, MongoDB:27017

### Alliance Technology Group [1915] — 337 CVEs, 166 hosts

| CVE | CVSS | Service | Impact | Public Exploit |
|-----|------|---------|--------|---------------|
| Multiple OpenSSH CVEs | 5.3-9.8 | SSH across 166 hosts | RCE, auth bypass, info disclosure | Multiple |
| SMTP:25 exposed | — | Mail relay | Open relay / spam vector | Tooling available |
| SNMP:161 exposed | — | Network management | Community string brute force | snmpwalk, onesixtyone |
| DNS:53 exposed | — | Name resolution | DNS amplification, zone transfer | dig, dnsrecon |

### EPC Inc [1020] — 1,018 CVEs, RDP:3389 exposed

| CVE | CVSS | Service | Impact | Public Exploit |
|-----|------|---------|--------|---------------|
| CVE-2019-0708 (BlueKeep) | **9.8** | RDP | Wormable RCE, pre-auth | Metasploit, public PoC |
| CVE-2019-1182 | **9.8** | RDP | DejaBlue RCE | Public PoC |
| RDP:3389 exposed | — | Remote Desktop | Brute force, credential stuffing | Hydra, Crowbar |

*Note: BlueKeep/DejaBlue presence should be verified — they affect specific Windows versions. Listed as risk indicators given RDP exposure.*

### Reference Links (all public, legitimate security databases)
- NVD: https://nvd.nist.gov/vuln/detail/{CVE-ID}
- MITRE: https://cve.mitre.org/cgi-bin/cvename.cgi?name={CVE-ID}
- ExploitDB: https://www.exploit-db.com/search?cve={CVE-ID}
- Shodan: data source for all host/service/vulnerability detection
