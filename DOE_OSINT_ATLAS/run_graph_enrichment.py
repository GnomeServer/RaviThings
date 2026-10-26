#!/usr/bin/env python3
"""
Run LLM entity extraction to enrich the knowledge graph.

Reads contract descriptions from SQLite, groups by recipient,
sends to GLM-5.3/Ollama for entity/relationship extraction,
and enriches the igraph with new typed nodes and edges.

Usage:
    python3 run_graph_enrichment.py [--limit N] [--rebuild-graph]
"""

import argparse
import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from backend.glm_client import GLMClient
from backend.ollama_client import OllamaClient
from backend.graph_enrichment import (
    extract_entities_from_text,
    enrich_graph_with_entities,
    deduplicate_nodes,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'doe_contracts.db')
GRAPH_PATH = os.path.join(BASE_DIR, 'graph.pkl')


def get_recipient_descriptions(limit=0):
    """Get AI research briefs from contractors.json as extraction source.

    AI research briefs are much richer than raw contract descriptions —
    they describe what contractors actually do, their technologies,
    facilities, and DOE relationships.
    """
    import json
    json_path = os.path.join(BASE_DIR, 'frontend', 'static', 'contractors.json')
    with open(json_path) as f:
        data = json.load(f)

    descriptions = []
    for c in data['contractors']:
        ar = c.get('osint', {}).get('ai_research', {})
        brief = ar.get('brief', '')
        if brief and len(brief) > 50:
            descriptions.append((c['name'], brief))

    if limit > 0:
        descriptions = descriptions[:limit]

    return descriptions


async def main():
    parser = argparse.ArgumentParser(description='Enrich knowledge graph with LLM entity extraction')
    parser.add_argument('--limit', type=int, default=0, help='Limit recipients to process (0=all)')
    parser.add_argument('--rebuild-graph', action='store_true', help='Rebuild base graph first')
    args = parser.parse_args()

    # Check graph exists
    if not os.path.exists(GRAPH_PATH):
        print(f'Graph not found at {GRAPH_PATH}. Run: python -m backend.build_graph')
        if not args.rebuild_graph:
            sys.exit(1)

    if args.rebuild_graph:
        from backend.build_graph import build_graph
        print('Rebuilding base graph...')
        build_graph(DB_PATH, GRAPH_PATH)

    # Load graph
    import igraph as ig
    graph = ig.Graph.Read_Pickle(GRAPH_PATH)
    print(f'Loaded graph: {graph.vcount()} nodes, {graph.ecount()} edges')

    # Initialize LLM client
    llm = GLMClient()
    ollama = OllamaClient()

    if not llm.is_available():
        print('ERROR: No LLM available (set OPENROUTER_API_KEY)')
        sys.exit(1)
    print('Using GLM-5.3 for entity extraction')

    # Get descriptions
    descriptions = get_recipient_descriptions(limit=args.limit)
    print(f'Processing {len(descriptions)} recipients with contract descriptions')

    # Extract and enrich
    total_nodes = 0
    total_edges = 0
    errors = 0
    start = time.time()

    for idx, (recipient, description) in enumerate(descriptions):
        print(f'  [{idx+1}/{len(descriptions)}] {recipient[:45]:45s}', end=' ', flush=True)

        try:
            result = await extract_entities_from_text(description, llm)
            entities = result.get('entities', [])
            relationships = result.get('relationships', [])

            if entities:
                stats = enrich_graph_with_entities(graph, result, recipient)
                total_nodes += stats['nodes_added']
                total_edges += stats['edges_added']
                print(f'+{stats["nodes_added"]} nodes, +{stats["edges_added"]} edges')
            else:
                print('no entities found')
        except Exception as e:
            errors += 1
            print(f'ERROR: {str(e)[:60]}')

        # Save every 100
        if (idx + 1) % 100 == 0:
            graph.write_pickle(GRAPH_PATH)
            print(f'  Saved progress ({idx+1}/{len(descriptions)})')

        # Rate limit
        await asyncio.sleep(0.5)

    # Deduplication pass
    print(f'\nRunning entity deduplication...')
    if ollama:
        try:
            dedup_result = deduplicate_nodes(graph, ollama.embed_sync, threshold=0.85)
            print(f'  Merged {dedup_result["merged_count"]} duplicate nodes')
        except Exception as e:
            print(f'  Dedup skipped: {e}')

    # Save final graph
    graph.write_pickle(GRAPH_PATH)
    elapsed = time.time() - start

    print(f'\n{"=" * 60}')
    print(f'ENTITY EXTRACTION COMPLETE')
    print(f'{"=" * 60}')
    print(f'  Recipients processed: {len(descriptions)}')
    print(f'  Nodes added:          {total_nodes}')
    print(f'  Edges added:          {total_edges}')
    print(f'  Errors:               {errors}')
    print(f'  Final graph:          {graph.vcount()} nodes, {graph.ecount()} edges')
    print(f'  Time:                 {elapsed/60:.1f} minutes')


if __name__ == '__main__':
    asyncio.run(main())
