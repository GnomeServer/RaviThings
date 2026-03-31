"""
Per-IP Shodan host enrichment for DOE contractors.

Two-phase approach:
  1. InternetDB screening — free, fast, identifies IPs with open ports
  2. Shodan api.host() — free on paid plans, returns full banner/SSL/vuln data

Usage:
    from osint.shodan_ip import enrich_contractor_ips, screen_ips_internetdb

    # Phase 1: Quick screen
    screening = screen_ips_internetdb(["1.2.3.4", "5.6.7.8"])

    # Phase 2: Full enrichment per contractor
    result = enrich_contractor_ips(api, contractor, existing_cache={})
"""

import time
import logging
from datetime import datetime, timezone

import httpx
import shodan

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# InternetDB screening (free, no API key)
# ---------------------------------------------------------------------------

INTERNETDB_URL = "https://internetdb.shodan.io"


def screen_ip_internetdb(ip: str, client: httpx.Client | None = None) -> dict | None:
    """Query InternetDB for a single IP. Returns dict with ports/vulns or None if no data."""
    try:
        c = client or httpx.Client(timeout=10)
        r = c.get(f"{INTERNETDB_URL}/{ip}")
        if r.status_code == 200:
            data = r.json()
            return {
                "ip": ip,
                "ports": data.get("ports", []),
                "hostnames": data.get("hostnames", []),
                "cpes": data.get("cpes", []),
                "vulns": data.get("vulns", []),
                "tags": data.get("tags", []),
            }
        elif r.status_code == 404:
            return None  # IP not in Shodan's database
        else:
            log.warning("InternetDB %s returned %d", ip, r.status_code)
            return None
    except Exception as e:
        log.warning("InternetDB error for %s: %s", ip, e)
        return None


def screen_ips_internetdb(
    ips: list[str],
    client: httpx.Client | None = None,
    delay: float = 0.1,
    progress_fn=None,
) -> dict[str, dict]:
    """Screen multiple IPs via InternetDB. Returns {ip: data} for IPs with open ports."""
    results = {}
    c = client or httpx.Client(timeout=10)

    for i, ip in enumerate(ips):
        data = screen_ip_internetdb(ip, client=c)
        if data and data.get("ports"):
            results[ip] = data

        if progress_fn and (i + 1) % 100 == 0:
            progress_fn(i + 1, len(ips), len(results))

        if delay > 0 and i < len(ips) - 1:
            time.sleep(delay)

    return results


# ---------------------------------------------------------------------------
# Shodan per-IP host lookup (free on paid plans, 0 credits)
# ---------------------------------------------------------------------------

def enrich_ip_shodan(api: shodan.Shodan, ip: str) -> dict | None:
    """Query Shodan for full host data on a single IP.

    Returns a condensed dict with the most useful fields, or None on error.
    Cost: 0 query credits on paid plans.
    """
    try:
        host = api.host(ip, minify=False)

        # Extract services from banner data
        services = []
        for banner in host.get("data", []):
            svc = {
                "port": banner.get("port"),
                "transport": banner.get("transport", "tcp"),
                "product": banner.get("product", ""),
                "version": banner.get("version", ""),
                "os": banner.get("os"),
                "module": banner.get("_shodan", {}).get("module", ""),
            }

            # HTTP info
            http = banner.get("http")
            if http:
                svc["http_title"] = http.get("title", "")
                svc["http_server"] = http.get("server", "")
                svc["http_status"] = http.get("status")

            # SSL info
            ssl = banner.get("ssl")
            if ssl:
                cert = ssl.get("cert", {})
                svc["ssl_subject"] = cert.get("subject", {}).get("CN", "")
                svc["ssl_issuer"] = cert.get("issuer", {}).get("O", "")
                svc["ssl_expires"] = cert.get("expires", "")
                svc["ssl_expired"] = cert.get("expired", False)
                # Extract SANs
                extensions = cert.get("extensions", [])
                for ext in extensions if isinstance(extensions, list) else []:
                    if ext.get("short_name") == "subjectAltName":
                        svc["ssl_sans"] = ext.get("data", "")[:200]

            services.append(svc)

        # Extract vulns
        vulns = host.get("vulns", [])

        return {
            "ip": host.get("ip_str", ip),
            "hostnames": host.get("hostnames", []),
            "domains": host.get("domains", []),
            "org": host.get("org", ""),
            "isp": host.get("isp", ""),
            "asn": host.get("asn", ""),
            "os": host.get("os"),
            "ports": host.get("ports", []),
            "vulns": vulns,
            "city": host.get("city", ""),
            "country_code": host.get("country_code", ""),
            "last_update": host.get("last_update", ""),
            "services": services,
        }
    except shodan.APIError as e:
        if "No information available" in str(e):
            return None  # IP not in Shodan
        log.warning("Shodan API error for %s: %s", ip, e)
        return None
    except Exception as e:
        log.warning("Shodan error for %s: %s", ip, e)
        return None


# ---------------------------------------------------------------------------
# Contractor-level enrichment
# ---------------------------------------------------------------------------

def collect_onprem_ips(contractor: dict) -> list[str]:
    """Extract unique on-prem IPs from a contractor's existing OSINT data."""
    onprem = contractor.get("osint", {}).get("onprem_network", {})
    if not onprem.get("queried"):
        return []
    return list(set(onprem.get("on_prem_ips", [])))


def enrich_contractor_ips(
    api: shodan.Shodan,
    contractor: dict,
    ip_cache: dict[str, dict] | None = None,
    internetdb_cache: dict[str, dict] | None = None,
    delay: float = 1.0,
) -> dict:
    """Enrich a single contractor with per-IP Shodan host data.

    Steps:
    1. Collect on-prem IPs from existing data
    2. Screen via InternetDB (skip if already cached)
    3. Full Shodan host lookup for IPs with open ports
    4. Aggregate results

    Args:
        api: Shodan API client
        contractor: Contractor dict with osint.onprem_network data
        ip_cache: Shared cache {ip: shodan_result} to avoid re-querying across contractors
        internetdb_cache: Shared cache {ip: internetdb_result} for screening
        delay: Seconds between Shodan API calls

    Returns:
        Dict with per-IP results and aggregate summary
    """
    if ip_cache is None:
        ip_cache = {}
    if internetdb_cache is None:
        internetdb_cache = {}

    ips = collect_onprem_ips(contractor)
    if not ips:
        return {
            "queried": True,
            "query_time": datetime.now(timezone.utc).isoformat(),
            "on_prem_ips_total": 0,
            "ips_with_ports": 0,
            "ips_enriched": 0,
            "hosts": [],
            "aggregate": _empty_aggregate(),
        }

    # Phase 1: InternetDB screening for IPs not yet screened
    screened = {}
    for ip in ips:
        if ip in internetdb_cache:
            if internetdb_cache[ip]:
                screened[ip] = internetdb_cache[ip]
        else:
            result = screen_ip_internetdb(ip)
            internetdb_cache[ip] = result
            if result and result.get("ports"):
                screened[ip] = result
            time.sleep(0.05)  # Gentle rate limit for InternetDB

    # Phase 2: Full Shodan lookup for IPs with ports
    hosts = []
    for ip in ips:
        if ip in ip_cache:
            if ip_cache[ip]:
                hosts.append(ip_cache[ip])
            continue

        if ip not in screened:
            ip_cache[ip] = None  # No ports, skip
            continue

        result = enrich_ip_shodan(api, ip)
        ip_cache[ip] = result
        if result:
            hosts.append(result)

        if delay > 0:
            time.sleep(delay)

    # Aggregate
    aggregate = _compute_aggregate(hosts)

    return {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "on_prem_ips_total": len(ips),
        "ips_with_ports": len(screened),
        "ips_enriched": len(hosts),
        "hosts": hosts,
        "aggregate": aggregate,
    }


def _empty_aggregate() -> dict:
    return {
        "total_services": 0,
        "total_vulns": 0,
        "unique_ports": [],
        "unique_products": [],
        "critical_findings": [],
        "ssl_issues": [],
        "os_list": [],
    }


def _compute_aggregate(hosts: list[dict]) -> dict:
    """Compute aggregate statistics across all enriched hosts."""
    if not hosts:
        return _empty_aggregate()

    all_ports = set()
    all_products = set()
    all_vulns = set()
    os_list = set()
    critical_findings = []
    ssl_issues = []
    total_services = 0

    # Dangerous ports that indicate critical exposure
    CRITICAL_PORTS = {
        3389: "RDP", 445: "SMB", 1433: "MSSQL", 3306: "MySQL",
        5432: "PostgreSQL", 6379: "Redis", 27017: "MongoDB",
        9200: "Elasticsearch", 5900: "VNC", 23: "Telnet",
        21: "FTP", 11211: "Memcached", 2049: "NFS",
    }

    for host in hosts:
        ip = host.get("ip", "")
        ports = host.get("ports", [])
        vulns = host.get("vulns", [])

        all_ports.update(ports)
        all_vulns.update(vulns)

        if host.get("os"):
            os_list.add(host["os"])

        for svc in host.get("services", []):
            total_services += 1
            product = svc.get("product", "")
            if product:
                all_products.add(product)

            port = svc.get("port")

            # Check for critical port exposure
            if port in CRITICAL_PORTS:
                critical_findings.append({
                    "ip": ip,
                    "port": port,
                    "service": CRITICAL_PORTS[port],
                    "product": product,
                    "severity": "critical",
                })

            # Check SSL issues
            if svc.get("ssl_expired"):
                ssl_issues.append({
                    "ip": ip,
                    "port": port,
                    "issue": "expired",
                    "subject": svc.get("ssl_subject", ""),
                    "expires": svc.get("ssl_expires", ""),
                })

    return {
        "total_services": total_services,
        "total_vulns": len(all_vulns),
        "unique_ports": sorted(all_ports),
        "unique_products": sorted(all_products),
        "critical_findings": critical_findings,
        "ssl_issues": ssl_issues,
        "os_list": sorted(os_list),
    }
