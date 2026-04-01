"""
Kill Chain Generator — MITRE ATT&CK-mapped attack path analysis.

Assembles all OSINT data for a contractor and generates a realistic
attack path using the Hermes 405B reasoning model. Each step is tagged
with MITRE ATT&CK tactics and techniques.

Usage:
    from backend.kill_chain import generate_kill_chain, assemble_contractor_intel
    intel = assemble_contractor_intel(contractor)
    kill_chain = await generate_kill_chain(hermes_client, intel)
"""

import json


# ─── MITRE ATT&CK Reference ─────────────────────────────────────
# Common techniques mapped to observable indicators
TECHNIQUE_MAP = {
    # Initial Access
    "exposed_ftp": {"tactic": "Initial Access", "technique": "T1190", "name": "Exploit Public-Facing Application", "detail": "FTP service exposed"},
    "exposed_rdp": {"tactic": "Initial Access", "technique": "T1133", "name": "External Remote Services", "detail": "RDP exposed to internet"},
    "exposed_ssh": {"tactic": "Initial Access", "technique": "T1133", "name": "External Remote Services", "detail": "SSH accessible from internet"},
    "exposed_smb": {"tactic": "Initial Access", "technique": "T1190", "name": "Exploit Public-Facing Application", "detail": "SMB/CIFS exposed"},
    "exposed_db": {"tactic": "Initial Access", "technique": "T1190", "name": "Exploit Public-Facing Application", "detail": "Database port exposed"},
    "no_dmarc": {"tactic": "Initial Access", "technique": "T1566.001", "name": "Spearphishing Attachment", "detail": "No DMARC policy enables email spoofing"},
    "weak_dmarc": {"tactic": "Initial Access", "technique": "T1566.002", "name": "Spearphishing Link", "detail": "DMARC=none allows domain spoofing"},
    "exposed_webmail": {"tactic": "Initial Access", "technique": "T1078", "name": "Valid Accounts", "detail": "Webmail login exposed for credential stuffing"},
    # Execution
    "exposed_admin_panel": {"tactic": "Execution", "technique": "T1059.004", "name": "Unix Shell", "detail": "Admin panel (cPanel/WHM) exposed"},
    # Credential Access
    "known_cves": {"tactic": "Credential Access", "technique": "T1212", "name": "Exploitation for Credential Access", "detail": "Known CVEs may yield credentials"},
    "expired_ssl": {"tactic": "Credential Access", "technique": "T1557", "name": "Adversary-in-the-Middle", "detail": "Expired SSL enables MITM attacks"},
    # Discovery
    "dns_exposure": {"tactic": "Discovery", "technique": "T1018", "name": "Remote System Discovery", "detail": "DNS records reveal internal topology"},
    "ct_subdomains": {"tactic": "Discovery", "technique": "T1596.003", "name": "Search Open Technical Databases", "detail": "CT logs expose subdomains"},
    # Lateral Movement
    "onprem_network": {"tactic": "Lateral Movement", "technique": "T1021", "name": "Remote Services", "detail": "On-premises IPs suggest flat network"},
    "vpn_endpoints": {"tactic": "Lateral Movement", "technique": "T1133", "name": "External Remote Services", "detail": "VPN endpoints may provide network access"},
    # Persistence
    "self_signed_ssl": {"tactic": "Persistence", "technique": "T1553.004", "name": "Install Root Certificate", "detail": "Self-signed certs = no certificate monitoring"},
    # Exfiltration
    "no_security_headers": {"tactic": "Exfiltration", "technique": "T1048", "name": "Exfiltration Over Alternative Protocol", "detail": "Missing security headers enable data extraction"},
}

# Port-to-risk mapping
CRITICAL_PORT_MAP = {
    21: "exposed_ftp", 22: "exposed_ssh", 23: "exposed_ftp",
    445: "exposed_smb", 3389: "exposed_rdp",
    1433: "exposed_db", 3306: "exposed_db", 5432: "exposed_db",
    6379: "exposed_db", 27017: "exposed_db", 9200: "exposed_db",
    5900: "exposed_rdp", 11211: "exposed_db", 2049: "exposed_smb",
}

ADMIN_PORTS = {2082, 2083, 2086, 2087, 8080, 8443, 9090, 10000}


def assemble_contractor_intel(contractor: dict) -> dict:
    """Extract all security-relevant data from a contractor into a structured intel brief."""
    osint = contractor.get("osint", {})
    shodan_ip = osint.get("shodan_ip", {})
    service_risk = osint.get("service_risk", {})
    dns = osint.get("dns", {})
    ct = osint.get("ct", {})
    web = osint.get("web", {})
    nvd = osint.get("nvd_cvss", {})
    onprem = osint.get("onprem_network", {})
    domain_info = osint.get("domain_verify", {}) or osint.get("domain_discovery", {})

    # Collect all services across hosts
    all_services = []
    all_vulns = set()
    all_ports = set()
    os_list = set()
    ssl_issues = []

    for host in shodan_ip.get("hosts", []):
        for svc in host.get("services", []):
            svc_entry = {**svc, "ip": host.get("ip", "")}
            all_services.append(svc_entry)
            all_ports.add(svc.get("port", 0))
            if svc.get("ssl_expired"):
                ssl_issues.append({"ip": host["ip"], "port": svc["port"], "subject": svc.get("ssl_subject", "")})
        all_vulns.update(host.get("vulns", []))
        if host.get("os"):
            os_list.add(host["os"])

    # Legacy Shodan data
    legacy_shodan = contractor.get("shodan", {})
    if legacy_shodan.get("total_hosts", 0) > 0:
        for v in legacy_shodan.get("vulns", []):
            all_vulns.add(v.get("cve", ""))
        for p in legacy_shodan.get("top_ports", []):
            all_ports.add(p.get("port", 0))

    # Identify attack vectors
    vectors = []
    for port in all_ports:
        if port in CRITICAL_PORT_MAP:
            key = CRITICAL_PORT_MAP[port]
            if key in TECHNIQUE_MAP:
                t = TECHNIQUE_MAP[key]
                svc_detail = next((s for s in all_services if s.get("port") == port), {})
                vectors.append({
                    **t,
                    "port": port,
                    "product": svc_detail.get("product", ""),
                    "version": svc_detail.get("version", ""),
                    "ip": svc_detail.get("ip", ""),
                })

    for port in all_ports:
        if port in ADMIN_PORTS:
            svc_detail = next((s for s in all_services if s.get("port") == port), {})
            title = svc_detail.get("http_title", "")
            vectors.append({
                **TECHNIQUE_MAP["exposed_admin_panel"],
                "port": port,
                "product": title or svc_detail.get("product", ""),
                "ip": svc_detail.get("ip", ""),
            })

    # Email security
    dmarc = dns.get("dmarc_policy", "")
    if dmarc in ("not_set", "none", ""):
        key = "no_dmarc" if dmarc in ("not_set", "") else "weak_dmarc"
        vectors.append({**TECHNIQUE_MAP[key], "evidence": f"DMARC={dmarc or 'not_set'}"})

    # SSL issues
    if ssl_issues:
        vectors.append({
            **TECHNIQUE_MAP["expired_ssl"],
            "evidence": f"{len(ssl_issues)} expired certificate(s)",
            "details": ssl_issues[:3],
        })

    # Network topology exposure
    if ct.get("subdomains"):
        n_subs = len(ct["subdomains"])
        vectors.append({
            **TECHNIQUE_MAP["ct_subdomains"],
            "evidence": f"{n_subs} subdomains discovered via CT logs",
        })

    onprem_count = onprem.get("on_prem_count", 0)
    if onprem_count > 1:
        vectors.append({
            **TECHNIQUE_MAP["onprem_network"],
            "evidence": f"{onprem_count} on-premises IPs identified",
        })

    # VPN/auth endpoints
    infra_hints = ct.get("infrastructure_hints", {})
    vpn_endpoints = infra_hints.get("vpn", [])
    auth_endpoints = infra_hints.get("auth", [])
    if vpn_endpoints or auth_endpoints:
        vectors.append({
            **TECHNIQUE_MAP["vpn_endpoints"],
            "evidence": f"{len(vpn_endpoints)} VPN + {len(auth_endpoints)} auth endpoints found",
        })

    # Web security
    web_score = web.get("security_score", 100)
    if web_score < 50:
        vectors.append({
            **TECHNIQUE_MAP["no_security_headers"],
            "evidence": f"Security score: {web_score}/100",
        })

    # CVEs
    if all_vulns:
        top_cves = sorted(all_vulns, key=lambda v: nvd.get("scores", {}).get(v, {}).get("score", 0) or 0, reverse=True)[:10]
        max_cvss = nvd.get("max_score", 0)
        vectors.append({
            **TECHNIQUE_MAP["known_cves"],
            "evidence": f"{len(all_vulns)} CVEs (max CVSS: {max_cvss})",
            "top_cves": top_cves,
        })

    # Collect all on-prem IPs for explicit listing in prompt
    onprem_ips = onprem.get("on_prem_ips", [])

    return {
        "name": contractor.get("name", ""),
        "city": contractor.get("city", ""),
        "state": contractor.get("state", ""),
        "category": contractor.get("category", ""),
        "domain": domain_info.get("domain", ""),
        "obligation": contractor.get("obligation", 0),
        "risk_score": None,  # Computed by frontend
        "vectors": vectors,
        "services_count": len(all_services),
        "vulns_count": len(all_vulns),
        "onprem_count": onprem_count,
        "onprem_ips": onprem_ips[:50],  # Explicit IP list for prompt
        "dmarc": dmarc,
        "web_score": web_score,
        "os_list": sorted(os_list),
        "ssl_issues_count": len(ssl_issues),
        "all_services": all_services[:20],  # Cap for prompt size
        "all_vulns": sorted(all_vulns)[:20],
    }


# ─── Kill Chain LLM Prompt ───────────────────────────────────────

KILL_CHAIN_SYSTEM_PROMPT = """\
You are a MITRE ATT&CK kill chain analyst for DOE contractor security assessments. \
You receive structured intelligence about a contractor's attack surface and generate \
a realistic, step-by-step attack path that an adversary could follow.

RULES:
1. ONLY use facts from the provided INTEL data. Never invent services, ports, IPs, or CVEs.
2. Each step must reference a specific MITRE ATT&CK tactic and technique ID.
3. Chain steps logically — each step should enable or lead to the next.
4. ALWAYS include specific IP addresses and port numbers. Use the ON-PREM IPs and EXPOSED SERVICES lists. NEVER say "undisclosed IP" or "unknown address" — always cite a real IP from the data.
5. Be concrete: "Exploit CVE-2023-44487 on nginx at 203.161.63.192:443" not "exploit a vulnerability."
6. Output valid JSON matching the schema below.
7. In the "evidence" field, always include the specific IP:port combination.

OUTPUT JSON SCHEMA:
{
  "summary": "One paragraph executive summary of the overall threat",
  "risk_level": "critical|high|medium|low",
  "steps": [
    {
      "step": 1,
      "tactic": "MITRE ATT&CK Tactic name",
      "technique_id": "T1234.001",
      "technique_name": "Technique Name",
      "description": "What the attacker does in this step",
      "evidence": "Specific data from INTEL supporting this step",
      "impact": "What this achieves for the attacker"
    }
  ],
  "remediation": [
    {"priority": 1, "action": "Specific remediation action", "impact": "What this prevents"}
  ]
}
"""


def build_kill_chain_prompt(intel: dict) -> list[dict]:
    """Build the LLM message chain for kill chain generation."""
    # Format vectors as readable text
    vector_text = ""
    for v in intel["vectors"]:
        line = f"- [{v['tactic']}] {v['technique']}: {v['name']}"
        if v.get("port"):
            line += f" (port {v['port']}"
            if v.get("product"):
                line += f", {v['product']} {v.get('version', '')}"
            if v.get("ip"):
                line += f" @ {v['ip']}"
            line += ")"
        if v.get("evidence"):
            line += f" — {v['evidence']}"
        vector_text += line + "\n"

    # Format services
    svc_text = ""
    for s in intel.get("all_services", [])[:15]:
        product = f"{s.get('product', '')} {s.get('version', '')}".strip()
        svc_text += f"  {s.get('ip','')}:{s['port']}/{s.get('transport','tcp')} {product}"
        if s.get("http_title"):
            svc_text += f" [{s['http_title'][:40]}]"
        if s.get("ssl_expired"):
            svc_text += " [SSL EXPIRED]"
        svc_text += "\n"

    user_content = f"""CONTRACTOR INTEL BRIEF:
Name: {intel['name']}
Location: {intel['city']}, {intel['state']}
Category: {intel['category']}
Domain: {intel['domain']}
Federal Obligation: ${intel['obligation']:,.0f}
DMARC Policy: {intel['dmarc'] or 'not_set'}
Web Security Score: {intel['web_score']}/100
Total Services Exposed: {intel['services_count']}
Total CVEs: {intel['vulns_count']}
SSL Issues: {intel['ssl_issues_count']} expired cert(s)
OS Detected: {', '.join(intel['os_list']) or 'unknown'}

ON-PREM IP ADDRESSES (use these exact IPs in your kill chain steps):
{chr(10).join('  ' + ip for ip in intel.get('onprem_ips', [])) or '  none identified'}

ATTACK VECTORS IDENTIFIED:
{vector_text}
EXPOSED SERVICES (IP:port/protocol product):
{svc_text}
TOP CVEs: {', '.join(intel.get('all_vulns', [])[:10]) or 'none identified'}

Generate a detailed kill chain with 4-8 steps. ALWAYS reference specific IP addresses from the ON-PREM IPs or EXPOSED SERVICES lists above. Never use generic phrases like "undisclosed IP" — cite the real IP."""

    return [
        {"role": "system", "content": KILL_CHAIN_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


async def generate_kill_chain(hermes_client, intel: dict) -> dict:
    """Generate a kill chain using Hermes 405B.

    Args:
        hermes_client: HermesClient instance
        intel: Output from assemble_contractor_intel()

    Returns:
        Parsed kill chain dict with steps, summary, remediation
    """
    messages = build_kill_chain_prompt(intel)

    try:
        # Try structured output first
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "risk_level": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "integer"},
                            "tactic": {"type": "string"},
                            "technique_id": {"type": "string"},
                            "technique_name": {"type": "string"},
                            "description": {"type": "string"},
                            "evidence": {"type": "string"},
                            "impact": {"type": "string"},
                        },
                        "required": ["step", "tactic", "technique_id", "technique_name", "description", "evidence", "impact"],
                    },
                },
                "remediation": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "priority": {"type": "integer"},
                            "action": {"type": "string"},
                            "impact": {"type": "string"},
                        },
                        "required": ["priority", "action", "impact"],
                    },
                },
            },
            "required": ["summary", "risk_level", "steps", "remediation"],
        }

        result = await hermes_client.chat_structured(messages, schema, max_tokens=4096)
        return result

    except Exception:
        # Fallback to regular chat + JSON parsing
        try:
            raw = await hermes_client.chat(messages, max_tokens=4096)
            # Extract JSON from response (may be wrapped in markdown)
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]
            return json.loads(json_str)
        except Exception as e:
            return {
                "summary": f"Kill chain generation failed: {e}",
                "risk_level": "unknown",
                "steps": [],
                "remediation": [],
                "error": str(e),
            }
