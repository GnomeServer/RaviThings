# backend/server.py
"""FastAPI server for DOE GraphRAG."""
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

# Keywords that indicate a "how to make" question warranting schematic extraction
_SCHEMATIC_KEYWORDS = re.compile(
    r"\b(how|make|made|manufacture|fabricate|produce|synthesize|process|recipe)\b",
    re.IGNORECASE,
)

_SCHEMATIC_JSON_SCHEMA = '{"title":"string","inputs":[{"id":"in1","name":"Chemical name (formula)","type":"raw_material|precursor|equipment|energy","sources":{"commercial":["Real supplier names"],"diy":"How to synthesize this yourself"},"feeds_into":["step1"]}],"steps":[{"id":"step1","name":"Process step name","description":"Detailed description of what happens in this step","parameters":{"key":"value with real numbers"},"equipment":["Specific equipment needed"],"inputs_from":["in1"],"outputs_to":["step2"],"doe_contractors":["Real lab names from contracts"],"investment":"Real dollar amount or unknown"}],"outputs":[{"id":"out1","name":"Product name","description":"Detailed description of the output product and its properties","type":"intermediate|final","receives_from":["step1"]}]}'

_SCHEMATIC_CREATE_PROMPT = """\
Extract a manufacturing process schematic from the information below. Return ONLY valid JSON.

RULES:
- Use REAL values, not placeholders. If unknown, omit the field or use "unknown".
- For inputs: actual chemical compounds with formulas. Commercial sources: real suppliers (Sigma-Aldrich, Alfa Aesar, MSE Supplies, MTI Corp, Thermo Fisher). DIY: how to synthesize the precursor.
- For steps: actual process parameters (real temperatures, times, pressures).
- For doe_contractors: actual lab/company names from the contract data.
- For investment: actual dollar amounts from contracts if available.
- Connect inputs to steps and steps to outputs using id fields.

JSON SCHEMA:
""" + _SCHEMATIC_JSON_SCHEMA + "\n\n"

_SCHEMATIC_UPDATE_PROMPT = """\
You have an EXISTING process schematic (shown below as JSON). The user asked a follow-up question and got a new answer with more detail. UPDATE the existing schematic by:

1. KEEP all existing steps, inputs, and outputs that are still relevant.
2. ADD new information: fill in missing parameters, add new inputs/steps/outputs discovered.
3. ENRICH existing entries: add more detail to descriptions, add equipment, add suppliers, update parameters with more specific values.
4. NEVER remove existing data unless it's clearly wrong.
5. Preserve all existing id values so connections aren't broken.

Return the COMPLETE updated schematic as valid JSON (not just the changes).

JSON SCHEMA:
""" + _SCHEMATIC_JSON_SCHEMA + """

EXISTING SCHEMATIC:
{existing_schematic}

"""


def _is_schematic_query(text: str) -> bool:
    """Return True if the user message looks like a 'how to make' question."""
    return bool(_SCHEMATIC_KEYWORDS.search(text))


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

        # Load embedding model (shared between ChromaDB retriever and graph engine)
        embed_model = None
        try:
            from sentence_transformers import SentenceTransformer
            embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            pass

        if graph_path and os.path.exists(graph_path):
            state["graph"] = GraphEngine(graph_path, embed_model=embed_model)
        else:
            state["graph"] = None

        state["ollama"] = OllamaClient(base_url=ollama_host, model=ollama_model)
        state["brave"] = BraveSearchClient()  # reads BRAVE_SEARCH_API_KEY from env

        chroma = chroma_path if chroma_path and os.path.exists(chroma_path) else None
        state["retriever"] = HybridRetriever(
            db_path=db_path,
            graph_engine=state["graph"],
            chroma_path=chroma,
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
            full_response_parts: list[str] = []
            async for token in ollama.chat_stream(augmented):
                full_response_parts.append(token)
                yield {"event": "token", "data": json.dumps({"content": token})}

            # 4. Process schematic extraction (only for "how to make" queries)
            if _is_schematic_query(user_msg):
                has_existing = req.schematic and req.schematic.get("title")
                status_msg = "Updating process schematic..." if has_existing else "Extracting process schematic..."
                yield {"event": "status", "data": json.dumps({"stage": "schematic", "message": status_msg})}
                try:
                    full_response_text = "".join(full_response_parts)
                    # Feed the extraction ALL context: contracts + web + LLM response
                    new_info = (
                        "DOE CONTRACT DATA:\n" + "\n".join(contract_lines) + "\n\n"
                        + (f"WEB RESEARCH:\n{web_context}\n\n" if web_context else "")
                        + "NEW INFORMATION FROM LATEST ANSWER:\n" + full_response_text
                    )

                    if has_existing:
                        # UPDATE existing schematic — enrich, don't replace
                        prompt = _SCHEMATIC_UPDATE_PROMPT.format(
                            existing_schematic=json.dumps(req.schematic, indent=2)
                        ) + new_info
                    else:
                        # CREATE new schematic from scratch
                        prompt = _SCHEMATIC_CREATE_PROMPT + new_info

                    raw_schematic = await ollama.generate(prompt)

                    # LLMs often return JSON with extra text — extract between first { and last }
                    start = raw_schematic.find("{")
                    end = raw_schematic.rfind("}")
                    if start >= 0 and end > start:
                        schematic_data = json.loads(raw_schematic[start:end + 1])
                    else:
                        schematic_data = json.loads(raw_schematic)

                    yield {
                        "event": "process_schematic",
                        "data": json.dumps(schematic_data),
                    }
                except Exception as e:
                    yield {"event": "status", "data": json.dumps({"stage": "schematic_failed", "message": f"Could not extract schematic: {type(e).__name__}"})}

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
