#!/usr/bin/env python3
"""
Enrich DOE contractor data with Shodan intelligence.
Queries Shodan for each contractor by org name, caches results into contractors.json.

Requires: SHODAN_API_KEY in .env
Usage: python3 enrich_shodan.py [--force] [--limit N]
"""

import json
import os
import sys
import time
import re
import argparse
from collections import Counter

import shodan
from dotenv import load_dotenv


def extract_domain(url_or_name):
    """Extract a clean domain from a URL or company name."""
    if not url_or_name:
        return None
    # Remove protocol
    domain = re.sub(r'^https?://', '', url_or_name.strip())
    # Remove path
    domain = domain.split('/')[0]
    # Remove www.
    domain = re.sub(r'^www\.', '', domain)
    if '.' in domain and len(domain) > 3:
        return domain.lower()
    return None


def clean_org_name(name):
    """Clean contractor name for Shodan org search."""
    if not name:
        return None
    # Remove common suffixes
    cleaned = re.sub(
        r',?\s*(LLC|INC\.?|CORP\.?|CORPORATION|COMPANY|CO\.|L\.?L\.?C\.?|L\.?P\.?|LTD\.?|GROUP|HOLDINGS?|SERVICES?|SOLUTIONS?)\.?\s*$',
        '', name, flags=re.IGNORECASE
    ).strip().rstrip(',').strip()
    # Remove quotes
    cleaned = cleaned.strip('"').strip("'")
    if len(cleaned) < 3:
        return None
    return cleaned


def query_shodan_for_contractor(api, contractor, retries=2):
    """Query Shodan for a contractor. Returns enrichment dict or None."""
    result = {
        'queried': True,
        'query_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'total_hosts': 0,
        'top_ports': [],
        'top_services': [],
        'vulns': [],
        'domains_found': [],
        'sample_hosts': [],
        'technologies': [],
        'asns': [],
        'query_used': '',
    }

    # Strategy 1: Search by org name
    org_name = clean_org_name(contractor.get('name', ''))
    domain = extract_domain(contractor.get('url', ''))

    queries_to_try = []
    if org_name:
        queries_to_try.append(f'org:"{org_name}"')
    if domain:
        queries_to_try.append(f'hostname:{domain}')

    if not queries_to_try:
        result['error'] = 'no_searchable_identifier'
        return result

    for query in queries_to_try:
        for attempt in range(retries):
            try:
                # Use count with facets for summary (fast, efficient)
                facets = [
                    ('port', 10),
                    ('product', 10),
                    ('vuln', 20),
                    ('domain', 5),
                    ('asn', 5),
                ]
                count_result = api.count(query, facets=facets)

                if count_result['total'] == 0:
                    break  # Try next query

                result['total_hosts'] = count_result['total']
                result['query_used'] = query

                # Extract facets
                facet_data = count_result.get('facets', {})

                if 'port' in facet_data:
                    result['top_ports'] = [
                        {'port': item['value'], 'count': item['count']}
                        for item in facet_data['port']
                    ]

                if 'product' in facet_data:
                    result['top_services'] = [
                        {'name': item['value'], 'count': item['count']}
                        for item in facet_data['product']
                    ]

                if 'vuln' in facet_data:
                    result['vulns'] = [
                        {'cve': item['value'], 'count': item['count']}
                        for item in facet_data['vuln']
                    ]

                if 'domain' in facet_data:
                    result['domains_found'] = [
                        item['value'] for item in facet_data['domain']
                    ]

                if 'asn' in facet_data:
                    result['asns'] = [
                        item['value'] for item in facet_data['asn']
                    ]

                # Now get a small sample of actual hosts for detail
                time.sleep(1)  # Rate limit
                try:
                    search_result = api.search(query, limit=5)
                    for match in search_result.get('matches', [])[:5]:
                        host_info = {
                            'ip': match.get('ip_str', ''),
                            'port': match.get('port', 0),
                            'product': match.get('product', ''),
                            'version': match.get('version', ''),
                            'hostnames': match.get('hostnames', [])[:3],
                            'os': match.get('os', ''),
                            'transport': match.get('transport', ''),
                        }
                        # Extract SSL info if available
                        ssl = match.get('ssl', {})
                        if ssl:
                            cert = ssl.get('cert', {})
                            if cert:
                                host_info['ssl_issuer'] = cert.get('issuer', {}).get('O', '')
                                host_info['ssl_expires'] = cert.get('expires', '')

                        # Extract HTTP info if available
                        http = match.get('http', {})
                        if http:
                            host_info['http_title'] = http.get('title', '')
                            host_info['http_server'] = http.get('server', '')

                        result['sample_hosts'].append(host_info)

                except shodan.APIError:
                    pass  # Sample hosts are optional

                # Deduplicate technologies from services
                tech_set = set()
                for svc in result['top_services']:
                    if svc['name']:
                        tech_set.add(svc['name'])
                for host in result['sample_hosts']:
                    if host.get('product'):
                        tech_set.add(host['product'])
                    if host.get('http_server'):
                        tech_set.add(host['http_server'])
                result['technologies'] = sorted(tech_set)

                return result

            except shodan.APIError as e:
                err_msg = str(e)
                if 'rate limit' in err_msg.lower() or 'too many' in err_msg.lower():
                    wait = 2 ** (attempt + 1)
                    print(f'    Rate limited, waiting {wait}s...')
                    time.sleep(wait)
                    continue
                elif 'access denied' in err_msg.lower():
                    result['error'] = f'access_denied: {err_msg}'
                    return result
                else:
                    result['error'] = err_msg
                    if attempt == retries - 1:
                        return result
                    time.sleep(1)
                    continue
            except Exception as e:
                result['error'] = str(e)
                return result

    # No results from any query
    result['error'] = 'no_results'
    return result


def main():
    parser = argparse.ArgumentParser(description='Enrich contractors with Shodan data')
    parser.add_argument('--force', action='store_true', help='Re-query already enriched contractors')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of contractors to query (0=all)')
    args = parser.parse_args()

    load_dotenv('/Users/rstarzl/Documents/GitHub/DOE_RedTeam/.env')
    api_key = os.getenv('SHODAN_API_KEY')
    if not api_key:
        print('ERROR: SHODAN_API_KEY not found in .env')
        sys.exit(1)

    api = shodan.Shodan(api_key)

    # Verify API key
    try:
        info = api.info()
        print(f'Shodan API connected. Plan: {info.get("plan", "unknown")}')
        print(f'  Scan credits: {info.get("scan_credits", "N/A")}')
        print(f'  Query credits: {info.get("query_credits", "N/A")}')
    except shodan.APIError as e:
        print(f'ERROR: Shodan API key invalid: {e}')
        sys.exit(1)

    # Load existing data
    json_path = '/Users/rstarzl/Documents/GitHub/DOE_RedTeam/frontend/static/contractors.json'
    print(f'\nLoading {json_path}...')
    with open(json_path, 'r') as f:
        data = json.load(f)

    contractors = data['contractors']
    total = len(contractors)
    print(f'  {total} contractors loaded')

    # Determine which contractors need querying
    to_query = []
    for idx, c in enumerate(contractors):
        if args.force or not c.get('shodan'):
            to_query.append(idx)

    if args.limit > 0:
        to_query = to_query[:args.limit]

    already_done = total - len(to_query)
    print(f'  {already_done} already enriched, {len(to_query)} to query')

    if not to_query:
        print('Nothing to do!')
        return

    # Estimate time
    est_minutes = len(to_query) * 2 / 60  # ~2 seconds per query (count + search + rate limit)
    print(f'  Estimated time: ~{est_minutes:.0f} minutes')
    print()

    # Query Shodan for each contractor
    success = 0
    found = 0
    errors = 0
    start_time = time.time()

    for i, idx in enumerate(to_query):
        c = contractors[idx]
        progress = f'[{i+1}/{len(to_query)}]'
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        eta = (len(to_query) - i - 1) / rate if rate > 0 else 0

        print(f'{progress} {c["name"][:50]:50s}', end=' ', flush=True)

        result = query_shodan_for_contractor(api, c)
        contractors[idx]['shodan'] = result

        if result.get('error'):
            if result['error'] == 'no_results':
                print(f'  -- no results')
            elif result['error'] == 'no_searchable_identifier':
                print(f'  -- no name/domain')
            else:
                print(f'  !! {result["error"][:40]}')
                errors += 1
        elif result['total_hosts'] > 0:
            ports = [str(p['port']) for p in result['top_ports'][:5]]
            vulns = len(result['vulns'])
            print(f'  OK  hosts={result["total_hosts"]}  ports=[{",".join(ports)}]  vulns={vulns}')
            found += 1
        else:
            print(f'  -- 0 hosts')

        success += 1

        # Save progress every 50 contractors
        if (i + 1) % 50 == 0:
            print(f'\n  Saving progress... ({i+1}/{len(to_query)}, ETA: {eta/60:.1f} min)\n')
            with open(json_path, 'w') as f:
                json.dump(data, f, separators=(',', ':'))

        # Rate limit: Shodan Freelancer = 1 req/sec, we do 2 requests per contractor
        time.sleep(1)

    # Final save
    print(f'\nSaving final results...')
    with open(json_path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    elapsed_total = time.time() - start_time
    print(f'\nDone! Queried {success} contractors in {elapsed_total/60:.1f} minutes')
    print(f'  Found Shodan data: {found}')
    print(f'  No results: {success - found - errors}')
    print(f'  Errors: {errors}')

    # Summary stats
    all_ports = Counter()
    all_vulns = Counter()
    total_hosts_sum = 0
    for c in contractors:
        s = c.get('shodan', {})
        total_hosts_sum += s.get('total_hosts', 0)
        for p in s.get('top_ports', []):
            all_ports[p['port']] += p['count']
        for v in s.get('vulns', []):
            all_vulns[v['cve']] += v['count']

    print(f'\nAggregate Shodan Intelligence:')
    print(f'  Total exposed hosts: {total_hosts_sum:,}')
    print(f'  Top ports: {all_ports.most_common(10)}')
    print(f'  Top CVEs: {all_vulns.most_common(10)}')


if __name__ == '__main__':
    main()
