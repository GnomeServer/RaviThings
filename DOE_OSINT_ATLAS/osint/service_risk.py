"""
Dangerous service classifier — flag high-risk services exposed to the internet.

Classifies Shodan port/service data into danger levels without any external
API calls.  Designed to make security posture immediately obvious in the
contractor intelligence map.

Danger levels:
  critical — services that should NEVER be internet-facing (RDP, SMB, databases)
  high     — services frequently targeted with known exploits
  medium   — services that leak information or have weak auth by default
  info     — notable but not directly dangerous
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Service classification database
# ---------------------------------------------------------------------------

_DANGEROUS_SERVICES: dict[int, dict[str, Any]] = {
    # CRITICAL — should never be internet-facing
    3389: {"name": "RDP", "danger": "critical", "reason": "Remote Desktop — BlueKeep, brute force, lateral movement"},
    445:  {"name": "SMB", "danger": "critical", "reason": "Server Message Block — EternalBlue, WannaCry, ransomware vector"},
    1433: {"name": "MSSQL", "danger": "critical", "reason": "Microsoft SQL Server — default credentials, SQL injection pivot"},
    3306: {"name": "MySQL", "danger": "critical", "reason": "MySQL — often has weak/no auth when exposed"},
    5432: {"name": "PostgreSQL", "danger": "critical", "reason": "PostgreSQL — database exfiltration risk"},
    1521: {"name": "Oracle DB", "danger": "critical", "reason": "Oracle Database — high-value target, known exploits"},
    27017: {"name": "MongoDB", "danger": "critical", "reason": "MongoDB — frequently left without authentication"},
    6379: {"name": "Redis", "danger": "critical", "reason": "Redis — no auth by default, RCE via SLAVEOF"},
    9200: {"name": "Elasticsearch", "danger": "critical", "reason": "Elasticsearch — unauthenticated data access by default"},
    11211: {"name": "Memcached", "danger": "critical", "reason": "Memcached — DDoS amplification, data exfiltration"},
    5900: {"name": "VNC", "danger": "critical", "reason": "VNC — remote framebuffer, weak auth common"},
    5901: {"name": "VNC-1", "danger": "critical", "reason": "VNC display :1 — same risks as 5900"},
    2375: {"name": "Docker API", "danger": "critical", "reason": "Docker daemon — unauthenticated container escape to host"},
    2376: {"name": "Docker TLS", "danger": "critical", "reason": "Docker TLS — container management, potential host escape"},
    9042: {"name": "Cassandra", "danger": "critical", "reason": "Cassandra CQL — NoSQL database, often no auth"},

    # HIGH — frequently targeted
    21:   {"name": "FTP", "danger": "high", "reason": "FTP — cleartext credentials, anonymous access, bounce attacks"},
    23:   {"name": "Telnet", "danger": "high", "reason": "Telnet — cleartext everything, default credentials on IoT"},
    25:   {"name": "SMTP", "danger": "high", "reason": "SMTP — open relay testing, email spoofing, user enumeration"},
    110:  {"name": "POP3", "danger": "high", "reason": "POP3 — cleartext email retrieval, credential sniffing"},
    143:  {"name": "IMAP", "danger": "high", "reason": "IMAP — cleartext email access, credential exposure"},
    161:  {"name": "SNMP", "danger": "high", "reason": "SNMP — community strings leak device configs and credentials"},
    389:  {"name": "LDAP", "danger": "high", "reason": "LDAP — directory enumeration, credential harvesting"},
    636:  {"name": "LDAPS", "danger": "high", "reason": "LDAP/SSL — directory service, user enumeration"},
    1883: {"name": "MQTT", "danger": "high", "reason": "MQTT — IoT message broker, often unauthenticated"},
    5672: {"name": "AMQP", "danger": "high", "reason": "RabbitMQ — message queue, potential data interception"},
    8081: {"name": "HTTP-Alt", "danger": "high", "reason": "HTTP alt port — often admin panels, APIs without auth"},
    9090: {"name": "Prometheus", "danger": "high", "reason": "Prometheus — metrics exposure, internal topology leaks"},
    2181: {"name": "Zookeeper", "danger": "high", "reason": "ZooKeeper — cluster coordination, config exposure"},
    8888: {"name": "HTTP-8888", "danger": "high", "reason": "Jupyter/admin — common for exposed notebooks and admin UIs"},

    # MEDIUM — information leakage or weak defaults
    8080: {"name": "HTTP-Proxy", "danger": "medium", "reason": "HTTP proxy/alt — often development servers, admin panels"},
    8443: {"name": "HTTPS-Alt", "danger": "medium", "reason": "HTTPS alt — management interfaces, self-signed certs"},
    53:   {"name": "DNS", "danger": "medium", "reason": "DNS — zone transfer risk, amplification attacks"},
    69:   {"name": "TFTP", "danger": "medium", "reason": "TFTP — unauthenticated file transfer, config exposure"},
    123:  {"name": "NTP", "danger": "medium", "reason": "NTP — amplification DDoS, monlist info leak"},
    502:  {"name": "Modbus", "danger": "medium", "reason": "Modbus — industrial control, no authentication by design"},
    1900: {"name": "UPnP", "danger": "medium", "reason": "UPnP — network device discovery, attack surface expansion"},
    5060: {"name": "SIP", "danger": "medium", "reason": "SIP — VoIP, toll fraud, eavesdropping"},
    47808: {"name": "BACnet", "danger": "medium", "reason": "BACnet — building automation, no auth by design"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_services(contractor: dict) -> dict[str, Any]:
    """Classify a contractor's exposed services by danger level.

    Parameters
    ----------
    contractor : dict
        Contractor record with 'shodan' and optionally 'osint.enhanced_shodan' data.

    Returns
    -------
    dict with standard enrichment schema:
        queried: bool
        query_time: str
        total_services: int
        dangerous_services: list[dict]  — sorted by danger level
        danger_summary: dict  — {critical: N, high: N, medium: N}
        max_danger: str  — highest danger level found
        error: str | None
    """
    result: dict[str, Any] = {
        "queried": True,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "total_services": 0,
        "dangerous_services": [],
        "danger_summary": {"critical": 0, "high": 0, "medium": 0},
        "max_danger": "none",
        "error": None,
    }

    # Build a map of port -> product banner from per-IP Shodan data
    # This lets us override port-based labels with actual product identification
    osint = contractor.get("osint", {})
    port_products: dict[int, str] = {}  # port -> product name from Shodan banner
    sip = osint.get("shodan_ip", {})
    for host in sip.get("hosts", []):
        for svc in host.get("services", []):
            port = svc.get("port", 0)
            product = svc.get("product", "")
            if port and product:
                port_products[port] = product

    # Collect all exposed ports
    seen_ports: set[int] = set()
    port_counts: dict[int, int] = {}

    shodan = contractor.get("shodan", {})
    for p in shodan.get("top_ports", []):
        port = p.get("port", 0) if isinstance(p, dict) else 0
        if port:
            seen_ports.add(port)
            port_counts[port] = max(port_counts.get(port, 0), p.get("count", 1))

    # Also check enhanced Shodan
    es = osint.get("enhanced_shodan", {})
    for p in es.get("top_ports", []):
        port = p.get("port", 0) if isinstance(p, dict) else 0
        if port:
            seen_ports.add(port)
            port_counts[port] = max(port_counts.get(port, 0), p.get("count", 1))

    # Also scan per-IP hosts for ports
    for host in sip.get("hosts", []):
        for p in host.get("ports", []):
            if p:
                seen_ports.add(p)

    # Also scan sample hosts for additional ports
    for host in shodan.get("sample_hosts", []):
        port = host.get("port", 0)
        if port:
            seen_ports.add(port)

    result["total_services"] = len(seen_ports)

    # Services that indicate the port-based label is WRONG
    # (e.g., OpenSSH on port 1433 is NOT MSSQL)
    _SSH_PRODUCTS = {"OpenSSH", "Dropbear"}
    _HTTP_PRODUCTS = {"nginx", "Apache httpd", "Microsoft IIS httpd", "lighttpd"}

    # Classify — using product banner to override port-based labels
    danger_order = {"critical": 0, "high": 1, "medium": 2}
    dangerous = []

    for port in sorted(seen_ports):
        svc = _DANGEROUS_SERVICES.get(port)
        if svc:
            product = port_products.get(port, "")
            svc_name = svc["name"]
            danger = svc["danger"]
            reason = svc["reason"]

            # Check for product mismatch — SSH on a database port is NOT a database
            if product:
                product_base = product.split()[0] if product else ""
                is_ssh = any(p in product for p in _SSH_PRODUCTS)
                is_http = any(p in product for p in _HTTP_PRODUCTS)

                # If Shodan says it's SSH but the port says database/RDP → override
                if is_ssh and svc_name in ("MSSQL", "MySQL", "PostgreSQL", "Redis",
                                           "MongoDB", "RDP", "VNC", "Elasticsearch",
                                           "Cassandra", "Oracle DB", "Memcached"):
                    svc_name = f"SSH-on-:{port}"
                    danger = "medium"
                    reason = f"SSH ({product}) on non-standard port {port} — tunneling or misconfig, not {svc['name']}"

                # If Shodan says it's HTTP but port says database → override
                elif is_http and svc_name in ("MSSQL", "MySQL", "PostgreSQL", "Redis",
                                              "MongoDB", "Elasticsearch", "Cassandra"):
                    svc_name = f"HTTP-on-:{port}"
                    danger = "medium"
                    reason = f"HTTP ({product}) on port {port} — web service, not {svc['name']}"

            dangerous.append({
                "port": port,
                "name": svc_name,
                "danger": danger,
                "reason": reason,
                "host_count": port_counts.get(port, 1),
                "product": product,  # Include the actual product for transparency
            })
            result["danger_summary"][svc["danger"]] += 1

    # Sort: critical first, then high, then medium
    dangerous.sort(key=lambda d: danger_order.get(d["danger"], 99))
    result["dangerous_services"] = dangerous

    # Determine max danger
    if result["danger_summary"]["critical"] > 0:
        result["max_danger"] = "critical"
    elif result["danger_summary"]["high"] > 0:
        result["max_danger"] = "high"
    elif result["danger_summary"]["medium"] > 0:
        result["max_danger"] = "medium"

    return result
