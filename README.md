# OSINT Atlas — DOE Contractor Attack Surface Intelligence Platform

An AI-powered open-source intelligence platform that maps the public-facing attack surface of 2,214 Department of Energy contractors across 51 states and territories, representing $127.6 billion in federal obligations.

**Classification: UNCLASSIFIED** — All data sourced from commercially and publicly available open sources. No classified methods, systems, or access employed.

## What It Does

OSINT Atlas runs a 14-layer automated OSINT pipeline against the entire DOE contractor population, then provides an AI-driven map interface for analyst queries.

**The pipeline collects:**
- Domain discovery and AI-powered domain validation (987 corrections)
- DNS intelligence (MX, SPF, DMARC, NS records)
- Certificate transparency logs (465,109 certificates, 19,874 subdomains)
- Web fingerprinting (server software, CMS, security headers)
- Shodan host enumeration (org-level and per-IP enrichment)
- ASN/network ownership classification
- On-premises vs cloud infrastructure separation
- Banner-aware service risk classification
- NVD/CVSS vulnerability scoring
- Named entity extraction into a knowledge graph (24,706 nodes, 72,064 relationships)

**The platform provides:**
- Natural language query interface (Hermes-4-405B reasoning model)
- MAP_CMD protocol for AI-driven map manipulation
- MITRE ATT&CK mapped kill chain generation per contractor
- Cross-contractor correlation (shared infrastructure, supply chain risk)
- Per-IP host intelligence with hosting attribution
- 4-lane hybrid retrieval (vector + keyword + graph + relationship search)

## Key Findings

- 1,460 contractors with internet-exposed infrastructure
- 483 with Shodan-confirmed hosts
- 237 with known CVEs on exposed services
- 227 with critical-severity dangerous services exposed
- 1,320 with no DMARC email authentication ($73.4B in obligations)
- 1,585 with on-premises IP addresses identified

## Architecture

```
Frontend: Vanilla JS + Leaflet.js (contractor-map.html)
Backend:  Python/FastAPI (test_atlas_server.py)
LLM:      Hermes-4-405B via OpenAI-compatible API
Search:   Brave Search API
Data:     Shodan, NVD, crt.sh, DNS
Graph:    igraph knowledge graph with hybrid retrieval
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys: OPENAI_API_KEY, SHODAN_API_KEY, BRAVE_API_KEY

# Start the server
python3 test_atlas_server.py

# Open in browser
open http://localhost:8000/atlas
```

## Pipeline Layers

| # | Layer | What It Finds |
|---|-------|--------------|
| 1 | Domain Discovery | Contractor internet presence from name + address |
| 2 | AI Research | Domain validation, company status, acquisition chains |
| 3 | Domain Verification | SSL cert, name match, parking page detection |
| 4 | DNS Intelligence | MX, SPF, DMARC, NS records |
| 5 | Certificate Transparency | Subdomains from crt.sh certificate logs |
| 6 | Web Fingerprinting | Server software, CMS, security headers |
| 7 | Shodan Org Search | Internet-facing hosts by organization |
| 8 | Shodan Per-IP | Service banners, SSL certs, CVEs per host |
| 9 | ASN Enumeration | Network ownership for each IP |
| 10 | On-Premises Classification | Contractor-owned vs cloud infrastructure |
| 11 | Service Risk | Banner-aware dangerous service classification |
| 12 | NVD CVSS Scoring | Vulnerability severity grading |
| 13 | Entity Extraction | Technologies, facilities, materials from briefs |
| 14 | Knowledge Graph | 24,706 nodes, 72,064 relationships, hybrid retrieval |

## Video Briefing

A narrated video briefing is available demonstrating the platform's capabilities. See `videos/` for production scripts and narration.

## Project Structure

```
frontend/static/
  contractor-map.html    # Main application (single-file, 6000+ lines)
  contractors.json       # Full contractor dataset with OSINT data

backend/
  hybrid_retriever.py    # 4-lane search with reranker
  kill_chain.py          # MITRE ATT&CK kill chain generator
  graph_enrichment.py    # LLM entity extraction
  reranker.py            # RRF + embedding reranker
  saturate.py            # Auto-explore and chat backend

osint/
  pipeline.py            # 14-layer OSINT pipeline orchestrator
  ai_research.py         # AI-powered domain research
  domain_verify.py       # Domain verification with confidence scoring
  service_risk.py        # Banner-aware service classification
  ct_logs.py             # Certificate transparency enrichment

test_atlas_server.py     # FastAPI server
```

## For Authorized Use Only

This platform is designed for **defensive security exercises** and authorized red team assessments. All data is from public OSINT sources and independently verifiable.
