"""
On-premises network identification — distinguish on-site infrastructure from cloud.

For each contractor, collects all known IPs from existing OSINT data
(Shodan hosts, DNS A records, MX resolution, SPF ip4 directives, VPN/auth
subdomain resolution), then classifies each as cloud or on-premises by
checking against published cloud provider IP ranges.

Signal sources:
  - Shodan sample_hosts (WHOIS org-matched = likely on-prem)
  - DNS A records (often cloud/CDN)
  - MX records resolved to IPs (on-prem mail if not Google/O365)
  - SPF ip4: directives from TXT records (explicit on-prem ranges)
  - VPN/auth/remote subdomains from CT logs (resolved = on-prem endpoints)
  - ASN data (org-owned ASN prefixes = confirmed on-prem ranges)

Cloud detection:
  - AWS, Azure, GCP, Cloudflare published IP ranges
  - Common CDN/hosting CIDR heuristics
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
import time
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cloud provider IP range loading
# ---------------------------------------------------------------------------

_AWS_RANGES_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
_GCP_RANGES_URL = "https://www.gstatic.com/ipranges/cloud.json"
_CLOUDFLARE_V4_URL = "https://www.cloudflare.com/ips-v4"
_AZURE_RANGES_URL = (
    "https://download.microsoft.com/download/7/1/D/"
    "71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_20260323.json"
)

# Known cloud/CDN CIDR blocks (fallback if live fetch fails)
_STATIC_CLOUD_CIDRS = [
    # Cloudflare
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    # Fastly
    "23.235.32.0/20", "43.249.72.0/22", "103.244.50.0/24", "103.245.222.0/23",
    "103.245.224.0/24", "104.156.80.0/20", "151.101.0.0/16", "157.52.64.0/18",
    # Akamai (partial)
    "23.0.0.0/12", "104.64.0.0/10",
]

# Cloud mail providers — MX exchanges that are NOT on-prem
_CLOUD_MX_PATTERNS = {
    "google.com", "googlemail.com", "outlook.com", "microsoft.com",
    "protection.outlook.com", "pphosted.com", "mimecast.com",
    "messagelabs.com", "secureserver.net", "emailsrvr.com",
}

_REQUEST_TIMEOUT = 15
_RESOLVE_TIMEOUT = 3
_RATE_DELAY = 0.1

# Module-level cache for cloud networks
_cloud_networks: list[ipaddress.IPv4Network] | None = None
_cloud_provider_map: dict[str, list[ipaddress.IPv4Network]] | None = None


def _load_cloud_ranges() -> tuple[list[ipaddress.IPv4Network], dict[str, list[ipaddress.IPv4Network]]]:
    """Fetch and parse cloud provider IP ranges. Cached after first call."""
    global _cloud_networks, _cloud_provider_map
    if _cloud_networks is not None:
        return _cloud_networks, _cloud_provider_map

    provider_map: dict[str, list[ipaddress.IPv4Network]] = {
        "AWS": [], "Azure": [], "GCP": [], "Cloudflare": [], "CDN/Other": [],
    }

    # AWS
    try:
        resp = requests.get(_AWS_RANGES_URL, timeout=_REQUEST_TIMEOUT)
        for p in resp.json().get("prefixes", []):
            net = ipaddress.IPv4Network(p["ip_prefix"], strict=False)
            provider_map["AWS"].append(net)
    except Exception as e:
        logger.warning("Failed to fetch AWS ranges: %s", e)

    # Azure
    try:
        resp = requests.get(_AZURE_RANGES_URL, timeout=_REQUEST_TIMEOUT)
        for svc in resp.json().get("values", []):
            for prefix in svc.get("properties", {}).get("addressPrefixes", []):
                if ":" not in prefix:  # skip IPv6
                    try:
                        net = ipaddress.IPv4Network(prefix, strict=False)
                        provider_map["Azure"].append(net)
                    except ValueError:
                        pass
    except Exception as e:
        logger.warning("Failed to fetch Azure ranges: %s", e)

    # GCP
    try:
        resp = requests.get(_GCP_RANGES_URL, timeout=_REQUEST_TIMEOUT)
        for p in resp.json().get("prefixes", []):
            v4 = p.get("ipv4Prefix")
            if v4:
                provider_map["GCP"].append(ipaddress.IPv4Network(v4, strict=False))
    except Exception as e:
        logger.warning("Failed to fetch GCP ranges: %s", e)

    # Cloudflare
    try:
        resp = requests.get(_CLOUDFLARE_V4_URL, timeout=_REQUEST_TIMEOUT)
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if line:
                provider_map["Cloudflare"].append(
                    ipaddress.IPv4Network(line, strict=False)
                )
    except Exception as e:
        logger.warning("Failed to fetch Cloudflare ranges: %s", e)

    # Static fallback CDN ranges
    for cidr in _STATIC_CLOUD_CIDRS:
        try:
            provider_map["CDN/Other"].append(
                ipaddress.IPv4Network(cidr, strict=False)
            )
        except ValueError:
            pass

    all_nets = []
    for nets in provider_map.values():
        all_nets.extend(nets)

    _cloud_networks = all_nets
    _cloud_provider_map = provider_map
    logger.info(
        "Loaded cloud IP ranges: AWS=%d, Azure=%d, GCP=%d, CF=%d, Other=%d",
        len(provider_map["AWS"]), len(provider_map["Azure"]),
        len(provider_map["GCP"]), len(provider_map["Cloudflare"]),
        len(provider_map["CDN/Other"]),
    )
    return _cloud_networks, _cloud_provider_map


def _classify_ip(ip_str: str) -> dict[str, Any]:
    """Classify a single IP as cloud or on-premises."""
    try:
        ip = ipaddress.IPv4Address(ip_str)
    except ValueError:
        return {"ip": ip_str, "classification": "invalid", "provider": None}

    # Skip private/reserved ranges
    if ip.is_private or ip.is_reserved or ip.is_loopback:
        return {"ip": ip_str, "classification": "private", "provider": None}

    _, provider_map = _load_cloud_ranges()

    for provider, nets in provider_map.items():
        for net in nets:
            if ip in net:
                return {"ip": ip_str, "classification": "cloud", "provider": provider}

    return {"ip": ip_str, "classification": "on_prem", "provider": None}


# ---------------------------------------------------------------------------
# IP collection from existing OSINT data
# ---------------------------------------------------------------------------

def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve a hostname to A records. Returns empty list on failure."""
    try:
        socket.setdefaulttimeout(_RESOLVE_TIMEOUT)
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        return list({r[4][0] for r in results})
    except (socket.gaierror, socket.timeout, OSError):
        return []


def _extract_spf_ips(txt_records: list[str]) -> list[str]:
    """Extract ip4: directives from SPF TXT records."""
    ips = []
    for rec in txt_records:
        if "v=spf1" not in rec.lower():
            continue
        # Match ip4:x.x.x.x or ip4:x.x.x.x/nn
        for match in re.finditer(r"ip4:(\d+\.\d+\.\d+\.\d+(?:/\d+)?)", rec, re.I):
            cidr = match.group(1)
            try:
                net = ipaddress.IPv4Network(cidr, strict=False)
                # Expand small ranges to individual IPs, keep CIDR for larger ones
                if net.prefixlen >= 24:
                    for ip in net.hosts():
                        ips.append(str(ip))
                else:
                    ips.append(str(net.network_address))
            except ValueError:
                pass
    return ips


def collect_all_ips(contractor: dict) -> dict[str, list[str]]:
    """Collect all IP addresses from a contractor's existing OSINT data.

    Returns a dict mapping source label to list of IPs.
    """
    sources: dict[str, list[str]] = {}

    # 1. Shodan sample hosts (strongest on-prem signal)
    shodan = contractor.get("shodan", {})
    shodan_ips = []
    for host in shodan.get("sample_hosts", []):
        ip = host.get("ip")
        if ip:
            shodan_ips.append(ip)
    if shodan_ips:
        sources["shodan_hosts"] = shodan_ips

    # 2. DNS A records (often cloud/CDN but some on-prem)
    osint = contractor.get("osint", {})
    dns = osint.get("dns", {})
    a_records = dns.get("a_records", [])
    if a_records:
        sources["dns_a_records"] = a_records

    # 3. MX records — resolve non-cloud MX hostnames
    mx_records = dns.get("mx_records", [])
    mx_ips = []
    for mx in mx_records:
        exchange = mx.get("exchange", "") if isinstance(mx, dict) else str(mx)
        # Skip known cloud mail providers
        if any(pattern in exchange.lower() for pattern in _CLOUD_MX_PATTERNS):
            continue
        # This is potentially an on-prem mail server — resolve it
        resolved = _resolve_hostname(exchange)
        mx_ips.extend(resolved)
    if mx_ips:
        sources["mx_onprem"] = mx_ips

    # 4. SPF ip4: directives from TXT records
    txt_records = dns.get("txt_records", [])
    spf_ips = _extract_spf_ips(txt_records)
    if spf_ips:
        sources["spf_ip4"] = spf_ips

    # 5. VPN/auth subdomains from CT logs — resolve them
    ct = osint.get("ct", {})
    hints = ct.get("infrastructure_hints", {})
    vpn_subs = hints.get("vpn", []) + hints.get("auth", []) + hints.get("remote", [])
    vpn_ips = []
    for sub in vpn_subs[:10]:  # cap to avoid too many DNS queries
        resolved = _resolve_hostname(sub)
        vpn_ips.extend(resolved)
        if resolved:
            time.sleep(_RATE_DELAY)
    if vpn_ips:
        sources["vpn_auth_subs"] = vpn_ips

    # 6. ASN-enumerated hosts
    asn_data = osint.get("asn", {})
    for host in asn_data.get("hosts", []):
        ip = host.get("ip")
        if ip:
            sources.setdefault("asn_hosts", []).append(ip)

    return sources


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def identify_onprem_network(contractor: dict) -> dict[str, Any]:
    """Identify on-premises vs cloud infrastructure for a contractor.

    Returns
    -------
    dict with enrichment schema:
        queried: bool
        query_time: str
        ip_sources: dict  — source label → IP list
        classified_ips: list[dict]  — each IP with classification
        on_prem_ips: list[str]
        cloud_ips: list[dict]  — IP + provider
        on_prem_count: int
        cloud_count: int
        on_prem_percentage: float
        inferred_isp: str | None
        on_prem_services: list[dict]  — ports/services on on-prem IPs
        error: str | None
    """
    result: dict[str, Any] = {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "ip_sources": {},
        "classified_ips": [],
        "on_prem_ips": [],
        "cloud_ips": [],
        "on_prem_count": 0,
        "cloud_count": 0,
        "on_prem_percentage": 0.0,
        "inferred_isp": None,
        "on_prem_services": [],
        "error": None,
    }

    try:
        sources = collect_all_ips(contractor)
    except Exception as e:
        result["error"] = f"IP collection failed: {e}"
        return result

    result["ip_sources"] = {k: v for k, v in sources.items()}

    # Deduplicate all IPs
    all_ips = set()
    for ip_list in sources.values():
        all_ips.update(ip_list)

    if not all_ips:
        result["error"] = "no_ips_found"
        return result

    # Classify each IP
    on_prem = []
    cloud = []
    classified = []

    for ip_str in sorted(all_ips):
        classification = _classify_ip(ip_str)

        # Determine which sources this IP came from
        ip_sources = [src for src, ips in sources.items() if ip_str in ips]
        classification["sources"] = ip_sources

        classified.append(classification)

        if classification["classification"] == "on_prem":
            on_prem.append(ip_str)
        elif classification["classification"] == "cloud":
            cloud.append({
                "ip": ip_str,
                "provider": classification["provider"],
            })

    result["classified_ips"] = classified
    result["on_prem_ips"] = on_prem
    result["cloud_ips"] = cloud
    result["on_prem_count"] = len(on_prem)
    result["cloud_count"] = len(cloud)

    total_public = len(on_prem) + len(cloud)
    if total_public > 0:
        result["on_prem_percentage"] = round(len(on_prem) / total_public * 100, 1)

    # Cross-reference on-prem IPs with Shodan data for service details
    shodan = contractor.get("shodan", {})
    shodan_host_map = {h.get("ip"): h for h in shodan.get("sample_hosts", [])}
    asn_host_map = {
        h.get("ip"): h
        for h in contractor.get("osint", {}).get("asn", {}).get("hosts", [])
    }

    on_prem_services = []
    for ip in on_prem:
        svc = {"ip": ip, "ports": [], "services": [], "reverse_dns": None}

        # Check Shodan data
        sh = shodan_host_map.get(ip)
        if sh:
            svc["ports"] = sh.get("open_ports", []) or []
            svc["services"] = sh.get("services", []) or []
            svc["reverse_dns"] = sh.get("hostnames", [None])[0] if sh.get("hostnames") else None

        # Check ASN data
        ah = asn_host_map.get(ip)
        if ah:
            svc["ports"] = svc["ports"] or ah.get("ports", [])
            svc["reverse_dns"] = svc["reverse_dns"] or ah.get("reverse_dns")

        on_prem_services.append(svc)

    result["on_prem_services"] = on_prem_services

    # Infer ISP from reverse DNS of on-prem IPs
    for svc in on_prem_services:
        rdns = svc.get("reverse_dns")
        if rdns and rdns != svc["ip"]:
            # Extract likely ISP domain from reverse DNS
            parts = rdns.lower().split(".")
            if len(parts) >= 2:
                isp_domain = ".".join(parts[-2:])
                result["inferred_isp"] = isp_domain
                break

    return result
