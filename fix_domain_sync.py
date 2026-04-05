#!/usr/bin/env python3
"""Sync AI research domains into domain_discovery for all mismatches."""

import json
from osint.ai_research import apply_domain_cascade

with open('frontend/static/contractors.json') as f:
    d = json.load(f)

fixed = 0
details = []

for i, c in enumerate(d['contractors']):
    ar = c.get('osint', {}).get('ai_research', {})
    dd = c.get('osint', {}).get('domain_discovery', {})

    ai_domain = ar.get('current_domain', '')
    dd_domain = dd.get('domain', '')
    ai_conf = ar.get('domain_confidence', 0)

    if ai_domain and dd_domain and ai_domain != dd_domain and ai_conf >= 70:
        changed = apply_domain_cascade(c, ai_domain, 'ai_research_sync')
        if changed:
            fixed += 1
            details.append(f'  [{i}] {c["name"][:40]:40s} {dd_domain:25s} -> {ai_domain}')

print(f'Fixed {fixed} domain mismatches')
for line in details:
    print(line)

with open('frontend/static/contractors.json', 'w') as f:
    json.dump(d, f, separators=(',', ':'))

# Verify
c10 = d['contractors'][10]
dd10 = c10.get('osint', {}).get('domain_discovery', {})
print(f'\nVerify Triad: {dd10.get("domain")} (source: {dd10.get("source")})')
