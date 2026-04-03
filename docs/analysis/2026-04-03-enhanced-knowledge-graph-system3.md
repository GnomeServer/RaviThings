# System 3 Analysis: Enhanced Knowledge Graph (LightRAG-Inspired)
Date: 2026-04-03

## Context
Build 4 improvements inspired by LightRAG analysis: (1) LLM entity extraction from contract text, (2) entity deduplication, (3) reranker on retrieval results, (4) relationship-level retrieval lane.

## Problem Frame
The current knowledge graph has only 3 deterministic entity types (recipient, PSC, NAICS) from SQL columns. It cannot discover implicit relationships in free text (supply chains, technology dependencies, process flows). LightRAG's key insight — LLM-driven entity extraction — addresses this without adopting the full framework.

## Architecture Decision
Separate enrichment step, not modification of build_graph.py:
1. `build_graph()` remains fast, deterministic, SQL-based (unchanged)
2. New `backend/graph_enrichment.py` loads the graph, runs LLM extraction, adds nodes/edges
3. New `backend/reranker.py` for post-retrieval reranking
4. Extended `hybrid_retriever.py` with 4th retrieval lane + reranker

## Key Constraints
- LLM calls must be mocked in tests
- Must not break existing 128 tests
- Graph node naming: `{type}:{label}` convention
- Embeddings: OllamaClient.embed_sync() for sync contexts
- RRF_K = 60 for fusion scoring

## Blind Spots
- LLM entity extraction quality varies by model
- Dedup threshold (0.85 cosine similarity) may need tuning
- Relationship descriptions depend on extraction quality
