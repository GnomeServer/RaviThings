# AI Research Layer — Approved Design
Date: 2026-04-02

## Goal
Add a 13th OSINT pipeline layer that uses Hermes-4-405B + Brave Search to research each contractor like a human analyst — finding correct domains, determining company status, tracing acquisitions, and producing structured intelligence briefs.

## Architecture: 4 Components

| Component | File | Purpose |
|-----------|------|---------|
| Core research function | `osint/ai_research.py` (new) | Brave Search + Hermes synthesis → structured JSON |
| Pipeline layer | `osint/pipeline.py` (modify) | Batch processing with smart targeting + cascade |
| On-demand endpoint | `test_atlas_server.py` (modify) | SSE streaming for single-contractor research |
| Frontend section | `frontend/static/contractor-map.html` (modify) | Display brief, status, sources + "Research" button |

## Research Flow per Contractor

1. **SEARCH** (3-5 Brave queries): name+DOE, acquisition/merger, official website, domain verification
2. **SYNTHESIZE** (Hermes-4-405B): structured JSON from search results + contractor record
3. **VALIDATE**: DNS-probe suggested domain before committing
4. **STORE**: `contractor['osint']['ai_research'] = result`

## Output Schema

```json
{
  "queried": true,
  "query_time": "2026-04-02T14:30:00",
  "company_status": "acquired",
  "company_status_detail": "Acquired by Emerson Electric in 2020",
  "current_domain": "aspentech.com",
  "domain_confidence": 90,
  "domain_validated": true,
  "previous_domain": "osii.com",
  "parent_company": "Emerson Electric",
  "acquisition_year": 2020,
  "brief": "2-3 paragraph intelligence brief",
  "sources": [{"title": "...", "url": "..."}],
  "search_queries_used": 4,
  "raw_search_results": 12,
  "error": null
}
```

## Smart Targeting (batch mode)
Process contractors matching ANY of: no domain, dns_probe source, low confidence (<50%), never AI-researched.

## Domain Cascade
When AI research finds a different domain: update domain_discovery, invalidate downstream layers (verify, dns, ct, web).

## Frontend
New "AI Research Brief" section with company status badge, brief text, clickable sources, domain correction callout, and "Research" button for on-demand generation.
