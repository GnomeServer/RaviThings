#!/usr/bin/env python3
"""
Enhanced Shodan enrichment for DOE contractors.

Extends the baseline org-name search with five query strategies tried in
priority order, stopping at the first that returns results:

    1. org:"Cleaned Name"             -- registered org in Shodan
    2. ssl.cert.subject.O:"Cleaned Name" -- SSL certs on cloud-hosted infra
    3. ssl:"domain.com"               -- any SSL cert mentioning their domain
    4. hostname:domain.com            -- DNS-resolved services
    5. http.title:"Cleaned Name"      -- web apps with company name in <title>

Usage as a library:
    import shodan
    from osint.enhanced_shodan import enrich_shodan

    api = shodan.Shodan(API_KEY)
    result = enrich_shodan(api, {"name": "Acme Corp", "url": "https://acme.com", "dba": "", "parent": ""})
"""

import re
import time

import shodan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_org_name(name: str) -> str | None:
    """Strip legal suffixes and punctuation so the name works as a Shodan filter.

    >>> clean_org_name("Acme Solutions, LLC")
    'Acme'
    >>> clean_org_name("")
    """
    if not name:
        return None
    cleaned = re.sub(
        r',?\s*'
        r'(LLC|INC\.?|CORP\.?|CORPORATION|COMPANY|CO\.'
        r'|L\.?L\.?C\.?|L\.?P\.?|LTD\.?|GROUP'
        r'|HOLDINGS?|SERVICES?|SOLUTIONS?'
        r'|TECHNOLOGIES|TECHNOLOGY|ENTERPRISES?|INTERNATIONAL'
        r'|ASSOCIATES?|PARTNERS?|CONSULTING)\s*\.?\s*$',
        '',
        name,
        flags=re.IGNORECASE,
    ).strip().rstrip(',').strip()
    # Remove surrounding quotes
    cleaned = cleaned.strip('"').strip("'")
    if len(cleaned) < 3:
        return None
    return cleaned


def extract_domain(url: str) -> str | None:
    """Return a bare domain (no scheme, no path, no ``www.`` prefix).

    >>> extract_domain("https://www.acme.com/about")
    'acme.com'
    >>> extract_domain("")
    """
    if not url:
        return None
    domain = re.sub(r'^https?://', '', url.strip())
    domain = domain.split('/')[0]
    domain = re.sub(r'^www\.', '', domain)
    if '.' in domain and len(domain) > 3:
        return domain.lower()
    return None


# ---------------------------------------------------------------------------
# Query-plan builder
# ---------------------------------------------------------------------------

def _build_query_plan(contractor: dict) -> list[str]:
    """Return an ordered list of Shodan query strings to try.

    Priority follows detection likelihood for DOE contractor infra:
      1. org name       -- direct match in WHOIS/BGP data
      2. SSL subject O  -- certs issued to the company on cloud infra
      3. ssl + domain   -- domain anywhere in the cert chain
      4. hostname       -- forward DNS records
      5. http.title     -- company branding on web apps
    """
    org = clean_org_name(contractor.get('name', ''))
    domain = extract_domain(contractor.get('url', ''))
    dba = clean_org_name(contractor.get('dba', ''))
    parent = clean_org_name(contractor.get('parent', ''))

    queries: list[str] = []

    # --- primary org name ---
    if org:
        queries.append(f'org:"{org}"')
        queries.append(f'ssl.cert.subject.O:"{org}"')

    # --- domain-based ---
    if domain:
        queries.append(f'ssl:"{domain}"')
        queries.append(f'hostname:{domain}')

    # --- title fallback (org, then DBA, then parent) ---
    if org:
        queries.append(f'http.title:"{org}"')
    elif dba:
        queries.append(f'http.title:"{dba}"')
    elif parent:
        queries.append(f'http.title:"{parent}"')

    return queries


# ---------------------------------------------------------------------------
# Facet / host extraction
# ---------------------------------------------------------------------------

_FACETS = [
    ('port', 10),
    ('product', 10),
    ('vuln', 20),
    ('domain', 5),
    ('asn', 5),
]


def _parse_facets(facets: dict) -> dict:
    """Normalise the raw ``facets`` dict returned by ``api.count``."""
    top_ports = [
        {'port': item['value'], 'count': item['count']}
        for item in facets.get('port', [])
    ]
    top_services = [
        {'name': item['value'], 'count': item['count']}
        for item in facets.get('product', [])
    ]
    vulns = [
        {'cve': item['value'], 'count': item['count']}
        for item in facets.get('vuln', [])
    ]
    domains_found = [item['value'] for item in facets.get('domain', [])]
    asns = [item['value'] for item in facets.get('asn', [])]

    return {
        'top_ports': top_ports,
        'top_services': top_services,
        'vulns': vulns,
        'domains_found': domains_found,
        'asns': asns,
    }


def _parse_host(match: dict) -> dict:
    """Extract a normalised summary from a single Shodan host banner."""
    host: dict = {
        'ip': match.get('ip_str', ''),
        'port': match.get('port', 0),
        'product': match.get('product', ''),
        'version': match.get('version', ''),
        'hostnames': match.get('hostnames', [])[:3],
        'os': match.get('os', ''),
        'transport': match.get('transport', ''),
    }

    ssl = match.get('ssl') or {}
    cert = ssl.get('cert') or {}
    if cert:
        host['ssl_subject'] = (cert.get('subject') or {}).get('O', '')
        host['ssl_issuer'] = (cert.get('issuer') or {}).get('O', '')
        host['ssl_expires'] = cert.get('expires', '')

    http = match.get('http') or {}
    if http:
        host['http_title'] = http.get('title', '')
        host['http_server'] = http.get('server', '')

    return host


def _collect_technologies(top_services: list[dict],
                          sample_hosts: list[dict]) -> list[str]:
    """Deduplicate technology identifiers from services and host samples."""
    tech: set[str] = set()
    for svc in top_services:
        if svc.get('name'):
            tech.add(svc['name'])
    for host in sample_hosts:
        if host.get('product'):
            tech.add(host['product'])
        if host.get('http_server'):
            tech.add(host['http_server'])
    return sorted(tech)


# ---------------------------------------------------------------------------
# Core enrichment
# ---------------------------------------------------------------------------

_MAX_RETRIES = 2


def _call_with_retry(fn, *args, **kwargs):
    """Execute *fn* with exponential-backoff retry on Shodan rate limits.

    Returns the API response on success.  Re-raises ``shodan.APIError`` for
    non-rate-limit errors after exhausting retries.
    """
    last_err: shodan.APIError | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except shodan.APIError as exc:
            last_err = exc
            msg = str(exc).lower()
            if 'rate limit' in msg or 'too many' in msg:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            raise  # non-retriable error -- propagate immediately
    # All retries exhausted on rate-limit errors.
    raise last_err  # type: ignore[misc]


def enrich_shodan(api: "shodan.Shodan", contractor: dict) -> dict:
    """Query Shodan with multiple strategies and return an enrichment dict.

    Parameters
    ----------
    api:
        An authenticated ``shodan.Shodan`` client instance.
    contractor:
        Dict with keys ``name``, ``url``, ``dba``, ``parent`` (all strings,
        may be empty).

    Returns
    -------
    dict
        Enrichment payload with the following keys:

        - **queried** (bool): always ``True``
        - **query_time** (str): ISO-8601 timestamp of the query
        - **query_used** (str): the Shodan filter string that matched
        - **total_hosts** (int): number of hosts found
        - **top_ports** (list[dict]): ``[{port, count}, ...]``
        - **top_services** (list[dict]): ``[{name, count}, ...]``
        - **vulns** (list[dict]): ``[{cve, count}, ...]``
        - **domains_found** (list[str])
        - **asns** (list[str])
        - **sample_hosts** (list[dict]): up to 5 representative host records
        - **technologies** (list[str]): deduplicated product/server strings
        - **error** (str | None): error description, or ``None`` on success
    """
    result: dict = {
        'queried': True,
        'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'query_used': '',
        'total_hosts': 0,
        'top_ports': [],
        'top_services': [],
        'vulns': [],
        'domains_found': [],
        'asns': [],
        'sample_hosts': [],
        'technologies': [],
        'error': None,
    }

    queries = _build_query_plan(contractor)
    if not queries:
        result['error'] = 'no_searchable_identifier'
        return result

    for query in queries:
        try:
            count_result = _call_with_retry(api.count, query, facets=_FACETS)
        except shodan.APIError as exc:
            msg = str(exc).lower()
            if 'access denied' in msg:
                result['error'] = f'access_denied: {exc}'
                return result
            # Record the error but try the next query.
            result['error'] = str(exc)
            time.sleep(1)
            continue

        if count_result['total'] == 0:
            time.sleep(1)
            continue

        # ----- We have results -- populate the enrichment dict. -----
        result['total_hosts'] = count_result['total']
        result['query_used'] = query
        result['error'] = None

        facet_data = count_result.get('facets', {})
        result.update(_parse_facets(facet_data))

        # Fetch a small sample of actual host banners.
        time.sleep(1)
        try:
            search_result = _call_with_retry(api.search, query, limit=5)
            for match in search_result.get('matches', [])[:5]:
                result['sample_hosts'].append(_parse_host(match))
        except shodan.APIError:
            pass  # sample hosts are best-effort

        result['technologies'] = _collect_technologies(
            result['top_services'], result['sample_hosts'],
        )
        return result

    # None of the queries returned results.
    if result['error'] is None:
        result['error'] = 'no_results'
    return result
