# backend/deep_analysis.py
"""
Deep Analysis Pipeline — 5-step evidence distillation for DOE contract research.

Steps:
  1. SCOPE   — Dolphin3 identifies search keywords and technical terms.
  2. FILTER  — SQLite narrows the candidate contract set.
  3. SCORE   — Dolphin3 rates each candidate for relevance (batches of 30).
  4. DISTILL — Dolphin3 extracts dense evidence from top-scored contracts.
  5. SYNTHESIZE — Mercury2 (or Dolphin3 fallback) produces the final answer.

This module is standalone: it does NOT depend on hybrid_retriever or recipe_engine.
"""

import json
import re
import sqlite3
from typing import AsyncGenerator

from backend.ollama_client import OllamaClient
from backend.mercury_client import MercuryClient
from backend.brave_search import BraveSearchClient

# ---------------------------------------------------------------------------
# Refusal detection patterns
# ---------------------------------------------------------------------------
_REFUSAL_PATTERNS = re.compile(
    r"I cannot|I'm unable|I can't assist|against my guidelines|not appropriate",
    re.IGNORECASE,
)


def _is_refusal(text: str, min_length: int = 50) -> bool:
    """Return True if *text* looks like a model refusal."""
    if len(text.strip()) < min_length:
        return True
    return bool(_REFUSAL_PATTERNS.search(text))


class DeepAnalysisPipeline:
    """Five-step deep-analysis pipeline over the DOE contracts database."""

    def __init__(
        self,
        db_path: str,
        ollama: OllamaClient,
        mercury: MercuryClient | None = None,
        brave: BraveSearchClient | None = None,
    ):
        self.db_path = db_path
        self.ollama = ollama
        self.mercury = mercury
        self.brave = brave

    # ------------------------------------------------------------------
    # Helpers — log event factory & total contract count
    # ------------------------------------------------------------------

    @staticmethod
    def _log_event(level: str, message: str) -> dict:
        """Create a log SSE event dict."""
        return {"event": "log", "data": {"level": level, "message": message}}

    def _get_total_contract_count(self) -> int:
        """Return the total number of rows in the contracts table."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    # ======================================================================
    # Public entry point
    # ======================================================================

    async def analyze(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Run the full deep-analysis pipeline.

        Yields SSE-compatible event dicts with ``event`` and ``data`` keys.
        """
        conversation_history = conversation_history or []

        # Fetch total contract count once at the start for log messages
        total_contract_count = self._get_total_contract_count()

        # ------------------------------------------------------------------
        # Step 1 — SCOPE
        # ------------------------------------------------------------------
        yield {
            "event": "status",
            "data": {"stage": "scope", "message": "Identifying relevant search scope..."},
        }
        yield self._log_event("info", "Analyzing query to identify relevant search scope...")

        scope = await self._step_scope(query)

        # Emit detailed log about what the scope step found
        search_terms = scope.get("search_terms", [])
        if search_terms:
            yield self._log_event(
                "detail",
                f"Search terms: {', '.join(search_terms[:10])}{'...' if len(search_terms) > 10 else ''}",
            )
        psc_kw = scope.get("psc_keywords", [])
        if psc_kw:
            yield self._log_event(
                "detail",
                f"Target PSC codes: {', '.join(psc_kw[:8])}{'...' if len(psc_kw) > 8 else ''}",
            )
        recipients = scope.get("recipients", [])
        if recipients:
            yield self._log_event(
                "detail",
                f"Target recipients: {', '.join(recipients[:8])}{'...' if len(recipients) > 8 else ''}",
            )
        naics_kw = scope.get("naics_keywords", [])
        if naics_kw:
            yield self._log_event(
                "detail",
                f"NAICS keywords: {', '.join(naics_kw[:8])}{'...' if len(naics_kw) > 8 else ''}",
            )

        # ------------------------------------------------------------------
        # Step 2 — FILTER
        # ------------------------------------------------------------------
        all_terms = (
            scope.get("psc_keywords", [])
            + scope.get("naics_keywords", [])
            + scope.get("recipients", [])
            + scope.get("search_terms", [])
        )
        num_filter_conditions = sum(1 for t in all_terms if t.strip())
        yield self._log_event(
            "info",
            f"Querying {total_contract_count:,} contracts with {num_filter_conditions} filter conditions...",
        )

        candidates = self._step_filter(scope)

        yield {
            "event": "status",
            "data": {
                "stage": "filter",
                "message": f"Found {len(candidates)} candidate contracts",
                "count": len(candidates),
            },
        }
        yield self._log_event(
            "success",
            f"Found {len(candidates):,} candidate contracts matching scope",
        )

        # ------------------------------------------------------------------
        # Step 3 — SCORE
        # ------------------------------------------------------------------
        scored = []
        batch_size = 30
        total_batches = (len(candidates) + batch_size - 1) // batch_size
        running_relevant = 0

        for batch_idx in range(total_batches):
            batch_num = batch_idx + 1
            start = batch_idx * batch_size
            end = min(start + batch_size, len(candidates))

            yield {
                "event": "status",
                "data": {
                    "stage": "scoring",
                    "message": f"Scoring batch {batch_num}/{total_batches}...",
                    "progress": batch_num,
                    "total": total_batches,
                },
            }
            yield self._log_event(
                "info",
                f"Scoring batch {batch_num}/{total_batches} (contracts {start + 1}-{end})...",
            )

            batch = candidates[start:end]
            batch_scored = await self._step_score_batch(query, batch)
            scored.extend(batch_scored)

            # Emit per-batch detail
            batch_relevant = [s for s in batch_scored if s["score"] >= 5]
            batch_not_relevant = len(batch_scored) - len(batch_relevant)
            running_relevant += len(batch_relevant)
            top_find = ""
            if batch_relevant:
                best = max(batch_relevant, key=lambda s: s["score"])
                desc_short = (best.get("description") or "")[:60]
                top_find = f" Top find: '{desc_short}...' (score: {best['score']})"
            yield self._log_event(
                "detail",
                f"Batch {batch_num}: {len(batch_relevant)} relevant, {batch_not_relevant} not relevant.{top_find}",
            )

            # Every 10 batches, emit a progress summary
            if batch_num % 10 == 0 or batch_num == total_batches:
                scored_so_far = batch_num * batch_size
                scored_so_far = min(scored_so_far, len(candidates))
                pct = (running_relevant / scored_so_far * 100) if scored_so_far else 0
                yield self._log_event(
                    "info",
                    f"Progress: {scored_so_far:,}/{len(candidates):,} scored, "
                    f"{running_relevant} relevant so far ({pct:.1f}%)",
                )

        # Keep only contracts scoring >= 5, sort descending
        relevant = [s for s in scored if s["score"] >= 5]
        relevant.sort(key=lambda s: s["score"], reverse=True)

        yield self._log_event(
            "success",
            f"Scoring complete: {len(relevant):,} relevant contracts out of {len(candidates):,}",
        )

        # ------------------------------------------------------------------
        # Step 4 — DISTILL
        # ------------------------------------------------------------------
        top_contracts = relevant[:100]

        yield {
            "event": "status",
            "data": {
                "stage": "distill",
                "message": f"Distilling evidence from {len(top_contracts)} contracts...",
            },
        }
        yield self._log_event(
            "info",
            f"Distilling evidence from {len(top_contracts)} relevant contracts...",
        )
        yield self._log_event(
            "detail",
            "Organizing by process steps identified in contract descriptions...",
        )

        evidence = await self._step_distill(query, top_contracts)

        evidence_lines = len(evidence.splitlines()) if evidence else 0
        yield self._log_event(
            "success",
            f"Extracted {evidence_lines} lines of structured evidence",
        )

        # ------------------------------------------------------------------
        # Step 5 — SYNTHESIZE
        # ------------------------------------------------------------------
        yield {
            "event": "status",
            "data": {"stage": "synthesize", "message": "Synthesizing final answer..."},
        }

        # Decide which model to use and log it
        using_mercury = self.mercury and self.mercury.is_available()
        if using_mercury:
            yield self._log_event(
                "info",
                "Synthesizing answer using Mercury2 (128K context)...",
            )
        else:
            yield self._log_event(
                "warn",
                "Mercury2 not available, using Dolphin3 for synthesis",
            )

        # Optional web context
        web_context = ""
        if self.brave and self.brave.is_available():
            yield self._log_event("detail", "Fetching supplemental web context via Brave Search...")
            try:
                web_context = await self.brave.search_for_context(query, count=5)
                if web_context:
                    yield self._log_event("detail", "Web context retrieved successfully")
            except Exception:
                yield self._log_event("warn", "Web search failed, proceeding without web context")

        full_response = ""
        async for event in self._step_synthesize(
            query, evidence, web_context, conversation_history
        ):
            if event.get("event") == "token":
                full_response += event["data"]["content"]
            yield event

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
        yield self._log_event(
            "success",
            f"Analysis complete: {len(relevant):,} relevant contracts, {evidence_lines} evidence lines",
        )
        yield {
            "event": "done",
            "data": {
                "contracts_reviewed": len(candidates),
                "contracts_relevant": len(relevant),
                "evidence_lines": evidence_lines,
            },
        }

    # ======================================================================
    # Step 1 — SCOPE
    # ======================================================================

    async def _step_scope(self, query: str) -> dict:
        """Ask Dolphin3 to identify search keywords for the query."""
        prompt = (
            "Given this research question, identify:\n"
            "(a) relevant PSC code keywords (product or service code descriptions),\n"
            "(b) relevant NAICS keywords,\n"
            "(c) relevant recipient/lab names,\n"
            "(d) 10-15 technical search terms.\n\n"
            "Return as JSON with keys: psc_keywords, naics_keywords, recipients, search_terms.\n"
            "Each value should be a list of strings.\n\n"
            f"Research question: {query}"
        )

        raw = await self.ollama.generate(prompt)

        # Parse JSON from the response
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: use the query itself as the only search term
        return {
            "psc_keywords": [],
            "naics_keywords": [],
            "recipients": [],
            "search_terms": [query],
        }

    # ======================================================================
    # Step 2 — FILTER
    # ======================================================================

    def _step_filter(self, scope: dict) -> list[dict]:
        """Build a SQL WHERE clause from the scope and fetch candidate contracts."""
        terms: list[str] = []
        for kw in scope.get("psc_keywords", []):
            terms.append(kw)
        for kw in scope.get("naics_keywords", []):
            terms.append(kw)
        for kw in scope.get("recipients", []):
            terms.append(kw)
        for kw in scope.get("search_terms", []):
            terms.append(kw)

        if not terms:
            return []

        # Build LIKE conditions across several columns
        like_clauses: list[str] = []
        params: list[str] = []
        for term in terms:
            clean = term.strip()
            if not clean:
                continue
            like_clauses.append(
                "(product_or_service_code_description LIKE ? "
                "OR naics_description LIKE ? "
                "OR transaction_description LIKE ? "
                "OR recipient_name LIKE ?)"
            )
            wildcard = f"%{clean}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        if not like_clauses:
            return []

        where = " OR ".join(like_clauses)
        sql = (
            "SELECT contract_transaction_unique_key, transaction_description, "
            "recipient_name, federal_action_obligation, action_date_fiscal_year, "
            "product_or_service_code_description, naics_description "
            f"FROM contracts WHERE ({where}) AND transaction_description IS NOT NULL"
        )

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        candidates = []
        for row in rows:
            candidates.append({
                "key": row["contract_transaction_unique_key"],
                "description": row["transaction_description"],
                "recipient": row["recipient_name"],
                "obligation": row["federal_action_obligation"],
                "fiscal_year": row["action_date_fiscal_year"],
                "psc": row["product_or_service_code_description"],
                "naics": row["naics_description"],
            })

        return candidates

    # ======================================================================
    # Step 3 — SCORE (single batch)
    # ======================================================================

    async def _step_score_batch(
        self, query: str, batch: list[dict]
    ) -> list[dict]:
        """Score a batch of candidates (up to 30) for relevance to the query."""
        contract_lines = []
        for c in batch:
            contract_lines.append(
                f'  {{"id": "{c["key"]}", "desc": "{c["description"][:200]}"}}'
            )

        batch_json = "[\n" + ",\n".join(contract_lines) + "\n]"

        prompt = (
            f"Rate each contract description 0-10 for relevance to: '{query}'.\n"
            "Return ONLY a JSON array of objects with keys: id, score, reason.\n"
            "score is an integer 0-10. reason is one short sentence.\n\n"
            f"Contracts:\n{batch_json}"
        )

        raw = await self.ollama.generate(prompt)

        # Parse the JSON array from the response
        try:
            start = raw.find("[")
            end = raw.rfind("]")
            if start >= 0 and end > start:
                scored = json.loads(raw[start : end + 1])
                # Merge scores back into candidates
                score_map = {s["id"]: s for s in scored if "id" in s and "score" in s}
                results = []
                for c in batch:
                    info = score_map.get(c["key"], {})
                    results.append({
                        **c,
                        "score": int(info.get("score", 0)),
                        "reason": info.get("reason", ""),
                    })
                return results
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Fallback: assign score 0 to everything
        return [{**c, "score": 0, "reason": "parse error"} for c in batch]

    # ======================================================================
    # Step 4 — DISTILL
    # ======================================================================

    async def _step_distill(self, query: str, contracts: list[dict]) -> str:
        """Extract dense evidence from the top-scored contracts."""
        if not contracts:
            return "No relevant contracts found."

        contract_lines = []
        for c in contracts:
            contract_lines.append(
                f"- [{c['key']}] {c['recipient']}: {c['description']} "
                f"(${c['obligation']:,.0f}, FY{c['fiscal_year']}, score={c['score']})"
            )

        prompt = (
            "From these DOE contracts, extract the key technical findings "
            "organized by process step. For each finding, note the specific "
            "materials, parameters, techniques, and which lab does the work.\n\n"
            f"Research question: {query}\n\n"
            "Contracts:\n" + "\n".join(contract_lines)
        )

        return await self.ollama.generate(prompt)

    # ======================================================================
    # Step 5 — SYNTHESIZE
    # ======================================================================

    async def _step_synthesize(
        self,
        query: str,
        evidence: str,
        web_context: str,
        conversation_history: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """Stream the final synthesized answer.

        Yields SSE event dicts — either token events or log events.
        Uses Mercury2 when available, with automatic refusal detection and
        Dolphin3 fallback.
        """
        system_msg = {
            "role": "system",
            "content": (
                "You are an expert process engineer and technical researcher with "
                "deep expertise in DOE-funded technologies. You have been given "
                "distilled evidence from DOE contract records and web research.\n\n"
                "Provide a comprehensive, technically detailed answer to the "
                "research question. Organize by process steps when applicable. "
                "Cite specific labs, materials, parameters, and dollar amounts "
                "from the evidence. Do NOT just list sources — synthesize them "
                "into integrated technical knowledge."
            ),
        }

        evidence_section = f"### DISTILLED EVIDENCE FROM DOE CONTRACTS:\n{evidence}\n"
        web_section = ""
        if web_context:
            web_section = f"\n### TECHNICAL RESEARCH FROM THE WEB:\n{web_context}\n"

        user_msg = {
            "role": "user",
            "content": (
                f"{evidence_section}{web_section}\n"
                f"### RESEARCH QUESTION:\n{query}"
            ),
        }

        messages = [system_msg] + list(conversation_history) + [user_msg]

        # Try Mercury2 first if available
        if self.mercury and self.mercury.is_available():
            response_text = ""
            try:
                async for token in self.mercury.chat_stream(messages):
                    response_text += token
                    yield {"event": "token", "data": {"content": token}}

                # Check for refusal
                if _is_refusal(response_text):
                    yield self._log_event(
                        "warn",
                        "Mercury2 declined query, reformulating via Dolphin3...",
                    )
                    # Attempt reformulation via Dolphin3
                    reformulated = await self._reformulate_query(query)
                    if reformulated and reformulated != query:
                        yield self._log_event(
                            "detail",
                            f"Reformulated: '{reformulated[:120]}{'...' if len(reformulated) > 120 else ''}'",
                        )
                        # Rebuild user message with reformulated query
                        retry_user_msg = {
                            "role": "user",
                            "content": (
                                f"{evidence_section}{web_section}\n"
                                f"### RESEARCH QUESTION:\n{reformulated}"
                            ),
                        }
                        retry_messages = [system_msg] + list(conversation_history) + [retry_user_msg]

                        retry_text = ""
                        try:
                            async for token in self.mercury.chat_stream(retry_messages):
                                retry_text += token
                                yield {"event": "token", "data": {"content": token}}

                            if not _is_refusal(retry_text):
                                return  # Success on retry
                        except Exception:
                            pass

                    # Retry also refused or failed — fall through to Dolphin3
                    yield self._log_event(
                        "warn",
                        "Mercury2 retry failed, falling back to Dolphin3...",
                    )
                    yield {"event": "token", "data": {"content": "\n\n---\n*Switching to local model for synthesis...*\n\n"}}
                    async for token in self.ollama.chat_stream(messages):
                        yield {"event": "token", "data": {"content": token}}
                    return

                # Mercury succeeded without refusal
                return
            except Exception:
                # Mercury failed entirely — fall through to Dolphin3
                yield self._log_event(
                    "warn",
                    "Mercury2 connection failed, falling back to Dolphin3...",
                )

        # Dolphin3 fallback (or primary when Mercury is unavailable)
        async for token in self.ollama.chat_stream(messages):
            yield {"event": "token", "data": {"content": token}}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _reformulate_query(self, query: str) -> str:
        """Ask Dolphin3 to reformulate a query that was refused by Mercury2."""
        prompt = (
            f"Mercury2 refused this question: '{query}'. "
            "Reformulate as an academic/research question that asks for the same "
            "technical information without triggering safety filters. "
            "Return ONLY the reformulated question."
        )
        try:
            return (await self.ollama.generate(prompt)).strip()
        except Exception:
            return query
