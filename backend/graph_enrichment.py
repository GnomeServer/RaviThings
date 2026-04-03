"""
Graph enrichment module for DOE Red Team knowledge graph.

Extracts technology entities and relationships from contract descriptions
using an LLM, adds them to an igraph knowledge graph, and deduplicates
near-duplicate nodes via embedding cosine similarity.
"""

import asyncio
import json
import logging
from typing import Callable, Optional

import igraph as ig
import numpy as np

from osint.ai_research import extract_research_json


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# System prompt for entity extraction (< 500 tokens)
# ─────────────────────────────────────────────────────────────

_ENTITY_EXTRACTION_PROMPT = """You are an entity extraction system for DOE (Department of Energy) contract descriptions.

Extract named entities and relationships from the provided text.

Entity types:
- technology: specific technologies, systems, or technical approaches
- material: physical materials, chemicals, fuels, or substances
- process: manufacturing, engineering, or scientific processes
- facility: named laboratories, plants, or physical sites
- organization: companies, agencies, or institutions

Rules:
- Only extract clearly stated entities, not inferences
- Use canonical names (e.g., "HALEU" not "high-assay low-enriched uranium" unless only the long form appears)
- Extract relationships only between entities you identified

Respond with ONLY a JSON object:
{"entities": [{"name": "...", "type": "..."}], "relationships": [{"source": "...", "target": "...", "description": "..."}]}"""


# ─────────────────────────────────────────────────────────────
# 1. Extract entities from text via LLM
# ─────────────────────────────────────────────────────────────

async def extract_entities_from_text(text: str, llm_client) -> dict:
    """Extract entities and relationships from contract text via LLM.

    Args:
        text: Contract description text.
        llm_client: HermesClient or OllamaClient with async chat() method.

    Returns:
        dict with keys:
        - entities: list of {"name": str, "type": str}
          types: "technology", "material", "process", "facility", "organization"
        - relationships: list of {"source": str, "target": str, "description": str}
    """
    empty_result = {"entities": [], "relationships": []}

    if not text or not text.strip():
        return empty_result

    messages = [
        {"role": "system", "content": _ENTITY_EXTRACTION_PROMPT},
        {"role": "user", "content": text.strip()},
    ]

    try:
        raw_response = await llm_client.chat(messages)
    except Exception as e:
        logger.warning("LLM call failed during entity extraction: %s", e)
        return empty_result

    parsed = extract_research_json(raw_response)
    if parsed is None:
        return empty_result

    # Validate structure
    entities = parsed.get("entities", [])
    relationships = parsed.get("relationships", [])

    # Filter to valid entities
    valid_types = {"technology", "material", "process", "facility", "organization"}
    validated_entities = [
        e for e in entities
        if isinstance(e, dict)
        and e.get("name")
        and e.get("type") in valid_types
    ]

    validated_relationships = [
        r for r in relationships
        if isinstance(r, dict)
        and r.get("source")
        and r.get("target")
        and r.get("description")
    ]

    return {"entities": validated_entities, "relationships": validated_relationships}


# ─────────────────────────────────────────────────────────────
# 2. Enrich graph with extracted entities
# ─────────────────────────────────────────────────────────────

def enrich_graph_with_entities(graph: ig.Graph, entities_data: dict, source_recipient: str) -> dict:
    """Add LLM-extracted entities to the knowledge graph.

    Args:
        graph: igraph.Graph object (modified in place).
        entities_data: Output from extract_entities_from_text().
        source_recipient: The recipient name this text came from (for edges).

    Returns:
        dict with counts: {"nodes_added": int, "edges_added": int, "nodes_existing": int}
    """
    nodes_added = 0
    edges_added = 0
    nodes_existing = 0

    # Build a set of existing node names for fast lookup
    existing_names = set(v["name"] for v in graph.vs) if graph.vcount() > 0 else set()

    # Map entity name -> node_name for relationship edge creation
    entity_node_map = {}

    for entity in entities_data.get("entities", []):
        ename = entity["name"]
        etype = entity["type"]
        node_name = f"{etype}:{ename}"

        entity_node_map[ename] = node_name

        if node_name in existing_names:
            nodes_existing += 1
            continue

        # Add new node
        idx = graph.vcount()
        graph.add_vertices(1)
        graph.vs[idx]["name"] = node_name
        graph.vs[idx]["label"] = ename
        graph.vs[idx]["type"] = etype
        existing_names.add(node_name)
        nodes_added += 1

    # Add edges from recipient to each entity
    recipient_node_name = f"recipient:{source_recipient}"
    if recipient_node_name in existing_names:
        recipient_idx = graph.vs.find(name=recipient_node_name).index
        for entity in entities_data.get("entities", []):
            ename = entity["name"]
            etype = entity["type"]
            node_name = f"{etype}:{ename}"
            try:
                entity_idx = graph.vs.find(name=node_name).index
            except ValueError:
                continue
            graph.add_edges([(recipient_idx, entity_idx)])
            eid = graph.ecount() - 1
            graph.es[eid]["edge_type"] = f"recipient_{etype}"
            graph.es[eid]["weight"] = 1.0
            graph.es[eid]["contract_count"] = 1
            edges_added += 1

    # Add relationship edges between entities
    for rel in entities_data.get("relationships", []):
        source_name = entity_node_map.get(rel["source"])
        target_name = entity_node_map.get(rel["target"])
        if source_name and target_name:
            try:
                source_idx = graph.vs.find(name=source_name).index
                target_idx = graph.vs.find(name=target_name).index
            except ValueError:
                continue
            graph.add_edges([(source_idx, target_idx)])
            eid = graph.ecount() - 1
            graph.es[eid]["edge_type"] = "entity_relationship"
            graph.es[eid]["description"] = rel["description"]
            graph.es[eid]["weight"] = 1.0
            edges_added += 1

    return {"nodes_added": nodes_added, "edges_added": edges_added, "nodes_existing": nodes_existing}


# ─────────────────────────────────────────────────────────────
# 3. Deduplicate near-duplicate nodes
# ─────────────────────────────────────────────────────────────

def deduplicate_nodes(graph: ig.Graph, embed_fn: Callable, threshold: float = 0.85) -> dict:
    """Find and merge near-duplicate nodes in the graph.

    Groups nodes by type, computes pairwise cosine similarity on labels,
    merges pairs above threshold (keeps the node with more edges).

    Args:
        graph: igraph.Graph (modified in place).
        embed_fn: Callable that takes list[str] and returns list[list[float]].
        threshold: Cosine similarity threshold for merging (0.0-1.0).

    Returns:
        dict: {"merged_count": int, "merge_pairs": list of (kept, removed)}
    """
    merge_pairs = []

    # Group node indices by type
    type_groups: dict[str, list[int]] = {}
    for v in graph.vs:
        ntype = v["type"]
        if ntype not in type_groups:
            type_groups[ntype] = []
        type_groups[ntype].append(v.index)

    # Track nodes to delete (collect all, delete at end)
    nodes_to_delete = set()

    for ntype, indices in type_groups.items():
        if len(indices) < 2:
            continue

        labels = [graph.vs[i]["label"] for i in indices]
        embeddings = embed_fn(labels)
        emb_matrix = np.array(embeddings, dtype=np.float64)

        # Compute cosine similarity matrix
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1e-10, norms)
        normalized = emb_matrix / norms
        sim_matrix = normalized @ normalized.T

        # Find pairs above threshold (upper triangle only)
        already_merged = set()
        for i in range(len(indices)):
            if indices[i] in already_merged or indices[i] in nodes_to_delete:
                continue
            for j in range(i + 1, len(indices)):
                if indices[j] in already_merged or indices[j] in nodes_to_delete:
                    continue
                if sim_matrix[i, j] >= threshold:
                    idx_a = indices[i]
                    idx_b = indices[j]

                    # Keep the node with more edges
                    degree_a = graph.degree(idx_a)
                    degree_b = graph.degree(idx_b)

                    if degree_a >= degree_b:
                        kept_idx, removed_idx = idx_a, idx_b
                    else:
                        kept_idx, removed_idx = idx_b, idx_a

                    # Transfer edges from removed node to kept node
                    _transfer_edges(graph, removed_idx, kept_idx)

                    nodes_to_delete.add(removed_idx)
                    already_merged.add(removed_idx)

                    kept_name = graph.vs[kept_idx]["name"]
                    removed_name = graph.vs[removed_idx]["name"]
                    merge_pairs.append((kept_name, removed_name))

    # Delete removed nodes (in reverse order to preserve indices)
    if nodes_to_delete:
        graph.delete_vertices(sorted(nodes_to_delete, reverse=True))

    return {"merged_count": len(merge_pairs), "merge_pairs": merge_pairs}


def _transfer_edges(graph: ig.Graph, from_idx: int, to_idx: int):
    """Transfer all edges from one node to another, avoiding duplicates."""
    # Get existing neighbors of the kept node
    kept_neighbors = set(graph.neighbors(to_idx))

    for edge_idx in graph.incident(from_idx):
        edge = graph.es[edge_idx]
        # Determine the other endpoint
        if edge.source == from_idx:
            other_idx = edge.target
        else:
            other_idx = edge.source

        # Skip self-loops and edges to the kept node
        if other_idx == to_idx or other_idx == from_idx:
            continue

        # Skip if kept node already has this connection
        if other_idx in kept_neighbors:
            continue

        # Add new edge from kept node to the other endpoint
        graph.add_edges([(to_idx, other_idx)])
        new_eid = graph.ecount() - 1
        # Copy edge attributes
        for attr in graph.es.attributes():
            graph.es[new_eid][attr] = edge[attr]

        kept_neighbors.add(other_idx)


# ─────────────────────────────────────────────────────────────
# 4. Batch extraction
# ─────────────────────────────────────────────────────────────

async def extract_batch(
    descriptions: list[tuple[str, str]],
    llm_client,
    batch_size: int = 5,
) -> list[dict]:
    """Extract entities from multiple descriptions.

    Args:
        descriptions: List of (recipient_name, description_text) tuples.
        llm_client: LLM client with async chat() method.
        batch_size: Number of concurrent extractions per batch.

    Returns:
        List of dicts, each with 'recipient', 'entities', 'relationships'.
    """
    results = []

    for i in range(0, len(descriptions), batch_size):
        batch = descriptions[i : i + batch_size]
        tasks = []
        for recipient_name, text in batch:
            tasks.append(_extract_single(recipient_name, text, llm_client))
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

    return results


async def _extract_single(recipient_name: str, text: str, llm_client) -> dict:
    """Extract entities from a single description, with error handling."""
    try:
        extracted = await extract_entities_from_text(text, llm_client)
        return {
            "recipient": recipient_name,
            "entities": extracted["entities"],
            "relationships": extracted["relationships"],
        }
    except Exception as e:
        logger.warning("Failed to extract entities for %s: %s", recipient_name, e)
        return {
            "recipient": recipient_name,
            "entities": [],
            "relationships": [],
        }
