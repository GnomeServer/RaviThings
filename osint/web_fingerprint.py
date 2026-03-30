"""
Web technology fingerprinting module.

Performs a single GET request to a target domain and inspects response
headers, cookies, and HTML body to identify server software, CDN
providers, CMS platforms, JS frameworks, and security-header posture.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Detection constants
# ---------------------------------------------------------------------------

_USER_AGENT = "Mozilla/5.0 (compatible; DOE-OSINT/1.0)"
_REQUEST_TIMEOUT = 10  # seconds
_BODY_LIMIT = 50 * 1024  # first 50 KB of response body

# CDN header -> friendly name
_CDN_HEADERS: dict[str, str] = {
    "cf-ray": "Cloudflare",
    "x-amz-cf-id": "CloudFront",
    "x-vercel-id": "Vercel",
}
# Prefix-based CDN detection
_CDN_PREFIXES: list[tuple[str, str]] = [
    ("x-akamai-", "Akamai"),
    ("fastly-", "Fastly"),
]

# Security headers we care about
_SECURITY_HEADERS: dict[str, str] = {
    "strict-transport-security": "hsts",
    "content-security-policy": "csp",
    "x-frame-options": "x_frame",
    "x-content-type-options": "x_content_type",
}

# Cookie-name patterns -> technology
_COOKIE_TECH: list[tuple[str, str]] = [
    ("jsessionid", "Java"),
    ("phpsessid", "PHP"),
    ("asp.net_sessionid", ".NET"),
    ("wordpress_", "WordPress"),
]

# CMS body signatures
_CMS_SIGNATURES: list[tuple[str, str]] = [
    ("wp-content", "WordPress"),
    ("drupal", "Drupal"),
    ("joomla", "Joomla"),
    ("sharepoint", "SharePoint"),
]

# JS framework body signatures (lower-cased matching)
_JS_FRAMEWORKS: list[str] = [
    "react",
    "angular",
    "vue",
    "jquery",
    "next.js",
    "gatsby",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_empty_result(domain: str, error: str | None = None) -> dict[str, Any]:
    """Return a result dict with empty/default values."""
    return {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "url_final": "",
        "status_code": 0,
        "server": "",
        "powered_by": "",
        "cdn_detected": "",
        "security_headers": {
            "hsts": False,
            "csp": False,
            "x_frame": False,
            "x_content_type": False,
        },
        "cookies_tech": [],
        "cms": "",
        "js_frameworks": [],
        "meta_generator": "",
        "technologies_detected": [],
        "security_score": 0,
        "error": error,
    }


def _detect_cdn(headers: dict[str, str]) -> str:
    """Identify CDN from response headers."""
    lower_headers = {k.lower(): v for k, v in headers.items()}

    for header, cdn_name in _CDN_HEADERS.items():
        if header in lower_headers:
            return cdn_name

    for key in lower_headers:
        for prefix, cdn_name in _CDN_PREFIXES:
            if key.startswith(prefix):
                return cdn_name

    return ""


def _detect_security_headers(headers: dict[str, str]) -> dict[str, bool]:
    """Check which security headers are present."""
    lower_headers = {k.lower() for k in headers}
    return {
        short: (full in lower_headers)
        for full, short in _SECURITY_HEADERS.items()
    }


def _detect_cookie_tech(response: requests.Response) -> list[str]:
    """Infer backend technology from cookie names."""
    detected: set[str] = set()
    for cookie in response.cookies:
        name_lower = cookie.name.lower()
        for pattern, tech in _COOKIE_TECH:
            if name_lower.startswith(pattern) or name_lower == pattern:
                detected.add(tech)
    return sorted(detected)


def _detect_cms(body: str) -> str:
    """Return the first CMS whose signature appears in the HTML body."""
    body_lower = body.lower()
    for pattern, cms in _CMS_SIGNATURES:
        if pattern in body_lower:
            return cms
    return ""


def _detect_js_frameworks(body: str) -> list[str]:
    """Return JS framework names found in the HTML body."""
    body_lower = body.lower()
    return [fw for fw in _JS_FRAMEWORKS if fw in body_lower]


def _extract_meta_generator(body: str) -> str:
    """Extract the ``<meta name="generator" content="...">`` value."""
    match = re.search(
        r'<meta\s+name=["\']generator["\']\s+content=["\']([^"\']+)["\']',
        body,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _aggregate_technologies(
    server: str,
    powered_by: str,
    cdn: str,
    cookies_tech: list[str],
    cms: str,
    js_frameworks: list[str],
    meta_generator: str,
) -> list[str]:
    """Build a de-duplicated, sorted list of every technology detected."""
    techs: set[str] = set()
    if server:
        techs.add(server)
    if powered_by:
        techs.add(powered_by)
    if cdn:
        techs.add(cdn)
    if cms:
        techs.add(cms)
    if meta_generator:
        techs.add(meta_generator)
    techs.update(cookies_tech)
    techs.update(js_frameworks)
    return sorted(techs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich_web(domain: str) -> dict[str, Any]:
    """
    Fingerprint the technology stack of *domain*.

    Performs a single HTTPS GET request and inspects response headers,
    cookies, and the first 50 KB of HTML to identify server software, CDN,
    CMS, JS frameworks, and security-header posture.

    Parameters
    ----------
    domain:
        The target domain (e.g. ``"example.com"``).  The request is sent
        to ``https://{domain}``.

    Returns
    -------
    dict
        Structured fingerprinting results including a 0--4 security score.
    """
    url = f"https://{domain}"

    try:
        resp = requests.get(
            url,
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=False,
            headers={"User-Agent": _USER_AGENT},
        )
    except (requests.ConnectionError, requests.Timeout, requests.RequestException) as exc:
        return _build_empty_result(domain, error=str(exc))

    headers = dict(resp.headers)
    body = resp.text[:_BODY_LIMIT]

    server = headers.get("Server", "")
    powered_by = headers.get("X-Powered-By", "")
    cdn = _detect_cdn(headers)
    sec_headers = _detect_security_headers(headers)
    cookies_tech = _detect_cookie_tech(resp)
    cms = _detect_cms(body)
    js_frameworks = _detect_js_frameworks(body)
    meta_generator = _extract_meta_generator(body)

    technologies = _aggregate_technologies(
        server, powered_by, cdn, cookies_tech, cms, js_frameworks, meta_generator,
    )

    security_score = sum(sec_headers.values())

    return {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "url_final": resp.url,
        "status_code": resp.status_code,
        "server": server,
        "powered_by": powered_by,
        "cdn_detected": cdn,
        "security_headers": sec_headers,
        "cookies_tech": cookies_tech,
        "cms": cms,
        "js_frameworks": js_frameworks,
        "meta_generator": meta_generator,
        "technologies_detected": technologies,
        "security_score": security_score,
        "error": None,
    }
