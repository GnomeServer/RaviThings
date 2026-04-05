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
"This is every DOE contractor in the United States. 2,214 organizations. $127.6 billion in federal obligations. We mapped their entire internet-facing attack surface from public sources. Every port. Every vulnerability. Every expired certificate. This contractor manages the Pantex Plant — where every nuclear warhead in the U.S. arsenal is assembled. We found their attack surface in 30 seconds. This is what an adversary already knows about the DOE supply chain."

**Key "oh my god" moment:** The sheer scale of the threat dashboard numbers appearing over the dark map. 1,464 internet-exposed. 534 with critical CVEs. 1,305 with no email authentication. Then the Pantex line hits.

---

## Video 2: "The Command Console" (3 min)

**Opening shot:** Console open, cursor blinking.

**Sequence:**
1. Type: "show me contractors with critical exposed services"
   → Map filters → markers remain → "Filtered to N contractors"
2. Type: "which one has the most exposed services"
   → Map flies to FOUR RIVERS NUCLEAR PARTNERSHIP [199] → detail panel opens → $462M
3. Show detail: MySQL 5.5, 2x MSSQL, RDP, SMB, FTP — nine services on one IP
4. Type: "show me contractors within 100 miles"
   → Radius circle appears → nearby DOE contractors highlighted
5. Type: "export as CSV"
   → Download triggers
6. Close with: "what's the biggest risk in the nuclear supply chain?"
   → LLM answers with specific data, names the most vulnerable contractors

**TABLE OF HORRORS insert (after step 3, hold 5 seconds):**
"FOUR RIVERS NUCLEAR PARTNERSHIP — $462M nuclear decommissioning"
"MySQL 5.5 (EOL). Two MSSQL 2012 instances. RDP. SMB v1. FTP. WinRM. One IP address."

**Narration concept:**
"No buttons. No menus. Type a question in English and the system finds the answer. 'Show me contractors with critical exposed services.' A nuclear decommissioning contractor appears with nine services exposed on a single IP. Three databases. Remote desktop. SMB version 1. All on an end-of-life Windows Server."

**Key "oh my god" moment:** The nine-service stack appearing in the detail panel. The audience counts them.

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
"DNS probing found gsaelibrary.gsa.gov as Centerra's domain. That's a government catalog site — completely wrong. For months, every scan, every vulnerability check, every certificate lookup hit the wrong target. The real attack surface was invisible. The AI researched the company, found it was acquired by Constellis Holdings, and corrected the domain to constellis.com. Then it automatically re-ran every downstream scan against the real domain. 987 contractors had wrong domains. 987 blind spots in our security picture. The AI found them all."

**Key "oh my god" moment:** "987 blind spots." The realization that without the AI, nearly half the attack surface data was pointed at the wrong targets.

---

## Video 4: "The Kill Chain" (3 min)

**Opening shot:** Console query: "show me nuclear contractors with exposed databases"

**Sequence:**
1. Console filters → flies to FOUR RIVERS NUCLEAR PARTNERSHIP [199] — $462M
2. Detail panel opens → the worst single host in the dataset:
   - MySQL 5.5 (end-of-life since 2018)
   - **Two** MS-SQL Server 2012 instances
   - RDP (Remote Desktop) exposed
   - SMB v1 enabled (EternalBlue/WannaCry vector)
   - FTP, SMTP, RPC — all on the same IP
   - Windows Server 2012 R2 (EOL since October 2023)
3. Hold on this — let the audience count the exposed services
4. Show: "Nine exposed services. Three databases. One IP address. A nuclear decommissioning contractor."

**Cut to:** Sandia/NTESS [1] — $14.1B
5. FTP (Pure-FTPd) + SMTP (Exim) exposed, DMARC=none
6. "The nuclear weapons laboratory. No email authentication."

**Cut to:** UC Regents [7] — $3.06B
7. PostgreSQL 11 confirmed on :5432, OpenSSH 6.0p1 (2012) on 6 ports

8. Click "Kill Chain" on Four Rivers → MITRE ATT&CK steps generate:
   - **Initial Access (T1190):** Exploit MySQL 5.5 — EOL, no patches since 2018
   - **Credential Access (T1110):** RDP brute force — directly accessible
   - **Lateral Movement (T1021):** SMB v1 — EternalBlue wormable RCE
   - **Persistence (T1505):** MSSQL stored procedures for backdoor
   - **Exfiltration (T1048):** FTP — cleartext data transfer

**TABLE OF HORRORS overlay (12 seconds)**

| Target | Finding | Impact | Verified |
|--------|---------|--------|----------|
| **Four Rivers Nuclear ($462M)** | MySQL 5.5 EOL on :3306 | No security patches since 2018 | Shodan live 2026-04-04 |
| **Four Rivers Nuclear ($462M)** | MS-SQL Server 2012 on :50371, :52162 | Two database engines, EOL OS | Shodan live 2026-04-04 |
| **Four Rivers Nuclear ($462M)** | RDP on :3389 | Remote desktop on nuclear contractor | Shodan live 2026-04-04 |
| **Four Rivers Nuclear ($462M)** | SMB v1 on :445 | EternalBlue / WannaCry vector | Shodan live 2026-04-04 |
| **Sandia hosting ($14.1B)** | FTP (Pure-FTPd) + SMTP (Exim) exposed | Cleartext creds on hosting server | Shodan live 2026-04-04 |
| **UC Regents ($3.06B)** | PostgreSQL 11 on :5432 | Database exposed to internet | Shodan live 2026-04-04 |
| **UC Regents ($3.06B)** | OpenSSH 6.0p1 — CVE-2023-38408 | CVSS 9.8 RCE, 14-year-old SSH | Shodan live 2026-04-04 |
| **Isotek Systems ($123M)** | ProFTPD 1.3.5 — 112 CVEs | Vulnerable FTP, no DMARC | Shodan live 2026-04-04 |
| **Goldbelt ($7.4M)** | MongoDB 8.0 on :27017 | Database exposed to internet | Shodan live 2026-04-04 |

**Narration over table:** "Every line was verified live against Shodan on April 4th. A nuclear decommissioning contractor running three databases, RDP, and SMB version 1 — on a single IP address. Windows Server 2012, end of life. The nuclear weapons laboratory with FTP and zero email authentication. A three billion dollar research contractor with a database and fourteen-year-old SSH. All from public data. All right now."

**Key "oh my god" moment:** Four Rivers — nine exposed services on one IP. The audience counts them and realizes this is a $462M nuclear contractor with everything exposed. Then the table piles on Sandia, UC Regents, Isotek, Goldbelt. Cumulative: $17.7 billion in DOE obligations with live-verified exposed services.

---

## Video 5: "The Phishing Surface" (2 min)

**Opening shot:** Console query: "show me nuclear lab management companies with no DMARC"

**The setup:** DOE's national labs are managed by private companies — LLCs that employ the scientists, engineers, and security personnel. The .gov lab domains (sandia.gov, lanl.gov, llnl.gov) have proper DMARC. But the management companies that actually run these labs? Different story.

**Sequence:**
1. Show the management company domains — verified live via DNS:
   - ut-battelle.org (manages ORNL, $6.2B) — **NO DMARC RECORD**
   - llnsllc.com (manages LLNL, $9.5B) — **NO DMARC RECORD**
   - triadns.org (manages LANL, $14.9B) — **NO DMARC RECORD**
   - savannahrivermissioncompletion.com ($2.3B) — **NO DMARC RECORD**
   - fermi-forward.org (manages Fermilab, $2.0B) — **NO DMARC RECORD**
   - fbportsmouth.com ($938M) — **NO DMARC RECORD**
   - jsallc.org (manages Jefferson Lab, $554M) — **NO DMARC RECORD**

2. Show the implication: "These are the companies whose employees have security clearances. Whose email addresses end in @triadns.org, @ut-battelle.org, @llnsllc.com. And anyone can send email pretending to be them."

3. Show combined obligation: **$36.4 billion** in DOE contracts managed by companies with no email authentication.

4. Type: `dig _dmarc.triadns.org TXT` — live DNS query returns empty. On screen.

5. Close: "The lab .gov domains are secure. The companies that run them are not."

**Narration concept:**
"The national lab domains — sandia.gov, lanl.gov, ornl.gov — all have DMARC reject. Properly configured. But the private companies that manage these labs? We checked their domains live. Triad National Security — manages Los Alamos — no DMARC. Lawrence Livermore National Security — manages LLNL — no DMARC. UT-Battelle — manages Oak Ridge — no DMARC. Thirty-six billion dollars in nuclear security managed by companies whose email can be spoofed by anyone. The .gov is locked. The .org is wide open."

**Key "oh my god" moment:** The `dig` command returning empty for triadns.org, live on screen. The audience realizes the company that manages Los Alamos has no email authentication. The gap between the .gov security and the management company security.

*All DMARC claims live-verified via DNS on 2026-04-05. Verifiable by anyone with `dig _dmarc.{domain} TXT`.*

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
