#!/usr/bin/env python3
"""
Multi-layer OSINT enrichment pipeline for DOE contractor intelligence.

Orchestrates 5 enrichment layers in priority order:
1. Enhanced Shodan (5 query patterns)
2. Domain Discovery (find domains for contractors without URLs)
3. DNS Intelligence (MX, SPF, TXT, NS records)
4. Certificate Transparency (crt.sh subdomain enumeration)
5. Web Fingerprinting (HTTP headers, HTML tech detection)

Usage:
    python -m osint.pipeline [--layers all|shodan|dns|ct|web|domain]
                             [--limit N] [--force] [--skip-shodan]
"""

import argparse
import json
import os
import sys
import time
from collections import Counter

import shodan
from dotenv import load_dotenv

from osint.domain_discovery import discover_domain, discover_domain_via_search
from osint.domain_verify import verify_domain
from osint.dns_intel import enrich_dns
from osint.ct_logs import enrich_ct
from osint.web_fingerprint import enrich_web
from osint.enhanced_shodan import enrich_shodan
from osint.asn_enum import enrich_asn
from osint.nvd_cvss import enrich_nvd_cvss, collect_cve_ids
from osint.service_risk import classify_services
from osint.onprem_network import identify_onprem_network
from osint.shodan_ip import enrich_contractor_ips
from osint.ai_research import research_contractor, needs_ai_research, apply_domain_cascade


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, 'frontend', 'static', 'contractors.json')
ENV_PATH = os.path.join(BASE_DIR, '.env')


def load_data():
    """Load contractor JSON data."""
    with open(JSON_PATH, 'r') as f:
        return json.load(f)


def save_data(data):
    """Save contractor JSON data."""
    with open(JSON_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))


def needs_layer(contractor, layer_name, force=False):
    """Check if a contractor needs a particular enrichment layer."""
    if force:
        return True
    osint = contractor.get('osint', {})
    layer_data = osint.get(layer_name)
    if not layer_data:
        return True
    if not layer_data.get('queried'):
        return True
    return False


def get_contractor_domain(contractor):
    """Get the best known domain for a contractor.

    Priority order:
    1. AI-researched domain (if validated via DNS probe) — highest confidence
    2. Domain discovery result (brave_search, dns_probe, csv_url)
    3. Original URL from CSV
    """
    osint = contractor.get('osint', {})

    # Priority 1: AI research found a domain with high confidence
    # Trust AI at >= 80% even without DNS validation (DNS probe can fail for
    # CDN-fronted domains, geo-restricted sites, or rate-limited servers)
    ar = osint.get('ai_research', {})
    if ar.get('current_domain'):
        if ar.get('domain_validated') or ar.get('domain_confidence', 0) >= 80:
            return ar['current_domain']

    # Priority 2: Domain discovery
    dd = osint.get('domain_discovery', {})
    if dd.get('domain'):
        return dd['domain']

    # Priority 3: Original URL from CSV
    from osint.domain_discovery import extract_domain_from_url
    url = contractor.get('url', '')
    if url:
        return extract_domain_from_url(url)
    return None


def run_layer_domain_discovery(contractors, force=False, limit=0):
    """Layer 2: Domain Discovery."""
    print('\n' + '=' * 60)
    print('LAYER: Domain Discovery')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'domain_discovery', force)
    ]
    if limit > 0:
        to_process = to_process[:limit]

    found = 0
    for idx, (i, c) in enumerate(to_process):
        print(f'  [{idx+1}/{len(to_process)}] {c["name"][:50]:50s}', end=' ', flush=True)

        result = discover_domain(c)
        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['domain_discovery'] = result

        if result['domain']:
            print(f'  -> {result["domain"]} ({result["source"]})')
            found += 1
        else:
            print(f'  -- no domain ({result.get("guesses_tried", 0)} tried)')

    print(f'\n  Domain Discovery: {found}/{len(to_process)} domains found')
    return found


def run_layer_domain_search(contractors, force=False, limit=0):
    """Layer: Brave Search domain validation — find correct domains via web search.

    Targets contractors with:
    - No domain discovered yet
    - Low verification confidence (< 50%)
    - Domain from dns_probe (heuristic, error-prone)
    """
    import asyncio
    from backend.brave_search import BraveSearchClient

    print('\n' + '=' * 60)
    print('LAYER: Brave Search Domain Validation')
    print('=' * 60)

    brave = BraveSearchClient()
    if not brave.is_available():
        print('  BRAVE_SEARCH_API_KEY not set. Skipping.')
        return 0

    # Find contractors needing domain validation
    to_process = []
    for i, c in enumerate(contractors):
        if force:
            to_process.append((i, c))
            continue

        osint = c.get('osint', {})
        dd = osint.get('domain_discovery', {})
        dv = osint.get('domain_verify', {})

        # Already validated via search
        if dd.get('source') == 'brave_search':
            continue

        # Needs validation if: no domain, low confidence, or dns_probe source
        needs_it = (
            not dd.get('domain')
            or dd.get('source') == 'dns_probe'
            or (dv.get('confidence', 100) < 50 and dv.get('queried'))
        )
        if needs_it:
            to_process.append((i, c))

    if limit > 0:
        to_process = to_process[:limit]

    if not to_process:
        print('  No contractors need domain search validation.')
        return 0

    print(f'  Processing {len(to_process)} contractors...')

    found = 0
    upgraded = 0

    async def process_all():
        nonlocal found, upgraded
        for idx, (i, c) in enumerate(to_process):
            old_domain = c.get('osint', {}).get('domain_discovery', {}).get('domain', '')
            print(f'  [{idx+1}/{len(to_process)}] {c["name"][:45]:45s}', end=' ', flush=True)

            result = await discover_domain_via_search(c, brave_client=brave)
            c.setdefault('osint', {})['domain_discovery_search'] = result

            if result['domain']:
                found += 1
                if result['domain'] != old_domain:
                    # Upgrade: replace the old domain with the search-validated one
                    c['osint']['domain_discovery']['domain'] = result['domain']
                    c['osint']['domain_discovery']['source'] = 'brave_search'
                    c['osint']['domain_discovery']['search_url'] = result.get('search_url', '')
                    upgraded += 1

                    # CASCADE: invalidate downstream layers that used the old domain
                    # These will be re-enriched on next pipeline run with the correct domain
                    cascade_layers = ['domain_verify', 'dns', 'ct', 'web']
                    invalidated = []
                    for layer in cascade_layers:
                        if layer in c['osint'] and c['osint'][layer].get('queried'):
                            c['osint'][layer]['queried'] = False
                            c['osint'][layer]['_invalidated_by'] = f'domain_upgrade:{old_domain}->{result["domain"]}'
                            invalidated.append(layer)

                    cascade_info = f' [cascade: {",".join(invalidated)}]' if invalidated else ''
                    print(f'  UPGRADED {old_domain or "none"} -> {result["domain"]} (conf={result["confidence"]}%){cascade_info}')
                else:
                    print(f'  CONFIRMED {result["domain"]} (conf={result["confidence"]}%)')
            else:
                print(f'  -- no domain found via search')

            # Save every 50
            if (idx + 1) % 50 == 0:
                print(f'\n  Saving progress ({idx+1}/{len(to_process)})...\n')
                save_data({'contractors': contractors,
                           **{k: v for k, v in load_data().items() if k != 'contractors'}})

            await asyncio.sleep(0.5)  # Rate limit

    asyncio.run(process_all())
    print(f'\n  Domain Search: {found} found, {upgraded} upgraded from {len(to_process)} checked')
    return upgraded


def run_layer_enhanced_shodan(contractors, api, force=False, limit=0):
    """Layer 1: Enhanced Shodan with 5 query patterns."""
    print('\n' + '=' * 60)
    print('LAYER: Enhanced Shodan')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'enhanced_shodan', force)
    ]
    if limit > 0:
        to_process = to_process[:limit]

    found = 0
    for idx, (i, c) in enumerate(to_process):
        print(f'  [{idx+1}/{len(to_process)}] {c["name"][:50]:50s}', end=' ', flush=True)

        domain = get_contractor_domain(c)
        result = enrich_shodan(api, c, domain=domain)
        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['enhanced_shodan'] = result

        if result.get('total_hosts', 0) > 0:
            ports = [str(p['port']) for p in result.get('top_ports', [])[:5]]
            print(f'  OK hosts={result["total_hosts"]} ports=[{",".join(ports)}] via {result.get("query_used","")[:30]}')
            found += 1
        else:
            print(f'  -- no results')

        # Save every 50
        if (idx + 1) % 50 == 0:
            print(f'\n  Saving progress ({idx+1}/{len(to_process)})...\n')
            save_data({'contractors': contractors, **{k: v for k, v in load_data().items() if k != 'contractors'}})

        time.sleep(1)  # Rate limit

    print(f'\n  Enhanced Shodan: {found}/{len(to_process)} with results')
    return found


def run_layer_domain_verification(contractors, force=False, limit=0):
    """Layer 2b: Domain Verification — confidence scoring."""
    print('\n' + '=' * 60)
    print('LAYER: Domain Verification')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'domain_verify', force) and get_contractor_domain(c)
    ]
    if limit > 0:
        to_process = to_process[:limit]

    print(f'  {len(to_process)} domains to verify')
    verified = 0
    parking = 0
    unverified = 0

    for idx, (i, c) in enumerate(to_process):
        domain = get_contractor_domain(c)
        print(f'  [{idx+1}/{len(to_process)}] {c["name"][:35]:35s} -> {domain:30s}', end=' ', flush=True)

        dns_data = c.get('osint', {}).get('dns')
        ct_data = c.get('osint', {}).get('ct')
        ai_research = c.get('osint', {}).get('ai_research')

        result = verify_domain(c['name'], domain, dba=c.get('dba', ''),
                               dns_data=dns_data, ct_data=ct_data,
                               ai_research=ai_research)

        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['domain_verify'] = result

        verdict = result['verdict']
        conf = result['confidence']
        if result['is_parking']:
            print(f'  PARKING  conf={conf} "{result["page_title"][:30]}"')
            parking += 1
        elif verdict == 'verified':
            print(f'  VERIFIED conf={conf}')
            verified += 1
        elif verdict == 'likely':
            print(f'  LIKELY   conf={conf}')
            verified += 1
        elif verdict == 'uncertain':
            print(f'  UNCERTAIN conf={conf}')
        else:
            print(f'  UNVERIFIED conf={conf}')
            unverified += 1

        time.sleep(0.5)  # Rate limit HTTP fetches

        if (idx + 1) % 100 == 0:
            print(f'\n  Saving progress ({idx+1}/{len(to_process)})...\n')
            save_data({'contractors': contractors, **{k: v for k, v in load_data().items() if k != 'contractors'}})

    print(f'\n  Domain Verification: {verified} verified/likely, {parking} parking, {unverified} unverified')
    return verified


def run_layer_asn(contractors, force=False, limit=0):
    """Layer 6: ASN/IP enumeration via InternetDB."""
    print('\n' + '=' * 60)
    print('LAYER: ASN / IP Enumeration')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'asn', force)
        and get_contractor_domain(c)
        and c.get('osint', {}).get('dns', {}).get('a_records')
        # Only process verified/likely domains
        and c.get('osint', {}).get('domain_verify', {}).get('verdict', '') in ('verified', 'likely', '')
    ]
    if limit > 0:
        to_process = to_process[:limit]

    print(f'  {len(to_process)} contractors with verified IPs to enumerate')
    found = 0

    for idx, (i, c) in enumerate(to_process):
        domain = get_contractor_domain(c)
        a_records = c.get('osint', {}).get('dns', {}).get('a_records', [])
        print(f'  [{idx+1}/{len(to_process)}] {domain:35s} ({len(a_records)} IPs)', end=' ', flush=True)

        result = enrich_asn(domain, a_records)
        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['asn'] = result

        if result.get('total_ports', 0) > 0:
            asn_info = result.get('asn', {})
            asn_str = asn_info.get('number', '?')
            print(f'  OK  {asn_str} ports={result["total_ports"]} vulns={result["total_vulns"]}')
            found += 1
        elif result.get('error'):
            print(f'  !! {result["error"][:30]}')
        else:
            print(f'  -- no data')

        if (idx + 1) % 100 == 0:
            print(f'\n  Saving progress ({idx+1}/{len(to_process)})...\n')
            save_data({'contractors': contractors, **{k: v for k, v in load_data().items() if k != 'contractors'}})

    print(f'\n  ASN Enumeration: {found}/{len(to_process)} with port/vuln data')
    return found


def run_layer_dns(contractors, force=False, limit=0):
    """Layer 3: DNS Intelligence."""
    print('\n' + '=' * 60)
    print('LAYER: DNS Intelligence')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'dns', force) and get_contractor_domain(c)
    ]
    if limit > 0:
        to_process = to_process[:limit]

    print(f'  {len(to_process)} contractors with domains to query')
    found = 0

    for idx, (i, c) in enumerate(to_process):
        domain = get_contractor_domain(c)
        print(f'  [{idx+1}/{len(to_process)}] {domain:40s}', end=' ', flush=True)

        result = enrich_dns(domain)
        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['dns'] = result

        tech = result.get('technologies_detected', [])
        if tech:
            print(f'  OK  {", ".join(tech[:4])}')
            found += 1
        elif result.get('error'):
            print(f'  !! {result["error"][:40]}')
        else:
            print(f'  -- no tech detected')

    print(f'\n  DNS Intelligence: {found}/{len(to_process)} with tech signals')
    return found


def run_layer_ct(contractors, force=False, limit=0):
    """Layer 4: Certificate Transparency logs."""
    print('\n' + '=' * 60)
    print('LAYER: Certificate Transparency')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'ct', force) and get_contractor_domain(c)
    ]
    if limit > 0:
        to_process = to_process[:limit]

    print(f'  {len(to_process)} contractors with domains to query')
    found = 0

    for idx, (i, c) in enumerate(to_process):
        domain = get_contractor_domain(c)
        print(f'  [{idx+1}/{len(to_process)}] {domain:40s}', end=' ', flush=True)

        result = enrich_ct(domain)
        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['ct'] = result

        subs = result.get('subdomain_count', 0)
        hints = result.get('infrastructure_hints', {})
        hint_count = sum(len(v) for v in hints.values())
        if subs > 0:
            print(f'  OK  {subs} subdomains, {hint_count} infra hints')
            found += 1
        elif result.get('error'):
            print(f'  !! {result["error"][:40]}')
        else:
            print(f'  -- no certs found')

        # crt.sh rate limiting
        time.sleep(2)

    print(f'\n  CT Logs: {found}/{len(to_process)} with subdomains')
    return found


def run_layer_web(contractors, force=False, limit=0):
    """Layer 5: Web Fingerprinting."""
    print('\n' + '=' * 60)
    print('LAYER: Web Fingerprinting')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'web', force) and get_contractor_domain(c)
    ]
    if limit > 0:
        to_process = to_process[:limit]

    print(f'  {len(to_process)} contractors with domains to fingerprint')
    found = 0

    for idx, (i, c) in enumerate(to_process):
        domain = get_contractor_domain(c)
        print(f'  [{idx+1}/{len(to_process)}] {domain:40s}', end=' ', flush=True)

        result = enrich_web(domain)
        if 'osint' not in contractors[i]:
            contractors[i]['osint'] = {}
        contractors[i]['osint']['web'] = result

        tech = result.get('technologies_detected', [])
        if tech:
            print(f'  OK  {", ".join(tech[:4])}')
            found += 1
        elif result.get('error'):
            print(f'  !! {result["error"][:40]}')
        else:
            print(f'  -- no tech detected')

        time.sleep(0.5)

    print(f'\n  Web Fingerprinting: {found}/{len(to_process)} with tech signals')
    return found


def run_layer_onprem(contractors, force=False, limit=0):
    """Identify on-premises vs cloud infrastructure for each contractor."""
    print(f'\n--- Layer: On-Premises Network Identification ---')
    processed = 0
    with_onprem = 0
    targets = contractors[:limit] if limit else contractors

    for i, c in enumerate(targets):
        if not needs_layer(c, 'onprem_network', force):
            continue
        result = identify_onprem_network(c)
        c.setdefault('osint', {})['onprem_network'] = result
        processed += 1
        if result['on_prem_count'] > 0:
            with_onprem += 1

        if (i + 1) % 100 == 0:
            print(f'  Progress: {i + 1}/{len(targets)}, on-prem found: {with_onprem}')

    print(f'  Processed: {processed}, with on-prem IPs: {with_onprem}')


def run_layer_service_risk(contractors, force=False, limit=0):
    """Classify dangerous services for each contractor."""
    print(f'\n--- Layer: Service Risk Classification ---')
    processed = 0
    flagged = 0
    targets = contractors[:limit] if limit else contractors

    for c in targets:
        if not needs_layer(c, 'service_risk', force):
            continue
        result = classify_services(c)
        c.setdefault('osint', {})['service_risk'] = result
        processed += 1
        if result['max_danger'] != 'none':
            flagged += 1

    print(f'  Processed: {processed}, Flagged: {flagged} with dangerous services')


def run_layer_shodan_ip(contractors, api, force=False, limit=0):
    """Per-IP Shodan host enrichment for on-prem IPs."""
    print('\n' + '=' * 60)
    print('LAYER: Per-IP Shodan Host Intelligence')
    print('=' * 60)

    to_process = [
        (i, c) for i, c in enumerate(contractors)
        if needs_layer(c, 'shodan_ip', force)
        and c.get('osint', {}).get('onprem_network', {}).get('on_prem_ips')
    ]
    if limit > 0:
        to_process = to_process[:limit]

    if not to_process:
        print('  No contractors to process.')
        return 0

    print(f'  Processing {len(to_process)} contractors with on-prem IPs...')

    # Shared caches across all contractors (deduplicates IP lookups)
    ip_cache = {}
    idb_cache = {}
    enriched = 0

    for idx, (i, c) in enumerate(to_process):
        name = c['name'][:45]
        ips = c.get('osint', {}).get('onprem_network', {}).get('on_prem_ips', [])
        print(f'  [{idx+1}/{len(to_process)}] {name:45s} ({len(ips)} IPs)', end=' ', flush=True)

        result = enrich_contractor_ips(
            api, c,
            ip_cache=ip_cache,
            internetdb_cache=idb_cache,
            delay=1.0,
        )

        c.setdefault('osint', {})['shodan_ip'] = result

        n_hosts = result.get('ips_enriched', 0)
        n_crit = len(result.get('aggregate', {}).get('critical_findings', []))
        if n_hosts > 0:
            print(f'  OK hosts={n_hosts} critical={n_crit}')
            enriched += 1
        else:
            print(f'  -- no exposed hosts')

        # Save every 25 contractors
        if (idx + 1) % 25 == 0:
            print(f'\n  Saving progress ({idx+1}/{len(to_process)}), '
                  f'IP cache: {len(ip_cache)} IPs...\n')
            save_data({'contractors': contractors,
                       **{k: v for k, v in load_data().items() if k != 'contractors'}})

    print(f'\n  Per-IP Shodan: {enriched}/{len(to_process)} with exposed hosts')
    print(f'  Total unique IPs queried: {len(ip_cache)}')
    return enriched


def run_layer_nvd(contractors, force=False, limit=0):
    """Enrich CVEs with CVSS scores from NVD."""
    print(f'\n--- Layer: NVD CVSS Scoring ---')

    # First: build a global cache of already-known scores
    global_cache = {}
    for c in contractors:
        existing = c.get('osint', {}).get('nvd_cvss', {}).get('scores', {})
        global_cache.update(existing)

    processed = 0
    scored = 0
    targets = contractors[:limit] if limit else contractors

    for i, c in enumerate(targets):
        if not needs_layer(c, 'nvd_cvss', force):
            continue

        cve_ids = collect_cve_ids(c)
        if not cve_ids:
            # Mark as queried with no CVEs
            c.setdefault('osint', {})['nvd_cvss'] = {
                'queried': True,
                'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'total_cves': 0,
                'scored_cves': 0,
                'scores': {},
                'summary': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'none': 0, 'unknown': 0},
                'max_severity': 'none',
                'max_score': 0.0,
                'error': None,
            }
            continue

        result = enrich_nvd_cvss(cve_ids, existing_scores=global_cache)

        # Update global cache with new scores
        global_cache.update(result.get('scores', {}))

        c.setdefault('osint', {})['nvd_cvss'] = result
        processed += 1
        scored += result.get('scored_cves', 0)

        if (i + 1) % 10 == 0:
            print(f'  Progress: {i + 1}/{len(targets)} contractors, {scored} CVEs scored')

    print(f'  Processed: {processed} contractors, {scored} total CVE scores')
    print(f'  Global cache: {len(global_cache)} unique CVEs')


def run_layer_ai_research(contractors, force=False, limit=0):
    """Layer: AI Research — web search + LLM reasoning for domain/status/brief."""
    import asyncio
    from backend.glm_client import GLMClient
    from backend.brave_search import BraveSearchClient

    print('\n' + '=' * 60)
    print('LAYER: AI Research (GLM-5.3 + Brave Search)')
    print('=' * 60)

    llm = GLMClient()
    brave = BraveSearchClient()

    if not llm.is_available():
        print('  OPENROUTER_API_KEY not set. Skipping.')
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
        print('  WARNING: Brave Search unavailable (no BRAVE_SEARCH_API_KEY). LLM will run without web context.')

    researched = 0
    upgraded = 0

    async def process_all():
        nonlocal researched, upgraded
        for idx, (i, c) in enumerate(to_process):
            name = c['name'][:45]
            print(f'  [{idx+1}/{len(to_process)}] {name:45s}', end=' ', flush=True)

            result = await research_contractor(c, llm, brave)
            c.setdefault('osint', {})['ai_research'] = result

            if result.get('error'):
                print(f'  ERROR: {result["error"][:50]}')
            else:
                researched += 1
                status = result.get('company_status', 'unknown')
                domain = result.get('current_domain', '')

                # Domain cascade if AI found a different, validated domain
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


def print_summary(contractors):
    """Print aggregate summary of all OSINT data."""
    print('\n' + '=' * 60)
    print('AGGREGATE OSINT SUMMARY')
    print('=' * 60)

    domains_found = sum(1 for c in contractors if get_contractor_domain(c))
    shodan_hits = sum(1 for c in contractors
                      if c.get('osint', {}).get('enhanced_shodan', {}).get('total_hosts', 0) > 0)
    dns_hits = sum(1 for c in contractors
                   if c.get('osint', {}).get('dns', {}).get('technologies_detected'))
    ct_hits = sum(1 for c in contractors
                  if c.get('osint', {}).get('ct', {}).get('subdomain_count', 0) > 0)
    web_hits = sum(1 for c in contractors
                   if c.get('osint', {}).get('web', {}).get('technologies_detected'))

    # Any signal at all
    any_signal = sum(1 for c in contractors if (
        c.get('osint', {}).get('enhanced_shodan', {}).get('total_hosts', 0) > 0 or
        c.get('osint', {}).get('dns', {}).get('technologies_detected') or
        c.get('osint', {}).get('ct', {}).get('subdomain_count', 0) > 0 or
        c.get('osint', {}).get('web', {}).get('technologies_detected') or
        c.get('shodan', {}).get('total_hosts', 0) > 0
    ))

    total = len(contractors)
    print(f'  Total contractors:       {total}')
    print(f'  Domains discovered:      {domains_found} ({domains_found*100//total}%)')
    print(f'  Enhanced Shodan hits:    {shodan_hits} ({shodan_hits*100//total}%)')
    print(f'  DNS intelligence hits:   {dns_hits} ({dns_hits*100//total}%)')
    print(f'  CT log hits:             {ct_hits} ({ct_hits*100//total}%)')
    print(f'  Web fingerprint hits:    {web_hits} ({web_hits*100//total}%)')
    print(f'  ANY signal:              {any_signal} ({any_signal*100//total}%)')

    # Top mail providers
    mail_providers = Counter()
    for c in contractors:
        mp = c.get('osint', {}).get('dns', {}).get('mail_provider', '')
        if mp and mp != 'Unknown':
            mail_providers[mp] += 1
    if mail_providers:
        print(f'\n  Top Email Providers:')
        for provider, count in mail_providers.most_common(10):
            print(f'    {count:4d} - {provider}')

    # Top DNS providers
    dns_providers = Counter()
    for c in contractors:
        dp = c.get('osint', {}).get('dns', {}).get('dns_provider', '')
        if dp and dp != 'Unknown':
            dns_providers[dp] += 1
    if dns_providers:
        print(f'\n  Top DNS Providers:')
        for provider, count in dns_providers.most_common(10):
            print(f'    {count:4d} - {provider}')


def main():
    parser = argparse.ArgumentParser(description='Multi-layer OSINT enrichment pipeline')
    parser.add_argument('--layers', default='all',
                        help='Comma-separated layers: all,shodan,domain,domain_search,verify,dns,ct,web,asn,onprem,service_risk,shodan_ip,nvd,ai_research')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit contractors per layer (0=all)')
    parser.add_argument('--force', action='store_true',
                        help='Re-run layers even if already enriched')
    parser.add_argument('--skip-shodan', action='store_true',
                        help='Skip Shodan layer (requires API key)')
    args = parser.parse_args()

    layers = set(args.layers.split(','))
    run_all = 'all' in layers

    # Load env and data
    load_dotenv(ENV_PATH)
    data = load_data()
    contractors = data['contractors']
    print(f'Loaded {len(contractors)} contractors')

    # Initialize Shodan if needed
    api = None
    if (run_all or 'shodan' in layers or 'shodan_ip' in layers) and not args.skip_shodan:
        api_key = os.getenv('SHODAN_API_KEY')
        if api_key:
            try:
                api = shodan.Shodan(api_key)
                info = api.info()
                print(f'Shodan API connected. Plan: {info.get("plan", "unknown")}')
            except shodan.APIError as e:
                print(f'Shodan API error: {e}. Skipping Shodan layer.')
                api = None
        else:
            print('No SHODAN_API_KEY in .env. Skipping Shodan layer.')

    start = time.time()

    # Run layers in priority order
    if run_all or 'domain' in layers:
        run_layer_domain_discovery(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'domain_search' in layers:
        run_layer_domain_search(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'verify' in layers:
        run_layer_domain_verification(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if (run_all or 'shodan' in layers) and api:
        run_layer_enhanced_shodan(contractors, api, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'dns' in layers:
        run_layer_dns(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'ct' in layers:
        run_layer_ct(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'web' in layers:
        run_layer_web(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'asn' in layers:
        run_layer_asn(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'onprem' in layers:
        run_layer_onprem(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'service_risk' in layers:
        run_layer_service_risk(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if (run_all or 'shodan_ip' in layers) and api:
        run_layer_shodan_ip(contractors, api, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'nvd' in layers:
        run_layer_nvd(contractors, force=args.force, limit=args.limit)
        save_data(data)

    if run_all or 'ai_research' in layers:
        run_layer_ai_research(contractors, force=args.force, limit=args.limit)
        save_data(data)

    # Final save and summary
    save_data(data)
    elapsed = time.time() - start
    print(f'\nPipeline complete in {elapsed/60:.1f} minutes')
    print_summary(contractors)


if __name__ == '__main__':
    main()
