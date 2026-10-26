"""
Certificate Transparency log enrichment via crt.sh.

Queries crt.sh to discover subdomains for a given domain and categorises
them by infrastructure role (VPN, email, dev/CI, cloud, auth).
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Category keywords (matched case-insensitively against subdomain labels)
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "vpn": ["vpn", "remote", "gateway"],
    "email": ["mail", "owa", "exchange", "smtp", "imap", "pop"],
    "dev_ci": [
        "jenkins", "gitlab", "jira", "confluence", "bamboo",
        "ci", "cd", "dev", "staging",
    ],
    "cloud": ["aws", "azure", "gcp", "cloud"],
    "auth": ["sso", "auth", "login", "adfs", "okta", "idp"],
}

_CRT_SH_URL = "https://crt.sh/"
_MAX_SUBDOMAINS = 50
_TOP_ISSUERS = 5
_REQUEST_TIMEOUT = 15  # seconds
_RETRY_WAIT = 5  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_empty_result(domain: str, error: str | None = None) -> dict[str, Any]:
    """Return a result dict with empty/default values."""
    return {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "total_certs": 0,
        "unique_subdomains": [],
        "subdomain_count": 0,
        "infrastructure_hints": {
            "vpn": [],
            "email": [],
            "dev_ci": [],
            "cloud": [],
            "auth": [],
        },
        "top_issuers": [],
        "error": error,
    }


def _extract_subdomains(entries: list[dict]) -> set[str]:
    """Extract unique, non-wildcard subdomains from crt.sh JSON entries."""
    subdomains: set[str] = set()
    for entry in entries:
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            name = name.strip().lower()
            if name and "*" not in name:
                subdomains.add(name)
    return subdomains


def _categorise_subdomains(
    subdomains: set[str],
) -> dict[str, list[str]]:
    """Bin subdomains into infrastructure categories."""
    hints: dict[str, list[str]] = {cat: [] for cat in _CATEGORY_KEYWORDS}
    for sub in sorted(subdomains):
        sub_lower = sub.lower()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in sub_lower for kw in keywords):
                hints[category].append(sub)
    return hints


def _top_issuers(entries: list[dict], n: int = _TOP_ISSUERS) -> list[dict[str, Any]]:
    """Return the *n* most common certificate issuers."""
    counter: Counter[str] = Counter()
    for entry in entries:
        issuer = entry.get("issuer_name", "").strip()
        if issuer:
            counter[issuer] += 1
    return [
        {"issuer": issuer, "count": count}
        for issuer, count in counter.most_common(n)
    ]


def _fetch_crt_sh(domain: str, max_retries: int = 3) -> requests.Response:
    """
    Query crt.sh with automatic retry on transient failures.

    Retries on HTTP 429 (rate-limit), connection drops (ChunkedEncodingError),
    and other transient errors. crt.sh is a free public service that frequently
    drops connections under load.
    """
    params = {"q": f"%.{domain}", "output": "json"}

    for attempt in range(max_retries):
        try:
            resp = requests.get(_CRT_SH_URL, params=params, timeout=_REQUEST_TIMEOUT)

            if resp.status_code == 429:
                time.sleep(_RETRY_WAIT * (attempt + 1))
                continue

            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as exc:
            if attempt < max_retries - 1:
                time.sleep(_RETRY_WAIT * (attempt + 1))
                continue
            raise

    # Final attempt (shouldn't reach here, but safety net)
    return requests.get(_CRT_SH_URL, params=params, timeout=_REQUEST_TIMEOUT)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_ct(domain: str) -> dict[str, Any]:
    """
    Query Certificate Transparency logs for *domain* via crt.sh.

    Parameters
    ----------
    domain:
        The base domain to search (e.g. ``"example.com"``).

    Returns
    -------
    dict
        A structured result containing discovered subdomains, infrastructure
        hints, top certificate issuers, and any error encountered.
    """
    try:
        resp = _fetch_crt_sh(domain)
        entries: list[dict] = resp.json()
    except (
        requests.ConnectionError,
        requests.Timeout,
        requests.HTTPError,
        requests.JSONDecodeError,
        requests.exceptions.ChunkedEncodingError,
    ) as exc:
        return _build_empty_result(domain, error=str(exc))

    subdomains = _extract_subdomains(entries)
    hints = _categorise_subdomains(subdomains)
    issuers = _top_issuers(entries)

    sorted_subdomains = sorted(subdomains)[:_MAX_SUBDOMAINS]

    return {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "total_certs": len(entries),
        "unique_subdomains": sorted_subdomains,
        "subdomain_count": len(subdomains),
        "infrastructure_hints": hints,
        "top_issuers": issuers,
        "error": None,
    }
