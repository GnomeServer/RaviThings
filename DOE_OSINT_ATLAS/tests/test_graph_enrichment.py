"""
Tests for the graph enrichment module.

Tests extract_entities_from_text, enrich_graph_with_entities,
deduplicate_nodes, and extract_batch.

Run: python -m pytest tests/test_graph_enrichment.py -v
"""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import igraph as ig


# ================================================================
# HELPER: build a small graph with recipient nodes
# ================================================================

def _make_graph_with_recipients(*names):
    """Create a minimal igraph with recipient nodes."""
    g = ig.Graph()
    for name in names:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"recipient:{name}"
        g.vs[idx]["label"] = name
        g.vs[idx]["type"] = "recipient"
    return g


# ================================================================
# EXTRACT_ENTITIES_FROM_TEXT TESTS
# ================================================================

class TestExtractEntities(unittest.TestCase):

    def test_extracts_entities_from_text(self):
        """Mock LLM returns JSON with entities + relationships. Verify parsed correctly."""
        from backend.graph_enrichment import extract_entities_from_text

        llm_response = json.dumps({
            "entities": [
                {"name": "HALEU", "type": "technology"},
                {"name": "uranium oxide", "type": "material"},
            ],
            "relationships": [
                {"source": "HALEU", "target": "uranium oxide", "description": "HALEU uses enriched uranium oxide fuel"},
            ],
        })

        client = MagicMock()
        client.chat = AsyncMock(return_value=llm_response)

        result = asyncio.run(extract_entities_from_text(
            "Contract for HALEU fuel fabrication using enriched uranium oxide.",
            client,
        ))

        self.assertIn("entities", result)
        self.assertIn("relationships", result)
        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(result["entities"][0]["name"], "HALEU")
        self.assertEqual(result["entities"][0]["type"], "technology")
        self.assertEqual(len(result["relationships"]), 1)
        self.assertEqual(result["relationships"][0]["source"], "HALEU")

    def test_handles_empty_text(self):
        """Empty string returns empty entities/relationships."""
        from backend.graph_enrichment import extract_entities_from_text

        client = MagicMock()
        client.chat = AsyncMock(return_value="")

        result = asyncio.run(extract_entities_from_text("", client))

        self.assertEqual(result["entities"], [])
        self.assertEqual(result["relationships"], [])
        # LLM should NOT be called for empty text
        client.chat.assert_not_called()

    def test_handles_malformed_llm_output(self):
        """LLM returns non-JSON. Verify graceful empty result."""
        from backend.graph_enrichment import extract_entities_from_text

        client = MagicMock()
        client.chat = AsyncMock(return_value="I cannot extract any entities from this text.")

        result = asyncio.run(extract_entities_from_text(
            "Some contract description.",
            client,
        ))

        self.assertEqual(result["entities"], [])
        self.assertEqual(result["relationships"], [])

    def test_extracts_multiple_entity_types(self):
        """Verify technology, material, facility types all parsed."""
        from backend.graph_enrichment import extract_entities_from_text

        llm_response = json.dumps({
            "entities": [
                {"name": "molten salt reactor", "type": "technology"},
                {"name": "FLiBe", "type": "material"},
                {"name": "Oak Ridge National Laboratory", "type": "facility"},
                {"name": "Kairos Power", "type": "organization"},
                {"name": "fluoride salt purification", "type": "process"},
            ],
            "relationships": [],
        })

        client = MagicMock()
        client.chat = AsyncMock(return_value=llm_response)

        result = asyncio.run(extract_entities_from_text(
            "Kairos Power molten salt reactor at ORNL using FLiBe.",
            client,
        ))

        types = {e["type"] for e in result["entities"]}
        self.assertIn("technology", types)
        self.assertIn("material", types)
        self.assertIn("facility", types)
        self.assertIn("organization", types)
        self.assertIn("process", types)
        self.assertEqual(len(result["entities"]), 5)


# ================================================================
# ENRICH_GRAPH_WITH_ENTITIES TESTS
# ================================================================

class TestEnrichGraph(unittest.TestCase):

    def test_adds_new_nodes_to_graph(self):
        """Create igraph with recipient nodes, add entities, verify new nodes exist with correct type attribute."""
        from backend.graph_enrichment import enrich_graph_with_entities

        g = _make_graph_with_recipients("Battelle Memorial Institute")
        entities_data = {
            "entities": [
                {"name": "HALEU", "type": "technology"},
                {"name": "uranium oxide", "type": "material"},
            ],
            "relationships": [],
        }

        stats = enrich_graph_with_entities(g, entities_data, "Battelle Memorial Institute")

        self.assertEqual(stats["nodes_added"], 2)
        # Verify nodes exist with correct attributes
        names = [v["name"] for v in g.vs]
        self.assertIn("technology:HALEU", names)
        self.assertIn("material:uranium oxide", names)
        # Verify type attributes
        haleu_node = g.vs.find(name="technology:HALEU")
        self.assertEqual(haleu_node["type"], "technology")

    def test_adds_edges_between_recipient_and_entities(self):
        """Verify edges created from recipient to technology/material nodes."""
        from backend.graph_enrichment import enrich_graph_with_entities

        g = _make_graph_with_recipients("ORNL")
        entities_data = {
            "entities": [
                {"name": "neutron scattering", "type": "technology"},
                {"name": "silicon carbide", "type": "material"},
            ],
            "relationships": [],
        }

        stats = enrich_graph_with_entities(g, entities_data, "ORNL")

        self.assertEqual(stats["edges_added"], 2)
        # Verify edge from recipient to technology
        recipient_idx = g.vs.find(name="recipient:ORNL").index
        tech_idx = g.vs.find(name="technology:neutron scattering").index
        edge = g.es.find(_source=recipient_idx, _target=tech_idx)
        self.assertEqual(edge["edge_type"], "recipient_technology")
        self.assertEqual(edge["weight"], 1.0)

    def test_skips_existing_nodes(self):
        """Add same entity twice, verify no duplicate. nodes_existing counter incremented."""
        from backend.graph_enrichment import enrich_graph_with_entities

        g = _make_graph_with_recipients("PNNL")
        entities_data = {
            "entities": [
                {"name": "hydrogen storage", "type": "technology"},
            ],
            "relationships": [],
        }

        # First enrichment
        stats1 = enrich_graph_with_entities(g, entities_data, "PNNL")
        self.assertEqual(stats1["nodes_added"], 1)
        self.assertEqual(stats1["nodes_existing"], 0)

        node_count_after_first = g.vcount()

        # Second enrichment with same entity
        stats2 = enrich_graph_with_entities(g, entities_data, "PNNL")
        self.assertEqual(stats2["nodes_added"], 0)
        self.assertEqual(stats2["nodes_existing"], 1)
        # Node count should not have increased
        self.assertEqual(g.vcount(), node_count_after_first)

    def test_adds_relationship_edges(self):
        """Verify relationship edges between entity nodes with description attribute."""
        from backend.graph_enrichment import enrich_graph_with_entities

        g = _make_graph_with_recipients("Kairos Power")
        entities_data = {
            "entities": [
                {"name": "molten salt reactor", "type": "technology"},
                {"name": "FLiBe", "type": "material"},
            ],
            "relationships": [
                {
                    "source": "molten salt reactor",
                    "target": "FLiBe",
                    "description": "uses FLiBe as primary coolant",
                },
            ],
        }

        stats = enrich_graph_with_entities(g, entities_data, "Kairos Power")

        # 2 recipient->entity edges + 1 relationship edge = 3
        self.assertEqual(stats["edges_added"], 3)

        # Find the relationship edge
        tech_idx = g.vs.find(name="technology:molten salt reactor").index
        mat_idx = g.vs.find(name="material:FLiBe").index
        rel_edge = g.es.find(_source=tech_idx, _target=mat_idx)
        self.assertEqual(rel_edge["edge_type"], "entity_relationship")
        self.assertEqual(rel_edge["description"], "uses FLiBe as primary coolant")


# ================================================================
# DEDUPLICATE_NODES TESTS
# ================================================================

class TestDeduplicateNodes(unittest.TestCase):

    def test_merges_near_duplicate_nodes(self):
        """Create graph with similar names. Mock embed_fn returns similar embeddings. Verify merged."""
        from backend.graph_enrichment import deduplicate_nodes
        import numpy as np

        g = ig.Graph()
        # Add two near-duplicate recipient nodes
        g.add_vertices(2)
        g.vs[0]["name"] = "recipient:Battelle Memorial Institute"
        g.vs[0]["label"] = "Battelle Memorial Institute"
        g.vs[0]["type"] = "recipient"
        g.vs[1]["name"] = "recipient:BATTELLE MEMORIAL INST"
        g.vs[1]["label"] = "BATTELLE MEMORIAL INST"
        g.vs[1]["type"] = "recipient"

        # Add a PSC node connected to node 1 (more edges -> kept)
        g.add_vertices(1)
        g.vs[2]["name"] = "psc:R&D"
        g.vs[2]["label"] = "R&D"
        g.vs[2]["type"] = "psc"
        g.add_edges([(0, 2), (1, 2)])
        g.es[0]["edge_type"] = "recipient_psc"
        g.es[0]["weight"] = 1.0
        g.es[1]["edge_type"] = "recipient_psc"
        g.es[1]["weight"] = 1.0

        # Mock embed_fn: return nearly identical embeddings for the two recipient labels
        def mock_embed(labels):
            embeddings = []
            for label in labels:
                if "battelle" in label.lower():
                    embeddings.append([0.9, 0.1, 0.05])
                else:
                    embeddings.append([0.1, 0.9, 0.05])
            # Make them very similar
            return [[0.9, 0.1, 0.05], [0.89, 0.11, 0.05]] if len(labels) == 2 and all("battelle" in l.lower() or "BATTELLE" in l for l in labels) else embeddings

        result = deduplicate_nodes(g, mock_embed, threshold=0.85)

        self.assertEqual(result["merged_count"], 1)
        self.assertEqual(len(result["merge_pairs"]), 1)
        # Verify one recipient node was removed
        recipient_nodes = [v for v in g.vs if v["type"] == "recipient"]
        self.assertEqual(len(recipient_nodes), 1)

    def test_preserves_distinct_nodes(self):
        """Create distinct nodes. Mock returns different embeddings. Verify NOT merged."""
        from backend.graph_enrichment import deduplicate_nodes

        g = ig.Graph()
        g.add_vertices(2)
        g.vs[0]["name"] = "technology:HALEU"
        g.vs[0]["label"] = "HALEU"
        g.vs[0]["type"] = "technology"
        g.vs[1]["name"] = "technology:molten salt reactor"
        g.vs[1]["label"] = "molten salt reactor"
        g.vs[1]["type"] = "technology"

        # Mock embed_fn: return very different embeddings
        def mock_embed(labels):
            return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        result = deduplicate_nodes(g, mock_embed, threshold=0.85)

        self.assertEqual(result["merged_count"], 0)
        self.assertEqual(len(result["merge_pairs"]), 0)
        # Both nodes should still exist
        self.assertEqual(g.vcount(), 2)

    def test_transfers_edges_on_merge(self):
        """Verify that when node B is merged into A, B's edges are transferred to A."""
        from backend.graph_enrichment import deduplicate_nodes

        g = ig.Graph()
        # Node A (index 0) - has 2 edges -> will be kept
        g.add_vertices(1)
        g.vs[0]["name"] = "recipient:Battelle Memorial Institute"
        g.vs[0]["label"] = "Battelle Memorial Institute"
        g.vs[0]["type"] = "recipient"

        # Node B (index 1) - has 1 edge -> will be removed
        g.add_vertices(1)
        g.vs[1]["name"] = "recipient:BATTELLE MEMORIAL INST"
        g.vs[1]["label"] = "BATTELLE MEMORIAL INST"
        g.vs[1]["type"] = "recipient"

        # PSC node connected to A
        g.add_vertices(1)
        g.vs[2]["name"] = "psc:R&D Physical Sciences"
        g.vs[2]["label"] = "R&D Physical Sciences"
        g.vs[2]["type"] = "psc"

        # NAICS node connected to B only
        g.add_vertices(1)
        g.vs[3]["name"] = "naics:Nuclear Energy"
        g.vs[3]["label"] = "Nuclear Energy"
        g.vs[3]["type"] = "naics"

        # Another PSC node connected to A
        g.add_vertices(1)
        g.vs[4]["name"] = "psc:R&D Energy"
        g.vs[4]["label"] = "R&D Energy"
        g.vs[4]["type"] = "psc"

        # Edges: A->psc1, A->psc2, B->naics
        g.add_edges([(0, 2), (0, 4), (1, 3)])
        g.es[0]["edge_type"] = "recipient_psc"
        g.es[0]["weight"] = 1.0
        g.es[1]["edge_type"] = "recipient_psc"
        g.es[1]["weight"] = 1.0
        g.es[2]["edge_type"] = "recipient_naics"
        g.es[2]["weight"] = 1.0

        # A has 2 edges, B has 1 edge -> A is kept, B's edges transfer to A

        # Mock embed_fn: nearly identical embeddings for Battelle variants,
        # distinct embeddings for everything else
        def mock_embed(labels):
            results = []
            for i, label in enumerate(labels):
                if "battelle" in label.lower():
                    # All Battelle variants get near-identical embeddings
                    results.append([0.9, 0.1, 0.05])
                else:
                    # Each non-Battelle label gets a unique, distant embedding
                    vec = [0.0, 0.0, 0.0]
                    vec[i % 3] = 1.0
                    results.append(vec)
            # When comparing exactly two Battelle labels, make them very similar but not identical
            if len(labels) == 2 and all("battelle" in l.lower() for l in labels):
                return [[0.9, 0.1, 0.05], [0.89, 0.11, 0.05]]
            return results

        initial_node_count = g.vcount()
        result = deduplicate_nodes(g, mock_embed, threshold=0.85)

        self.assertEqual(result["merged_count"], 1)
        # Node B was removed
        self.assertEqual(g.vcount(), initial_node_count - 1)

        # Find the kept Battelle node
        kept_node = g.vs.find(name="recipient:Battelle Memorial Institute")

        # The kept node should now have edges to psc1, psc2, AND naics (transferred from B)
        neighbor_names = [g.vs[n]["name"] for n in g.neighbors(kept_node.index)]
        self.assertIn("psc:R&D Physical Sciences", neighbor_names)
        self.assertIn("psc:R&D Energy", neighbor_names)
        self.assertIn("naics:Nuclear Energy", neighbor_names)


# ================================================================
# EXTRACT_BATCH TESTS
# ================================================================

class TestExtractBatch(unittest.TestCase):

    def test_processes_multiple_descriptions(self):
        """Mock LLM, pass 3 descriptions, verify all processed."""
        from backend.graph_enrichment import extract_batch

        responses = [
            json.dumps({
                "entities": [{"name": "HALEU", "type": "technology"}],
                "relationships": [],
            }),
            json.dumps({
                "entities": [{"name": "tritium", "type": "material"}],
                "relationships": [],
            }),
            json.dumps({
                "entities": [{"name": "Y-12", "type": "facility"}],
                "relationships": [],
            }),
        ]

        client = MagicMock()
        client.chat = AsyncMock(side_effect=responses)

        descriptions = [
            ("Battelle", "HALEU fuel fabrication contract."),
            ("ORNL", "Tritium production and storage."),
            ("CNS", "Y-12 facility operations."),
        ]

        results = asyncio.run(extract_batch(descriptions, client, batch_size=5))

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["recipient"], "Battelle")
        self.assertEqual(results[0]["entities"][0]["name"], "HALEU")
        self.assertEqual(results[1]["recipient"], "ORNL")
        self.assertEqual(results[1]["entities"][0]["name"], "tritium")
        self.assertEqual(results[2]["recipient"], "CNS")
        self.assertEqual(results[2]["entities"][0]["name"], "Y-12")

    def test_handles_llm_errors_gracefully(self):
        """Mock LLM raises exception for one description. Verify others still processed."""
        from backend.graph_enrichment import extract_batch

        good_response = json.dumps({
            "entities": [{"name": "HALEU", "type": "technology"}],
            "relationships": [],
        })

        client = MagicMock()
        client.chat = AsyncMock(side_effect=[
            good_response,
            Exception("LLM timeout"),
            good_response,
        ])

        descriptions = [
            ("Battelle", "HALEU fuel fabrication."),
            ("BadCorp", "This one will fail."),
            ("ORNL", "HALEU enrichment operations."),
        ]

        results = asyncio.run(extract_batch(descriptions, client, batch_size=5))

        self.assertEqual(len(results), 3)
        # First and third should have entities
        self.assertEqual(len(results[0]["entities"]), 1)
        self.assertEqual(len(results[2]["entities"]), 1)
        # Second (error) should have empty entities
        self.assertEqual(results[1]["entities"], [])
        self.assertEqual(results[1]["relationships"], [])


if __name__ == "__main__":
    unittest.main()
