# backend/recipe_engine.py
"""Recipe synthesis engine: multi-query agentic research loop."""
import asyncio
import json
from typing import AsyncGenerator
from backend.glm_client import GLMClient
from backend.hybrid_retriever import HybridRetriever, ContractResult

DECOMPOSE_PROMPT = """You are a process engineer researching how something is made.
Given this question: "{query}"

Generate 5-8 specific technical search queries that would help you find information about
every stage of this manufacturing/research process. Think about:
- Raw materials and precursors
- Synthesis and fabrication methods
- Processing and forming techniques
- Characterization and testing
- Assembly and integration
- Scale-up and manufacturing

Return ONLY a JSON array of search query strings. No explanation.

Example for "how are solid electrolytes made":
["ceramic electrolyte powder synthesis", "solid electrolyte thin film deposition", "garnet LLZO sintering", "electrolyte characterization ionic conductivity", "electrode electrolyte interface processing"]"""

SYNTHESIZE_PROMPT = """You are a process engineer synthesizing a complete manufacturing recipe.

QUESTION: {query}

You have gathered evidence from two sources:
1. {count} DOE contracts (${dollars:,.0f} total investment) — reveal what processes and techniques are actually being funded
2. Web research — provides technical details, process parameters, and published science

EVIDENCE:
{evidence}

TASK: Synthesize a step-by-step manufacturing recipe by combining BOTH sources.
- DOE contracts tell you WHAT is being done and WHO is doing it
- Web research tells you HOW it's done (specific parameters, materials, conditions)
- Your expertise connects the dots and fills remaining gaps

For each step provide:
1. Step name (the actual process)
2. Detailed technical description — specific materials, temperatures, techniques, equipment
3. Which DOE labs/contractors perform this work (from contract evidence)
4. Key technical parameters (from web research)

Be specific and technical. Integrate all sources into a unified, actionable recipe.
Do not just list sources — synthesize them into engineering knowledge.

Format as numbered steps."""


class RecipeEngine:
    def __init__(
        self,
        llm: GLMClient,
        retriever: HybridRetriever,
        brave_search=None,  # Optional BraveSearchClient
        max_rounds: int = 3,
    ):
        self.llm = llm
        self.retriever = retriever
        self.brave_search = brave_search
        self.max_rounds = max_rounds

    async def synthesize(self, query: str) -> AsyncGenerator[dict, None]:
        """Run the full recipe synthesis loop. Yields SSE-compatible event dicts."""

        # Phase 1: DECOMPOSE
        decompose_prompt = DECOMPOSE_PROMPT.format(query=query)
        raw_response = await self.llm.generate(decompose_prompt)

        try:
            # Try to parse JSON array from response
            sub_queries = json.loads(raw_response)
            if not isinstance(sub_queries, list):
                sub_queries = [query]
        except json.JSONDecodeError:
            sub_queries = [query]

        # Ensure we always include the original query
        if query not in sub_queries:
            sub_queries.insert(0, query)

        yield {"event": "phase", "data": {"phase": "decompose", "sub_queries": len(sub_queries)}}

        # Phase 2: EXPLORE
        all_contracts: dict[str, ContractResult] = {}
        all_topics: set[str] = set()
        all_graph_paths = {"nodes": [], "edges": []}

        round_num = 0
        for round_num in range(1, self.max_rounds + 1):
            round_new_topics = set()

            for sq in sub_queries:
                # Run sync retriever in thread to avoid blocking event loop
                results = await asyncio.to_thread(self.retriever.search, sq, 20)
                for contract in results.contracts:
                    if contract.key not in all_contracts:
                        all_contracts[contract.key] = contract
                # Collect topics from graph paths
                for node in results.graph_paths.get("nodes", []):
                    if node.get("type") == "topic":
                        topic_name = node.get("label", "")
                        if topic_name and topic_name not in all_topics:
                            round_new_topics.add(topic_name)
                            all_topics.add(topic_name)

                # Merge graph paths
                all_graph_paths["nodes"].extend(results.graph_paths.get("nodes", []))
                all_graph_paths["edges"].extend(results.graph_paths.get("edges", []))

            yield {
                "event": "round",
                "data": {
                    "round": round_num,
                    "contracts": len(all_contracts),
                    "topics": len(all_topics),
                    "new_topics": len(round_new_topics),
                },
            }

            # Convergence check: <10% new topics
            if len(all_topics) > 0 and len(round_new_topics) / max(len(all_topics), 1) < 0.1:
                break

            # Generate new sub-queries from discovered topics for next round
            if round_new_topics:
                sub_queries = list(round_new_topics)[:5]
            else:
                break

        yield {
            "event": "converged",
            "data": {
                "total_contracts": len(all_contracts),
                "total_topics": len(all_topics),
                "rounds": round_num,
            },
        }

        # Phase 3: SYNTHESIZE
        total_dollars = sum(c.obligation for c in all_contracts.values())
        evidence_lines = []
        for c in sorted(all_contracts.values(), key=lambda x: abs(x.obligation), reverse=True)[:30]:
            evidence_lines.append(
                f"- {c.recipient}: {c.description} (${c.obligation:,.0f}, FY{c.fiscal_year}) [{c.psc}]"
            )

        # Web research to supplement DOE contract evidence
        web_context = ""
        if self.brave_search and self.brave_search.is_available():
            yield {"event": "phase", "data": {"phase": "web_research"}}
            web_context = await self.brave_search.search_for_context(
                f"{query} manufacturing process technical details", count=5
            )

        evidence = "\n".join(evidence_lines)
        if web_context:
            evidence += (
                "\n\n--- TECHNICAL RESEARCH FROM THE WEB ---\n"
                f"{web_context}"
            )

        synth_prompt = SYNTHESIZE_PROMPT.format(
            query=query,
            count=len(all_contracts),
            dollars=total_dollars,
            evidence=evidence,
        )

        # Stream the synthesis narrative
        full_response = ""
        async for token in self.llm.chat_stream(
            [{"role": "user", "content": synth_prompt}]
        ):
            full_response += token
            yield {"event": "token", "data": {"content": token}}

        # Extract structured recipe steps from the response
        steps = self._parse_recipe_steps(full_response, all_contracts)
        for step in steps:
            yield {"event": "recipe_step", "data": step}

        # Emit graph highlight
        yield {
            "event": "graph_highlight",
            "data": all_graph_paths,
        }

        # Determine confidence based on evidence density
        confidence = "high" if len(all_contracts) > 20 else "medium" if len(all_contracts) > 5 else "low"

        yield {
            "event": "done",
            "data": {
                "steps": len(steps),
                "confidence": confidence,
                "total_contracts": len(all_contracts),
                "total_dollars": total_dollars,
            },
        }

    @staticmethod
    def _parse_recipe_steps(text: str, contracts: dict[str, ContractResult]) -> list[dict]:
        """Parse numbered steps from LLM response into structured recipe_step dicts."""
        import re
        steps = []
        # Match patterns like "1. Step Name" or "Step 1: Name"
        pattern = r'(?:^|\n)\s*(?:Step\s+)?(\d+)[.:)\-]\s*\*?\*?([^\n*]+)'
        matches = re.findall(pattern, text)
        for num, name in matches:
            # Find contractors mentioned in this step's text
            step_contractors = set()
            for c in contracts.values():
                if c.recipient and c.recipient.lower() in text.lower():
                    step_contractors.add(c.recipient)
            steps.append({
                "step": int(num),
                "name": name.strip().rstrip("*"),
                "who": list(step_contractors)[:5],
                "dollars": 0,  # Approximation -- full attribution requires deeper analysis
                "contracts": 0,
            })
        return steps if steps else [{"step": 1, "name": "See narrative above", "who": [], "dollars": 0, "contracts": 0}]
