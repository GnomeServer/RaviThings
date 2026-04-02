# AI Research Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 13th OSINT pipeline layer that uses Hermes-4-405B + Brave Search to research contractors, find correct domains, determine company status, trace acquisitions, and produce intelligence briefs.

**Architecture:** Core research function in `osint/ai_research.py`, pipeline layer in `osint/pipeline.py`, on-demand SSE endpoint in `test_atlas_server.py`, frontend section in `contractor-map.html`.

**Tech Stack:** Python 3.12, FastAPI, httpx, Hermes-4-405B (Nous Research API), Brave Search API, pytest + unittest.mock

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `osint/ai_research.py` | Core research function: search + synthesize + validate |
| Create | `tests/test_ai_research.py` | Unit tests for research function |
| Modify | `osint/pipeline.py` | Add `run_layer_ai_research()`, CLI flag |
| Modify | `test_atlas_server.py` | Add `/api/ai-research` SSE endpoint |
| Modify | `frontend/static/contractor-map.html` | AI Research Brief section + Research button |

---

### Task 1: Core Research Module — `osint/ai_research.py`

**Files:**
- Create: `osint/ai_research.py`
- Create: `tests/test_ai_research.py`

**Provides:**
- `async research_contractor(contractor: dict, hermes: HermesClient, brave: BraveSearchClient) -> dict`
- `build_research_prompt(contractor: dict, search_context: str) -> list[dict]`
- `extract_research_json(raw: str) -> dict`
- `RESEARCH_SCHEMA` — expected JSON output keys

**Ground Truth:**
- `HermesClient.chat(messages: list[dict], max_tokens: int = 4096) -> str` — async, in `backend/mercury_client.py`
- `BraveSearchClient.search(query: str, count: int = 5) -> list[dict]` — async, returns `{title, url, description}`, in `backend/brave_search.py`
- `probe_domain(domain: str, timeout: float = 3.0) -> bool` — sync, in `osint/domain_discovery.py`
- `extract_domain_from_url(url: str) -> Optional[str]` — sync, in `osint/domain_discovery.py`

- [ ] **Step 1: Write failing tests for `extract_research_json`**

```python
# tests/test_ai_research.py
import os
import sys
import json
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExtractResearchJson(unittest.TestCase):
    """Test JSON extraction from LLM output."""

    def test_clean_json(self):
        from osint.ai_research import extract_research_json
        raw = '{"company_status": "active", "current_domain": "example.com", "brief": "A company."}'
        result = extract_research_json(raw)
        self.assertEqual(result['company_status'], 'active')
        self.assertEqual(result['current_domain'], 'example.com')

    def test_json_with_think_tags(self):
        from osint.ai_research import extract_research_json
        raw = '<think>reasoning here</think>\n{"company_status": "acquired", "current_domain": "parent.com"}'
        result = extract_research_json(raw)
        self.assertEqual(result['company_status'], 'acquired')

    def test_json_with_markdown_fence(self):
        from osint.ai_research import extract_research_json
        raw = 'Here is the result:\n```json\n{"company_status": "active", "current_domain": "ex.com"}\n```'
        result = extract_research_json(raw)
        self.assertEqual(result['company_status'], 'active')

    def test_malformed_returns_empty(self):
        from osint.ai_research import extract_research_json
        result = extract_research_json('not json at all')
        self.assertIsNone(result)

    def test_json_with_surrounding_text(self):
        from osint.ai_research import extract_research_json
        raw = 'Based on my research:\n{"company_status": "dissolved", "current_domain": null, "brief": "Gone."}\nEnd.'
        result = extract_research_json(raw)
        self.assertEqual(result['company_status'], 'dissolved')
        self.assertIsNone(result['current_domain'])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python -m pytest tests/test_ai_research.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'osint.ai_research'`

- [ ] **Step 3: Implement `extract_research_json`**

```python
# osint/ai_research.py
"""
AI-powered contractor research using web search + LLM reasoning.

Researches each contractor to find correct domains, determine company status
(active/acquired/dissolved), trace acquisition chains, and produce
structured intelligence briefs with sources.
"""

import json
import re
import time
from typing import Optional


def extract_research_json(raw: str) -> Optional[dict]:
    """Extract structured JSON from LLM output.

    Handles: clean JSON, <think> tags, markdown fences, surrounding text.
    Returns None if no valid JSON found.
    """
    if not raw:
        return None

    # Strip <think>...</think> tags
    cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

    # Strip markdown code fences
    cleaned = re.sub(r'```(?:json)?\s*', '', cleaned).strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # Extract between first { and last }
    first = cleaned.find('{')
    last = cleaned.rfind('}')
    if first != -1 and last > first:
        try:
            return json.loads(cleaned[first:last + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python -m pytest tests/test_ai_research.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Write failing tests for `build_research_prompt`**

```python
class TestBuildResearchPrompt(unittest.TestCase):
    """Test prompt construction for LLM research."""

    def test_basic_prompt(self):
        from osint.ai_research import build_research_prompt
        contractor = {
            'name': 'Acme Corp',
            'dba': '',
            'city': 'Denver',
            'state': 'CO',
            'category': 'IT & Cyber',
            'contract_ids': ['DE-AC01-1234'],
            'obligation': 5000000,
        }
        search_context = "Source: Acme Corp - IT Services\nURL: https://acme.com\nAcme provides IT."
        messages = build_research_prompt(contractor, search_context)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['role'], 'system')
        self.assertEqual(messages[1]['role'], 'user')
        self.assertIn('Acme Corp', messages[1]['content'])
        self.assertIn('Denver', messages[1]['content'])
        self.assertIn('company_status', messages[0]['content'])

    def test_prompt_includes_existing_domain(self):
        from osint.ai_research import build_research_prompt
        contractor = {
            'name': 'Test Inc',
            'dba': '',
            'city': 'DC',
            'state': 'DC',
            'category': 'Other',
            'contract_ids': [],
            'obligation': 0,
            'osint': {'domain_discovery': {'domain': 'testinc.com', 'source': 'dns_probe'}},
        }
        messages = build_research_prompt(contractor, "")
        self.assertIn('testinc.com', messages[1]['content'])
        self.assertIn('dns_probe', messages[1]['content'])

    def test_prompt_requests_json_output(self):
        from osint.ai_research import build_research_prompt
        contractor = {'name': 'X', 'dba': '', 'city': '', 'state': '', 'category': '', 'contract_ids': [], 'obligation': 0}
        messages = build_research_prompt(contractor, "")
        system = messages[0]['content']
        self.assertIn('JSON', system)
        self.assertIn('company_status', system)
        self.assertIn('current_domain', system)
        self.assertIn('brief', system)
```

- [ ] **Step 6: Implement `build_research_prompt`**

```python
def build_research_prompt(contractor: dict, search_context: str) -> list[dict]:
    """Build LLM messages for contractor research.

    Args:
        contractor: Contractor dict with name, dba, city, state, etc.
        search_context: Formatted web search results.

    Returns:
        List of message dicts for HermesClient.chat().
    """
    name = contractor.get('name', '')
    dba = contractor.get('dba', '')
    city = contractor.get('city', '')
    state = contractor.get('state', '')
    category = contractor.get('category', '')
    contract_ids = contractor.get('contract_ids', [])
    obligation = contractor.get('obligation', 0)
    naics = contractor.get('naics_desc', '') or contractor.get('naics', '')
    role = contractor.get('role', '')

    # Existing domain info
    dd = contractor.get('osint', {}).get('domain_discovery', {})
    existing_domain = dd.get('domain', '')
    domain_source = dd.get('source', '')

    system_prompt = """You are a DOE contractor intelligence analyst. Research the company below using the provided web search results.

OUTPUT FORMAT: Respond with ONLY a JSON object (no markdown, no explanation):
{
  "company_status": "active|acquired|merged|dissolved|unknown",
  "company_status_detail": "one sentence explaining current status",
  "current_domain": "the company's current primary website domain (e.g., example.com) or null if defunct",
  "domain_confidence": 0-100,
  "parent_company": "parent/acquirer name or null",
  "acquisition_year": year as integer or null,
  "brief": "2-3 paragraph intelligence brief about this company and their DOE work. Cite specific sources.",
  "sources": [{"title": "source title", "url": "source URL"}]
}

RULES:
- ONLY use information from the web search results provided. Do not use training knowledge for factual claims.
- If a company was acquired, find the acquiring company's current domain.
- If search results are insufficient, set company_status to "unknown" and domain_confidence low.
- The brief should cover: what the company does, their DOE relationship, and current operational status.
- Include ALL relevant sources from the search results."""

    contractor_info = f"""CONTRACTOR RECORD:
Name: {name}
DBA: {dba}
Location: {city}, {state}
Category: {category}
NAICS: {naics}
Role: {role}
Contract IDs: {', '.join(contract_ids) if contract_ids else 'none'}
Federal Obligation: ${obligation:,.0f}
Current Domain (may be incorrect): {existing_domain} (source: {domain_source})"""

    user_content = contractor_info
    if search_context:
        user_content += f"\n\nWEB SEARCH RESULTS:\n{search_context}"
    else:
        user_content += "\n\nNo web search results available. Set company_status to 'unknown' and domain_confidence to 0."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
```

- [ ] **Step 7: Run tests to verify prompt tests pass**

Run: `cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python -m pytest tests/test_ai_research.py -v`
Expected: All 8 PASS

- [ ] **Step 8: Write failing tests for `research_contractor`**

```python
class TestResearchContractor(unittest.TestCase):
    """Test the full research pipeline."""

    def _make_contractor(self, name='Acme Corp', domain=None, source='dns_probe'):
        c = {
            'name': name, 'dba': '', 'city': 'Denver', 'state': 'CO',
            'category': 'IT & Cyber', 'contract_ids': ['DE-AC01-1234'],
            'obligation': 5000000, 'osint': {},
        }
        if domain:
            c['osint']['domain_discovery'] = {'domain': domain, 'source': source}
        return c

    def test_successful_research(self):
        import asyncio
        from osint.ai_research import research_contractor

        mock_hermes = AsyncMock()
        mock_hermes.is_available.return_value = True
        mock_hermes.chat.return_value = json.dumps({
            'company_status': 'active',
            'company_status_detail': 'Acme Corp is an active IT services company.',
            'current_domain': 'acmecorp.com',
            'domain_confidence': 85,
            'parent_company': None,
            'acquisition_year': None,
            'brief': 'Acme Corp provides IT services to DOE.',
            'sources': [{'title': 'Acme Corp', 'url': 'https://acmecorp.com'}],
        })

        mock_brave = AsyncMock()
        mock_brave.is_available.return_value = True
        mock_brave.search.return_value = [
            {'title': 'Acme Corp - IT Services', 'url': 'https://acmecorp.com', 'description': 'IT services'},
        ]

        with patch('osint.ai_research.probe_domain', return_value=True):
            result = asyncio.run(research_contractor(self._make_contractor(), mock_hermes, mock_brave))

        self.assertTrue(result['queried'])
        self.assertEqual(result['company_status'], 'active')
        self.assertEqual(result['current_domain'], 'acmecorp.com')
        self.assertTrue(result['domain_validated'])
        self.assertIsNone(result['error'])

    def test_domain_validation_failure(self):
        import asyncio
        from osint.ai_research import research_contractor

        mock_hermes = AsyncMock()
        mock_hermes.is_available.return_value = True
        mock_hermes.chat.return_value = json.dumps({
            'company_status': 'active',
            'current_domain': 'fakecorp.com',
            'domain_confidence': 50,
            'brief': 'Test.',
            'sources': [],
        })

        mock_brave = AsyncMock()
        mock_brave.is_available.return_value = True
        mock_brave.search.return_value = []

        with patch('osint.ai_research.probe_domain', return_value=False):
            result = asyncio.run(research_contractor(self._make_contractor(), mock_hermes, mock_brave))

        self.assertFalse(result['domain_validated'])
        # Domain should still be stored but marked as unvalidated

    def test_hermes_unavailable_fallback(self):
        import asyncio
        from osint.ai_research import research_contractor

        mock_hermes = AsyncMock()
        mock_hermes.is_available.return_value = False

        mock_brave = AsyncMock()
        mock_brave.is_available.return_value = True
        mock_brave.search.return_value = []

        result = asyncio.run(research_contractor(self._make_contractor(), mock_hermes, mock_brave))
        self.assertEqual(result['error'], 'hermes_unavailable')

    def test_brave_unavailable(self):
        import asyncio
        from osint.ai_research import research_contractor

        mock_hermes = AsyncMock()
        mock_hermes.is_available.return_value = True
        mock_hermes.chat.return_value = json.dumps({
            'company_status': 'unknown',
            'current_domain': None,
            'domain_confidence': 0,
            'brief': 'No search results available.',
            'sources': [],
        })

        mock_brave = AsyncMock()
        mock_brave.is_available.return_value = False

        result = asyncio.run(research_contractor(self._make_contractor(), mock_hermes, mock_brave))
        self.assertTrue(result['queried'])
        # Should still attempt with no search context

    def test_hermes_returns_malformed_json(self):
        import asyncio
        from osint.ai_research import research_contractor

        mock_hermes = AsyncMock()
        mock_hermes.is_available.return_value = True
        mock_hermes.chat.return_value = 'This is not JSON at all, sorry!'

        mock_brave = AsyncMock()
        mock_brave.is_available.return_value = True
        mock_brave.search.return_value = [
            {'title': 'Test', 'url': 'https://test.com', 'description': 'test'},
        ]

        result = asyncio.run(research_contractor(self._make_contractor(), mock_hermes, mock_brave))
        self.assertEqual(result['error'], 'json_parse_failed')

    def test_search_queries_include_name_and_acquisition(self):
        import asyncio
        from osint.ai_research import research_contractor

        mock_hermes = AsyncMock()
        mock_hermes.is_available.return_value = True
        mock_hermes.chat.return_value = json.dumps({
            'company_status': 'active', 'current_domain': 'test.com',
            'domain_confidence': 50, 'brief': 'Test.', 'sources': [],
        })

        mock_brave = AsyncMock()
        mock_brave.is_available.return_value = True
        mock_brave.search.return_value = []

        with patch('osint.ai_research.probe_domain', return_value=True):
            asyncio.run(research_contractor(
                self._make_contractor(name='OSI Inc'), mock_hermes, mock_brave))

        # Should have made at least 3 search queries
        self.assertGreaterEqual(mock_brave.search.call_count, 3)
        queries = [call.args[0] for call in mock_brave.search.call_args_list]
        # One should be about the company + DOE
        self.assertTrue(any('OSI' in q and 'DOE' in q.upper() or 'Energy' in q for q in queries))
        # One should check for acquisitions
        self.assertTrue(any('acquired' in q.lower() or 'merged' in q.lower() for q in queries))
```

- [ ] **Step 9: Implement `research_contractor`**

```python
async def research_contractor(
    contractor: dict,
    hermes,
    brave,
    on_status=None,
) -> dict:
    """Research a contractor using web search + LLM reasoning.

    Args:
        contractor: Contractor dict from contractors.json.
        hermes: HermesClient instance.
        brave: BraveSearchClient instance.
        on_status: Optional async callback(phase, detail) for progress.

    Returns:
        Research result dict matching the output schema.
    """
    from osint.domain_discovery import probe_domain, extract_domain_from_url

    result = {
        'queried': True,
        'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'company_status': 'unknown',
        'company_status_detail': None,
        'current_domain': None,
        'domain_confidence': 0,
        'domain_validated': False,
        'previous_domain': None,
        'parent_company': None,
        'acquisition_year': None,
        'brief': None,
        'sources': [],
        'search_queries_used': 0,
        'raw_search_results': 0,
        'error': None,
    }

    if not hermes.is_available():
        result['error'] = 'hermes_unavailable'
        return result

    name = contractor.get('name', '')
    dba = contractor.get('dba', '')
    city = contractor.get('city', '')
    state = contractor.get('state', '')
    search_name = dba if dba and dba != name else name

    # Existing domain for comparison
    dd = contractor.get('osint', {}).get('domain_discovery', {})
    result['previous_domain'] = dd.get('domain')

    # --- Phase 1: Web Search ---
    all_results = []
    queries = [
        f'"{search_name}" Department of Energy contractor',
        f'"{search_name}" acquired OR merged OR subsidiary',
        f'"{search_name}" official website {city} {state}',
    ]

    # Add domain-specific query if we have one
    existing_domain = dd.get('domain', '')
    if existing_domain:
        queries.append(f'site:{existing_domain} {search_name}')

    if brave.is_available():
        for query in queries:
            if on_status:
                await on_status('search', query[:60])
            try:
                results = await brave.search(query, count=5)
                all_results.extend(results)
                result['search_queries_used'] += 1
            except Exception:
                pass

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r['url'] not in seen_urls:
            seen_urls.add(r['url'])
            unique_results.append(r)

    result['raw_search_results'] = len(unique_results)

    # Format search context for LLM
    search_context = ''
    if unique_results:
        lines = []
        for r in unique_results[:12]:
            lines.append(f"Source: {r['title']}")
            lines.append(f"URL: {r['url']}")
            if r.get('description'):
                lines.append(f"Content: {r['description']}")
            lines.append('')
        search_context = '\n'.join(lines)

    # --- Phase 2: LLM Synthesis ---
    if on_status:
        await on_status('synthesizing', f'{len(unique_results)} sources')

    messages = build_research_prompt(contractor, search_context)

    try:
        raw = await hermes.chat(messages, max_tokens=1500)
    except Exception as e:
        result['error'] = f'hermes_error: {str(e)[:100]}'
        return result

    parsed = extract_research_json(raw)
    if not parsed:
        result['error'] = 'json_parse_failed'
        return result

    # --- Phase 3: Populate result from LLM output ---
    result['company_status'] = parsed.get('company_status', 'unknown')
    result['company_status_detail'] = parsed.get('company_status_detail')
    result['parent_company'] = parsed.get('parent_company')
    result['acquisition_year'] = parsed.get('acquisition_year')
    result['brief'] = parsed.get('brief')
    result['domain_confidence'] = parsed.get('domain_confidence', 0)

    # Extract sources
    sources = parsed.get('sources', [])
    if isinstance(sources, list):
        result['sources'] = [
            {'title': s.get('title', ''), 'url': s.get('url', '')}
            for s in sources if isinstance(s, dict)
        ]

    # --- Phase 4: Domain Validation ---
    suggested_domain = parsed.get('current_domain')
    if suggested_domain:
        # Clean it
        suggested_domain = extract_domain_from_url(
            f'https://{suggested_domain}' if '://' not in str(suggested_domain) else suggested_domain
        )

    if suggested_domain:
        if on_status:
            await on_status('validating', suggested_domain)
        validated = probe_domain(suggested_domain, timeout=3.0)
        result['current_domain'] = suggested_domain
        result['domain_validated'] = validated
    else:
        result['domain_validated'] = False

    return result
```

- [ ] **Step 10: Run all tests to verify they pass**

Run: `cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python -m pytest tests/test_ai_research.py -v`
Expected: All 11 PASS

- [ ] **Step 11: Commit Task 1**

```bash
git add osint/ai_research.py tests/test_ai_research.py
git commit -m "feat: add AI research module with web search + LLM synthesis"
```

**Integration test:** Import `research_contractor` from `osint.ai_research` — should succeed.

---

### Task 2: Pipeline Layer — `run_layer_ai_research`

**Files:**
- Modify: `osint/pipeline.py` (add layer function + CLI integration)
- Modify: `tests/test_ai_research.py` (add pipeline integration tests)

**Requires:** Task 1 (`research_contractor` function)

**Provides:**
- `run_layer_ai_research(contractors, force=False, limit=0)` in `osint/pipeline.py`
- CLI: `--layers ai_research`

**Ground Truth:**
- `needs_layer(contractor, 'ai_research', force)` — existing utility in pipeline.py
- `get_contractor_domain(contractor)` — existing utility
- `save_data(data)` — writes to contractors.json
- `load_data()` — reads contractors.json
- Domain cascade pattern: set `queried=False` on downstream layers, add `_invalidated_by` metadata

- [ ] **Step 1: Write failing test for smart targeting**

```python
class TestPipelineLayer(unittest.TestCase):
    """Test the pipeline layer integration."""

    def test_smart_targeting_skips_brave_search_domains(self):
        """Contractors with brave_search-validated domains should be skipped."""
        from osint.ai_research import needs_ai_research
        c = {
            'osint': {
                'domain_discovery': {'domain': 'good.com', 'source': 'brave_search'},
                'domain_verify': {'queried': True, 'confidence': 80},
                'ai_research': None,
            }
        }
        self.assertFalse(needs_ai_research(c))

    def test_smart_targeting_includes_dns_probe(self):
        c = {
            'osint': {
                'domain_discovery': {'domain': 'maybe.com', 'source': 'dns_probe'},
                'domain_verify': {'queried': True, 'confidence': 30},
            }
        }
        self.assertTrue(needs_ai_research(c))

    def test_smart_targeting_includes_no_domain(self):
        c = {'osint': {'domain_discovery': {'domain': None, 'source': None}}}
        self.assertTrue(needs_ai_research(c))

    def test_smart_targeting_includes_low_confidence(self):
        c = {
            'osint': {
                'domain_discovery': {'domain': 'x.com', 'source': 'csv_url'},
                'domain_verify': {'queried': True, 'confidence': 40},
            }
        }
        self.assertTrue(needs_ai_research(c))

    def test_smart_targeting_skips_already_researched(self):
        c = {
            'osint': {
                'domain_discovery': {'domain': 'x.com', 'source': 'dns_probe'},
                'ai_research': {'queried': True, 'error': None},
            }
        }
        self.assertFalse(needs_ai_research(c))
```

- [ ] **Step 2: Implement `needs_ai_research` in `osint/ai_research.py`**

```python
def needs_ai_research(contractor: dict) -> bool:
    """Determine if a contractor needs AI research.

    Smart targeting: skip contractors with good data, research those with:
    - No domain discovered
    - Domain from dns_probe (heuristic, error-prone)
    - Low domain verification confidence (<50%)
    - Never AI-researched before
    """
    osint = contractor.get('osint', {})

    # Already researched successfully
    ar = osint.get('ai_research', {})
    if ar and ar.get('queried') and not ar.get('error'):
        return False

    dd = osint.get('domain_discovery', {})
    dv = osint.get('domain_verify', {})

    # No domain at all
    if not dd.get('domain'):
        return True

    # Domain from dns_probe (heuristic, often wrong)
    if dd.get('source') == 'dns_probe':
        return True

    # Low verification confidence
    if dv.get('queried') and dv.get('confidence', 100) < 50:
        return True

    return False
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai_research.py::TestPipelineLayer -v`
Expected: All 5 PASS

- [ ] **Step 4: Write test for domain cascade**

```python
    def test_domain_cascade_on_upgrade(self):
        from osint.ai_research import apply_domain_cascade
        c = {
            'osint': {
                'domain_discovery': {'domain': 'old.com', 'source': 'dns_probe'},
                'domain_verify': {'queried': True, 'confidence': 30},
                'dns': {'queried': True, 'a_records': ['1.2.3.4']},
                'ct': {'queried': True, 'subdomain_count': 5},
                'web': {'queried': True, 'status_code': 200},
            }
        }
        changed = apply_domain_cascade(c, 'new.com', 'ai_research')
        self.assertTrue(changed)
        self.assertEqual(c['osint']['domain_discovery']['domain'], 'new.com')
        self.assertEqual(c['osint']['domain_discovery']['source'], 'ai_research')
        self.assertFalse(c['osint']['domain_verify']['queried'])
        self.assertFalse(c['osint']['dns']['queried'])
        self.assertFalse(c['osint']['ct']['queried'])
        self.assertFalse(c['osint']['web']['queried'])

    def test_no_cascade_when_domain_unchanged(self):
        from osint.ai_research import apply_domain_cascade
        c = {
            'osint': {
                'domain_discovery': {'domain': 'same.com', 'source': 'brave_search'},
                'dns': {'queried': True},
            }
        }
        changed = apply_domain_cascade(c, 'same.com', 'ai_research')
        self.assertFalse(changed)
        self.assertTrue(c['osint']['dns']['queried'])
```

- [ ] **Step 5: Implement `apply_domain_cascade`**

```python
def apply_domain_cascade(contractor: dict, new_domain: str, source: str) -> bool:
    """Apply domain cascade when AI research finds a different domain.

    Updates domain_discovery and invalidates downstream layers.
    Returns True if domain was changed.
    """
    osint = contractor.get('osint', {})
    dd = osint.get('domain_discovery', {})
    old_domain = dd.get('domain', '')

    if new_domain == old_domain:
        return False

    # Update domain discovery
    dd['domain'] = new_domain
    dd['source'] = source
    contractor.setdefault('osint', {})['domain_discovery'] = dd

    # Invalidate downstream layers
    cascade_layers = ['domain_verify', 'dns', 'ct', 'web']
    for layer in cascade_layers:
        if layer in osint and osint[layer].get('queried'):
            osint[layer]['queried'] = False
            osint[layer]['_invalidated_by'] = f'ai_research:{old_domain}->{new_domain}'

    return True
```

- [ ] **Step 6: Run tests to verify cascade tests pass**

Run: `python -m pytest tests/test_ai_research.py::TestPipelineLayer -v`
Expected: All 7 PASS

- [ ] **Step 7: Add `run_layer_ai_research` to `osint/pipeline.py`**

Add import at top of pipeline.py:
```python
from osint.ai_research import research_contractor, needs_ai_research, apply_domain_cascade
```

Add layer function (before `print_summary`):
```python
def run_layer_ai_research(contractors, force=False, limit=0):
    """Layer: AI Research — web search + LLM reasoning for domain/status/brief."""
    import asyncio
    from backend.mercury_client import HermesClient
    from backend.brave_search import BraveSearchClient

    print('\n' + '=' * 60)
    print('LAYER: AI Research (Hermes + Brave Search)')
    print('=' * 60)

    hermes = HermesClient()
    brave = BraveSearchClient()

    if not hermes.is_available():
        print('  NOUS_API_KEY not set. Skipping.')
        return 0

    # Smart targeting
    to_process = []
    for i, c in enumerate(contractors):
        if force or needs_ai_research(c):
            to_process.append((i, c))

    if limit > 0:
        to_process = to_process[:limit]

    if not to_process:
        print('  No contractors need AI research.')
        return 0

    print(f'  Processing {len(to_process)} contractors...')
    if brave.is_available():
        print('  Brave Search: available')
    else:
        print('  Brave Search: unavailable (BRAVE_SEARCH_API_KEY not set)')

    researched = 0
    upgraded = 0

    async def process_all():
        nonlocal researched, upgraded
        for idx, (i, c) in enumerate(to_process):
            name = c['name'][:45]
            print(f'  [{idx+1}/{len(to_process)}] {name:45s}', end=' ', flush=True)

            result = await research_contractor(c, hermes, brave)
            c.setdefault('osint', {})['ai_research'] = result

            if result.get('error'):
                print(f'  ERROR: {result["error"]}')
            else:
                researched += 1
                status = result.get('company_status', 'unknown')
                domain = result.get('current_domain', '')

                # Domain cascade if AI found a different domain
                if domain and result.get('domain_validated'):
                    old = c.get('osint', {}).get('domain_discovery', {}).get('domain', '')
                    if domain != old:
                        apply_domain_cascade(c, domain, 'ai_research')
                        upgraded += 1
                        print(f'  {status.upper()} domain: {old or "none"} -> {domain}')
                    else:
                        print(f'  {status.upper()} domain: {domain} (confirmed)')
                else:
                    print(f'  {status.upper()} domain: {domain or "none"} (unvalidated)')

            # Save every 25
            if (idx + 1) % 25 == 0:
                print(f'\n  Saving progress ({idx+1}/{len(to_process)})...\n')
                save_data({'contractors': contractors,
                           **{k: v for k, v in load_data().items() if k != 'contractors'}})

            await asyncio.sleep(1.0)  # Rate limit

    asyncio.run(process_all())
    print(f'\n  AI Research: {researched}/{len(to_process)} researched, {upgraded} domains upgraded')
    return researched
```

Add to CLI in `main()` (before final save):
```python
    if run_all or 'ai_research' in layers:
        run_layer_ai_research(contractors, force=args.force, limit=args.limit)
        save_data(data)
```

Update `--layers` help string to include `ai_research`.

- [ ] **Step 8: Run all tests**

Run: `python -m pytest tests/test_ai_research.py -v`
Expected: All PASS

- [ ] **Step 9: Commit Task 2**

```bash
git add osint/ai_research.py osint/pipeline.py tests/test_ai_research.py
git commit -m "feat: add AI research pipeline layer with smart targeting and domain cascade"
```

**Integration test:** `python -m osint.pipeline --layers ai_research --limit 1` should process 1 contractor (requires API keys).

---

### Task 3: On-Demand API Endpoint

**Files:**
- Modify: `test_atlas_server.py` (add `/api/ai-research` endpoint)

**Requires:** Task 1 (`research_contractor` function)

**Provides:**
- `POST /api/ai-research` — SSE endpoint accepting `{contractor_index: int}`
- Streams phases: search → synthesizing → validating → complete

**Ground Truth:**
- `StreamingResponse` from `starlette.responses` — already imported in test_atlas_server.py
- SSE format: `data: {json}\n\n` — existing pattern in summarize_role_endpoint
- Contractor loading: `json.load(BASE / "frontend" / "static" / "contractors.json")` — existing pattern

- [ ] **Step 1: Add `/api/ai-research` endpoint to `test_atlas_server.py`**

After the `summarize_role_endpoint`, add:

```python
@app.post("/api/ai-research")
async def ai_research_endpoint(req: KillChainRequest):
    """AI-powered contractor research. Streams SSE progress."""
    import json as _json
    from backend.brave_search import BraveSearchClient
    from osint.ai_research import research_contractor

    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid index"}, status_code=400)

    c = contractors[req.contractor_index]

    async def stream():
        brave = BraveSearchClient()

        async def on_status(phase, detail):
            yield_data = _json.dumps({'phase': phase, 'detail': detail})
            # on_status can't yield directly; we use a shared list
            pass

        # Use a progress list to collect status updates
        progress = []

        async def collect_status(phase, detail):
            progress.append({'phase': phase, 'detail': detail})

        result = await research_contractor(c, hermes, brave, on_status=collect_status)

        # Emit progress events
        for p in progress:
            yield f"data: {_json.dumps(p)}\n\n"

        # Emit final result
        yield f"data: {_json.dumps({'phase': 'complete', **result})}\n\n"

        # Save result to contractors.json if successful
        if not result.get('error'):
            c.setdefault('osint', {})['ai_research'] = result

            # Apply domain cascade if domain upgraded
            domain = result.get('current_domain')
            if domain and result.get('domain_validated'):
                from osint.ai_research import apply_domain_cascade
                old = c.get('osint', {}).get('domain_discovery', {}).get('domain', '')
                if domain != old:
                    apply_domain_cascade(c, domain, 'ai_research')

            with open(BASE / "frontend" / "static" / "contractors.json", "w") as f:
                _json.dump(data, f, separators=(',', ':'))

    return StreamingResponse(stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Test endpoint manually**

Verify the server starts and the endpoint responds:
```bash
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python test_atlas_server.py &
curl -X POST http://localhost:8000/api/ai-research -H "Content-Type: application/json" -d '{"contractor_index": 0}'
```
Expected: SSE stream with phase events and final complete event.

- [ ] **Step 3: Fix the SSE streaming pattern**

The `on_status` callback can't yield from inside `research_contractor`. Restructure to use real-time streaming:

Instead of the callback pattern, modify the endpoint to call brave search and hermes inline (like summarize_role does), streaming each phase. This is more reliable than the callback approach.

```python
@app.post("/api/ai-research")
async def ai_research_endpoint(req: KillChainRequest):
    """AI-powered contractor research with SSE streaming."""
    import json as _json
    from backend.brave_search import BraveSearchClient
    from osint.ai_research import (
        build_research_prompt, extract_research_json,
        apply_domain_cascade,
    )
    from osint.domain_discovery import probe_domain, extract_domain_from_url

    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid index"}, status_code=400)

    c = contractors[req.contractor_index]

    async def stream():
        import time as _time
        brave = BraveSearchClient()
        name = c.get('name', '')
        dba = c.get('dba', '')
        city = c.get('city', '')
        state = c.get('state', '')
        search_name = dba if dba and dba != name else name
        dd = c.get('osint', {}).get('domain_discovery', {})

        # Phase 1: Web Search
        all_results = []
        queries = [
            f'"{search_name}" Department of Energy contractor',
            f'"{search_name}" acquired OR merged OR subsidiary',
            f'"{search_name}" official website {city} {state}',
        ]
        if dd.get('domain'):
            queries.append(f'site:{dd["domain"]} {search_name}')

        if brave.is_available():
            for q in queries:
                yield f"data: {_json.dumps({'phase': 'search', 'detail': q[:60]})}\n\n"
                try:
                    results = await brave.search(q, count=5)
                    all_results.extend(results)
                except Exception:
                    pass

        # Deduplicate
        seen = set()
        unique = []
        for r in all_results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique.append(r)

        yield f"data: {_json.dumps({'phase': 'search_complete', 'results': len(unique)})}\n\n"

        # Format context
        search_context = ''
        if unique:
            lines = []
            for r in unique[:12]:
                lines.append(f"Source: {r['title']}")
                lines.append(f"URL: {r['url']}")
                if r.get('description'):
                    lines.append(f"Content: {r['description']}")
                lines.append('')
            search_context = '\n'.join(lines)

        # Phase 2: LLM Synthesis
        yield f"data: {_json.dumps({'phase': 'synthesizing', 'sources': len(unique)})}\n\n"
        messages = build_research_prompt(c, search_context)

        result = {
            'queried': True,
            'query_time': _time.strftime('%Y-%m-%dT%H:%M:%S'),
            'company_status': 'unknown',
            'company_status_detail': None,
            'current_domain': None,
            'domain_confidence': 0,
            'domain_validated': False,
            'previous_domain': dd.get('domain'),
            'parent_company': None,
            'acquisition_year': None,
            'brief': None,
            'sources': [],
            'search_queries_used': len(queries),
            'raw_search_results': len(unique),
            'error': None,
        }

        if hermes.is_available():
            try:
                raw = await hermes.chat(messages, max_tokens=1500)
                parsed = extract_research_json(raw)
                if parsed:
                    result['company_status'] = parsed.get('company_status', 'unknown')
                    result['company_status_detail'] = parsed.get('company_status_detail')
                    result['parent_company'] = parsed.get('parent_company')
                    result['acquisition_year'] = parsed.get('acquisition_year')
                    result['brief'] = parsed.get('brief')
                    result['domain_confidence'] = parsed.get('domain_confidence', 0)
                    sources = parsed.get('sources', [])
                    if isinstance(sources, list):
                        result['sources'] = [
                            {'title': s.get('title', ''), 'url': s.get('url', '')}
                            for s in sources if isinstance(s, dict)
                        ]

                    # Domain validation
                    suggested = parsed.get('current_domain')
                    if suggested:
                        suggested = extract_domain_from_url(
                            f'https://{suggested}' if '://' not in str(suggested) else suggested
                        )
                    if suggested:
                        yield f"data: {_json.dumps({'phase': 'validating', 'domain': suggested})}\n\n"
                        validated = probe_domain(suggested, timeout=3.0)
                        result['current_domain'] = suggested
                        result['domain_validated'] = validated
                else:
                    result['error'] = 'json_parse_failed'
            except Exception as e:
                result['error'] = f'hermes_error: {str(e)[:100]}'
        else:
            result['error'] = 'hermes_unavailable'

        # Save to data
        c.setdefault('osint', {})['ai_research'] = result

        if not result.get('error') and result.get('current_domain') and result.get('domain_validated'):
            old = dd.get('domain', '')
            if result['current_domain'] != old:
                apply_domain_cascade(c, result['current_domain'], 'ai_research')

        with open(BASE / "frontend" / "static" / "contractors.json", "w") as f:
            _json.dump(data, f, separators=(',', ':'))

        yield f"data: {_json.dumps({'phase': 'complete', **result})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
```

- [ ] **Step 4: Run existing tests to verify no regressions**

Run: `python -m pytest tests/ -v --timeout=30`
Expected: All existing tests still PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add test_atlas_server.py
git commit -m "feat: add /api/ai-research SSE endpoint for on-demand contractor research"
```

---

### Task 4: Frontend Integration

**Files:**
- Modify: `frontend/static/contractor-map.html`

**Requires:** Task 3 (API endpoint)

**Provides:**
- `buildAIResearchSection(c)` — renders the AI Research Brief section
- `generateAIResearch()` — triggers on-demand research via SSE
- Company status badge (green/amber/red/gray)

- [ ] **Step 1: Add `buildAIResearchSection` function**

Insert after `buildPanelBody` helper functions (after buildColocationSection). Pattern follows existing section builders.

```javascript
function buildAIResearchSection(c) {
    const ar = c.osint?.ai_research;
    if (!ar || !ar.queried) {
        return `<div class="panel-section">
            <div class="section-title">AI RESEARCH BRIEF</div>
            <div style="color:var(--hud-text-dim);padding:8px 0;">
                Not yet researched.
                <button onclick="generateAIResearch()" class="action-btn"
                    style="margin-left:8px;font-size:11px;padding:2px 10px;"
                    id="aiResearchBtn">Research</button>
            </div>
        </div>`;
    }

    if (ar.error) {
        return `<div class="panel-section">
            <div class="section-title">AI RESEARCH BRIEF</div>
            <div style="color:var(--hud-danger);padding:8px 0;">Error: ${ar.error}</div>
            <button onclick="generateAIResearch()" class="action-btn"
                style="font-size:11px;padding:2px 10px;" id="aiResearchBtn">Retry</button>
        </div>`;
    }

    const statusColors = {
        'active': 'var(--hud-success)',
        'acquired': 'var(--hud-warning)',
        'merged': 'var(--hud-warning)',
        'dissolved': 'var(--hud-danger)',
        'unknown': 'var(--hud-text-dim)',
    };
    const statusColor = statusColors[ar.company_status] || 'var(--hud-text-dim)';

    let html = '<div class="panel-section"><div class="section-title">AI RESEARCH BRIEF</div>';

    // Status badge
    html += `<div style="display:flex;align-items:center;gap:10px;margin:6px 0;">
        <span style="background:${statusColor};color:#000;padding:2px 8px;border-radius:2px;
            font-size:10px;font-weight:700;text-transform:uppercase;">${ar.company_status}</span>`;

    if (ar.parent_company) {
        html += `<span style="color:var(--hud-text-dim);font-size:11px;">
            Parent: <span style="color:var(--hud-cyan)">${ar.parent_company}</span>`;
        if (ar.acquisition_year) html += ` (${ar.acquisition_year})`;
        html += '</span>';
    }
    html += '</div>';

    // Domain correction callout
    if (ar.current_domain && ar.previous_domain && ar.current_domain !== ar.previous_domain) {
        html += `<div style="background:rgba(14,165,233,0.1);border-left:2px solid var(--hud-cyan);
            padding:6px 10px;margin:6px 0;font-size:11px;">
            Domain corrected: <span style="color:var(--hud-danger);text-decoration:line-through;">
            ${ar.previous_domain}</span> → <span style="color:var(--hud-success);">
            ${ar.current_domain}</span>
            ${ar.domain_validated ? ' ✓ validated' : ' (unvalidated)'}
        </div>`;
    }

    // Brief
    if (ar.brief) {
        const paragraphs = ar.brief.split('\n').filter(p => p.trim());
        for (const p of paragraphs) {
            html += `<p style="color:var(--hud-text);font-size:12px;line-height:1.5;margin:8px 0;">${p}</p>`;
        }
    }

    // Sources
    if (ar.sources && ar.sources.length > 0) {
        html += '<div style="margin-top:8px;border-top:1px solid var(--hud-border);padding-top:6px;">';
        html += `<div style="color:var(--hud-text-dim);font-size:10px;margin-bottom:4px;">
            ${ar.sources.length} SOURCE${ar.sources.length !== 1 ? 'S' : ''}</div>`;
        for (const s of ar.sources) {
            html += `<div style="font-size:11px;margin:2px 0;">
                <a href="${s.url}" target="_blank" rel="noopener"
                   style="color:var(--hud-cyan);text-decoration:none;">${s.title || s.url}</a>
            </div>`;
        }
        html += '</div>';
    }

    // Refresh button
    html += `<button onclick="generateAIResearch()" class="action-btn"
        style="margin-top:8px;font-size:10px;padding:2px 8px;" id="aiResearchBtn">Refresh</button>`;

    html += '</div>';
    return html;
}
```

- [ ] **Step 2: Insert AI Research section into `buildPanelBody`**

In `buildPanelBody(c)`, add after the Mission Profile section (before Financial Summary):

```javascript
html += buildAIResearchSection(c);
```

- [ ] **Step 3: Add `generateAIResearch` function**

Insert after `summarizeContractorRole` function:

```javascript
async function generateAIResearch() {
    if (selectedContractor === null) return;
    const btn = document.getElementById('aiResearchBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Researching...';
        btn.style.opacity = '0.6';
    }

    try {
        const resp = await fetch('/api/ai-research', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({contractor_index: selectedContractor}),
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let lastResult = null;

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const payload = line.slice(6).trim();
                if (payload === '[DONE]') continue;
                try {
                    const event = JSON.parse(payload);
                    if (btn) {
                        if (event.phase === 'search') {
                            btn.textContent = `Searching: ${event.detail || ''}`;
                        } else if (event.phase === 'synthesizing') {
                            btn.textContent = `Synthesizing (${event.sources} sources)...`;
                        } else if (event.phase === 'validating') {
                            btn.textContent = `Validating ${event.domain}...`;
                        } else if (event.phase === 'complete') {
                            lastResult = event;
                        }
                    }
                } catch (e) {}
            }
        }

        // Refresh the detail panel with updated data
        if (lastResult) {
            const c = allContractors[selectedContractor];
            if (!c.osint) c.osint = {};
            c.osint.ai_research = lastResult;

            // Update domain if cascaded
            if (lastResult.current_domain && lastResult.domain_validated &&
                lastResult.current_domain !== lastResult.previous_domain) {
                if (!c.osint.domain_discovery) c.osint.domain_discovery = {};
                c.osint.domain_discovery.domain = lastResult.current_domain;
                c.osint.domain_discovery.source = 'ai_research';
            }

            // Rebuild the panel
            document.getElementById('panelBody').innerHTML = buildPanelBody(c);
        }
    } catch (e) {
        console.error('AI Research failed:', e);
        if (btn) {
            btn.textContent = 'Research (failed)';
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    }
}
```

- [ ] **Step 4: Verify the app loads and displays correctly**

Start the server and open the app:
```bash
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python test_atlas_server.py
```
Open browser, click a contractor, verify:
- AI Research Brief section appears
- For unresearched contractors: shows "Not yet researched" with Research button
- Clicking Research triggers SSE and updates the panel

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit Task 4**

```bash
git add frontend/static/contractor-map.html
git commit -m "feat: add AI Research Brief section to frontend detail panel"
```

---

### Task 5: Integration Test & Final Verification

**Files:**
- All files from Tasks 1-4

**Requires:** Tasks 1-4 complete

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python -m pytest tests/ -v
```
Expected: All tests PASS (including new test_ai_research.py)

- [ ] **Step 2: Verify pipeline CLI works**

```bash
python -m osint.pipeline --layers ai_research --limit 2
```
Expected: Processes 2 contractors (if API keys available), prints results, saves to contractors.json

- [ ] **Step 3: Verify server endpoint works**

```bash
python test_atlas_server.py &
curl -s -X POST http://localhost:8000/api/ai-research \
  -H "Content-Type: application/json" \
  -d '{"contractor_index": 0}' | head -20
```
Expected: SSE events with search/synthesizing/complete phases

- [ ] **Step 4: Visual verification in browser**

Open the app, click a contractor, verify the AI Research Brief section renders properly.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: AI Research Layer — complete implementation with pipeline, API, and frontend"
```
