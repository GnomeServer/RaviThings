# backend/server.py
"""FastAPI server for DOE GraphRAG."""
import asyncio
import os
import json
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from backend.graph_engine import GraphEngine
from backend.hybrid_retriever import HybridRetriever
from backend.ollama_client import OllamaClient
from backend.recipe_engine import RecipeEngine
from backend.setup_fts import ensure_fts5
from backend.brave_search import BraveSearchClient
from backend.mercury_client import HermesClient
from backend.deep_analysis import DeepAnalysisPipeline
from backend.saturate import SaturationPipeline, _merge_schematic, _SATURATE_DELTA_PROMPT

# Keywords that indicate a "how to make" question warranting schematic extraction
_SCHEMATIC_KEYWORDS = re.compile(
    r"\b(how|make|made|manufacture|fabricate|produce|synthesize|process|recipe)\b",
    re.IGNORECASE,
)

_SCHEMATIC_JSON_SCHEMA = '{"title":"string","inputs":[{"id":"in1","name":"Chemical name (formula)","type":"raw_material|precursor|equipment|energy","sources":{"commercial":["Real supplier names"],"diy":"How to synthesize this yourself"},"feeds_into":["step1"]}],"steps":[{"id":"step1","name":"Process step name","description":"Detailed description of what happens in this step","parameters":{"key":"value with real numbers"},"equipment":["Specific equipment needed"],"inputs_from":["in1"],"outputs_to":["step2"],"doe_contractors":["Real lab names from contracts"],"investment":"Real dollar amount or unknown","contractor_details":[{"name":"Real contractor/lab name","role":"Specific contribution to this step","contract_value":12400000,"significance_pct":42.3}],"step_total_capital":29400000}],"outputs":[{"id":"out1","name":"Product name","description":"Detailed description of the output product and its properties","type":"intermediate|final","receives_from":["step1"]}]}'

_SCHEMATIC_CREATE_PROMPT = """\
Extract a manufacturing process schematic from the information below. Return ONLY valid JSON.

RULES:
- Use REAL values, not placeholders. If unknown, omit the field or use "unknown".
- For inputs: actual chemical compounds with formulas. Commercial sources: real suppliers (Sigma-Aldrich, Alfa Aesar, MSE Supplies, MTI Corp, Thermo Fisher). DIY: how to synthesize the precursor.
- For steps: actual process parameters (real temperatures, times, pressures).
- For doe_contractors: actual lab/company names from the contract data.
- For investment: actual dollar amounts from contracts if available.
- Connect inputs to steps and steps to outputs using id fields.
- For contractor_details: list each DOE contractor that participates in this step. Include their specific role/contribution, actual contract_value in dollars, and significance_pct as their share of the total capital for this step (percentages should sum to ~100 within each step). Set step_total_capital to the sum of all contract values for that step.

JSON SCHEMA:
""" + _SCHEMATIC_JSON_SCHEMA + "\n\n"

_SCHEMATIC_UPDATE_PROMPT = """\
You have an EXISTING process schematic (shown below as JSON). The user asked a follow-up question and got a new answer with more detail. UPDATE the existing schematic by:

1. The EXISTING SCHEMATIC below is the MASTER. Start from it. NEVER discard or replace it.
2. KEEP ALL existing steps, inputs, and outputs — every single one.
3. ADD new sub-steps, inputs, outputs, contractors, parameters, or equipment discovered.
4. If the user asked about ONE specific step, ENRICH that step's description, parameters, equipment, and contractors. Do NOT replace the entire schematic with a schematic about only that step.
5. NEVER remove existing data unless clearly wrong.
6. Preserve all existing id values so connections aren't broken.
7. Pay special attention to the USER'S QUESTION below — focus enrichment on the step or area they asked about.

CRITICAL: The output must contain ALL steps from the existing schematic PLUS any new ones. If the existing schematic has 7 steps, the output must have at least 7 steps.

Return the COMPLETE updated schematic as valid JSON (not just the changes).

JSON SCHEMA:
""" + _SCHEMATIC_JSON_SCHEMA + """

EXISTING SCHEMATIC:
{existing_schematic}

USER'S QUESTION:
{user_question}

"""


def _is_schematic_query(text: str) -> bool:
    """Return True if the user message looks like a 'how to make' question."""
    return bool(_SCHEMATIC_KEYWORDS.search(text))


def _strip_think_traces(text: str) -> str:
    """Remove <think>...</think> reasoning traces from Hermes-4 responses."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def create_app() -> FastAPI:
    # Load .env file if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv is optional

    # Config from environment (read at app creation time)
    db_path = os.environ.get("DB_PATH", "doe_contracts.db")
    graph_path = os.environ.get("GRAPH_PATH", "graph.pkl")
    chroma_path = os.environ.get("CHROMA_PATH", "./chroma_db")
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "dolphin3")
    static_dir = os.environ.get("STATIC_DIR", "frontend/build")

    # Per-app state (not shared across create_app() calls)
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        if db_path and os.path.exists(db_path):
            ensure_fts5(db_path)

        # Create Ollama client first — used for chat, embeddings, and graph search
        state["ollama"] = OllamaClient(base_url=ollama_host, model=ollama_model)

        if graph_path and os.path.exists(graph_path):
            # Use Ollama for graph node embeddings (no SentenceTransformer/HuggingFace needed)
            state["graph"] = GraphEngine(graph_path, embed_fn=state["ollama"].embed_sync)
        else:
            state["graph"] = None

        state["brave"] = BraveSearchClient()  # reads BRAVE_SEARCH_API_KEY from env
        state["mercury"] = HermesClient()  # reads NOUS_API_KEY from env

        chroma = chroma_path if chroma_path and os.path.exists(chroma_path) else None
        state["retriever"] = HybridRetriever(
            db_path=db_path,
            graph_engine=state["graph"],
            chroma_path=chroma,
            ollama=state["ollama"],
        )

        state["recipe"] = RecipeEngine(
            ollama=state["ollama"],
            retriever=state["retriever"],
            brave_search=state["brave"],
        )

        state["ready"] = True
        yield
        state.clear()

    app = FastAPI(title="DOE GraphRAG", lifespan=lifespan)

    # --- Health ---
    @app.get("/api/health")
    async def health():
        ollama_ok = await state["ollama"].is_available() if state.get("ollama") else False
        return {
            "status": "ready" if state.get("ready") else "starting",
            "graph_loaded": state.get("graph") is not None,
            "ollama_available": ollama_ok,
            "fts5": True,
        }

    # --- Graph ---
    @app.get("/api/graph")
    async def get_graph(entity: str = Query(...), hops: int = Query(1, ge=1, le=3)):
        if not state.get("graph"):
            return JSONResponse({"error": "Graph not loaded"}, 503)
        return state["graph"].get_subgraph(entity, hops=hops)

    @app.get("/api/graph/expand/{node_id}")
    async def expand_node(node_id: str):
        if not state.get("graph"):
            return JSONResponse({"error": "Graph not loaded"}, 503)
        neighbors = state["graph"].get_neighbors(node_id)
        return {"neighbors": neighbors}

    # --- Search ---
    @app.get("/api/search")
    async def search(q: str = Query(...), mode: str = Query("hybrid")):
        retriever = state["retriever"]
        if mode == "keyword":
            results = retriever.search_keyword(q)
            return {"contracts": results, "mode": mode}
        elif mode == "vector":
            keys = retriever.search_vector(q)
            contracts = retriever._get_contracts_by_keys(keys)
            return {"contracts": list(contracts.values()), "mode": mode}
        else:
            hybrid = retriever.search(q)
            return {
                "contracts": [
                    {
                        "key": c.key, "description": c.description,
                        "recipient": c.recipient, "obligation": c.obligation,
                        "fiscal_year": c.fiscal_year, "psc": c.psc,
                        "naics": c.naics, "sources": c.sources,
                        "rrf_score": c.rrf_score,
                    }
                    for c in hybrid.contracts
                ],
                "retrieval_counts": hybrid.retrieval_counts,
                "graph_paths": hybrid.graph_paths,
                "mode": mode,
            }

    # --- Communities ---
    @app.get("/api/communities")
    async def get_communities():
        if not state.get("graph"):
            return JSONResponse({"error": "Graph not loaded"}, 503)
        return state["graph"].get_communities()

    # --- Stats ---
    @app.get("/api/stats")
    async def get_stats():
        graph = state.get("graph")
        return {
            "node_count": graph.node_count if graph else 0,
            "edge_count": graph.edge_count if graph else 0,
            "communities": len(graph.get_communities()) if graph else 0,
        }

    # --- Chat (SSE) ---
    class ChatRequest(BaseModel):
        messages: list[dict]
        schematic: dict | None = None  # Current process schematic on screen, if any

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        retriever = state["retriever"]
        ollama = state["ollama"]
        hermes = state.get("mercury")

        # Extract last user message for retrieval
        user_msg = next(
            (m["content"] for m in reversed(req.messages) if m["role"] == "user"), ""
        )

        async def event_stream():
            import asyncio

            # Status: searching
            yield {"event": "status", "data": json.dumps({"stage": "searching", "message": "Searching contracts and web..."})}

            # 1. Hybrid retrieval + web search in parallel
            brave = state["brave"]

            async def do_retrieval():
                return await asyncio.to_thread(retriever.search, user_msg)

            async def do_web_search():
                if brave.is_available():
                    return await brave.search_for_context(user_msg, count=5)
                return ""

            results, web_context = await asyncio.gather(
                do_retrieval(), do_web_search()
            )

            retrieval_counts = results.retrieval_counts
            if web_context:
                retrieval_counts["web"] = len(web_context.split("\n- "))
            yield {
                "event": "retrieval",
                "data": json.dumps(retrieval_counts),
            }

            # Status: generating
            yield {"event": "status", "data": json.dumps({"stage": "generating", "message": "Generating response..."})}

            # 2. Build augmented prompt with conversation history + new evidence
            contract_lines = []
            for c in results.contracts:
                contract_lines.append(
                    f"- {c.recipient}: {c.description} (${c.obligation:,.0f}, FY{c.fiscal_year})"
                )

            web_section = ""
            if web_context:
                web_section = (
                    f"\n\n### TECHNICAL RESEARCH FROM THE WEB:\n"
                    f"{web_context}\n"
                )

            # Build schematic context if one exists on screen
            schematic_section = ""
            if req.schematic and req.schematic.get("title"):
                s = req.schematic
                steps_text = "\n".join(
                    f"  Step {i+1}: {step.get('name', '?')} - {step.get('description', '')}"
                    for i, step in enumerate(s.get("steps", []))
                )
                schematic_section = (
                    f"\n\n### CURRENT PROCESS SCHEMATIC ON SCREEN:\n"
                    f"Title: {s['title']}\n{steps_text}\n"
                    f"(The user can see this schematic. Reference it when relevant.)\n"
                )

            # System prompt
            system_msg = {
                "role": "system",
                "content": (
                    "You are a process engineer and technical researcher with deep expertise in DOE-funded technologies. "
                    "You have access to DOE contract records and web research. Use contracts as evidence clues about "
                    "what processes are used and who does the work. Use web research for technical details.\n\n"
                    "When asked 'how is X made?', provide step-by-step processes with specific materials, "
                    "temperatures, techniques, and equipment. Cite DOE contractors where relevant.\n\n"
                    "You are in a multi-turn conversation. The user may ask follow-up questions about previous answers "
                    "or about specific steps in the process schematic shown on screen. Use the full conversation "
                    "context to provide coherent, cumulative answers.\n\n"
                    "Do NOT just list or summarize sources. Synthesize them into integrated technical knowledge."
                ),
            }

            # New evidence for this turn
            evidence_msg = {
                "role": "user",
                "content": (
                    f"### NEW EVIDENCE FOR THIS QUERY:\n"
                    f"DOE Contracts:\n" + "\n".join(contract_lines)
                    + web_section
                    + schematic_section
                    + f"\n\n### QUESTION:\n{user_msg}"
                ),
            }

            # Build full message list: system + prior conversation + new evidence
            prior_messages = [
                m for m in req.messages[:-1]  # All messages except the last (which is the current question)
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]

            augmented = [system_msg] + prior_messages + [evidence_msg]

            # 3. Stream LLM response (collect full text for potential schematic extraction)
            #    Use Hermes-4 when available, fall back to local Dolphin3
            full_response_parts: list[str] = []
            use_hermes = hermes and hermes.is_available()
            fell_back = False
            if use_hermes:
                try:
                    async for token in hermes.chat_stream(augmented):
                        full_response_parts.append(token)
                        yield {"event": "token", "data": json.dumps({"content": token})}
                except Exception:
                    if not full_response_parts:
                        fell_back = True  # will use Dolphin3 below
            if not use_hermes or fell_back:
                # Dolphin3: primary (no Hermes key) or fallback (Hermes failed)
                async for token in ollama.chat_stream(augmented):
                    full_response_parts.append(token)
                    yield {"event": "token", "data": json.dumps({"content": token})}

            # 4. Process schematic extraction
            # Create new schematic for "how to make" queries, OR update existing schematic on any follow-up
            has_existing = req.schematic and req.schematic.get("title")
            should_extract = _is_schematic_query(user_msg) or has_existing
            if should_extract:
                is_update = bool(has_existing)
                status_msg = "Updating process schematic..." if is_update else "Extracting process schematic..."
                yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": status_msg})}
                try:
                    full_response_text = "".join(full_response_parts)

                    # Log: building context
                    yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": "Building schematic context from contracts, web, and response..."})}

                    # Feed the extraction ALL context: contracts + web + LLM response
                    new_info = (
                        "DOE CONTRACT DATA:\n" + "\n".join(contract_lines) + "\n\n"
                        + (f"WEB RESEARCH:\n{web_context}\n\n" if web_context else "")
                        + "NEW INFORMATION FROM LATEST ANSWER:\n" + full_response_text
                    )

                    if is_update:
                        # DELTA approach: ask LLM for additions only, merge in code
                        step_names = ", ".join(
                            s.get("name", "?") for s in req.schematic.get("steps", [])
                        )
                        prompt = (
                            _SATURATE_DELTA_PROMPT
                            .replace("{existing_step_names}", step_names)
                        ) + new_info
                    else:
                        # CREATE new schematic from scratch
                        prompt = _SCHEMATIC_CREATE_PROMPT + new_info

                    # Use Hermes-4 for all schematic work (better JSON, 131K context)
                    hermes_available = hermes and hermes.is_available()
                    if hermes_available:
                        action = "Extracting additions for" if is_update else "Generating"
                        yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": f"{action} schematic with Hermes-4..."})}
                        schematic_msgs = [{"role": "user", "content": prompt}]
                        try:
                            raw_schematic = await hermes.chat(schematic_msgs)
                        except Exception:
                            yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": "Hermes-4 unavailable, using Dolphin3..."})}
                            if len(prompt) > 7000:
                                prompt = prompt[:7000] + "\n\n[...truncated for context window]"
                            raw_schematic = await ollama.generate(prompt)
                    else:
                        yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": "Generating schematic with Dolphin3..."})}
                        if len(prompt) > 7000:
                            prompt = prompt[:7000] + "\n\n[...truncated for context window]"
                        raw_schematic = await ollama.generate(prompt)

                    # Strip <think> reasoning traces (Hermes-4) before JSON extraction
                    raw_schematic = _strip_think_traces(raw_schematic)

                    yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": "Parsing schematic JSON..."})}

                    # LLMs often return JSON with extra text — extract between first { and last }
                    start = raw_schematic.find("{")
                    end = raw_schematic.rfind("}")
                    if start >= 0 and end > start:
                        schematic_data = json.loads(raw_schematic[start:end + 1])
                    else:
                        schematic_data = json.loads(raw_schematic)

                    # For updates: merge delta into existing schematic in code
                    if is_update:
                        yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": "Merging additions into existing schematic..."})}
                        schematic_data, merge_counts = _merge_schematic(req.schematic, schematic_data)
                        n_new = merge_counts.get("total_new", 0)
                        yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": f"Merged {n_new} new entities into schematic"})}

                    # Validate it has at least a title or steps
                    if schematic_data.get("title") or schematic_data.get("steps"):
                        yield {
                            "event": "process_schematic",
                            "data": json.dumps(schematic_data),
                        }
                        n_steps = len(schematic_data.get("steps", []))
                        n_inputs = len(schematic_data.get("inputs", []))
                        yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": f"Schematic {'updated' if is_update else 'created'}: {n_steps} steps, {n_inputs} inputs"})}
                    else:
                        yield {"event": "status", "data": json.dumps({"stage": "schematic_failed", "message": "Generated schematic was empty"})}
                except json.JSONDecodeError:
                    yield {"event": "status", "data": json.dumps({"stage": "schematic_failed", "message": "Could not parse schematic JSON from model response"})}
                except Exception as e:
                    yield {"event": "status", "data": json.dumps({"stage": "schematic_failed", "message": f"Schematic extraction failed: {type(e).__name__}: {e}"})}

            # 5. Graph highlight
            yield {
                "event": "graph_highlight",
                "data": json.dumps(results.graph_paths),
            }

            # 6. Done
            yield {"event": "status", "data": json.dumps({"stage": "done", "message": "Complete"})}
            total_dollars = sum(c.obligation for c in results.contracts)
            yield {
                "event": "done",
                "data": json.dumps({
                    "total_contracts": len(results.contracts),
                    "total_dollars": total_dollars,
                }),
            }

        return EventSourceResponse(event_stream())

    # --- Recipe (SSE) ---
    class RecipeRequest(BaseModel):
        query: str

    @app.post("/api/recipe")
    async def recipe(req: RecipeRequest):
        engine = state["recipe"]

        async def event_stream():
            async for event in engine.synthesize(req.query):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }

        return EventSourceResponse(event_stream())

    # --- Topic Extraction (SSE) ---
    class TopicExtractRequest(BaseModel):
        batch_size: int = 100
        limit: int | None = None
        rebuild_graph: bool = False

    @app.post("/api/topics/extract")
    async def extract_topics(req: TopicExtractRequest):
        from backend.extract_topics import extract_topics_stream
        topics_db = os.environ.get("TOPICS_DB_PATH", "/data/topics.db")
        ollama = state["ollama"]

        async def event_stream():
            async for event in extract_topics_stream(
                db_path, topics_db, ollama, req.batch_size, req.limit
            ):
                yield {"event": event["event"], "data": json.dumps(event["data"])}

        return EventSourceResponse(event_stream())

    # --- Deep Analysis Chat (SSE) ---
    class DeepChatRequest(BaseModel):
        messages: list[dict]

    @app.post("/api/deep-chat")
    async def deep_chat(req: DeepChatRequest):
        ollama = state["ollama"]
        mercury = state.get("mercury")
        brave = state.get("brave")

        pipeline = DeepAnalysisPipeline(
            db_path=db_path,
            ollama=ollama,
            mercury=mercury if mercury and mercury.is_available() else None,
            brave=brave,
        )

        # Extract conversation history (all but the last user message)
        conversation_history = [
            m for m in req.messages[:-1]
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

        # Last user message is the query
        user_msg = next(
            (m["content"] for m in reversed(req.messages) if m["role"] == "user"), ""
        )

        async def event_stream():
            async for event in pipeline.analyze(user_msg, conversation_history):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }

        return EventSourceResponse(event_stream())

    # --- Saturate Chat (SSE) ---
    class SaturateChatRequest(BaseModel):
        messages: list[dict]
        max_passes: int | None = None  # None = no limit, run until converged
        auto_explore: bool = True
        max_depth: int = 3

    @app.post("/api/saturate-chat")
    async def saturate_chat(req: SaturateChatRequest):
        ollama = state["ollama"]
        mercury = state.get("mercury")
        brave = state.get("brave")
        retriever = state["retriever"]

        pipeline = SaturationPipeline(
            retriever=retriever,
            ollama=ollama,
            hermes=mercury if mercury and mercury.is_available() else None,
            brave=brave,
        )

        user_msg = next(
            (m["content"] for m in reversed(req.messages) if m["role"] == "user"), ""
        )

        async def event_stream():
            async for event in pipeline.saturate(
                    user_msg,
                    max_passes=req.max_passes,
                    auto_explore=req.auto_explore,
                    max_depth=req.max_depth,
                ):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }

        return EventSourceResponse(event_stream())

    # --- Atlas Chat (SSE with map commands) ---
    _ATLAS_SYSTEM_PROMPT = """\
You are the OSINT Atlas Intelligence Analyst for DOE contractor security. You have access to \
intelligence data on DOE contractors including their network exposure, vulnerabilities, and infrastructure.

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

MAP COMMANDS — emit these as JSON on a line by itself, prefixed with MAP_CMD:
The frontend will execute these to manipulate the map in real-time.

Available commands:
- MAP_CMD:{"action":"fly_to","lat":39.5,"lon":-105.0,"zoom":8}
- MAP_CMD:{"action":"filter","field":"state","value":"CO","op":"eq"}
- MAP_CMD:{"action":"filter","field":"osint.service_risk.max_danger","value":"critical","op":"eq"}
- MAP_CMD:{"action":"filter","field":"shodan.total_hosts","value":0,"op":"gt"}
- MAP_CMD:{"action":"filter","field":"category","value":"IT & Cyber","op":"eq"}
- MAP_CMD:{"action":"reset"}
- MAP_CMD:{"action":"open_panel","contractor_index":42}

Filter operators: eq, contains, gt, gte, lt, exists
Field paths use dot notation into the contractor JSON.

RULES:
1. Always emit MAP_CMD commands BEFORE your text explanation so the map updates first
2. Use fly_to when the user asks about a geographic area
3. Use filter when the user wants to see a subset of contractors
4. Use reset before applying new filters to clear previous state
5. Be specific with numbers — cite actual counts from the data
6. When mentioning a specific contractor, use open_panel with their index
7. Keep answers concise but impactful — this is a security briefing tool
"""

    class AtlasChatRequest(BaseModel):
        query: str
        messages: list[dict] = []
        contractor_count: int = 0

    @app.post("/api/atlas-chat")
    async def atlas_chat(req: AtlasChatRequest):
        ollama = state["ollama"]
        mercury = state.get("mercury")

        # Build context with data summary for the LLM
        retriever = state["retriever"]
        results = await asyncio.to_thread(retriever.search, req.query)
        contract_context = "\n".join(
            f"- {c.recipient}: {c.description} (${c.obligation:,.0f})"
            for c in results.contracts[:20]
        )

        messages = [
            {"role": "system", "content": _ATLAS_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Contractor dataset: {req.contractor_count} DOE contractors\n\n"
                f"RELEVANT CONTRACT DATA:\n{contract_context}\n\n"
                f"USER QUESTION: {req.query}"
            )},
        ]

        # Add conversation history
        for msg in req.messages[-6:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"][:500]})

        async def event_stream():
            import asyncio as aio

            use_hermes = mercury and mercury.is_available()
            response_parts = []

            try:
                if use_hermes:
                    try:
                        async for token in mercury.chat_stream(messages):
                            response_parts.append(token)
                            # Check for MAP_CMD in accumulated text
                            text_so_far = "".join(response_parts)
                            while "MAP_CMD:" in text_so_far:
                                idx = text_so_far.index("MAP_CMD:")
                                # Find the JSON after MAP_CMD:
                                json_start = idx + 8
                                # Find the end of the JSON line
                                line_end = text_so_far.find("\n", json_start)
                                if line_end == -1:
                                    break  # Incomplete — wait for more tokens
                                json_str = text_so_far[json_start:line_end].strip()
                                try:
                                    cmd = json.loads(json_str)
                                    yield f"data: {json.dumps({'type': 'map_command', 'command': cmd})}\n\n"
                                except json.JSONDecodeError:
                                    pass
                                # Remove the MAP_CMD line from text and emit remaining as tokens
                                before = text_so_far[:idx]
                                after = text_so_far[line_end + 1:]
                                text_so_far = before + after
                                response_parts = [text_so_far]
                                continue
                            # Yield text tokens (non-command parts)
                            clean = text_so_far
                            # Don't emit text that contains partial MAP_CMD
                            if "MAP_CMD:" in clean:
                                break
                            if clean and clean != getattr(event_stream, '_last_emitted', ''):
                                diff = clean[len(getattr(event_stream, '_last_emitted', '')):]
                                if diff:
                                    yield f"data: {json.dumps({'type': 'token', 'content': diff})}\n\n"
                                event_stream._last_emitted = clean
                    except Exception:
                        response_parts = []

                if not response_parts:
                    event_stream._last_emitted = ''
                    async for token in ollama.chat_stream(messages):
                        response_parts.append(token)
                        text_so_far = "".join(response_parts)

                        # Extract and emit MAP_CMDs
                        while "\nMAP_CMD:" in text_so_far or text_so_far.startswith("MAP_CMD:"):
                            prefix = "MAP_CMD:" if text_so_far.startswith("MAP_CMD:") else "\nMAP_CMD:"
                            idx = text_so_far.index(prefix)
                            json_start = idx + len(prefix)
                            line_end = text_so_far.find("\n", json_start)
                            if line_end == -1:
                                break
                            json_str = text_so_far[json_start:line_end].strip()
                            try:
                                cmd = json.loads(json_str)
                                yield f"data: {json.dumps({'type': 'map_command', 'command': cmd})}\n\n"
                            except json.JSONDecodeError:
                                pass
                            text_so_far = text_so_far[:idx] + text_so_far[line_end + 1:]
                            response_parts = [text_so_far]

                        # Emit clean text
                        clean = text_so_far
                        if "MAP_CMD:" in clean:
                            continue
                        last = getattr(event_stream, '_last_emitted', '')
                        if len(clean) > len(last):
                            diff = clean[len(last):]
                            yield f"data: {json.dumps({'type': 'token', 'content': diff})}\n\n"
                            event_stream._last_emitted = clean

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            yield "data: [DONE]\n\n"

        event_stream._last_emitted = ''
        from starlette.responses import StreamingResponse
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # --- Atlas route (OSINT intelligence map) ---
    @app.get("/atlas")
    async def serve_atlas():
        """Serve the OSINT Atlas contractor intelligence map."""
        from fastapi.responses import FileResponse
        import pathlib
        atlas_path = pathlib.Path(__file__).parent.parent / "frontend" / "static" / "contractor-map.html"
        if atlas_path.is_file():
            return FileResponse(atlas_path, media_type="text/html")
        return JSONResponse({"error": "Atlas map not found"}, 404)

    # --- Static files (SvelteKit build) ---
    # Mount on a sub-path first, then add a catch-all for SPA fallback
    # This prevents the static mount from shadowing /api/* routes
    if static_dir and os.path.isdir(static_dir):
        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve static files, falling back to index.html for SPA routing."""
            import pathlib
            file_path = pathlib.Path(static_dir) / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            index = pathlib.Path(static_dir) / "index.html"
            if index.is_file():
                return FileResponse(index)
            return JSONResponse({"error": "Not found"}, 404)

    return app


# For uvicorn: `uvicorn backend.server:app`
app = create_app()
