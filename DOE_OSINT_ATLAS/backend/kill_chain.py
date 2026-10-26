"""
Kill Chain Generator — MITRE ATT&CK-mapped attack path analysis.

Assembles all OSINT data for a contractor and generates a realistic
attack path using the GLM-5.3 reasoning model. Each step is tagged
with MITRE ATT&CK tactics and techniques.

Step detail generation is extracted here so both the web map
(/api/step-detail) and desktop sidecar (POST /step-detail + Tauri)
share the single prompt and red-team extension handling.

Usage:
    from backend.kill_chain import generate_kill_chain, assemble_contractor_intel, generate_step_detail
    intel = assemble_contractor_intel(contractor)
    kill_chain = await generate_kill_chain(llm_client, intel)
    detail = await generate_step_detail(llm_client, intel, step)
"""

import json
import os
import pathlib
import re
from typing import Callable

from backend.jev import verify_kill_chain
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

    # Hosting context from per-IP Shodan data
    hosting_context = []
    for host in shodan_ip.get("hosts", []):
        org = host.get("org", "")
        ip = host.get("ip", "")
        if org and ip:
            hosting_context.append(f"{ip}: {org}")

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
        "hosting_context": hosting_context,
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

    # Build hosting context section
    hosting_section = ""
    if intel.get('hosting_context'):
        hosting_lines = ["HOSTING CONTEXT (note: services on third-party hosting providers affect the attack path):"]
        for entry in intel['hosting_context']:
            hosting_lines.append(f"  {entry}")
        hosting_section = chr(10).join(hosting_lines) + chr(10)

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

{hosting_section}ATTACK VECTORS IDENTIFIED:
{vector_text}
EXPOSED SERVICES (IP:port/protocol product):
{svc_text}
TOP CVEs: {', '.join(intel.get('all_vulns', [])[:10]) or 'none identified'}

Generate a detailed kill chain with 4-8 steps. ALWAYS reference specific IP addresses from the ON-PREM IPs or EXPOSED SERVICES lists above. Never use generic phrases like "undisclosed IP" — cite the real IP."""

    return [
        {"role": "system", "content": KILL_CHAIN_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _progress_stage(on_progress, stage: str, message: str) -> None:
    if on_progress is not None:
        on_progress({"type": "stage", "stage": stage, "message": message})


async def generate_kill_chain(
    llm_client, intel: dict, *, on_progress: Callable[[dict], None] | None = None,
) -> dict:
    """Generate a kill chain using GLM-5.3.

    Args:
        llm_client: GLMClient instance
        intel: Output from assemble_contractor_intel()

    Returns:
        Parsed kill chain dict with steps, summary, remediation
    """
    _progress_stage(on_progress, "preparing", "Preparing kill chain analysis")
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

        result = await llm_client.chat_structured(messages, schema, max_tokens=4096)
        _progress_stage(on_progress, "verifying", "Verifying kill chain evidence")
        return await verify_kill_chain(result, intel)

    except Exception:
        # Fallback to regular chat + JSON parsing
        try:
            raw = await llm_client.chat(messages, max_tokens=4096)
            _progress_stage(on_progress, "parsing", "Parsing model output")
            # Extract JSON from response (may be wrapped in markdown)
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]
            chain = json.loads(json_str)
            _progress_stage(on_progress, "verifying", "Verifying kill chain evidence")
            return await verify_kill_chain(chain, intel)
        except Exception as e:
            return {
                "summary": f"Kill chain generation failed: {e}",
                "risk_level": "unknown",
                "steps": [],
                "remediation": [],
                "error": str(e),
            }

# ─── Step Detail Prompt & Generator (single source) ────────────────────────
# Extracted from test_atlas_server.py step_detail_endpoint and full-assessment
# stream. Both the web server and the desktop sidecar now call this so the
# prompt text, red-team injection, and JSON salvage live in one place only.

STEP_DETAIL_SYSTEM_PROMPT = """\
You are a defensive security analyst providing detailed technical analysis of a \
specific attack vector identified in a DOE contractor's infrastructure. Your goal \
is to help defenders understand the vulnerability deeply so they can protect against it.

For the given kill chain step, provide:

1. VULNERABILITY ANALYSIS: What the weakness is, why it exists, what versions are affected
2. WHAT AN ATTACKER SEES: The exact banner/response an attacker would observe (from our Shodan data)
3. DETECTION: How to detect if this vector is being probed or exploited (Snort/Sigma rules, log patterns)
4. REMEDIATION: Specific commands to fix this on this exact system (firewall rules, config changes, patches)
5. REFERENCES: Links to CVE advisories, CISA alerts, vendor bulletins, MITRE ATT&CK page

RULES:
- Be specific to the exact IP, port, service version, and CVE provided
- Include concrete detection signatures and remediation commands
- Reference only real CVEs and advisories
- Output valid JSON matching the schema

OUTPUT JSON:
{
  "vulnerability": {"description": "...", "affected_versions": "...", "cvss": "...", "cwe": "..."},
  "attacker_view": {"banner": "...", "what_they_see": "..."},
  "detection": {"signatures": ["..."], "log_indicators": ["..."], "monitoring_advice": "..."},
  "remediation": {"immediate": ["..."], "long_term": ["..."], "commands": ["..."]},
  "references": [{"title": "...", "url": "..."}],
  "alternative_vectors": ["Description of other ways this service could be attacked"]
}
"""

# === AUTHORIZED RED TEAM PROMPT EXTENSION ===
# Loaded from RED_TEAM_PROMPT.json if present, or RED_TEAM_PROMPT env var as fallback.
# The backend LLM (GLM-5.3) executes this in your controlled environment.
_RED_TEAM_EXTENSION = ""
_rt_path = pathlib.Path(__file__).parent.parent / "RED_TEAM_PROMPT.json"
if _rt_path.exists():
    try:
        import json as _rtjson
        _rt_data = _rtjson.loads(_rt_path.read_text())
        # Support both {"prompt": "..."} and structured JSON (serialize as context)
        if isinstance(_rt_data, dict) and "prompt" in _rt_data:
            _RED_TEAM_EXTENSION = _rt_data["prompt"]
        elif isinstance(_rt_data, dict):
            _RED_TEAM_EXTENSION = (
                "AUTHORIZED RED TEAM ANALYSIS FRAMEWORK:\n"
                + _rtjson.dumps(_rt_data, indent=2)
            )
        else:
            _RED_TEAM_EXTENSION = str(_rt_data)
    except Exception:
        pass
if not _RED_TEAM_EXTENSION:
    _RED_TEAM_EXTENSION = os.environ.get("RED_TEAM_PROMPT", "")


async def generate_step_detail(
    llm, intel: dict, step: dict, *, on_progress: Callable[[dict], None] | None = None,
) -> dict:
    """Generate detailed analysis for a specific kill chain step.

    This central implementation is called by:
    - test_atlas_server.py /api/step-detail and the full-assessment SSE stream
    - desktop/sidecar.py POST /step-detail

    Keeps identical prompt text, red-team extension substitutions (when active),
    and the markdown-fence / brace-slice / raw-fallback JSON salvage behavior.
    Returns the keys expected by the map overlay and desktop dossier:
    vulnerability, attacker_view, detection, remediation, references,
    and red_team (populated only when the red-team extension is active).
    """
    import json as _json

    _progress_stage(on_progress, "preparing", "Preparing step analysis")
    # Build the user prompt with step context + contractor intel (exact copy of prior logic)
    svc_lines = "\n".join(
        f"  {s.get('ip','')}:{s['port']}/{s.get('transport','tcp')} "
        f"{s.get('product','')} {s.get('version','')}"
        for s in intel.get("all_services", [])[:15]
    )

    user_content = f"""KILL CHAIN STEP TO ANALYZE:
Tactic: {step.get('tactic', '')}
Technique: {step.get('technique_id', '')} — {step.get('technique_name', '')}
Description: {step.get('description', '')}
Evidence: {step.get('evidence', '')}

CONTRACTOR: {intel['name']} ({intel['city']}, {intel['state']})
Domain: {intel['domain']}

ON-PREM IPs:
{chr(10).join('  ' + ip for ip in intel.get('onprem_ips', [])[:20])}

EXPOSED SERVICES:
{svc_lines}

TOP CVEs: {', '.join(intel.get('all_vulns', [])[:15])}

Provide a complete defensive analysis of this specific step."""

    system_prompt = STEP_DETAIL_SYSTEM_PROMPT

    if _RED_TEAM_EXTENSION:
        # Dynamically substitute placeholders with real step data
        rt_context = _RED_TEAM_EXTENSION

        # Extract the primary IP and port from the step evidence
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', step.get('evidence', '') + ' ' + step.get('description', ''))
        port_match = re.search(r':(\d+)', step.get('evidence', '') + ' ' + step.get('description', ''))
        target_ip = ip_match.group(1) if ip_match else (intel.get('onprem_ips', [''])[0] if intel.get('onprem_ips') else '')
        target_port = port_match.group(1) if port_match else ''

        # Find the matching service for product/version info
        target_svc = next(
            (s for s in intel.get('all_services', [])
             if str(s.get('port')) == target_port or s.get('ip') == target_ip),
            {}
        )
        target_product = f"{target_svc.get('product', '')} {target_svc.get('version', '')}".strip()

        # Map MITRE tactic to the relevant red team phase
        tactic_to_phase = {
            'Initial Access': 'reconnaissance + vulnerability_identification',
            'Execution': 'vulnerability_exploitation',
            'Credential Access': 'vulnerability_exploitation + exploitation',
            'Lateral Movement': 'post_exploitation',
            'Persistence': 'post_exploitation',
        }
        relevant_phase = tactic_to_phase.get(step.get('tactic', ''), 'vulnerability_identification')

        # Perform substitutions
        rt_context = rt_context.replace('TARGET_IP_HERE', target_ip)
        rt_context = rt_context.replace('TARGET_PROTOCOL_HERE', target_svc.get('transport', 'tcp'))
        rt_context = rt_context.replace('TARGET_URL_HERE', f'http://{target_ip}:{target_port}' if target_port else f'http://{target_ip}')
        rt_context = rt_context.replace('PORT_RANGE', target_port or '1-65535')
        rt_context = rt_context.replace('SERVICE_NAME', target_product or 'unknown')

        system_prompt += f"\n\n{rt_context}"
        system_prompt += f"\n\nFOCUS: This step maps to red team phase(s): {relevant_phase}. "
        system_prompt += f"Target: {target_ip}:{target_port} running {target_product}. "
        system_prompt += "Provide phase-specific tool commands and techniques for THIS exact target. "
        system_prompt += "Add a 'red_team' key to your JSON output with: {\"tools\": [...], \"commands\": [...], \"techniques\": [...]}. "
        system_prompt += "IMPORTANT: In JSON strings, escape all backslashes as \\\\. Do not use raw \\n or \\t in string values."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    if getattr(llm, "is_available", lambda: False)():
        try:
            raw = await llm.chat(messages, max_tokens=None, reasoning_effort="low")
            _progress_stage(on_progress, "parsing", "Parsing step analysis")
            # Parse JSON from response
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]

            # Robust JSON parsing — handle LLM escape issues
            try:
                result = _json.loads(json_str)
            except _json.JSONDecodeError:
                # Fix common LLM JSON errors: unescaped backslashes
                fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)
                try:
                    result = _json.loads(fixed)
                except _json.JSONDecodeError:
                    # Try finding first { to last }
                    brace_start = json_str.find('{')
                    brace_end = json_str.rfind('}')
                    if brace_start >= 0 and brace_end > brace_start:
                        subset = json_str[brace_start:brace_end+1]
                        # Remove control characters that break JSON
                        subset = re.sub(r'[\x00-\x1f]', ' ', subset)
                        try:
                            result = _json.loads(subset)
                        except _json.JSONDecodeError:
                            # Truly broken — return raw as vulnerability description
                            result = {
                                "vulnerability": {"description": raw[:2000]},
                                "detection": {"signatures": [], "log_indicators": [], "monitoring_advice": "See raw analysis above."},
                                "remediation": {"immediate": [], "long_term": [], "commands": []},
                                "references": [],
                            }
                    else:
                        result = {
                            "vulnerability": {"description": raw[:2000]},
                            "detection": {"signatures": [], "log_indicators": [], "monitoring_advice": ""},
                            "remediation": {"immediate": [], "long_term": [], "commands": []},
                            "references": [],
                        }
            return result
        except Exception as e:
            return {
                "vulnerability": {"description": f"Analysis generation failed: {e}"},
                "error": str(e),
                "detection": {"signatures": [], "log_indicators": [], "monitoring_advice": ""},
                "remediation": {"immediate": [], "long_term": [], "commands": []},
                "references": [],
                "alternative_vectors": [],
            }
    else:
        return {
            "vulnerability": {"description": "GLM-5.3 not available for detailed analysis."},
            "error": "GLM-5.3 not available for detailed analysis.",
            "detection": {"signatures": [], "log_indicators": [], "monitoring_advice": "Enable logging on this service."},
            "remediation": {"immediate": ["Block this port at the firewall"], "long_term": ["Patch to latest version"], "commands": []},
            "references": [{"title": "MITRE ATT&CK", "url": f"https://attack.mitre.org/techniques/{step.get('technique_id', 'T1190')}/"}],
            "alternative_vectors": [],
        }
