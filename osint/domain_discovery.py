"""
Domain discovery for DOE contractors.

Attempts to find a contractor's website domain when the CSV lacks a company_url.
Uses multiple strategies: existing URL extraction, common domain patterns,
and DNS probing.
"""

import re
import socket
import time
from typing import Optional


# Common TLDs to probe
TLDS = ['.com', '.org', '.net', '.gov', '.us', '.io']

# Words to strip from company names when generating domain guesses
STRIP_WORDS = {
    'llc', 'inc', 'corp', 'corporation', 'company', 'co', 'ltd',
    'lp', 'llp', 'group', 'holdings', 'services', 'solutions',
    'technologies', 'technology', 'tech', 'the', 'of', 'and', '&',
    'associates', 'international', 'enterprises', 'consulting',
    'federal', 'government', 'govt',
}


def extract_domain_from_url(url: str) -> Optional[str]:
    """Extract a clean domain from a URL string."""
    if not url:
        return None
    domain = re.sub(r'^https?://', '', url.strip())
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    domain = re.sub(r'^www\.', '', domain).lower().strip('.')
    if '.' in domain and len(domain) > 3:
        return domain
    return None


def generate_domain_guesses(name: str) -> list[str]:
    """Generate plausible domain names from a company name.

    Examples:
        'Lockheed Martin Corp' -> ['lockheedmartin.com', 'lockheed-martin.com', ...]
        'Booz Allen Hamilton Inc' -> ['boozallen.com', 'bah.com', ...]
    """
    if not name:
        return []

    # Clean the name
    cleaned = re.sub(r'[,."\'()]+', '', name.lower())
    words = cleaned.split()
    words = [w for w in words if w not in STRIP_WORDS and len(w) > 1]

    if not words:
        return []

    guesses = []

    # Strategy 1: All words joined (e.g., lockheedmartin)
    if len(words) <= 4:
        joined = ''.join(words)
        for tld in TLDS[:3]:  # .com, .org, .net
            guesses.append(joined + tld)

    # Strategy 2: Hyphenated (e.g., lockheed-martin)
    if 2 <= len(words) <= 3:
        hyphenated = '-'.join(words)
        guesses.append(hyphenated + '.com')

    # Strategy 3: First word only (e.g., lockheed)
    if len(words[0]) >= 4:
        guesses.append(words[0] + '.com')

    # Strategy 4: Initials (e.g., bah for Booz Allen Hamilton)
    if len(words) >= 2:
        initials = ''.join(w[0] for w in words)
        if len(initials) >= 2:
            guesses.append(initials + '.com')

    # Strategy 5: First two words joined
    if len(words) >= 2:
        guesses.append(words[0] + words[1] + '.com')

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for g in guesses:
        if g not in seen:
            seen.add(g)
            unique.append(g)

    return unique


def probe_domain(domain: str, timeout: float = 3.0) -> bool:
    """Check if a domain resolves via DNS."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(domain, 80)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False


def discover_domain(contractor: dict) -> dict:
    """Attempt to discover a contractor's domain.

    Args:
        contractor: dict with keys 'name', 'url', 'dba' (all may be empty strings)

    Returns:
        dict with discovery results
    """
    result = {
        'queried': True,
        'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'domain': None,
        'source': None,
        'guesses_tried': 0,
        'error': None,
    }

    # Strategy 1: Extract from existing URL
    existing = extract_domain_from_url(contractor.get('url', ''))
    if existing and probe_domain(existing):
        result['domain'] = existing
        result['source'] = 'csv_url'
        return result

    # Strategy 2: Generate and probe guesses from name
    name = contractor.get('name', '')
    dba = contractor.get('dba', '')

    # Try DBA name first (often simpler/more recognizable)
    names_to_try = []
    if dba:
        names_to_try.append(dba)
    if name:
        names_to_try.append(name)

    for try_name in names_to_try:
        guesses = generate_domain_guesses(try_name)
        for guess in guesses:
            result['guesses_tried'] += 1
            if probe_domain(guess, timeout=2.0):
                result['domain'] = guess
                result['source'] = 'dns_probe'
                return result

    # No domain found via DNS probing
    result['error'] = 'no_domain_found'
    return result


async def discover_domain_via_search(contractor: dict, brave_client=None) -> dict:
    """Discover a contractor's domain via Brave web search.

    More accurate than DNS probing because it finds the company's actual
    website rather than guessing from name patterns.

    Args:
        contractor: dict with 'name', 'dba', 'city', 'state'
        brave_client: BraveSearchClient instance (or None to create one)

    Returns:
        dict with domain, source, confidence
    """
    result = {
        'queried': True,
        'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'domain': None,
        'source': None,
        'search_url': None,
        'confidence': 0,
        'error': None,
    }

    if brave_client is None:
        try:
            from backend.brave_search import BraveSearchClient
            brave_client = BraveSearchClient()
        except ImportError:
            result['error'] = 'brave_search_not_available'
            return result

    if not brave_client.is_available():
        result['error'] = 'no_brave_api_key'
        return result

    import asyncio

    name = contractor.get('name', '')
    dba = contractor.get('dba', '')
    city = contractor.get('city', '')
    state = contractor.get('state', '')

    # Use DBA if available (often more recognizable)
    search_name = dba if dba and dba != name else name

    # Search for the company's official website
    queries = [
        f'"{search_name}" official website {city} {state}',
        f'"{search_name}" {state}',
    ]

    for query in queries:
        try:
            results = await brave_client.search(query, count=5)
        except Exception:
            continue

        for r in results:
            url = r.get('url', '')
            title = (r.get('title', '') + ' ' + r.get('description', '')).lower()
            domain = extract_domain_from_url(url)

            if not domain:
                continue

            # Skip known non-company domains
            skip_domains = {
                'facebook.com', 'linkedin.com', 'twitter.com', 'x.com',
                'yelp.com', 'bbb.org', 'glassdoor.com', 'indeed.com',
                'wikipedia.org', 'bloomberg.com', 'dnb.com', 'zoominfo.com',
                'opencorporates.com', 'usaspending.gov', 'sam.gov',
                'fpds.gov', 'google.com', 'youtube.com', 'instagram.com',
            }
            base = '.'.join(domain.split('.')[-2:])
            if base in skip_domains:
                continue

            # Check if the company name appears in the title/description
            name_words = [w.lower() for w in search_name.split() if len(w) > 2]
            name_words = [w for w in name_words if w not in STRIP_WORDS]
            matches = sum(1 for w in name_words if w in title)
            match_ratio = matches / max(len(name_words), 1)

            if match_ratio >= 0.3:  # At least 30% of name words match
                # Verify it resolves
                if probe_domain(domain, timeout=3.0):
                    confidence = int(min(match_ratio * 80 + 20, 100))
                    result['domain'] = domain
                    result['source'] = 'brave_search'
                    result['search_url'] = url
                    result['confidence'] = confidence
                    return result

    result['error'] = 'no_domain_found_via_search'
    return result
