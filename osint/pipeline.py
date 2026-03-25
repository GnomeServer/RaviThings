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

from osint.domain_discovery import discover_domain
from osint.dns_intel import enrich_dns
from osint.ct_logs import enrich_ct
from osint.web_fingerprint import enrich_web
from osint.enhanced_shodan import enrich_shodan


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
    """Get the best known domain for a contractor."""
    # Check if domain discovery already found one
    dd = contractor.get('osint', {}).get('domain_discovery', {})
    if dd.get('domain'):
        return dd['domain']
    # Check original URL
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
                        help='Comma-separated layers to run: all,shodan,domain,dns,ct,web')
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
    if (run_all or 'shodan' in layers) and not args.skip_shodan:
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

    # Final save and summary
    save_data(data)
    elapsed = time.time() - start
    print(f'\nPipeline complete in {elapsed/60:.1f} minutes')
    print_summary(contractors)


if __name__ == '__main__':
    main()
