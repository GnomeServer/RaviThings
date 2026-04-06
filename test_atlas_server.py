"""Test server for Atlas — uses real Hermes/Ollama for chat, no ChromaDB dependency."""
import asyncio
import hashlib
import json
import os
import pathlib
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

app = FastAPI()

# ── Simple password protection ──
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "")
AUTH_COOKIE = "osint_atlas_auth"
AUTH_TOKEN = hashlib.sha256(SITE_PASSWORD.encode()).hexdigest()[:32] if SITE_PASSWORD else ""

LOGIN_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>OSINT Atlas — Access Required</title>
<style>
  body { background: #0a0e1a; color: #c8d6e5; font-family: 'JetBrains Mono', monospace;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
  .login { text-align: center; }
  .login h1 { color: #00e5ff; font-size: 14px; letter-spacing: 6px; text-transform: uppercase; }
  .login h2 { color: #e0e6ed; font-size: 24px; margin: 8px 0 24px; }
  input { background: #111827; border: 1px solid #1e3a5f; color: #00e5ff; padding: 12px 20px;
          font-size: 16px; font-family: inherit; width: 260px; text-align: center; outline: none; }
  input:focus { border-color: #00e5ff; }
  button { background: #00e5ff; color: #0a0e1a; border: none; padding: 12px 32px; font-size: 14px;
           font-family: inherit; font-weight: 700; cursor: pointer; margin-top: 12px; letter-spacing: 2px; }
  button:hover { background: #00b8d4; }
  .error { color: #ff1744; font-size: 12px; margin-top: 8px; }
  .class { color: #8899aa; font-size: 10px; margin-top: 24px; letter-spacing: 2px; }
</style></head><body>
<div class="login">
  <h1>OSINT ATLAS</h1>
  <h2>Access Required</h2>
  <form method="POST" action="/auth">
    <input type="password" name="password" placeholder="Enter access code" autofocus><br>
    <button type="submit">AUTHENTICATE</button>
  </form>
  <div class="class">UNCLASSIFIED // FOR OFFICIAL USE ONLY</div>
</div></body></html>"""


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not SITE_PASSWORD:
            return await call_next(request)

        # Allow health check and auth endpoint without auth
        if request.url.path in ("/health", "/auth"):
            return await call_next(request)

        # Check auth cookie
        token = request.cookies.get(AUTH_COOKIE)
        if token == AUTH_TOKEN:
            return await call_next(request)

        # Show login page
        return HTMLResponse(LOGIN_PAGE, status_code=401)


app.add_middleware(AuthMiddleware)
BASE = pathlib.Path(__file__).parent

# Try to import LLM clients
# ── Root redirect ──
@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/atlas")


# ── Health check (bypasses auth for Railway) ──
@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


# ── Auth endpoint ──
@app.post("/auth")
async def authenticate(request: Request):
    form = await request.form()
    password = form.get("password", "")
    if password == SITE_PASSWORD:
        response = HTMLResponse('<script>window.location="/atlas"</script>')
        response.set_cookie(AUTH_COOKIE, AUTH_TOKEN, httponly=True, max_age=86400 * 7)
        return response
    return HTMLResponse(LOGIN_PAGE.replace("</form>", '<div class="error">Invalid access code</div></form>'), status_code=401)


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

ACTION COMMANDS — use when the user asks you to DO something (research, analyze, compare, export):
- MAP_CMD:{"action":"research","contractor_index":42} — Run AI research (web search + LLM analysis) on a contractor
- MAP_CMD:{"action":"kill_chain","contractor_index":42} — Generate MITRE ATT&CK kill chain for a contractor
- MAP_CMD:{"action":"assess","contractor_index":42} — Run full threat assessment (kill chain + all step details)
- MAP_CMD:{"action":"compare","contractor_indices":[0,5,12]} — Side-by-side security comparison (2-5 contractors)
- MAP_CMD:{"action":"export_csv"} — Export currently visible/filtered contractors as downloadable CSV
- MAP_CMD:{"action":"radius","lat":36.01,"lon":-84.27,"miles":50} — Show contractors within radius, draw circle

INTENT INFERENCE — users will NOT use exact command names. Infer the right action:
- "tell me about X" / "dig into X" / "what do we know about X" → research + open_panel
- "how would you attack X" / "attack path" / "vulnerabilities for X" → kill_chain
- "full report on X" / "assess X" / "deep dive on X" → assess (full assessment)
- "compare X and Y" / "how do they stack up" / "which is riskier" → compare
- "export" / "get me a list" / "download" / "CSV" → export_csv
- "anything near X" / "within 50 miles" / "contractors around X" → radius using the contractor's lat/lon
- "those ones" / "narrow it down" / "just the critical ones" → filter on current visible set

LONG-RUNNING ACTIONS: For research, kill_chain, and assess, ALWAYS announce what you're doing before emitting the command:
"I'll run a kill chain analysis on ORNL — generating now..."
MAP_CMD:{"action":"kill_chain","contractor_index":5}
This gives the user context before a 10-30 second operation starts.

SESSION CONTEXT — the frontend sends these with each query:
- active_filter: what filter is currently applied (field, op, value)
- visible_count: how many contractors are currently visible on the map
- selected_contractor: index of the currently open detail panel (or -1)
- recent_indices: contractor indices referenced in the last few messages
Use this context for follow-up queries: "those", "that contractor", "the filtered set".

MULTI-STEP ANALYSIS — for complex queries requiring multiple steps:
1. Explain your analysis plan briefly
2. Execute one command at a time, observing results
3. Use the session context to track what's visible after each step
4. Conclude with a synthesis of findings
Example: "Find contractors sharing IPs with critical-CVE companies" requires:
  Step 1: filter to critical CVE → report count
  Step 2: note their shared infrastructure from the data context
  Step 3: present the supply chain risk

RESPONSE RULES:
7. Be specific with numbers — cite actual counts from the data
8. Keep answers concise but impactful — this is a security briefing tool
9. When asked about "highest risk" or "most dangerous", sort by the risk= field in the data
10. Cite the specific data fields: risk score, danger level, DMARC policy, exposed services, CVE count
11. For action commands, always identify the contractor by [index] from the data block
12. When the user references a contractor by name, find its [index] and use that in commands
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


@app.post("/api/summarize-role")
async def summarize_role_endpoint(req: KillChainRequest):
    """Generate an enhanced description using web search + LLM synthesis. Streams SSE progress."""
    import json as _json
    from backend.brave_search import BraveSearchClient

    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid index"}, status_code=400)

    c = contractors[req.contractor_index]
    name = c.get("name", "")
    contract_ids = c.get("contract_ids", [])

    async def stream():
        brave = BraveSearchClient()
        web_context = ""
        unique = []

        if brave.is_available():
            # Search 1: contractor name + DOE
            query1 = f'"{name}" Department of Energy'
            yield f"data: {_json.dumps({'phase': 'search', 'query': query1[:60]})}\n\n"
            results1 = await brave.search(query1, count=5)

            # Search 2: contractor name + what they do
            dba = c.get('dba', '')
            search_name = dba if dba and dba != name else name
            query2 = f'"{search_name}" site:energy.gov OR site:doe.gov'
            yield f"data: {_json.dumps({'phase': 'search', 'query': query2[:60]})}\n\n"
            results1b = await brave.search(query2, count=3)
            results1.extend(results1b)

            yield f"data: {_json.dumps({'phase': 'search_complete', 'results': len(results1)})}\n\n"

            # Search 3: specific contract IDs
            results2 = []
            for cid in contract_ids[:3]:
                yield f"data: {_json.dumps({'phase': 'contract_search', 'contract_id': cid})}\n\n"
                r = await brave.search(f'"{cid}" DOE', count=3)
                results2.extend(r)

            # Search 4: company website directly
            query4 = f'{search_name} official website'
            yield f"data: {_json.dumps({'phase': 'search', 'query': 'company website'})}\n\n"
            results4 = await brave.search(query4, count=2)
            results2.extend(results4)

            all_results = results1 + results2
            seen_urls = set()
            for r in all_results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    unique.append(r)

            if unique:
                web_lines = []
                for r in unique[:8]:
                    web_lines.append(f"Source: {r['title']}")
                    web_lines.append(f"URL: {r['url']}")
                    if r.get("description"):
                        web_lines.append(f"Content: {r['description']}")
                    web_lines.append("")
                web_context = "\n".join(web_lines)

        yield f"data: {_json.dumps({'phase': 'synthesizing', 'sources': len(unique)})}\n\n"

        osint_domain = c.get('osint', {}).get('domain_verify', {}).get('domain', '') or c.get('osint', {}).get('domain_discovery', {}).get('domain', '')
        contract_context = (
            f"Contractor: {name}\nDBA: {c.get('dba', '')}\nParent: {c.get('parent', '')}\n"
            f"Category: {c.get('category', '')}\nCity: {c.get('city', '')}, {c.get('state', '')}\n"
            f"NAICS: {c.get('naics_desc', '') or c.get('naics', '')}\n"
            f"Product/Service: {c.get('product_service', '')}\n"
            f"Federal Obligation: ${c.get('obligation', 0):,.0f}\n"
            f"Max Potential: ${c.get('max_potential', 0):,.0f}\n"
            f"Contract IDs ({len(contract_ids)}): {', '.join(contract_ids)}\n"
            f"Fiscal Years: {c.get('fiscal_years', '')}\n"
            f"Start: {c.get('start_date', '')} End: {c.get('end_date', '')}\n"
            f"Funding: {', '.join(c.get('funding_agencies', []))}\n"
            f"Role: {c.get('role', '')}\n"
            f"OSINT Domain (may be incorrect): {osint_domain}\n"
            f"Personnel: {', '.join(c.get('personnel', [])[:10]) if c.get('personnel') else 'none'}\n"
            f"Size: {c.get('size_determination', '')}\n"
            f"Business Designations: {', '.join(c.get('business_designations', []))}"
        )

        user_content = f"CONTRACT RECORD:\n{contract_context}"
        if web_context:
            user_content += f"\n\nWEB SEARCH RESULTS (cite these sources):\n{web_context}"

        messages = [
            {"role": "system", "content": (
                "You are a DOE contractor intelligence analyst creating an enhanced description. "
                "You have (1) the official contract record and (2) web search results. "
                "Write 2-3 paragraphs: what they do for DOE, scope of work from web findings, "
                "key contract facts including all contract IDs and their purposes if known. "
                "If the web search reveals the company's real website URL, include it. "
                "Note if the OSINT domain appears incorrect based on web findings. "
                "ONLY use provided data/web results. No training knowledge. "
                "Professional intelligence briefing style."
            )},
            {"role": "user", "content": user_content},
        ]

        if hermes.is_available():
            try:
                summary = await hermes.chat(messages, max_tokens=700)
                yield f"data: {_json.dumps({'phase': 'complete', 'summary': summary.strip(), 'sources': len(unique)})}\n\n"
            except Exception as e:
                yield f"data: {_json.dumps({'phase': 'complete', 'summary': f'Failed: {e}', 'sources': 0})}\n\n"
        else:
            yield f"data: {_json.dumps({'phase': 'complete', 'summary': 'Hermes 405B not available.', 'sources': 0})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/ai-research")
async def ai_research_endpoint(req: KillChainRequest):
    """AI-powered contractor research with SSE streaming.

    Uses the core research_contractor() function with an on_status callback
    to emit SSE progress events.
    """
    import json as _json
    from backend.brave_search import BraveSearchClient
    from osint.ai_research import research_contractor, apply_domain_cascade

    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid index"}, status_code=400)

    c = contractors[req.contractor_index]

    async def stream():
        brave = BraveSearchClient()

        # Collect progress events from the callback
        progress_events = []

        async def on_status(msg):
            progress_events.append(msg)

        # Run the core research function
        result = await research_contractor(c, hermes, brave, on_status=on_status)

        # Emit collected progress events
        for msg in progress_events:
            # Map status messages to SSE phase events
            if 'Searching' in msg:
                yield f"data: {_json.dumps({'phase': 'search', 'detail': msg[:60]})}\n\n"
            elif 'Analyzing' in msg:
                yield f"data: {_json.dumps({'phase': 'synthesizing', 'sources': result.get('raw_search_results', 0)})}\n\n"
            elif 'Validating' in msg:
                yield f"data: {_json.dumps({'phase': 'validating', 'domain': result.get('current_domain', '')})}\n\n"

        # Save to contractor data
        c.setdefault('osint', {})['ai_research'] = result
        dd = c.get('osint', {}).get('domain_discovery', {})

        if not result.get('error') and result.get('current_domain') and result.get('domain_validated'):
            old = dd.get('domain', '')
            if result['current_domain'] != old:
                apply_domain_cascade(c, result['current_domain'], 'ai_research')

        # Persist to file
        with open(BASE / "frontend" / "static" / "contractors.json", "w") as f:
            _json.dump(data, f, separators=(',', ':'))

        yield f"data: {_json.dumps({'phase': 'complete', **result})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/full-assessment")
async def full_assessment_endpoint(req: KillChainRequest):
    """Generate a complete assessment: kill chain + detailed analysis of every step.

    Returns SSE stream with progress events:
      {"phase": "kill_chain", "status": "generating"}
      {"phase": "kill_chain", "status": "complete", "data": {...}}
      {"phase": "step_detail", "step": 1, "total": 6, "status": "generating"}
      {"phase": "step_detail", "step": 1, "total": 6, "status": "complete", "data": {...}}
      ...
      {"phase": "complete", "summary": {...}}
    """
    import json as _json
    import re as _re2
    from backend.kill_chain import assemble_contractor_intel, generate_kill_chain

    with open(BASE / "frontend" / "static" / "contractors.json") as f:
        data = _json.load(f)

    contractors = data.get("contractors", [])
    if req.contractor_index < 0 or req.contractor_index >= len(contractors):
        return JSONResponse({"error": "Invalid contractor index"}, status_code=400)

    contractor = contractors[req.contractor_index]
    intel = assemble_contractor_intel(contractor)

    async def stream():
        # Phase 1: Generate kill chain
        yield f"data: {_json.dumps({'phase': 'kill_chain', 'status': 'generating'})}\n\n"

        if hermes.is_available():
            kill_chain = await generate_kill_chain(hermes, intel)
        else:
            steps = []
            for i, v in enumerate(intel["vectors"][:8], 1):
                steps.append({
                    "step": i, "tactic": v.get("tactic", ""),
                    "technique_id": v.get("technique", ""),
                    "technique_name": v.get("name", ""),
                    "description": v.get("detail", ""),
                    "evidence": v.get("evidence", f"Port {v.get('port', '')}"),
                    "impact": "Enables further attack progression",
                })
            kill_chain = {
                "summary": f"{intel['name']} has {len(intel['vectors'])} attack vectors.",
                "risk_level": "high" if len(intel["vectors"]) > 2 else "medium",
                "steps": steps, "remediation": [],
            }

        yield f"data: {_json.dumps({'phase': 'kill_chain', 'status': 'complete', 'data': kill_chain})}\n\n"

        # Phase 2: Detailed analysis for each step
        steps = kill_chain.get("steps", [])
        step_details = []

        for idx, step in enumerate(steps):
            yield f"data: {_json.dumps({'phase': 'step_detail', 'step': idx + 1, 'total': len(steps), 'status': 'generating', 'tactic': step.get('tactic', '')})}\n\n"

            if hermes.is_available():
                # Build step detail prompt (same as /api/step-detail endpoint)
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
                    rt_context = _RED_TEAM_EXTENSION
                    ip_match = _re2.search(r'(\d+\.\d+\.\d+\.\d+)', step.get('evidence', '') + ' ' + step.get('description', ''))
                    port_match = _re2.search(r':(\d+)', step.get('evidence', '') + ' ' + step.get('description', ''))
                    target_ip = ip_match.group(1) if ip_match else (intel.get('onprem_ips', [''])[0] if intel.get('onprem_ips') else '')
                    target_port = port_match.group(1) if port_match else ''
                    target_svc = next((s for s in intel.get('all_services', []) if str(s.get('port')) == target_port or s.get('ip') == target_ip), {})
                    target_product = f"{target_svc.get('product', '')} {target_svc.get('version', '')}".strip()

                    rt_context = rt_context.replace('TARGET_IP_HERE', target_ip)
                    rt_context = rt_context.replace('TARGET_PROTOCOL_HERE', target_svc.get('transport', 'tcp'))
                    rt_context = rt_context.replace('TARGET_URL_HERE', f'http://{target_ip}:{target_port}' if target_port else f'http://{target_ip}')
                    rt_context = rt_context.replace('PORT_RANGE', target_port or '1-65535')
                    rt_context = rt_context.replace('SERVICE_NAME', target_product or 'unknown')
                    system_prompt += f"\n\n{rt_context}\n\nFOCUS: Target {target_ip}:{target_port} running {target_product}. Add 'red_team' key to JSON. IMPORTANT: Escape all backslashes as \\\\\\\\ in JSON strings."

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]

                try:
                    raw = await hermes.chat(messages, max_tokens=4096)
                    json_str = raw
                    if "```json" in raw:
                        json_str = raw.split("```json")[1].split("```")[0]
                    elif "```" in raw:
                        json_str = raw.split("```")[1].split("```")[0]
                    try:
                        detail = _json.loads(json_str)
                    except _json.JSONDecodeError:
                        fixed = _re2.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)
                        try:
                            detail = _json.loads(fixed)
                        except _json.JSONDecodeError:
                            # Strip control chars, try brace extraction
                            clean = _re2.sub(r'[\x00-\x1f]', ' ', json_str)
                            b0, b1 = clean.find('{'), clean.rfind('}')
                            if b0 >= 0 and b1 > b0:
                                try:
                                    detail = _json.loads(clean[b0:b1+1])
                                except _json.JSONDecodeError:
                                    detail = {"vulnerability": {"description": raw[:2000]}, "detection": {}, "remediation": {}, "references": []}
                            else:
                                detail = {"vulnerability": {"description": raw[:2000]}, "detection": {}, "remediation": {}, "references": []}
                except Exception as e:
                    detail = {"vulnerability": {"description": f"Analysis failed: {e}"}, "detection": {}, "remediation": {}, "references": []}
            else:
                detail = {"vulnerability": {"description": "Hermes not available"}, "detection": {}, "remediation": {}, "references": []}

            step_details.append(detail)
            yield f"data: {_json.dumps({'phase': 'step_detail', 'step': idx + 1, 'total': len(steps), 'status': 'complete', 'data': detail})}\n\n"

        # Final summary
        yield f"data: {_json.dumps({'phase': 'complete', 'total_steps': len(steps), 'total_details': len(step_details)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


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
        # Dynamically substitute placeholders with real step data
        rt_context = _RED_TEAM_EXTENSION

        # Extract the primary IP and port from the step evidence
        import re as _re
        ip_match = _re.search(r'(\d+\.\d+\.\d+\.\d+)', step.get('evidence', '') + ' ' + step.get('description', ''))
        port_match = _re.search(r':(\d+)', step.get('evidence', '') + ' ' + step.get('description', ''))
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
            'Discovery': 'reconnaissance',
            'Collection': 'post_exploitation',
            'Exfiltration': 'post_exploitation',
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

    if hermes.is_available():
        try:
            raw = await hermes.chat(messages, max_tokens=4096)
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
                import re as _re2
                fixed = _re2.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)
                try:
                    result = _json.loads(fixed)
                except _json.JSONDecodeError:
                    # Try finding first { to last }
                    brace_start = json_str.find('{')
                    brace_end = json_str.rfind('}')
                    if brace_start >= 0 and brace_end > brace_start:
                        subset = json_str[brace_start:brace_end+1]
                        # Remove control characters that break JSON
                        subset = _re2.sub(r'[\x00-\x1f]', ' ', subset)
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
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
