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

from backend.glm_client import GLMClient
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

_SATURATE_DELTA_PROMPT = """\
You are analyzing new evidence about a manufacturing process. An existing schematic already covers these steps:

EXISTING STEPS (do NOT repeat these — only provide NEW information):
{existing_step_names}

Based on the new evidence below, extract ONLY:
1. NEW process steps not already in the list above
2. NEW parameters, equipment, or contractor details for existing steps (reference them by name)
3. NEW inputs or outputs not already captured

Return a JSON object with this structure:
{{
  "new_steps": [same schema as steps array],
  "new_inputs": [same schema as inputs array],
  "new_outputs": [same schema as outputs array],
  "enrichments": [
    {{
      "step_name": "name of existing step to enrich",
      "add_parameters": {{"key": "value"}},
      "add_equipment": ["new equipment"],
      "add_contractors": [{{"name": "...", "role": "...", "contract_value": 0, "significance_pct": 0}}],
      "append_description": "additional detail to append"
    }}
  ]
}}

If there is nothing new to add, return: {{"new_steps":[],"new_inputs":[],"new_outputs":[],"enrichments":[]}}

Return ONLY valid JSON.

"""


def _strip_think_traces(text: str) -> str:
    """Remove <think>...</think> reasoning traces from GLM-5.3 responses."""
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


def _merge_schematic(base: dict, delta: dict) -> tuple[dict, dict]:
    """Merge a delta into the base schematic. Returns (merged, diff_counts).

    The base schematic is NEVER reduced — only additions and enrichments.
    """
    merged = json.loads(json.dumps(base))  # deep copy

    counts = {"new_steps": 0, "new_inputs": 0, "new_outputs": 0,
              "new_contractors": 0, "new_params": 0, "new_equipment": 0}

    # Build lookup of existing steps by name (case-insensitive)
    step_by_name: dict[str, dict] = {}
    for s in merged.get("steps", []):
        step_by_name[s.get("name", "").lower()] = s

    existing_input_names = {i.get("name", "").lower() for i in merged.get("inputs", [])}
    existing_output_names = {o.get("name", "").lower() for o in merged.get("outputs", [])}

    # 1. Add new steps
    for new_step in delta.get("new_steps", []):
        if isinstance(new_step, str):
            new_step = {"name": new_step, "description": ""}
        if not isinstance(new_step, dict):
            continue
        name = new_step.get("name", "").lower()
        if name and name not in step_by_name:
            # Assign a new id if missing
            if not new_step.get("id"):
                idx = len(merged.get("steps", [])) + 1
                new_step["id"] = f"step{idx}"
            merged.setdefault("steps", []).append(new_step)
            step_by_name[name] = new_step
            counts["new_steps"] += 1

    # 2. Add new inputs (handle both dict and string formats from LLM)
    for new_input in delta.get("new_inputs", []):
        if isinstance(new_input, str):
            new_input = {"name": new_input, "type": "raw_material"}
        if not isinstance(new_input, dict):
            continue
        name = new_input.get("name", "").lower()
        if name and name not in existing_input_names:
            if not new_input.get("id"):
                idx = len(merged.get("inputs", [])) + 1
                new_input["id"] = f"in{idx}"
            merged.setdefault("inputs", []).append(new_input)
            existing_input_names.add(name)
            counts["new_inputs"] += 1

    # 3. Add new outputs (handle both dict and string formats from LLM)
    for new_output in delta.get("new_outputs", []):
        if isinstance(new_output, str):
            new_output = {"name": new_output, "type": "intermediate"}
        if not isinstance(new_output, dict):
            continue
        name = new_output.get("name", "").lower()
        if name and name not in existing_output_names:
            if not new_output.get("id"):
                idx = len(merged.get("outputs", [])) + 1
                new_output["id"] = f"out{idx}"
            merged.setdefault("outputs", []).append(new_output)
            existing_output_names.add(name)
            counts["new_outputs"] += 1

    # 4. Apply enrichments to existing steps
    for enrichment in delta.get("enrichments", []):
        if not isinstance(enrichment, dict):
            continue
        step_name = enrichment.get("step_name", "").lower()
        target = step_by_name.get(step_name)
        if not target:
            # Try fuzzy match — find step whose name contains the enrichment name
            for sname, step in step_by_name.items():
                if step_name in sname or sname in step_name:
                    target = step
                    break
        if not target:
            continue

        # Add parameters
        add_params = enrichment.get("add_parameters", {})
        if add_params and isinstance(add_params, dict):
            existing_params = target.setdefault("parameters", {})
            for k, v in add_params.items():
                if k not in existing_params:
                    existing_params[k] = str(v)
                    counts["new_params"] += 1

        # Add equipment
        add_equip = enrichment.get("add_equipment", [])
        if add_equip:
            existing_equip = target.setdefault("equipment", [])
            existing_equip_lower = {e.lower() for e in existing_equip if isinstance(e, str)}
            for e in add_equip:
                if isinstance(e, dict):
                    e = e.get("name", "") or str(e)
                if not isinstance(e, str) or not e:
                    continue
                if e.lower() not in existing_equip_lower:
                    existing_equip.append(e)
                    existing_equip_lower.add(e.lower())
                    counts["new_equipment"] += 1

        # Add contractors
        add_contractors = enrichment.get("add_contractors", [])
        if add_contractors:
            existing_cd = target.setdefault("contractor_details", [])
            existing_names = {c.get("name", "").lower() for c in existing_cd if isinstance(c, dict)}
            # Also check flat doe_contractors list
            existing_dc = target.setdefault("doe_contractors", [])
            existing_names.update(c.lower() for c in existing_dc if isinstance(c, str))
            for c in add_contractors:
                if isinstance(c, str):
                    c = {"name": c, "role": "unknown"}
                if not isinstance(c, dict):
                    continue
                cname = c.get("name", "").lower()
                if cname and cname not in existing_names:
                    existing_cd.append(c)
                    if c.get("name") and c["name"] not in existing_dc:
                        existing_dc.append(c["name"])
                    existing_names.add(cname)
                    counts["new_contractors"] += 1

        # Append description
        append_desc = enrichment.get("append_description", "")
        if append_desc and append_desc.strip():
            existing_desc = target.get("description", "")
            # Don't duplicate — check if this content is already there
            if append_desc.strip().lower() not in existing_desc.lower():
                target["description"] = (existing_desc + " " + append_desc.strip()).strip()

    counts["total_new"] = sum(counts.values())
    return merged, counts


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
        llm: GLMClient,
        brave: BraveSearchClient | None = None,
    ):
        self.retriever = retriever
        self.llm = llm
        self.brave = brave

    @staticmethod
    def _evt(event: str, data: dict) -> dict:
        return {"event": event, "data": data}

    async def saturate(
        self,
        query: str,
        max_passes: int | None = None,
        auto_explore: bool = True,
        max_depth: int = 3,
    ) -> AsyncGenerator[dict, None]:
        """Run iterative saturation with optional auto-explore.

        When auto_explore is True, after saturating the initial query,
        automatically drills into each discovered step, saturating each
        one and merging results into the master schematic. Repeats
        recursively until no new steps are discovered at any level.
        """
        master_schematic: dict | None = None
        explored_steps: set[str] = set()
        global_contracts: set[str] = set()
        global_entities = 0
        global_passes = 0
        depth = 0

        # --- Phase 1: Saturate the initial query ---
        async for event in self._saturate_query(
            query, max_passes=max_passes,
            accumulated_schematic=None, seen_contract_keys=global_contracts,
            label="Initial",
        ):
            # Capture the final schematic from process_schematic events
            if event["event"] == "process_schematic":
                master_schematic = event["data"]
            elif event["event"] == "done":
                global_passes += event["data"].get("passes", 0)
                global_entities += event["data"].get("total_new_entities", 0)
                continue  # don't emit done yet — more work to do
            yield event

        if not auto_explore or not master_schematic:
            yield self._evt("done", {
                "passes": global_passes,
                "total_new_entities": global_entities,
                "unique_contracts": len(global_contracts),
            })
            return

        # --- Phase 2+: Recursive auto-explore ---
        while True:
            depth += 1
            if depth > max_depth:
                yield self._evt("status", {
                    "stage": "explore_done",
                    "message": f"Auto-explore reached max depth ({max_depth}). Stopping.",
                })
                break
            # Find unexplored steps
            all_steps = master_schematic.get("steps", [])
            unexplored = [
                s for s in all_steps
                if s.get("name", "").lower() not in explored_steps
            ]

            if not unexplored:
                yield self._evt("status", {
                    "stage": "explore_done",
                    "message": f"Auto-explore complete — all {len(all_steps)} steps explored across {depth - 1} levels",
                })
                break

            yield self._evt("status", {
                "stage": "explore_level",
                "message": f"Auto-explore level {depth} — {len(unexplored)} steps to drill into",
            })

            level_new_steps = 0

            for i, step in enumerate(unexplored, 1):
                step_name = step.get("name", "Unknown")
                explored_steps.add(step_name.lower())

                yield self._evt("status", {
                    "stage": "explore_step",
                    "message": f"Level {depth} — Exploring step {i}/{len(unexplored)}: \"{step_name}\"",
                })

                drill_query = (
                    f"Provide detailed technical specifications for the \"{step_name}\" process step. "
                    f"Include specific equipment models, operating parameters (temperatures, pressures, "
                    f"flow rates, tolerances), materials and their grades/purities, safety requirements, "
                    f"quality control procedures, and which DOE contractors perform this work."
                )

                yield self._evt("token", {
                    "content": f"\n\n---\n**Auto-Explore: Drilling into \"{step_name}\"...**\n\n",
                })

                steps_before = {s.get("name", "").lower() for s in master_schematic.get("steps", [])}

                async for event in self._saturate_query(
                    drill_query, max_passes=3,
                    accumulated_schematic=master_schematic,
                    seen_contract_keys=global_contracts,
                    label=f"L{depth}/{step_name}",
                ):
                    if event["event"] == "process_schematic":
                        master_schematic = event["data"]
                    elif event["event"] == "done":
                        global_passes += event["data"].get("passes", 0)
                        global_entities += event["data"].get("total_new_entities", 0)
                        continue
                    yield event

                steps_after = {s.get("name", "").lower() for s in master_schematic.get("steps", [])}
                new_step_names = steps_after - steps_before
                level_new_steps += len(new_step_names)

                if new_step_names:
                    yield self._evt("status", {
                        "stage": "explore_step",
                        "message": f"Level {depth} — \"{step_name}\" revealed {len(new_step_names)} new sub-steps: {', '.join(new_step_names)}",
                    })

            yield self._evt("status", {
                "stage": "explore_level",
                "message": f"Level {depth} complete — {level_new_steps} new sub-steps discovered across {len(unexplored)} steps explored",
            })

            if level_new_steps == 0:
                yield self._evt("status", {
                    "stage": "explore_done",
                    "message": f"No new sub-steps at level {depth}. Exploration complete.",
                })
                break

        # ---- FINAL DONE ----
        total_steps = len(master_schematic.get("steps", [])) if master_schematic else 0
        total_contractors = sum(
            len(s.get("contractor_details", []))
            for s in (master_schematic or {}).get("steps", [])
        )
        yield self._evt("status", {
            "stage": "explore_done",
            "message": (
                f"Auto-explore complete — {depth} levels, {total_steps} steps, "
                f"{total_contractors} contractors, {global_entities} entities "
                f"from {len(global_contracts)} unique contracts across {global_passes} passes"
            ),
        })

        yield self._evt("done", {
            "passes": global_passes,
            "total_new_entities": global_entities,
            "unique_contracts": len(global_contracts),
            "depth_levels": depth,
            "total_steps": total_steps,
        })

    async def _saturate_query(
        self,
        query: str,
        max_passes: int | None = None,
        accumulated_schematic: dict | None = None,
        seen_contract_keys: set[str] | None = None,
        label: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Internal: saturate a single query. Yields SSE events.

        Can receive an existing schematic to merge into (for drill-downs).
        """
        if seen_contract_keys is None:
            seen_contract_keys = set()
        prefix = f"[{label}] " if label else ""
        consecutive_zero = 0
        total_zero_passes = 0
        pass_num = 0
        cumulative_new = 0
        all_responses: list[str] = []

        yield self._evt("status", {
            "stage": "saturate_start",
            "message": f"{prefix}Saturation mode — searching until knowledge is exhausted",
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
                "message": f"{prefix}Pass {pass_num} — Searching contracts (vector + keyword + graph)...",
            })

            results = await asyncio.to_thread(self.retriever.search, query)
            total_contracts = len(results.contracts)
            new_keys = {c.key for c in results.contracts} - seen_contract_keys
            seen_contract_keys.update(c.key for c in results.contracts)

            yield self._evt("status", {
                "stage": "saturate_search",
                "message": f"{prefix}Pass {pass_num} — Retrieved {total_contracts} contracts ({len(new_keys)} not seen in prior passes)",
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
            if not (self.llm and self.llm.is_available()):
                yield self._evt("token", {
                    "content": "GLM-5.3 is not configured. Set OPENROUTER_API_KEY.",
                })
                return

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

            try:
                async for token in self.llm.chat_stream(messages):
                    response_parts.append(token)
                    yield self._evt("token", {"content": token})
            except Exception as e:
                yield self._evt("token", {
                    "content": f"\n\n[GLM-5.3 request failed: {e}]\n\n",
                })
                return

            response_text = "".join(response_parts)
            all_responses.append(response_text)

            word_count = len(response_text.split())
            yield self._evt("status", {
                "stage": "saturate_generate",
                "message": f"Pass {pass_num} — Response complete: {word_count} words",
            })

            # Check for explicit "no new information" signal — skip extraction
            # and count toward convergence. We track total zero-gain passes
            # (not just consecutive) to handle LLM oscillation.
            if "NO NEW INFORMATION" in response_text.upper() and pass_num > 1:
                total_zero_passes += 1
                consecutive_zero += 1
                yield self._evt("status", {
                    "stage": "saturate_generate",
                    "message": f"Pass {pass_num} — Model reports no new information (zero-gain: {total_zero_passes} total, {consecutive_zero} consecutive)",
                })
                # Stop if 2 consecutive OR 3 total zero-gain passes
                if consecutive_zero >= 2 or total_zero_passes >= 3:
                    yield self._evt("status", {
                        "stage": "saturate_converged",
                        "message": f"Pass {pass_num} — Knowledge saturated ({total_zero_passes} zero-gain passes total).",
                    })
                    break
                continue

            # ---- EXTRACT/UPDATE SCHEMATIC ----
            new_info = (
                "DOE CONTRACT DATA:\n" + "\n".join(contract_lines) + "\n\n"
                + (f"WEB RESEARCH:\n{web_context}\n\n" if web_context else "")
                + "NEW INFORMATION FROM LATEST ANSWER:\n" + response_text
            )

            if accumulated_schematic:
                # DELTA approach: ask LLM for additions ONLY, then merge in code
                yield self._evt("status", {
                    "stage": "saturate_schematic",
                    "message": f"Pass {pass_num} — Extracting new additions (delta mode)...",
                })

                step_names = ", ".join(
                    s.get("name", "?") for s in accumulated_schematic.get("steps", [])
                )
                prompt = (
                    _SATURATE_DELTA_PROMPT
                    .replace("{existing_step_names}", step_names)
                ) + new_info
            else:
                # First pass: create full schematic
                yield self._evt("status", {
                    "stage": "saturate_schematic",
                    "message": f"Pass {pass_num} — Extracting initial schematic...",
                })
                prompt = _SATURATE_CREATE_PROMPT + new_info

            raw_schematic = None
            try:
                raw_schematic = await self.llm.chat(
                    [{"role": "user", "content": prompt}]
                )
            except Exception as e:
                yield self._evt("status", {
                    "stage": "saturate_schematic",
                    "message": f"Pass {pass_num} — schematic extraction failed: {e}",
                })
                continue

            parsed = _extract_json(raw_schematic)

            if parsed is None:
                yield self._evt("status", {
                    "stage": "saturate_schematic",
                    "message": f"Pass {pass_num} — Could not parse JSON, retrying next pass",
                })
                continue

            # ---- MERGE OR SET ----
            if accumulated_schematic:
                # Merge delta into existing — schematic can only grow, never shrink
                yield self._evt("status", {
                    "stage": "saturate_schematic",
                    "message": f"Pass {pass_num} — Merging additions into existing schematic...",
                })
                new_schematic, diff = _merge_schematic(accumulated_schematic, parsed)
            else:
                # First pass — the parsed result IS the schematic
                new_schematic = parsed
                diff = _structural_diff(None, new_schematic)

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

            # Convergence check — based on structural diff, not LLM opinion
            if diff["total_new"] == 0:
                consecutive_zero += 1
                total_zero_passes += 1
                if consecutive_zero >= 2 or total_zero_passes >= 3:
                    yield self._evt("status", {
                        "stage": "saturate_converged",
                        "message": f"Pass {pass_num} — Knowledge saturated ({total_zero_passes} zero-gain passes total).",
                    })
                    break
                else:
                    yield self._evt("status", {
                        "stage": "saturate_converging",
                        "message": f"Pass {pass_num} — No new entities (zero-gain: {total_zero_passes} total, {consecutive_zero} consecutive)",
                    })
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
                f"{prefix}Knowledge saturated after {pass_num} passes. "
                f"Total: {cumulative_new} entities from {len(seen_contract_keys)} unique contracts"
            ),
        })

        yield self._evt("done", {
            "passes": pass_num,
            "total_new_entities": cumulative_new,
            "unique_contracts": len(seen_contract_keys),
        })
