"""ASN enumeration and Shodan InternetDB enrichment.

Maps a contractor's IP addresses to ASN ownership information and queries
the Shodan InternetDB for open-port / vulnerability data on each IP.
"""

import logging
import socket
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

_INTERNETDB_URL = "https://internetdb.shodan.io/{ip}"
_BGPVIEW_URL = "https://api.bgpview.io/ip/{ip}"
_REQUEST_TIMEOUT = 5
_RATE_LIMIT_DELAY = 0.3
_MAX_IPS = 10


def _empty_result(domain: str, error: str | None = None) -> dict:
    """Return a skeleton result dict with default empty values."""
    return {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "asn": {"number": None, "name": None, "description": None, "prefix": None},
        "hosts": [],
        "total_ports": 0,
        "total_vulns": 0,
        "all_ports": [],
        "all_vulns": [],
        "error": error,
    }


def _query_internetdb(ip: str) -> dict:
    """Query Shodan InternetDB for a single IP.

    Returns a dict with ports, vulns, cpes, hostnames, and tags.
    On failure, all list fields default to empty.
    """
    try:
        resp = requests.get(
            _INTERNETDB_URL.format(ip=ip), timeout=_REQUEST_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "ports": data.get("ports", []),
                "vulns": data.get("vulns", []),
                "cpes": data.get("cpes", []),
                "hostnames": data.get("hostnames", []),
                "tags": data.get("tags", []),
            }
        logger.warning("InternetDB returned %s for %s", resp.status_code, ip)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("InternetDB query failed for %s: %s", ip, exc)

    return {"ports": [], "vulns": [], "cpes": [], "hostnames": [], "tags": []}


def _query_bgpview(ip: str) -> dict:
    """Fetch ASN ownership data from BGPView for a single IP.

    Returns a dict with number, name, description, and prefix.
    All values default to ``None`` on failure.
    """
    asn_info: dict = {
        "number": None,
        "name": None,
        "description": None,
        "prefix": None,
    }
    try:
        resp = requests.get(
            _BGPVIEW_URL.format(ip=ip), timeout=_REQUEST_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            prefixes = data.get("prefixes", [])
            if prefixes:
                first = prefixes[0]
                asn_block = first.get("asn", {})
                asn_number = asn_block.get("asn")
                asn_info["number"] = (
                    f"AS{asn_number}" if asn_number is not None else None
                )
                asn_info["name"] = asn_block.get("name")
                asn_info["description"] = asn_block.get("description")
                # Prefer the prefix string; fall back to CIDR if available.
                asn_info["prefix"] = first.get("prefix") or first.get("cidr")
        else:
            logger.warning("BGPView returned %s for %s", resp.status_code, ip)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("BGPView query failed for %s: %s", ip, exc)

    return asn_info


def _reverse_dns(ip: str) -> str:
    """Return the reverse-DNS name for *ip*, falling back to the IP itself."""
    try:
        fqdn = socket.getfqdn(ip)
        return fqdn if fqdn else ip
    except (socket.herror, OSError):
        return ip


def enrich_asn(domain: str, a_records: list[str]) -> dict:
    """Enrich a list of A-record IPs with ASN and Shodan InternetDB data.

    Parameters
    ----------
    domain:
        The domain name associated with the IP addresses.
    a_records:
        A list of IPv4 address strings (e.g. ``["1.2.3.4", "5.6.7.8"]``).

    Returns
    -------
    dict
        A result dictionary containing ASN ownership, per-host port and
        vulnerability data, and aggregate statistics.  See module docstring
        for the full schema.
    """
    if not a_records:
        return _empty_result(domain, error="no_ips")

    # Cap the number of IPs we process.
    ips = a_records[:_MAX_IPS]

    result = _empty_result(domain)

    # --- ASN lookup on the first IP ---
    result["asn"] = _query_bgpview(ips[0])

    # --- Per-IP enrichment ---
    all_ports: set[int] = set()
    all_vulns: set[str] = set()
    hosts: list[dict] = []

    for idx, ip in enumerate(ips):
        # Rate-limit between InternetDB queries (skip delay before the first).
        if idx > 0:
            time.sleep(_RATE_LIMIT_DELAY)

        idb = _query_internetdb(ip)
        rdns = _reverse_dns(ip)

        host_entry = {
            "ip": ip,
            "reverse_dns": rdns,
            "ports": idb["ports"],
            "vulns": idb["vulns"],
            "cpes": idb["cpes"],
            "hostnames": idb["hostnames"],
            "tags": idb["tags"],
        }
        hosts.append(host_entry)

        all_ports.update(idb["ports"])
        all_vulns.update(idb["vulns"])

    result["hosts"] = hosts
    result["total_ports"] = len(all_ports)
    result["total_vulns"] = len(all_vulns)
    result["all_ports"] = sorted(all_ports)
    result["all_vulns"] = sorted(all_vulns)
    result["error"] = None

    return result
