"""Test server for Atlas — uses real Hermes/Ollama for chat, no ChromaDB dependency."""
import asyncio
import json
import os
import pathlib

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.responses import StreamingResponse

load_dotenv()

app = FastAPI()
BASE = pathlib.Path(__file__).parent

# Try to import LLM clients
from backend.mercury_client import HermesClient
from backend.ollama_client import OllamaClient

hermes = HermesClient()
ollama = OllamaClient()

_ATLAS_SYSTEM_PROMPT = """\
You are the OSINT Atlas Intelligence Analyst for DOE contractor security. You have access to \
intelligence data on 2,214 DOE contractors including their network exposure, vulnerabilities, and infrastructure.

You answer questions about the contractor data AND emit map commands to visualize your answers.

CONTRACTOR DATA SCHEMA (each contractor has these fields):
- name, city, state, zip, lat, lon, category
- obligation (federal dollars), contract_count
- shodan.total_hosts, shodan.top_ports[{port,count}], shodan.vulns[{cve,count}], shodan.sample_hosts[{ip,port,product}]
- osint.dns.dmarc_policy (reject|quarantine|none|not_set), osint.dns.mail_provider, osint.dns.dns_provider
- osint.ct.subdomains[], osint.ct.infrastructure_hints.vpn[], osint.ct.infrastructure_hints.auth[]
- osint.web.security_score (0-100), osint.web.server, osint.web.cms
- osint.service_risk.max_danger (critical|high|medium|none), osint.service_risk.dangerous_services[{port,name,danger,reason}]
- osint.nvd_cvss.max_score, osint.nvd_cvss.max_severity, osint.nvd_cvss.summary.{critical,high,medium,low}
- osint.onprem_network.on_prem_count, osint.onprem_network.cloud_count, osint.onprem_network.on_prem_percentage

CATEGORIES: Research & Labs, IT & Cyber, Construction & Facilities, Engineering, Environmental, \
Security & Defense, Manufacturing, Management & Consulting, Energy & Utilities, Transportation & Logistics, Other Services

KEY STATS:
- 483 contractors with internet-exposed hosts
- 237 with critical CVEs, 1,456 with no DMARC policy
- 22 with CRITICAL dangerous services (RDP, SMB, databases exposed)
- 1,585 with on-premises IPs identified (49,463 on-prem IPs total)

MAP COMMANDS — emit these as JSON on a line by itself, prefixed with MAP_CMD:
The frontend will execute these to manipulate the map in real-time.

Available commands:
- MAP_CMD:{"action":"fly_to","lat":39.5,"lon":-105.0,"zoom":8}
- MAP_CMD:{"action":"filter","field":"state","value":"CO","op":"eq"}
- MAP_CMD:{"action":"filter","field":"osint.service_risk.max_danger","value":"critical","op":"eq"}
- MAP_CMD:{"action":"filter","field":"shodan.total_hosts","value":0,"op":"gt"}
- MAP_CMD:{"action":"filter","field":"category","value":"Manufacturing","op":"eq"}
- MAP_CMD:{"action":"filter","field":"name","value":"battery","op":"contains"}
- MAP_CMD:{"action":"reset"}
- MAP_CMD:{"action":"open_panel","contractor_index":42}

Filter operators: eq, contains, gt, gte, lt, exists
Field paths use dot notation into the contractor JSON.

CRITICAL ANTI-HALLUCINATION RULES:
- You will receive a CONTRACTOR DATA block with real contractor records. ONLY cite contractors, IPs, CVEs, ports, and risk scores that appear in this data block.
- NEVER invent, fabricate, or guess contractor names, IP addresses, CVE numbers, port numbers, or vulnerability details.
- If the user asks about something not in the provided data, say "I don't have data on that" rather than guessing.
- Every factual claim you make must trace to a specific field in the CONTRACTOR DATA block.

MAP COMMAND RULES:
1. Always emit MAP_CMD commands BEFORE your text explanation so the map updates first
2. Use fly_to when discussing a geographic area or specific contractor location
3. Use filter when the user wants to see a subset of contractors
4. Use reset before applying new filters to clear previous state
5. When mentioning a specific contractor, ALWAYS emit open_panel with their [index] number from the data
6. ALWAYS fly_to the contractor's lat/lon AND open_panel so the user sees both map position and details

RESPONSE RULES:
7. Be specific with numbers — cite actual counts from the data
8. Keep answers concise but impactful — this is a security briefing tool
9. When asked about "highest risk" or "most dangerous", sort by the risk= field in the data
10. Cite the specific data fields: risk score, danger level, DMARC policy, exposed services, CVE count
"""


class AtlasChatRequest(BaseModel):
    query: str
    messages: list[dict] = []
    contractor_count: int = 0
    data_context: str = ""


@app.get("/atlas")
async def atlas():
    return FileResponse(BASE / "frontend" / "static" / "contractor-map.html")


@app.get("/contractors.json")
async def contractors():
    return FileResponse(BASE / "frontend" / "static" / "contractors.json")


class KillChainRequest(BaseModel):
    contractor_index: int


class StepDetailRequest(BaseModel):
    contractor_index: int
    step: dict  # The kill chain step object


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
# The backend LLM (Hermes 405B) executes this in your controlled environment.
_RED_TEAM_EXTENSION = ""
_rt_path = BASE / "RED_TEAM_PROMPT.json"
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
        print(f"Red team prompt loaded from {_rt_path} ({len(_RED_TEAM_EXTENSION)} chars)")
    except Exception as _e:
        print(f"Warning: could not load {_rt_path}: {_e}")
if not _RED_TEAM_EXTENSION:
    _RED_TEAM_EXTENSION = os.environ.get("RED_TEAM_PROMPT", "")


@app.post("/api/step-detail")
async def step_detail_endpoint(req: StepDetailRequest):
    """Generate detailed analysis for a specific kill chain step."""
    import json as _json
    from backend.kill_chain import assemble_contractor_intel

    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid contractor index"}, status_code=400)

    contractor = contractors[req.contractor_index]
    intel = assemble_contractor_intel(contractor)
    step = req.step

    # Build the user prompt with step context + contractor intel
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
        system_prompt += "\n\n" + _RED_TEAM_EXTENSION

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    if hermes.is_available():
        try:
            raw = await hermes.chat(messages, max_tokens=4096)
            # Parse JSON from response
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]
            result = _json.loads(json_str)
        except Exception as e:
            result = {
                "vulnerability": {"description": f"Analysis generation failed: {e}"},
                "detection": {"signatures": [], "log_indicators": [], "monitoring_advice": ""},
                "remediation": {"immediate": [], "long_term": [], "commands": []},
                "references": [],
                "alternative_vectors": [],
            }
    else:
        result = {
            "vulnerability": {"description": "Hermes 405B not available for detailed analysis."},
            "detection": {"signatures": [], "log_indicators": [], "monitoring_advice": "Enable logging on this service."},
            "remediation": {"immediate": ["Block this port at the firewall"], "long_term": ["Patch to latest version"], "commands": []},
            "references": [{"title": "MITRE ATT&CK", "url": f"https://attack.mitre.org/techniques/{step.get('technique_id', 'T1190')}/"}],
            "alternative_vectors": [],
        }

    return JSONResponse(result)


@app.post("/api/kill-chain")
async def kill_chain_endpoint(req: KillChainRequest):
    """Generate a MITRE ATT&CK kill chain for a specific contractor."""
    import json as _json
    from backend.kill_chain import assemble_contractor_intel, generate_kill_chain

    # Load contractor data
    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid contractor index"}, status_code=400)

    contractor = contractors[req.contractor_index]
    intel = assemble_contractor_intel(contractor)

    if hermes.is_available():
        result = await generate_kill_chain(hermes, intel)
    else:
        # Fallback: generate a basic kill chain from vectors alone (no LLM)
        steps = []
        for i, v in enumerate(intel["vectors"][:8], 1):
            steps.append({
                "step": i,
                "tactic": v.get("tactic", ""),
                "technique_id": v.get("technique", ""),
                "technique_name": v.get("name", ""),
                "description": v.get("detail", ""),
                "evidence": v.get("evidence", f"Port {v.get('port', '')} {v.get('product', '')}".strip()),
                "impact": "Enables further attack progression",
            })
        result = {
            "summary": f"{intel['name']} has {len(intel['vectors'])} identified attack vectors.",
            "risk_level": "critical" if len(intel["vectors"]) > 5 else "high" if len(intel["vectors"]) > 2 else "medium",
            "steps": steps,
            "remediation": [{"priority": 1, "action": "Address critical exposures first", "impact": "Reduces attack surface"}],
            "note": "Generated without AI reasoning — Hermes 405B not available",
        }

    return JSONResponse(result)


@app.post("/api/atlas-chat")
async def atlas_chat(req: AtlasChatRequest):
    # Inject live data context into system prompt
    system_content = _ATLAS_SYSTEM_PROMPT
    if req.data_context:
        system_content += req.data_context

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": req.query},
    ]

    # Add conversation history
    for msg in req.messages[-6:]:
        if msg.get("role") in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"][:500]})

    async def stream():
        use_hermes = hermes.is_available()
        response_parts = []
        last_emitted = ""
        _MAP_PREFIX = "MAP_CMD:"
        _PARTIAL_PREFIXES = [_MAP_PREFIX[:i] for i in range(1, len(_MAP_PREFIX) + 1)]

        def _ends_with_partial_prefix(text):
            """Check if text ends with any partial prefix of MAP_CMD:"""
            for p in _PARTIAL_PREFIXES:
                if text.endswith(p) or text.endswith("\n" + p):
                    return True
            return False

        try:
            gen = hermes.chat_stream(messages) if use_hermes else ollama.chat_stream(messages)
            async for token in gen:
                response_parts.append(token)
                text_so_far = "".join(response_parts)

                # Extract complete MAP_CMD lines
                while True:
                    for prefix in ("\nMAP_CMD:", "MAP_CMD:"):
                        idx = text_so_far.find(prefix)
                        if idx >= 0:
                            break
                    else:
                        break

                    json_start = idx + len(prefix)
                    line_end = text_so_far.find("\n", json_start)
                    if line_end == -1:
                        break  # incomplete, wait

                    json_str = text_so_far[json_start:line_end].strip()
                    try:
                        cmd = json.loads(json_str)
                        yield f"data: {json.dumps({'type': 'map_command', 'command': cmd})}\n\n"
                    except json.JSONDecodeError:
                        pass

                    # Remove the MAP_CMD line
                    text_so_far = text_so_far[:idx] + text_so_far[line_end + 1:]
                    response_parts = [text_so_far]

                # Don't emit text if it contains a full or partial MAP_CMD
                clean = text_so_far
                if "MAP_CMD:" in clean or _ends_with_partial_prefix(clean):
                    continue

                if len(clean) > len(last_emitted):
                    diff = clean[len(last_emitted):]
                    yield f"data: {json.dumps({'type': 'token', 'content': diff})}\n\n"
                    last_emitted = clean

            # Flush any remaining text after stream ends
            final_text = "".join(response_parts)
            # Remove any remaining MAP_CMD lines
            while "MAP_CMD:" in final_text:
                idx = final_text.find("MAP_CMD:")
                line_end = final_text.find("\n", idx)
                if line_end == -1:
                    final_text = final_text[:idx]
                else:
                    final_text = final_text[:idx] + final_text[line_end + 1:]
            if len(final_text) > len(last_emitted):
                diff = final_text[len(last_emitted):]
                if diff.strip():
                    yield f"data: {json.dumps({'type': 'token', 'content': diff})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
