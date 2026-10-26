"""
Domain verification — multi-signal confidence scoring.

Validates whether a discovered domain actually belongs to the contractor
it was assigned to. Detects parking pages, domain squatters, and
misattributed domains. Produces a 0–100 confidence score.
"""

from __future__ import annotations

import re
import ssl
import socket
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_REQUEST_TIMEOUT = 8
_USER_AGENT = "Mozilla/5.0 (compatible; DOE-OSINT-Verify/1.0)"

# ───────────────────────────────────────────────────────────────
# Parking / squatter detection patterns
# ───────────────────────────────────────────────────────────────

_PARKING_PATTERNS = [
    r"this\s+domain\s+(is\s+)?for\s+sale",
    r"buy\s+this\s+domain",
    r"domain\s+may\s+be\s+for\s+sale",
    r"parked\s+free",
    r"sedo\.com",
    r"sedoparking\.com",
    r"parkingcrew\.net",
    r"dan\.com",
    r"afternic\.com",
    r"hugedomains\.com",
    r"godaddy\s+auctions",
    r"this\s+webpage\s+was\s+generated\s+by\s+the\s+domain\s+owner",
    r"domain\s+parking",
    r"undeveloped\.com",
    r"brandpa\.com",
    r"domainmarket\.com",
    r"is\s+available\s+for\s+purchase",
    r"make\s+an?\s+offer\s+(on|for)\s+this\s+domain",
    r"inquire\s+about\s+this\s+domain",
    r"related\s+searches|related\s+links|sponsored\s+listings",
    r"domainlore\.com",
    r"above\.com",
    r"bodis\.com",
]

_PARKING_RE = re.compile("|".join(_PARKING_PATTERNS), re.IGNORECASE)

# Common registrar parking page titles
_PARKING_TITLES = [
    "domain for sale",
    "parked domain",
    "this domain is for sale",
    "buy this domain",
    "domain parking",
    "coming soon",
    "website coming soon",
    "under construction",
    "future home of",
]


def _normalize_name(name: str) -> str:
    """Normalize a company name for fuzzy matching."""
    name = name.lower()
    # Remove common suffixes
    name = re.sub(
        r",?\s*(llc|inc\.?|corp\.?|corporation|company|co\.?|ltd\.?|l\.?l\.?c\.?|"
        r"l\.?p\.?|group|holdings?|services?|solutions?|technologies?|"
        r"enterprises?|associates?|consulting|the)\s*\.?\s*$",
        "", name, flags=re.IGNORECASE,
    )
    # Remove punctuation and extra whitespace
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _fuzzy_name_in_text(name: str, text: str, threshold: int = 2) -> bool:
    """Check if a normalized name appears in text (case-insensitive).

    Uses substring matching with tolerance for the first N significant words.
    """
    if not name or not text:
        return False
    text_lower = text.lower()
    name_norm = _normalize_name(name)

    # Direct substring match
    if name_norm in text_lower:
        return True

    # Match first 2-3 significant words (handles "Lockheed Martin" in page)
    words = name_norm.split()
    if len(words) >= 2:
        two_word = " ".join(words[:2])
        if two_word in text_lower:
            return True
        # Also try without space (e.g., "lockheedmartin")
        if "".join(words[:2]) in text_lower.replace(" ", ""):
            return True

    if len(words) >= 3:
        three_word = " ".join(words[:3])
        if three_word in text_lower:
            return True

    # Single word match for distinctive names (5+ chars)
    if len(words) == 1 and len(words[0]) >= 5:
        if words[0] in text_lower:
            return True

    return False


def _get_ssl_cert_org(domain: str) -> Optional[str]:
    """Retrieve the organization from the SSL certificate."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                if cert:
                    subject = dict(x[0] for x in cert.get("subject", ()))
                    return subject.get("organizationName", "")
        return None
    except Exception:
        return None


def _fetch_page(domain: str) -> dict[str, Any]:
    """Fetch homepage and return response metadata."""
    result = {"title": "", "body_snippet": "", "final_url": "", "status": 0, "error": None}
    try:
        resp = requests.get(
            f"https://{domain}",
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=False,
            headers={"User-Agent": _USER_AGENT},
        )
        result["status"] = resp.status_code
        result["final_url"] = resp.url

        body = resp.text[:50000]
        result["body_snippet"] = body

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["title"] = title_match.group(1).strip()[:200]

    except requests.exceptions.SSLError:
        # Try HTTP fallback
        try:
            resp = requests.get(
                f"http://{domain}",
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
                headers={"User-Agent": _USER_AGENT},
            )
            result["status"] = resp.status_code
            result["final_url"] = resp.url
            body = resp.text[:50000]
            result["body_snippet"] = body
            title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
            if title_match:
                result["title"] = title_match.group(1).strip()[:200]
        except Exception as e:
            result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    return result


def verify_domain(contractor_name: str, domain: str, dba: str = "",
                  dns_data: dict | None = None, ct_data: dict | None = None,
                  ai_research: dict | None = None) -> dict[str, Any]:
    """Verify whether a domain actually belongs to a contractor.

    Args:
        contractor_name: The contractor's official name
        domain: The domain to verify
        dba: Doing-business-as name (alternate name)
        dns_data: Existing DNS enrichment data (optional, avoids re-querying)
        ct_data: Existing CT log data (optional)
        ai_research: AI research results (optional, boosts confidence if domain matches)

    Returns:
        dict with confidence score, verdict, and signal details
    """
    result = {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "confidence": 0,
        "verdict": "unverified",
        "signals": [],
        "is_parking": False,
        "is_redirect_away": False,
        "page_title": "",
        "ssl_org": "",
        "name_in_page": False,
        "name_in_ssl": False,
        "has_real_mx": False,
        "has_ct_certs": False,
        "error": None,
    }

    if not domain or not contractor_name:
        result["error"] = "missing_domain_or_name"
        return result

    score = 0
    signals = []
    names_to_check = [contractor_name]
    if dba:
        names_to_check.append(dba)

    # ── Signal 1: Fetch homepage, check for name match & parking ──
    page = _fetch_page(domain)
    result["page_title"] = page["title"]

    if page["body_snippet"]:
        # Check parking / for-sale
        if _PARKING_RE.search(page["body_snippet"]):
            result["is_parking"] = True
            score -= 40
            signals.append(("parking_detected", -40))

        # Check parking titles
        title_lower = page["title"].lower()
        if any(pt in title_lower for pt in _PARKING_TITLES):
            if not result["is_parking"]:
                result["is_parking"] = True
                score -= 30
                signals.append(("parking_title", -30))

        # Check name in page content
        for name in names_to_check:
            if _fuzzy_name_in_text(name, page["body_snippet"]):
                result["name_in_page"] = True
                score += 25
                signals.append(("name_in_page", +25))
                break

        # Check name in title specifically (stronger signal)
        if not result["name_in_page"]:
            for name in names_to_check:
                if _fuzzy_name_in_text(name, page["title"]):
                    result["name_in_page"] = True
                    score += 25
                    signals.append(("name_in_title", +25))
                    break

        # Check redirect to unrelated domain
        if page["final_url"]:
            from osint.domain_discovery import extract_domain_from_url
            final_domain = extract_domain_from_url(page["final_url"])
            if final_domain and final_domain != domain and not final_domain.endswith("." + domain):
                result["is_redirect_away"] = True
                score -= 25
                signals.append(("redirect_away", -25, final_domain))

    elif page["error"]:
        # Couldn't fetch — no signal either way
        signals.append(("fetch_failed", 0))

    # ── Signal 2: SSL certificate org match ──
    ssl_org = _get_ssl_cert_org(domain)
    if ssl_org:
        result["ssl_org"] = ssl_org
        for name in names_to_check:
            if _fuzzy_name_in_text(name, ssl_org):
                result["name_in_ssl"] = True
                score += 20
                signals.append(("ssl_org_match", +20))
                break

    # ── Signal 3: DNS has real MX records ──
    if dns_data:
        mx = dns_data.get("mx_records", [])
        mail_provider = dns_data.get("mail_provider", "Unknown")
        if mx and mail_provider != "Unknown":
            result["has_real_mx"] = True
            score += 10
            signals.append(("real_mx", +10, mail_provider))

    # ── Signal 4: CT certificates exist (beyond just 1-2 parking certs) ──
    if ct_data:
        sub_count = ct_data.get("subdomain_count", 0)
        if sub_count >= 3:
            result["has_ct_certs"] = True
            score += 10
            signals.append(("ct_certs", +10, sub_count))

    # ── Signal 5: Domain name itself contains company words ──
    name_norm = _normalize_name(contractor_name)
    domain_base = domain.split(".")[0].lower()
    name_words = name_norm.split()
    if len(name_words) >= 2:
        # Check if first two words are in domain (e.g., "lockheedmartin" in "lockheedmartin.com")
        first_two = "".join(name_words[:2])
        if first_two in domain_base or domain_base in first_two:
            score += 15
            signals.append(("domain_name_match", +15))
    elif len(name_words) == 1 and len(name_words[0]) >= 4:
        if name_words[0] in domain_base:
            score += 15
            signals.append(("domain_name_match", +15))

    # ── Signal 6: AI Research validation ──
    # If the AI Research Layer confirmed this domain with high confidence + sources,
    # that's strong evidence — the LLM cross-referenced web search results.
    if ai_research and ai_research.get('current_domain'):
        ai_domain = ai_research['current_domain'].lower().strip()
        if ai_domain == domain.lower().strip():
            ai_conf = ai_research.get('domain_confidence', 0)
            ai_sources = len(ai_research.get('sources', []))
            if ai_conf >= 80:
                score += 35
                signals.append(("ai_research_high_confidence", +35, f"conf={ai_conf}%, {ai_sources} sources"))
            elif ai_conf >= 50:
                score += 20
                signals.append(("ai_research_moderate_confidence", +20, f"conf={ai_conf}%, {ai_sources} sources"))
            elif ai_conf > 0:
                score += 10
                signals.append(("ai_research_low_confidence", +10, f"conf={ai_conf}%"))

    # ── Clamp and classify ──
    score = max(0, min(100, score))
    result["confidence"] = score
    result["signals"] = signals

    if score >= 70:
        result["verdict"] = "verified"
    elif score >= 40:
        result["verdict"] = "likely"
    elif score >= 20:
        result["verdict"] = "uncertain"
    else:
        result["verdict"] = "unverified"

    return result
