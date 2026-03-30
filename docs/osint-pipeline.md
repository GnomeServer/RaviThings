# OSINT Intelligence Pipeline

Multi-layer open-source intelligence enrichment for DOE contractor attack surface mapping.

## Architecture

```
contractors.json (2,214 contractors with geocoded addresses)
       |
       v
  OSINT Pipeline (osint/pipeline.py)
       |
       +-- Layer 1: Enhanced Shodan ........ Internet-facing hosts, ports, services
       +-- Layer 2: Domain Discovery ....... Corporate website identification
       +-- Layer 3: Domain Verification .... Confidence scoring on discovered domains
       +-- Layer 4: DNS Intelligence ....... MX, SPF, DMARC, NS, CNAME analysis
       +-- Layer 5: CT Log Enumeration ..... Certificate Transparency subdomain discovery
       +-- Layer 6: Web Fingerprinting ..... HTTP headers, CMS, security headers
       +-- Layer 7: ASN Enumeration ........ Autonomous System Number mapping
       +-- Layer 8: Service Risk ........... Dangerous service classification (NEW)
       +-- Layer 9: NVD CVSS Scoring ....... Real vulnerability severity scores (NEW)
       |
       v
  contractors.json (enriched with osint.* fields)
       |
       v
  contractor-map.html (interactive intelligence map)
```

## Quick Start

```bash
# Run all layers (takes hours due to API rate limits)
python -m osint.pipeline --layers all

# Run specific layers
python -m osint.pipeline --layers service_risk       # Instant, no API needed
python -m osint.pipeline --layers nvd                # ~6 min with API key, ~57 min without
python -m osint.pipeline --layers shodan,dns,ct      # Multiple layers

# Limit to first N contractors (for testing)
python -m osint.pipeline --layers nvd --limit 10

# Force re-process already-enriched contractors
python -m osint.pipeline --layers service_risk --force
```

## Available Layers

| Layer | Module | External API | Rate Limit | Data Produced |
|-------|--------|-------------|------------|---------------|
| `shodan` | `osint/enhanced_shodan.py` | Shodan API | Requires `SHODAN_API_KEY` | Hosts, ports, services, CVEs, ASNs, SSL certs |
| `domain` | `osint/domain_discovery.py` | None (DNS probing) | N/A | Corporate domains from contract data |
| `verify` | `osint/domain_verify.py` | None (DNS/HTTP) | N/A | Domain confidence scores |
| `dns` | `osint/dns_intel.py` | None (DNS queries) | N/A | MX, SPF, DMARC, NS, CNAME records |
| `ct` | `osint/ct_logs.py` | crt.sh | ~1 req/3 sec | Subdomains, infrastructure hints, issuers |
| `web` | `osint/web_fingerprint.py` | None (HTTP) | N/A | Headers, CMS, security score |
| `asn` | `osint/asn_enum.py` | Shodan InternetDB | Free/rate-limited | ASN/IP mapping, per-host vulns |
| `service_risk` | `osint/service_risk.py` | **None** | **Instant** | Dangerous service classification |
| `nvd` | `osint/nvd_cvss.py` | NVD API v2.0 | 5 req/30s (free), 50 req/30s (keyed) | CVSS v3.1 scores, severity, vectors |

## Environment Variables

```bash
# Required for Shodan layers
SHODAN_API_KEY=your_shodan_api_key

# Optional — speeds up NVD from ~57 min to ~6 min for 522 CVEs
# Get a free key at: https://nvd.nist.gov/developers/request-an-api-key
NVD_API_KEY=your_nvd_api_key
```

## Layer Details

### Service Risk Classification (`osint/service_risk.py`)

Classifies exposed services by danger level without any external API calls.
Uses port/service data from Shodan enrichment.

**Danger levels:**
- **CRITICAL** — services that should NEVER be internet-facing:
  RDP (3389), SMB (445), MSSQL (1433), MySQL (3306), PostgreSQL (5432),
  MongoDB (27017), Redis (6379), Elasticsearch (9200), VNC (5900),
  Docker API (2375), Cassandra (9042)
- **HIGH** — frequently targeted with known exploits:
  FTP (21), Telnet (23), SMTP (25), POP3 (110), IMAP (143),
  SNMP (161), LDAP (389), MQTT (1883)
- **MEDIUM** — information leakage or weak defaults:
  HTTP-Proxy (8080), DNS (53), TFTP (69), Modbus (502), BACnet (47808)

**Output schema:**
```json
{
  "queried": true,
  "query_time": "2026-03-28T...",
  "total_services": 12,
  "dangerous_services": [
    {"port": 3389, "name": "RDP", "danger": "critical", "reason": "...", "host_count": 3}
  ],
  "danger_summary": {"critical": 1, "high": 2, "medium": 0},
  "max_danger": "critical",
  "error": null
}
```

### NVD CVSS Scoring (`osint/nvd_cvss.py`)

Looks up real CVSS v3.1 scores for CVE identifiers found by Shodan/ASN enumeration.
Replaces the frontend's year-based heuristic with actual severity data from NIST.

**Features:**
- Prefers CVSS v3.1, falls back to v3.0, then v2.0
- Global caching across contractors (522 unique CVEs shared across 2,214 contractors)
- Rate-limit aware with retry/backoff
- Extracts base score, severity, vector string, and description

**Output schema:**
```json
{
  "queried": true,
  "query_time": "2026-03-28T...",
  "total_cves": 15,
  "scored_cves": 14,
  "scores": {
    "CVE-2021-44228": {
      "cve_id": "CVE-2021-44228",
      "version": "3.1",
      "base_score": 10.0,
      "severity": "critical",
      "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
      "description": "Apache Log4j2 2.0-beta9 through 2.15.0...",
      "exploitability_score": 3.9,
      "impact_score": 6.0
    }
  },
  "summary": {"critical": 2, "high": 5, "medium": 4, "low": 3, "none": 0, "unknown": 1},
  "max_severity": "critical",
  "max_score": 10.0,
  "error": null
}
```

## Frontend Intelligence Map

The contractor intelligence map (`frontend/static/contractor-map.html`) visualizes all enrichment data.

### Threat Dashboard
Fixed banner below the nav bar showing aggregate attack surface stats:
- Exposed hosts, contractors with CVEs, missing DMARC, risky ports, weak SSL, missing security headers
- Pulsing red threat indicator
- Average risk score across all contractors

### Risk Scoring Engine
Client-side 0-100 score computed from 7 weighted factors:

| Factor | Weight | Source |
|--------|--------|--------|
| Internet exposure (host count) | 20 pts | Shodan |
| Vulnerabilities (CVSS-weighted if available) | 30 pts | NVD CVSS / Shodan |
| Dangerous services | 15 pts | Service Risk |
| DMARC policy | 10 pts | DNS Intel |
| Web security headers | 10 pts | Web Fingerprint |
| CT subdomain exposure | 10 pts | CT Logs |
| SSL certificate issues | 5 pts | Shodan |

**Severity levels:** Critical (70-100), High (40-69), Medium (15-39), Low (0-14)

### Heat Map
Toggle-able Leaflet.heat overlay showing geographic concentration of risk.
Risk-weighted data points create a red-gradient heat map.

### Per-Contractor Detail Panel
Click any marker to see:
- Risk gauge with severity and contributing factors
- Dangerous services with danger level and attack explanation
- Network topology diagram
- OSINT intelligence (DNS, CT, web fingerprinting)
- Shodan data with CVE badges showing real CVSS scores

## Data Flow

```
1. preprocess_contractors.py     — geocode addresses, categorize NAICS
2. enrich_shodan.py              — basic Shodan org/hostname queries
3. osint/pipeline.py             — 9-layer deep enrichment
4. contractor-map.html           — client-side risk scoring + visualization
```

## Current Coverage (2,214 contractors)

| Layer | Coverage |
|-------|----------|
| Domain discovery | 2,172 (98%) |
| DNS intelligence | 1,953 (88%) |
| CT log enumeration | 1,403 (63%) |
| Web fingerprinting | 1,438 (64%) |
| Shodan (basic) | 483 (22%) |
| Service risk classification | 2,214 (100%) |
| NVD CVSS scoring | In progress |

## Adding a New Layer

Follow the pattern in `osint/ct_logs.py`:

1. Create `osint/your_layer.py` with a public `enrich_*` function
2. Return dict with `queried`, `query_time`, `error` fields + custom data
3. Add import and `run_layer_*` function to `osint/pipeline.py`
4. Register in the main execution flow
5. Add frontend rendering in `contractor-map.html` if needed
