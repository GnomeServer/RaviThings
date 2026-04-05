# OSINT Atlas — Video Demo Scripts

**Format:** 5 videos, each 2-3 minutes, scenario-driven.
**Goal:** Viewers come away thinking "Oh my god."
**Classification:** UNCLASSIFIED — all data from public OSINT sources.
**Accuracy standard:** Every claim verified against Shodan product banners. No port-number assumptions.

---

## Video 1: "The Scale" (2 min)

**Opening shot:** Black screen → map loads → 2,214 contractors appear.

**Sequence:**
1. Map at full zoom-out (US overview) — hold 3 seconds
2. Threat dashboard visible: 1,464 internet-exposed, 534 with critical CVEs, 1,305 with no DMARC
3. Slowly zoom toward Tennessee → Oak Ridge cluster comes into focus
4. Click CONSOLIDATED NUCLEAR SECURITY, LLC [3] — detail panel opens
5. Risk score appears: show the number, the factors
6. Scroll to AI Research Brief: "manages Y-12 National Security Complex and Pantex Plant"
7. Pull back to full map view

**Narration concept:**
"This is every DOE contractor in the United States. 2,214 organizations. $127.6 billion in federal obligations. We mapped their entire internet-facing attack surface from public sources. Every port. Every vulnerability. Every expired certificate. This is what an adversary already knows about the DOE supply chain."

**Key "oh my god" moment:** The sheer scale of the threat dashboard numbers appearing over the dark map. 1,464 internet-exposed. 534 with critical CVEs. 1,305 with no email authentication.

---

## Video 2: "The Command Console" (3 min)

**Opening shot:** Console open, cursor blinking.

**Sequence:**
1. Type: "show me nuclear contractors with no DMARC"
   → Map filters → markers remain for Sandia, Isotek, Four Rivers Nuclear → "Filtered to N contractors"
2. Type: "which one has the highest obligation"
   → Map flies to SANDIA / NTESS [1] → detail panel opens → $14.1 billion
3. Show detail: FTP exposed (Pure-FTPd), SMTP exposed (Exim), DMARC=none
4. Type: "show me contractors within 100 miles of Albuquerque"
   → Radius circle appears → nearby DOE contractors highlighted
5. Type: "export as CSV"
   → Download triggers
6. Close with: "what's the biggest risk to the nuclear weapons complex?"
   → LLM answers with specific data

**TABLE OF HORRORS insert (after step 3, hold 5 seconds):**
"SANDIA NATIONAL LABORATORIES — $14.1B nuclear weapons contractor"
"FTP exposed (cleartext credentials). SMTP exposed (direct mail relay). No DMARC (anyone can spoof their email)."

**Narration concept:**
"No buttons. No menus. Type a question in English and the system finds the answer. 'Show me nuclear contractors with no email authentication.' The fourteen billion dollar nuclear weapons laboratory appears. With FTP and SMTP exposed to the internet."

**Key "oh my god" moment:** The $14.1B number appearing next to "DMARC: none" and "FTP exposed."

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

**Opening shot:** Console query: "show me the highest obligation contractor with exposed services"

**Sequence:**
1. Console identifies NTESS / Sandia National Laboratories [1] — $14.1B
2. Detail panel opens → shows exposed FTP (Pure-FTPd), SMTP (Exim)
3. DMARC: none — no email spoofing protection on a nuclear weapons lab
4. Click "Kill Chain" → MITRE ATT&CK steps generate:
   - **Initial Access (T1566):** Phishing — no DMARC means spoofed emails from @sandia.gov are not rejected by recipients
   - **Credential Access (T1110):** FTP brute force — Pure-FTPd directly accessible, cleartext protocol
   - **Lateral Movement (T1021):** SSH pivot using harvested credentials
   - **Collection (T1114):** Email access via exposed SMTP relay
5. Click a step → detailed analysis with specific IPs and ports

**Cut to secondary example:** UC Regents [7] — $3.06B
6. PostgreSQL 11 confirmed exposed on port 5432 (banner verified)
7. OpenSSH 6.0p1 from 2012 running on 10+ ports — 191 CVEs
8. Show: "This SSH version is 13 years old. It has a CVSS 9.8 remote code execution."

**TABLE OF HORRORS overlay (10 seconds)**

| Target | Finding | Impact |
|--------|---------|--------|
| **Sandia ($14.1B)** | FTP (Pure-FTPd) exposed to internet | Cleartext credential capture |
| **Sandia ($14.1B)** | SMTP (Exim) exposed to internet | Direct mail relay access |
| **Sandia ($14.1B)** | DMARC policy: **none** | Any email from @sandia.gov can be spoofed |
| **UC Regents ($3.06B)** | PostgreSQL 11 on :5432 | Confirmed database exposed to internet |
| **UC Regents ($3.06B)** | OpenSSH 6.0p1 (2012) — CVE-2023-38408 | CVSS 9.8 RCE, public exploit |
| **Four Rivers Nuclear ($462M)** | MySQL 5.5 (EOL) on :3306 | End-of-life database, no security patches |
| **Isotek Systems ($123M)** | ProFTPD 1.3.5 — 112 CVEs | Known vulnerable FTP, no DMARC |

**Narration over table:** "These findings are verified. Product banners confirmed by Shodan. A fourteen billion dollar nuclear weapons contractor with FTP and no email authentication. A three billion dollar research contractor with a database and 13-year-old SSH exposed. A nuclear decommissioning contractor running end-of-life MySQL. All from public data. All right now."

**Key "oh my god" moment:** The table showing dollar amounts next to specific, verified vulnerabilities. The cumulative weight of $17.7 billion in DOE obligations with confirmed exposed services.

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

**Accuracy rule:** Every specific claim (CVE, service, product version) must be verified against Shodan product banners before recording. Port-number assumptions are not sufficient — the product must be confirmed.

**Sizzle reel:** 90-second cut of the best moments from all 5:
- Map loading (3s)
- Threat dashboard numbers (3s)
- Console: "nuclear contractors with no DMARC" → Sandia appears (5s)
- **Table of Horrors: Sandia $14.1B + FTP + no DMARC (4s)**
- Kill chain steps appearing (5s)
- Domain correction callout (3s)
- Radius circle + comparison table (5s)
- Heat map glow (3s)
- Close on: "UNCLASSIFIED. All public sources."

---

## Appendix: Verified Findings — Shodan Product Banners Confirmed

### NTESS / Sandia National Laboratories [1] — $14.1B obligation

| Service | Product Banner (Shodan-verified) | Port | IP | Risk |
|---------|--------------------------------|------|----|------|
| FTP | Pure-FTPd | 21 | 203.161.63.192 | Cleartext credential protocol |
| SSH | OpenSSH 8.7 | 22 | 203.161.63.192 | Current version — lower risk |
| HTTP | nginx 1.20.1 | 80, 443 | Multiple | Web server |
| SMTP | Exim smtpd 4.99.1 | 465, 587 | Multiple | Exposed mail relay |
| DMARC | **none** | — | — | Zero email spoofing protection |

### UC Regents / University of California [7] — $3.06B obligation, 191 CVEs

*Live Shodan verified 2026-04-04. Org confirmed: "The Regents of the University of California - University of California, San Diego."*

| Service | Product Banner (Shodan-verified) | Port | IP | Risk |
|---------|--------------------------------|------|----|------|
| PostgreSQL | PostgreSQL 11.19-11.22 | 5432 | 67.58.57.42 | **Confirmed database exposed** |
| SSH (ancient) | OpenSSH 6.0p1 Debian (2012) | 1433, 2222, 3306, 3389, 5432, 27017 | 67.58.63.9 | **14-year-old SSH on 6 non-standard ports** |
| SSH (modern) | OpenSSH 9.6p1 Ubuntu | 22 | 67.58.63.9 | Standard SSH |
| HTTP | Apache httpd | 80, 443 | 67.58.57.42 | CVE-2024-38475 (CVSS 9.1) |

*Note: Ports 1433/3306/3389 show OpenSSH 6.0p1, not MSSQL/MySQL/RDP. SSH on database ports is suspicious (tunneling?) but should not be called "exposed databases." Port 5432 on 67.58.57.42 IS confirmed PostgreSQL.*

### Four Rivers Nuclear Partnership [199] — $462M obligation (nuclear decommissioning)

*Live Shodan verified 2026-04-04. OS: Windows Server 2012 R2 (build 6.3.9600). Org: GoDaddy.com, LLC.*

| Service | Product Banner (Shodan-verified) | Port | IP | Risk |
|---------|--------------------------------|------|----|------|
| MySQL | MySQL 5.5.45-log | 3306 | 192.169.249.165 | **EOL database, no patches since 2018** |
| MS-SQL | MS-SQL Server 2012 RTM 11.0.2100.0 | 50371 | Same host | **Second database engine exposed** |
| MS-SQL | MS-SQL Server 2012 SP2 11.0.5058.0 | 52162 | Same host | **Third database instance** |
| RDP | Remote Desktop Protocol | 3389 | Same host | **Remote desktop on nuclear contractor** |
| SMB | SMB v1 enabled | 445 | Same host | **EternalBlue/WannaCry vector** |
| FTP | Microsoft ftpd | 21 | Same host | Cleartext credentials |
| SMTP | MailEnable smptd 10.12 | 25 | Same host | Exposed mail relay |
| RPC | Microsoft RPC Endpoint Mapper | 135 | Same host | Service enumeration |
| HTTP | Microsoft IIS 8.5 | 80, 443 | Same host | Older IIS version |
| DMARC | **not_set** | — | — | No email authentication |

*This is the worst single host in the dataset: a $462M nuclear decommissioning contractor running Windows Server 2012 R2 with MySQL, two MSSQL instances, RDP, SMB v1, FTP, and SMTP all exposed on the same IP. EOL operating system — no security patches since October 2023.*

### Isotek Systems LLC [50] — $123M obligation (nuclear waste processing)

| Service | Product Banner (Shodan-verified) | Port | IP | Risk |
|---------|--------------------------------|------|----|------|
| FTP | ProFTPD 1.3.5 | 21 | 185.141.141.144 | Known vulnerable FTP server |
| HTTP | Apache httpd 2.4.10 | 80, 443 | Same host | Older Apache |
| DMARC | **none** | — | — | Zero email authentication |
| CVEs | 112 total | — | — | Extensive vulnerability surface |

### Goldbelt Operations Support [239] — $7.4M obligation, 302 CVEs

| Service | Product Banner (Shodan-verified) | Port | IP | Risk |
|---------|--------------------------------|------|----|------|
| MongoDB | MongoDB 8.0.19 | 27017 | 74.63.202.75 | **Database exposed to internet** |
| FTP | Pure-FTPd | 21 | 208.115.214.173 | Cleartext credentials |
| MySQL | MySQL | 3306 | 208.115.214.173 | Database exposed |
| DMARC | **not_set** | — | — | No email authentication |

### Reference Links (all public, legitimate security databases)
- NVD: https://nvd.nist.gov/vuln/detail/{CVE-ID}
- MITRE: https://cve.mitre.org/cgi-bin/cvename.cgi?name={CVE-ID}
- ExploitDB: https://www.exploit-db.com/search?cve={CVE-ID}
- Shodan: data source for all host/service/vulnerability detection
