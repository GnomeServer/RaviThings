# backend/saturate.py
"""
Saturation Pipeline — iterative knowledge extraction until convergence.

Repeatedly queries the same question, accumulating knowledge in the
schematic until structural diffing shows no new entities are being
discovered.  Uses stochasticity in retrieval + LLM as a feature:
each pass surfaces different contracts and angles.
"""

import asyncio
import json
import re
from typing import AsyncGenerator

from backend.ollama_client import OllamaClient
from backend.mercury_client import HermesClient
from backend.brave_search import BraveSearchClient
from backend.hybrid_retriever import HybridRetriever


# Reuse the same schema/prompts from server.py would create a circular import,
# so we define a local copy of what we need.

_SCHEMATIC_JSON_SCHEMA = '{"title":"string","inputs":[{"id":"in1","name":"Chemical name (formula)","type":"raw_material|precursor|equipment|energy","sources":{"commercial":["Real supplier names"],"diy":"How to synthesize this yourself"},"feeds_into":["step1"]}],"steps":[{"id":"step1","name":"Process step name","description":"Detailed description of what happens in this step","parameters":{"key":"value with real numbers"},"equipment":["Specific equipment needed"],"inputs_from":["in1"],"outputs_to":["step2"],"doe_contractors":["Real lab names from contracts"],"investment":"Real dollar amount or unknown","contractor_details":[{"name":"Real contractor/lab name","role":"Specific contribution to this step","contract_value":12400000,"significance_pct":42.3}],"step_total_capital":29400000}],"outputs":[{"id":"out1","name":"Product name","description":"Detailed description of the output product and its properties","type":"intermediate|final","receives_from":["step1"]}]}'

_SATURATE_CREATE_PROMPT = """\
Extract a manufacturing process schematic from the information below. Return ONLY valid JSON.

RULES:
- Use REAL values, not placeholders. If unknown, omit the field or use "unknown".
- For inputs: actual chemical compounds with formulas.
- For steps: actual process parameters (real temperatures, times, pressures).
- For doe_contractors: actual lab/company names from the contract data.
- For contractor_details: list each DOE contractor with their specific role, contract_value in dollars, and significance_pct (share of capital for this step, summing to ~100 within each step).
- Connect inputs to steps and steps to outputs using id fields.

JSON SCHEMA:
""" + _SCHEMATIC_JSON_SCHEMA + "\n\n"

_SATURATE_UPDATE_PROMPT = """\
You have an EXISTING process schematic (shown below as JSON). New evidence has been gathered. UPDATE the existing schematic by:

1. KEEP all existing steps, inputs, and outputs.
2. ADD new steps, inputs, outputs, contractors, parameters, or equipment discovered in the new evidence.
3. ENRICH existing entries: add more detail, update parameters with more specific values.
4. NEVER remove existing data unless clearly wrong.
5. Preserve all existing id values so connections aren't broken.
6. For contractor_details: add any newly discovered contractors. Update significance_pct values based on the complete picture.

Return the COMPLETE updated schematic as valid JSON (not just the changes).

JSON SCHEMA:
""" + _SCHEMATIC_JSON_SCHEMA + """

EXISTING SCHEMATIC:
{existing_schematic}

"""


def _strip_think_traces(text: str) -> str:
    """Remove <think>...</think> reasoning traces from Hermes-4 responses."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _structural_diff(old: dict | None, new: dict | None) -> dict:
    """Compare two schematics and return counts of new entities."""
    if new is None:
        return {"new_steps": 0, "new_inputs": 0, "new_outputs": 0,
                "new_contractors": 0, "new_params": 0, "new_equipment": 0, "total_new": 0}

    if old is None:
        n_steps = len(new.get("steps", []))
        n_inputs = len(new.get("inputs", []))
        n_outputs = len(new.get("outputs", []))
        n_contractors = sum(len(s.get("contractor_details", [])) for s in new.get("steps", []))
        n_params = sum(len(s.get("parameters", {})) for s in new.get("steps", []))
        n_equip = sum(len(s.get("equipment", [])) for s in new.get("steps", []))
        total = n_steps + n_inputs + n_outputs + n_contractors + n_params + n_equip
        return {"new_steps": n_steps, "new_inputs": n_inputs, "new_outputs": n_outputs,
                "new_contractors": n_contractors, "new_params": n_params,
                "new_equipment": n_equip, "total_new": total}

    # Extract entity sets from old schematic
    old_step_names = {s.get("name", "").lower() for s in old.get("steps", [])}
    old_input_names = {i.get("name", "").lower() for i in old.get("inputs", [])}
    old_output_names = {o.get("name", "").lower() for o in old.get("outputs", [])}
    old_contractors: set[str] = set()
    old_params: set[str] = set()
    old_equipment: set[str] = set()
    for s in old.get("steps", []):
        sid = s.get("id", "")
        for c in s.get("contractor_details", []):
            old_contractors.add(c.get("name", "").lower())
        # Also count doe_contractors flat list
        for c in s.get("doe_contractors", []):
            old_contractors.add(c.lower())
        for k in s.get("parameters", {}):
            old_params.add(f"{sid}:{k.lower()}")
        for e in s.get("equipment", []):
            old_equipment.add(e.lower())

    # Count new entities
    new_steps = {s.get("name", "").lower() for s in new.get("steps", [])} - old_step_names
    new_inputs = {i.get("name", "").lower() for i in new.get("inputs", [])} - old_input_names
    new_outputs = {o.get("name", "").lower() for o in new.get("outputs", [])} - old_output_names
    new_contractors: set[str] = set()
    new_params: set[str] = set()
    new_equip: set[str] = set()
    for s in new.get("steps", []):
        sid = s.get("id", "")
        for c in s.get("contractor_details", []):
            name = c.get("name", "").lower()
            if name and name not in old_contractors:
                new_contractors.add(name)
        for c in s.get("doe_contractors", []):
            if c.lower() not in old_contractors:
                new_contractors.add(c.lower())
        for k in s.get("parameters", {}):
            key = f"{sid}:{k.lower()}"
            if key not in old_params:
                new_params.add(key)
        for e in s.get("equipment", []):
            if e.lower() not in old_equipment:
                new_equip.add(e.lower())

    return {
        "new_steps": len(new_steps),
        "new_inputs": len(new_inputs),
        "new_outputs": len(new_outputs),
        "new_contractors": len(new_contractors),
        "new_params": len(new_params),
        "new_equipment": len(new_equip),
        "total_new": (len(new_steps) + len(new_inputs) + len(new_outputs)
                      + len(new_contractors) + len(new_params) + len(new_equip)),
    }


def _extract_json(raw: str) -> dict | None:
    """Extract JSON object from LLM response, stripping think traces."""
    raw = _strip_think_traces(raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


class SaturationPipeline:
    """Iterative knowledge saturation pipeline."""

    def __init__(
        self,
        retriever: HybridRetriever,
        ollama: OllamaClient,
        hermes: HermesClient | None = None,
        brave: BraveSearchClient | None = None,
    ):
        self.retriever = retriever
        self.ollama = ollama
        self.hermes = hermes
        self.brave = brave

    @staticmethod
    def _evt(event: str, data: dict) -> dict:
        return {"event": event, "data": data}

    async def saturate(
        self,
        query: str,
        max_passes: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Run iterative saturation. Yields SSE event dicts.

        Stops when structural diff shows 0 new entities for 2 consecutive passes,
        or when max_passes is reached (if set).
        """
        accumulated_schematic: dict | None = None
        seen_contract_keys: set[str] = set()
        consecutive_zero = 0
        pass_num = 0
        cumulative_new = 0
        all_responses: list[str] = []

        yield self._evt("status", {
            "stage": "saturate_start",
            "message": "Saturation mode — searching until knowledge is exhausted",
        })

        while True:
            pass_num += 1

            if max_passes is not None and pass_num > max_passes:
                yield self._evt("status", {
                    "stage": "saturate_limit",
                    "message": f"Reached pass limit ({max_passes}). Stopping.",
                })
                break

            # ---- RETRIEVE ----
            yield self._evt("status", {
                "stage": "saturate_search",
                "message": f"Pass {pass_num} — Searching contracts (vector + keyword + graph)...",
            })

            results = await asyncio.to_thread(self.retriever.search, query)
            total_contracts = len(results.contracts)
            new_keys = {c.key for c in results.contracts} - seen_contract_keys
            seen_contract_keys.update(c.key for c in results.contracts)

            yield self._evt("status", {
                "stage": "saturate_search",
                "message": f"Pass {pass_num} — Retrieved {total_contracts} contracts ({len(new_keys)} not seen in prior passes)",
            })

            # Build contract context
            contract_lines = []
            for c in results.contracts:
                contract_lines.append(
                    f"- {c.recipient}: {c.description} (${c.obligation:,.0f}, FY{c.fiscal_year})"
                )

            # ---- WEB SEARCH ----
            web_context = ""
            if self.brave and self.brave.is_available():
                yield self._evt("status", {
                    "stage": "saturate_web",
                    "message": f"Pass {pass_num} — Searching web for supplemental context...",
                })
                try:
                    web_context = await self.brave.search_for_context(query, count=5)
                    if web_context:
                        n_results = len(web_context.split("\n- "))
                        yield self._evt("status", {
                            "stage": "saturate_web",
                            "message": f"Pass {pass_num} — Web: {n_results} results retrieved",
                        })
                except Exception:
                    yield self._evt("status", {
                        "stage": "saturate_web",
                        "message": f"Pass {pass_num} — Web search failed, continuing without",
                    })

            # ---- GENERATE RESPONSE ----
            # Build prompt that steers toward NEW information
            system_msg = {
                "role": "system",
                "content": (
                    "You are an expert process engineer and technical researcher with "
                    "deep expertise in DOE-funded technologies. "
                    "You have access to DOE contract records and web research.\n\n"
                    "IMPORTANT: Focus on information NOT already covered in the "
                    "existing knowledge summary below. Identify NEW details, "
                    "contractors, parameters, materials, equipment, or process steps.\n\n"
                    "If you find nothing new, respond with: NO NEW INFORMATION"
                ),
            }

            existing_knowledge = ""
            if accumulated_schematic:
                existing_knowledge = (
                    "\n\n### WHAT WE ALREADY KNOW (do NOT repeat this):\n"
                    + json.dumps(accumulated_schematic, indent=2)[:6000]
                )

            web_section = ""
            if web_context:
                web_section = f"\n\n### TECHNICAL RESEARCH FROM THE WEB:\n{web_context}\n"

            user_msg = {
                "role": "user",
                "content": (
                    f"### DOE CONTRACTS:\n" + "\n".join(contract_lines)
                    + web_section
                    + existing_knowledge
                    + f"\n\n### RESEARCH QUESTION:\n{query}"
                ),
            }

            messages = [system_msg, user_msg]

            yield self._evt("status", {
                "stage": "saturate_generate",
                "message": f"Pass {pass_num} — Generating response (focusing on new information)...",
            })

            # Stream response
            response_parts: list[str] = []
            use_hermes = self.hermes and self.hermes.is_available()

            if pass_num == 1:
                # First pass: stream tokens to user
                yield self._evt("status", {
                    "stage": "generating",
                    "message": "Generating initial response...",
                })
            else:
                yield self._evt("token", {
                    "content": f"\n\n---\n**Pass {pass_num} — New findings:**\n\n",
                })

            fell_back = False
            if use_hermes:
                try:
                    async for token in self.hermes.chat_stream(messages):
                        response_parts.append(token)
                        yield self._evt("token", {"content": token})
                except Exception:
                    if not response_parts:
                        fell_back = True
            if not use_hermes or fell_back:
                async for token in self.ollama.chat_stream(messages):
                    response_parts.append(token)
                    yield self._evt("token", {"content": token})

            response_text = "".join(response_parts)
            all_responses.append(response_text)

            word_count = len(response_text.split())
            yield self._evt("status", {
                "stage": "saturate_generate",
                "message": f"Pass {pass_num} — Response complete: {word_count} words",
            })

            # Check for explicit "no new information" signal
            if "NO NEW INFORMATION" in response_text.upper() and pass_num > 1:
                yield self._evt("status", {
                    "stage": "saturate_converged",
                    "message": f"Pass {pass_num} — Model reports no new information. Saturated.",
                })
                consecutive_zero += 1
                if consecutive_zero >= 2:
                    break
                continue

            # ---- EXTRACT/UPDATE SCHEMATIC ----
            yield self._evt("status", {
                "stage": "saturate_schematic",
                "message": f"Pass {pass_num} — {'Updating' if accumulated_schematic else 'Extracting'} schematic...",
            })

            new_info = (
                "DOE CONTRACT DATA:\n" + "\n".join(contract_lines) + "\n\n"
                + (f"WEB RESEARCH:\n{web_context}\n\n" if web_context else "")
                + "NEW INFORMATION FROM LATEST ANSWER:\n" + response_text
            )

            if accumulated_schematic:
                prompt = (
                    _SATURATE_UPDATE_PROMPT
                    .replace("{existing_schematic}", json.dumps(accumulated_schematic, indent=2))
                ) + new_info
            else:
                prompt = _SATURATE_CREATE_PROMPT + new_info

            # Use Hermes for schematic extraction (large context)
            raw_schematic = None
            if use_hermes and not fell_back:
                try:
                    raw_schematic = await self.hermes.chat(
                        [{"role": "user", "content": prompt}]
                    )
                except Exception:
                    pass

            if raw_schematic is None:
                # Truncate for Dolphin3
                if len(prompt) > 7000:
                    prompt = prompt[:7000] + "\n\n[...truncated]"
                raw_schematic = await self.ollama.generate(prompt)

            new_schematic = _extract_json(raw_schematic)

            if new_schematic is None:
                yield self._evt("status", {
                    "stage": "saturate_schematic",
                    "message": f"Pass {pass_num} — Could not parse schematic JSON, retrying next pass",
                })
                continue

            # ---- STRUCTURAL DIFF ----
            diff = _structural_diff(accumulated_schematic, new_schematic)

            yield self._evt("status", {
                "stage": "saturate_diff",
                "message": (
                    f"Pass {pass_num} — Structural diff: {diff['total_new']} new entities "
                    f"(steps: +{diff['new_steps']}, contractors: +{diff['new_contractors']}, "
                    f"params: +{diff['new_params']}, equipment: +{diff['new_equipment']})"
                ),
            })

            cumulative_new += diff["total_new"]

            # Update accumulated schematic
            accumulated_schematic = new_schematic

            # Emit updated schematic to frontend
            yield self._evt("process_schematic", new_schematic)

            n_steps = len(new_schematic.get("steps", []))
            n_inputs = len(new_schematic.get("inputs", []))
            n_contractors = sum(
                len(s.get("contractor_details", []))
                for s in new_schematic.get("steps", [])
            )
            yield self._evt("status", {
                "stage": "saturate_schematic",
                "message": (
                    f"Pass {pass_num} — Schematic: {n_steps} steps, "
                    f"{n_inputs} inputs, {n_contractors} contractors mapped"
                ),
            })

            # Convergence check
            if diff["total_new"] == 0:
                consecutive_zero += 1
                yield self._evt("status", {
                    "stage": "saturate_converging",
                    "message": (
                        f"Pass {pass_num} — No new entities found "
                        f"({consecutive_zero}/2 consecutive zero-gain passes)"
                    ),
                })
                if consecutive_zero >= 2:
                    break
            else:
                consecutive_zero = 0

            yield self._evt("status", {
                "stage": "saturate_progress",
                "message": (
                    f"Pass {pass_num} complete — Cumulative: {cumulative_new} new entities "
                    f"from {len(seen_contract_keys)} unique contracts across {pass_num} passes"
                ),
            })

        # ---- DONE ----
        yield self._evt("status", {
            "stage": "saturate_done",
            "message": (
                f"Knowledge saturated after {pass_num} passes. "
                f"Total: {cumulative_new} entities from {len(seen_contract_keys)} unique contracts"
            ),
        })

        yield self._evt("done", {
            "passes": pass_num,
            "total_new_entities": cumulative_new,
            "unique_contracts": len(seen_contract_keys),
        })
