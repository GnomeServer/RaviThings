"""
NVD CVSS enrichment — look up real CVSS v3.1 scores for CVE identifiers.

Queries the NIST NVD API v2.0 to retrieve severity, base score, and vector
string for each CVE found by Shodan/ASN enumeration.  Results are cached
per contractor so re-runs skip already-scored CVEs.

Rate limits:
  - Without API key: 5 requests per 30 seconds (~1 per 6 sec)
  - With NVD_API_KEY: 50 requests per 30 seconds (~1.7 per sec)

Usage:
  python -m osint.nvd_cvss            # standalone test
  python -m osint.pipeline --layers nvd  # via pipeline
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_REQUEST_TIMEOUT = 20  # seconds
_RETRY_WAIT = 8  # seconds — generous for NVD rate limits
_MAX_RETRIES = 2

# Severity thresholds per CVSS v3.1 spec
_SEVERITY_THRESHOLDS = [
    (9.0, "critical"),
    (7.0, "high"),
    (4.0, "medium"),
    (0.1, "low"),
    (0.0, "none"),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_headers() -> dict[str, str]:
    """Build request headers, including API key if available."""
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("NVD_API_KEY", "")
    if api_key:
        headers["apiKey"] = api_key
    return headers


def _rate_delay() -> float:
    """Return delay between requests based on API key availability."""
    if os.environ.get("NVD_API_KEY"):
        return 0.7  # ~50 req / 30 sec with key
    return 6.5  # ~5 req / 30 sec without key


def _parse_cvss(vuln_data: dict) -> dict[str, Any] | None:
    """Extract CVSS v3.1 (preferred) or v3.0 score from NVD vulnerability."""
    metrics = vuln_data.get("metrics", {})

    # Prefer v3.1, fall back to v3.0
    for version_key in ("cvssMetricV31", "cvssMetricV30"):
        entries = metrics.get(version_key, [])
        if entries:
            primary = entries[0]  # first entry is usually the primary
            cvss = primary.get("cvssData", {})
            return {
                "version": cvss.get("version", "3.1"),
                "base_score": cvss.get("baseScore", 0.0),
                "severity": cvss.get("baseSeverity", "UNKNOWN").lower(),
                "vector": cvss.get("vectorString", ""),
                "exploitability_score": primary.get("exploitabilityScore"),
                "impact_score": primary.get("impactScore"),
            }

    # Fall back to v2.0
    v2_entries = metrics.get("cvssMetricV2", [])
    if v2_entries:
        primary = v2_entries[0]
        cvss = primary.get("cvssData", {})
        score = cvss.get("baseScore", 0.0)
        # Map v2 score to severity labels
        if score >= 9.0:
            sev = "critical"
        elif score >= 7.0:
            sev = "high"
        elif score >= 4.0:
            sev = "medium"
        else:
            sev = "low"
        return {
            "version": "2.0",
            "base_score": score,
            "severity": sev,
            "vector": cvss.get("vectorString", ""),
            "exploitability_score": primary.get("exploitabilityScore"),
            "impact_score": primary.get("impactScore"),
        }

    return None


def _fetch_cve(cve_id: str) -> dict[str, Any] | None:
    """Fetch a single CVE from NVD API. Returns parsed CVSS data or None."""
    headers = _get_headers()

    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.get(
                _NVD_API_URL,
                params={"cveId": cve_id},
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )

            if resp.status_code == 403 or resp.status_code == 429:
                # Rate limited — wait and retry
                wait = _RETRY_WAIT * (attempt + 1)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()

            vulns = data.get("vulnerabilities", [])
            if not vulns:
                return None

            vuln = vulns[0].get("cve", {})
            cvss = _parse_cvss(vuln)
            if cvss:
                cvss["cve_id"] = cve_id
                # Extract description
                descs = vuln.get("descriptions", [])
                en_desc = next(
                    (d["value"] for d in descs if d.get("lang") == "en"),
                    "",
                )
                cvss["description"] = en_desc[:300]
            return cvss

        except requests.Timeout:
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_WAIT)
                continue
            return None
        except (requests.ConnectionError, requests.HTTPError):
            return None

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_nvd_cvss(cve_ids: list[str], existing_scores: dict | None = None) -> dict[str, Any]:
    """Look up CVSS scores for a list of CVE IDs.

    Parameters
    ----------
    cve_ids : list[str]
        CVE identifiers to look up (e.g., ["CVE-2021-44228", "CVE-2023-1234"])
    existing_scores : dict | None
        Previously cached scores to skip re-querying.

    Returns
    -------
    dict with standard enrichment schema:
        queried: bool
        query_time: str (ISO-8601)
        total_cves: int
        scored_cves: int
        scores: dict[str, dict]  — CVE ID → {base_score, severity, vector, ...}
        summary: dict  — severity distribution counts
        max_severity: str
        max_score: float
        error: str | None
    """
    if existing_scores is None:
        existing_scores = {}

    result: dict[str, Any] = {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "total_cves": len(cve_ids),
        "scored_cves": 0,
        "scores": {},
        "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0, "unknown": 0},
        "max_severity": "none",
        "max_score": 0.0,
        "error": None,
    }

    if not cve_ids:
        return result

    # Deduplicate and normalize to uppercase (NVD requires CVE-YYYY-NNNN format)
    unique_cves = sorted({cve.upper() for cve in cve_ids})
    delay = _rate_delay()
    errors = 0

    for i, cve_id in enumerate(unique_cves):
        # Use cached score if available (case-insensitive)
        if cve_id in existing_scores or cve_id.lower() in existing_scores:
            cvss = existing_scores[cve_id]
            result["scores"][cve_id] = cvss
            sev = cvss.get("severity", "unknown")
            result["summary"][sev] = result["summary"].get(sev, 0) + 1
            result["scored_cves"] += 1
            continue

        # Rate limit
        if i > 0:
            time.sleep(delay)

        cvss = _fetch_cve(cve_id)

        if cvss:
            result["scores"][cve_id] = cvss
            sev = cvss.get("severity", "unknown")
            result["summary"][sev] = result["summary"].get(sev, 0) + 1
            result["scored_cves"] += 1
            if cvss["base_score"] > result["max_score"]:
                result["max_score"] = cvss["base_score"]
                result["max_severity"] = sev
        else:
            errors += 1
            result["summary"]["unknown"] += 1

    if errors > 0 and errors == len(unique_cves):
        result["error"] = f"All {errors} CVE lookups failed"
    elif errors > 0:
        result["error"] = f"{errors}/{len(unique_cves)} lookups failed"

    return result


def collect_cve_ids(contractor: dict) -> list[str]:
    """Extract all CVE IDs from a contractor's Shodan + ASN data."""
    cves = set()

    # From Shodan vulns
    shodan = contractor.get("shodan", {})
    for v in shodan.get("vulns", []):
        if isinstance(v, dict) and v.get("cve"):
            cves.add(v["cve"])
        elif isinstance(v, str):
            cves.add(v)

    # From enhanced Shodan
    osint = contractor.get("osint", {})
    es = osint.get("enhanced_shodan", {})
    for v in es.get("vulns", []):
        if isinstance(v, dict) and v.get("cve"):
            cves.add(v["cve"])
        elif isinstance(v, str):
            cves.add(v)

    # From ASN enumeration
    asn = osint.get("asn", {})
    for v in asn.get("all_vulns", []):
        if isinstance(v, str):
            cves.add(v)

    return sorted(cves)
