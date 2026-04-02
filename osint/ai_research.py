"""
AI-powered contractor research layer.

Uses LLM (Hermes-4-405B) + Brave Search to intelligently research DOE
contractors: verify domains, detect acquisitions/mergers, identify parent
companies, and generate intelligence briefs.

This layer targets contractors where automated discovery was unreliable
(dns_probe source, low confidence, no domain found) and produces structured
intelligence that upgrades the OSINT data.
"""

import json
import re
import time
from typing import Optional


# Reuse the DNS probe from domain_discovery
from osint.domain_discovery import probe_domain, extract_domain_from_url


# ─────────────────────────────────────────────────────────────
# 1. Extract JSON from LLM output
# ─────────────────────────────────────────────────────────────

def extract_research_json(raw: str) -> Optional[dict]:
    """Extract a JSON object from raw LLM output.

    Handles multiple common LLM output patterns:
    - Clean JSON
    - JSON wrapped in <think>...</think> tags
    - JSON inside markdown code fences (```json ... ```)
    - JSON embedded within surrounding narrative text

    Returns:
        Parsed dict if valid JSON found, None otherwise.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip <think>...</think> tags (Hermes reasoning traces)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # Try 1: Direct parse (clean JSON)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try 2: Extract from markdown code fence
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, flags=re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Try 3: Find the outermost { ... } in the text
    # Use a brace-counting approach for robustness
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except (json.JSONDecodeError, ValueError):
                    # Keep looking for another brace pair
                    break

    return None


# ─────────────────────────────────────────────────────────────
# 2. Build LLM research prompt
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an OSINT intelligence analyst specializing in U.S. Department of Energy contractors. Your task is to research a contractor and provide structured intelligence.

You MUST respond with a single JSON object containing these fields:
- company_status: one of "active", "acquired", "merged", "dissolved", "unknown"
- company_status_detail: string explaining current status, or null
- current_domain: the company's current official website domain (no protocol), or null
- domain_confidence: integer 0-100 indicating confidence in the domain
- parent_company: name of parent/acquiring company if applicable, or null
- acquisition_year: year of acquisition/merger as integer, or null
- brief: 2-4 sentence intelligence summary of the company
- sources: array of objects with "title" and "url" fields citing your findings

Rules:
- Output ONLY valid JSON, no markdown fences or extra text
- For domain, provide just the domain (e.g., "example.com") not a full URL
- If the company was acquired, provide the NEW parent company's domain as current_domain
- Set domain_confidence based on evidence: 90+ for official sites, 60-89 for likely, below 60 for uncertain
- Always cite sources from the search results provided"""


def build_research_prompt(contractor: dict, search_context: str) -> list[dict]:
    """Build LLM messages (system + user) for contractor research.

    Args:
        contractor: Contractor record dict with name, dba, city, state, etc.
        search_context: Formatted web search results for the LLM to analyze.

    Returns:
        List of message dicts with 'role' and 'content' keys.
    """
    # Build the contractor profile section
    parts = []
    parts.append(f"Contractor Name: {contractor.get('name', 'Unknown')}")

    dba = contractor.get('dba', '')
    if dba and dba != contractor.get('name', ''):
        parts.append(f"DBA / Trade Name: {dba}")

    city = contractor.get('city', '')
    state = contractor.get('state', '')
    if city or state:
        parts.append(f"Location: {city}, {state}")

    category = contractor.get('category', '')
    if category:
        parts.append(f"Category: {category}")

    contract_ids = contractor.get('contract_ids', [])
    if contract_ids:
        parts.append(f"DOE Contract IDs: {', '.join(contract_ids[:5])}")

    obligation = contractor.get('obligation', 0)
    if obligation:
        parts.append(f"Total Obligation: ${obligation:,.0f}")

    naics = contractor.get('naics', '')
    if naics:
        parts.append(f"NAICS: {naics}")

    role = contractor.get('role', '')
    if role:
        parts.append(f"Role: {role}")

    # Include existing domain intel if present (nested under 'osint')
    osint = contractor.get('osint', {})
    dd = osint.get('domain_discovery', {})
    if dd and dd.get('domain'):
        parts.append(f"\nExisting Domain Intel:")
        parts.append(f"  Domain: {dd['domain']}")
        parts.append(f"  Source: {dd.get('source', 'unknown')}")
        confidence = dd.get('confidence')
        if confidence is not None:
            parts.append(f"  Confidence: {confidence}%")

    contractor_profile = '\n'.join(parts)

    user_content = f"""Research the following DOE contractor and provide intelligence:

--- CONTRACTOR RECORD ---
{contractor_profile}

--- WEB SEARCH RESULTS ---
{search_context}

Analyze the search results and provide your assessment as a JSON object."""

    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': user_content},
    ]


# ─────────────────────────────────────────────────────────────
# 3. Full research pipeline
# ─────────────────────────────────────────────────────────────

def _build_result_template() -> dict:
    """Return an empty research result dict."""
    return {
        'queried': True,
        'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'company_status': None,
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


async def research_contractor(contractor: dict, hermes, brave, on_status=None) -> dict:
    """Full AI research pipeline for a single contractor.

    Phases:
        1. Run 3-4 Brave Search queries targeting different aspects
        2. Deduplicate results, format as context, call Hermes chat()
        3. Extract JSON from response, populate result dict
        4. DNS-validate any suggested domain via probe_domain()

    Args:
        contractor: Contractor record dict.
        hermes: HermesClient instance.
        brave: BraveSearchClient instance.
        on_status: Optional async callback(str) for progress updates.

    Returns:
        Structured research result dict.
    """
    result = _build_result_template()

    # Record any existing domain as previous_domain (nested under 'osint')
    osint = contractor.get('osint', {})
    dd = osint.get('domain_discovery', {})
    if dd and dd.get('domain'):
        result['previous_domain'] = dd['domain']

    # ── Availability checks ──
    if not hermes.is_available():
        result['error'] = 'hermes_unavailable'
        return result

    # Brave unavailable is not fatal — we proceed without search context
    brave_available = brave.is_available()

    # ── Phase 1: Brave Search queries ──
    if on_status:
        await on_status('Searching web for contractor intelligence...')

    name = contractor.get('name', '')
    dba = contractor.get('dba', '')
    search_name = dba if (dba and dba != name) else name
    existing_domain = dd.get('domain', '') if dd else ''

    queries = [
        f'"{search_name}" DOE Department of Energy contractor',
        f'"{search_name}" acquisition merger acquired',
        f'"{search_name}" official website',
    ]
    # Add site: query if we have an existing domain
    if existing_domain:
        queries.append(f'site:{existing_domain} {search_name}')

    all_results = []
    seen_urls = set()

    if brave_available:
        for query in queries:
            try:
                search_results = await brave.search(query, count=5)
                result['search_queries_used'] += 1
                for sr in search_results:
                    url = sr.get('url', '')
                    if url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(sr)
            except Exception:
                continue

    result['raw_search_results'] = len(all_results)

    # ── Phase 2: Format context and call Hermes ──
    if on_status:
        await on_status('Analyzing search results with AI...')

    # Format search results as context for the LLM
    context_lines = []
    for sr in all_results:
        context_lines.append(f"Title: {sr.get('title', '')}")
        context_lines.append(f"URL: {sr.get('url', '')}")
        desc = sr.get('description', '')
        if desc:
            context_lines.append(f"Description: {desc}")
        context_lines.append('')

    search_context = '\n'.join(context_lines)

    messages = build_research_prompt(contractor, search_context)

    try:
        llm_response = await hermes.chat(messages, max_tokens=4096)
    except Exception as e:
        result['error'] = f'Hermes chat error: {str(e)}'
        return result

    # ── Phase 3: Extract structured data ──
    if on_status:
        await on_status('Extracting structured intelligence...')

    parsed = extract_research_json(llm_response)

    if parsed is None:
        result['error'] = 'Failed to parse JSON from LLM response'
        return result

    # Populate result from parsed LLM output
    result['company_status'] = parsed.get('company_status', 'unknown')
    result['company_status_detail'] = parsed.get('company_status_detail')
    result['current_domain'] = parsed.get('current_domain')
    result['domain_confidence'] = parsed.get('domain_confidence', 0)
    result['parent_company'] = parsed.get('parent_company')
    result['acquisition_year'] = parsed.get('acquisition_year')
    result['brief'] = parsed.get('brief')
    result['sources'] = parsed.get('sources', [])

    # ── Phase 4: DNS-validate the suggested domain ──
    domain = result['current_domain']
    if domain:
        if on_status:
            await on_status(f'Validating domain {domain}...')
        result['domain_validated'] = probe_domain(domain)

    return result


# ─────────────────────────────────────────────────────────────
# 4. Smart targeting
# ─────────────────────────────────────────────────────────────

def needs_ai_research(contractor: dict) -> bool:
    """Determine if a contractor needs AI-powered research.

    Returns True when:
    - No domain was discovered
    - Domain was found via dns_probe (unreliable)
    - Domain confidence is below 50%
    - Contractor has never been AI-researched

    Returns False when:
    - Already researched via AI (ai_research.queried == True)
    - Has a high-confidence domain from a reliable source (brave_search >= 50%)
    """
    osint = contractor.get('osint', {})

    # Already researched -> skip
    ai = osint.get('ai_research', {})
    if ai and ai.get('queried'):
        return False

    dd = osint.get('domain_discovery', {})

    # No domain at all -> research needed
    if not dd or not dd.get('domain'):
        return True

    # Domain from dns_probe is unreliable -> research needed
    source = dd.get('source', '')
    if source == 'dns_probe':
        return True

    # Low confidence -> research needed
    confidence = dd.get('confidence', 0)
    if confidence < 50:
        return True

    # High-confidence domain from reliable source -> skip
    return False


# ─────────────────────────────────────────────────────────────
# 5. Domain cascade
# ─────────────────────────────────────────────────────────────

# Downstream layers that depend on the domain
_DOWNSTREAM_LAYERS = ['domain_verify', 'dns', 'ct', 'web']


def apply_domain_cascade(contractor: dict, new_domain: str, source: str) -> bool:
    """Update contractor domain and invalidate downstream layers if changed.

    When AI research discovers a better domain than what was previously found,
    this function updates domain_discovery and marks downstream layers
    (domain_verify, dns, ct, web) as needing re-query.

    Args:
        contractor: Contractor record dict (modified in place).
        new_domain: The new domain to set.
        source: Source attribution (e.g., 'ai_research').

    Returns:
        True if domain changed and cascade was applied, False if unchanged.
    """
    osint = contractor.get('osint', {})
    dd = osint.get('domain_discovery', {})
    old_domain = dd.get('domain', '')

    # No change -> no cascade
    if old_domain == new_domain:
        return False

    # Update domain_discovery under osint
    contractor.setdefault('osint', {})['domain_discovery'] = {
        **dd,
        'domain': new_domain,
        'source': source,
        '_previous_domain': old_domain,
        '_cascade_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }

    # Invalidate downstream layers under osint
    osint = contractor['osint']
    for layer in _DOWNSTREAM_LAYERS:
        if layer in osint and isinstance(osint[layer], dict):
            osint[layer]['queried'] = False
            osint[layer]['_invalidated_by'] = source
            osint[layer]['_invalidated_time'] = time.strftime('%Y-%m-%dT%H:%M:%S')

    return True
