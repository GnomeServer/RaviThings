# backend/hybrid_retriever.py
"""Hybrid retrieval: vector + keyword + graph + relationships, fused with RRF."""
import sqlite3
import numpy as np
from dataclasses import dataclass, field
from backend.setup_fts import search_fts5
from backend.graph_engine import GraphEngine
from backend.ollama_client import OllamaClient

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


@dataclass
class ContractResult:
    key: str
    description: str
    recipient: str
    obligation: float
    fiscal_year: int
    psc: str
    naics: str
    sources: list[str] = field(default_factory=list)
    rrf_score: float = 0.0


@dataclass
class HybridResults:
    contracts: list[ContractResult]
    retrieval_counts: dict[str, int]
    graph_paths: dict


RRF_K = 60


class HybridRetriever:
    def __init__(
        self,
        db_path: str,
        graph_engine: GraphEngine | None = None,
        chroma_path: str | None = None,
        ollama: OllamaClient | None = None,
    ):
        self.db_path = db_path
        self.graph_engine = graph_engine
        self.chroma_collection = None
        self.ollama = ollama

        if chroma_path and CHROMA_AVAILABLE:
            client = chromadb.PersistentClient(path=chroma_path)
            try:
                self.chroma_collection = client.get_collection("doe_contracts")
            except Exception:
                pass

    def _get_contracts_by_keys(self, keys: list[str]) -> dict[str, dict]:
        """Fetch full contract records from SQLite by keys."""
        if not keys:
            return {}
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(keys))
        rows = conn.execute(
            f"SELECT * FROM contracts WHERE contract_transaction_unique_key IN ({placeholders})",
            keys,
        ).fetchall()
        conn.close()
        return {row["contract_transaction_unique_key"]: dict(row) for row in rows}

    def search_vector(self, query: str, limit: int = 20) -> list[str]:
        """Semantic search via ChromaDB using Ollama embeddings. Returns ranked contract keys."""
        if not self.chroma_collection or not self.ollama:
            return []
        try:
            embedding = self.ollama.embed_sync([query])[0]
        except Exception as e:
            print(f"[hybrid] vector lane unavailable, continuing without it: {e}")
            return []
        results = self.chroma_collection.query(
            query_embeddings=[embedding], n_results=limit
        )
        return results["ids"][0] if results["ids"] else []

    def search_keyword(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5 keyword search. Returns contract dicts."""
        keys = search_fts5(self.db_path, query, limit=limit)
        contracts = self._get_contracts_by_keys(keys)
        return [contracts[k] for k in keys if k in contracts]

    def search_graph(self, query: str, hops: int = 1) -> dict:
        """Graph-based search: find matching nodes, traverse, return connected contracts."""
        if not self.graph_engine:
            return {"contracts": [], "paths": {"nodes": [], "edges": []}}

        # Semantic search: find graph nodes whose labels are semantically similar to the query
        matching_nodes = self.graph_engine.search_nodes(query, limit=15)
        if not matching_nodes:
            return {"contracts": [], "paths": {"nodes": [], "edges": []}}

        # Gather contract keys from neighbors of matching nodes
        all_contract_keys = set()
        all_node_names = set()

        for node in matching_nodes:
            all_node_names.add(node["name"])
            subgraph = self.graph_engine.get_subgraph(node["name"], hops=hops)
            all_node_names.update(n["name"] for n in subgraph["nodes"])

            # Get recipient names from the subgraph
            recipient_names = [
                n["label"] for n in subgraph["nodes"] if n["type"] == "recipient"
            ]
            if recipient_names:
                conn = sqlite3.connect(self.db_path)
                placeholders = ",".join("?" * len(recipient_names))
                rows = conn.execute(
                    f"SELECT contract_transaction_unique_key FROM contracts "
                    f"WHERE recipient_name IN ({placeholders}) LIMIT 50",
                    recipient_names,
                ).fetchall()
                conn.close()
                all_contract_keys.update(r[0] for r in rows)

        # Get graph paths for visualization
        paths = self.graph_engine.get_graph_paths(list(all_node_names))

        return {"contracts": list(all_contract_keys), "paths": paths}

    def search_relationships(self, query: str, limit: int = 20) -> list[str]:
        """Relationship-level retrieval: search over edge descriptions in the graph.

        Embeds edge descriptions and finds edges semantically similar to the query.
        Returns contract keys linked to the recipients on those edges.
        """
        if not self.graph_engine or not self.ollama:
            return []

        graph = self.graph_engine.graph
        if graph.ecount() == 0:
            return []
        # Embedding every edge is a per-request scan. The production graph
        # is ~72k edges; doing that here crashed chat (Edge has no .get)
        # and would stall the console even after the attribute fix.
        # Keyword + graph traversal cover this query until an edge index exists.
        if graph.ecount() > 2000:
            return []

        # Collect edge descriptions (edge_type + source/target labels)
        edge_texts = []
        edge_indices = []
        for idx in range(graph.ecount()):
            e = graph.es[idx]
            src = graph.vs[e.source]
            tgt = graph.vs[e.target]
            edge_type = e.attributes().get("edge_type") or "related"
            desc = f"{src['label']} -- {edge_type} -- {tgt['label']}"
            edge_texts.append(desc)
            edge_indices.append(idx)

        if not edge_texts:
            return []

        # Embed query and edges
        try:
            all_texts = [query] + edge_texts
            embeddings = self.ollama.embed_sync(all_texts)
            if not embeddings or len(embeddings) < 2:
                return []

            query_emb = np.array(embeddings[0], dtype=np.float32)
            edge_embs = np.array(embeddings[1:], dtype=np.float32)

            # L2 normalize
            q_norm = np.linalg.norm(query_emb)
            if q_norm > 0:
                query_emb = query_emb / q_norm
            norms = np.linalg.norm(edge_embs, axis=1, keepdims=True)
            norms[norms == 0] = 1
            edge_embs = edge_embs / norms

            # Cosine similarity
            sims = edge_embs @ query_emb
            top_indices = np.argsort(sims)[::-1][:limit]

        except Exception:
            return []

        # Extract recipient names from top-matching edges
        recipient_names = set()
        for idx in top_indices:
            if sims[idx] < 0.2:
                break
            e = graph.es[edge_indices[idx]]
            for vid in [e.source, e.target]:
                v = graph.vs[vid]
                if v["type"] == "recipient":
                    recipient_names.add(v["label"])

        if not recipient_names:
            return []

        # Fetch contract keys for those recipients
        conn = sqlite3.connect(self.db_path)
        placeholders = ",".join("?" * len(recipient_names))
        rows = conn.execute(
            f"SELECT contract_transaction_unique_key FROM contracts "
            f"WHERE recipient_name IN ({placeholders}) LIMIT {limit}",
            list(recipient_names),
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]

    def search(self, query: str, n_results: int = 15, use_reranker: bool = True) -> HybridResults:
        """Full hybrid search with 4-lane RRF fusion and optional reranking."""
        # 1. Four-lane retrieval. One dead lane must not drop the others.
        vector_keys = self.search_vector(query, limit=20)
        try:
            keyword_results = self.search_keyword(query, limit=20)
        except Exception as e:
            print(f"[hybrid] keyword lane unavailable, continuing without it: {e}")
            keyword_results = []
        keyword_keys = [r["contract_transaction_unique_key"] for r in keyword_results]
        try:
            graph_result = self.search_graph(query, hops=1)
        except Exception as e:
            print(f"[hybrid] graph lane unavailable, continuing without it: {e}")
            graph_result = {"contracts": [], "paths": {"nodes": [], "edges": []}}
        graph_keys = graph_result["contracts"]
        try:
            relationship_keys = self.search_relationships(query, limit=20)
        except Exception as e:
            print(f"[hybrid] relationship lane unavailable, continuing without it: {e}")
            relationship_keys = []

        # 2. Build ranked lists for RRF (4 lanes)
        rankings = {}  # key -> {source: rank}
        for rank, key in enumerate(vector_keys):
            rankings.setdefault(key, {})["vector"] = rank + 1
        for rank, key in enumerate(keyword_keys):
            rankings.setdefault(key, {})["keyword"] = rank + 1
        for rank, key in enumerate(graph_keys):
            rankings.setdefault(key, {})["graph"] = rank + 1
        for rank, key in enumerate(relationship_keys):
            rankings.setdefault(key, {})["relationship"] = rank + 1

        # 3. Compute RRF scores
        scored = []
        for key, sources in rankings.items():
            score = sum(1.0 / (RRF_K + rank) for rank in sources.values())
            scored.append((key, score, list(sources.keys())))
        scored.sort(key=lambda x: x[1], reverse=True)

        # 4. Fetch full records for top N
        top_keys = [s[0] for s in scored[:n_results]]
        contracts_data = self._get_contracts_by_keys(top_keys)

        # 5. Build results
        contracts = []
        for key, score, sources in scored[:n_results]:
            data = contracts_data.get(key, {})
            if not data:
                continue
            contracts.append(ContractResult(
                key=key,
                description=data.get("transaction_description", ""),
                recipient=data.get("recipient_name", ""),
                obligation=data.get("federal_action_obligation", 0) or 0,
                fiscal_year=data.get("action_date_fiscal_year", 0) or 0,
                psc=data.get("product_or_service_code_description", ""),
                naics=data.get("naics_description", ""),
                sources=sources,
                rrf_score=score,
            ))

        # 6. Optional reranking with embedding similarity
        if use_reranker and self.ollama and contracts:
            try:
                from backend.reranker import rerank
                contracts = rerank(
                    query, contracts,
                    embed_fn=self.ollama.embed_sync,
                    limit=n_results,
                )
            except Exception:
                pass  # Reranker failure is non-fatal

        # 7. Build graph paths from result recipients (always populate graph)
        graph_paths = graph_result.get("paths", {"nodes": [], "edges": []})
        if self.graph_engine and (not graph_paths["nodes"]):
            # Graph search returned nothing — build paths from recipients found via vector/keyword
            recipient_names = list({c.recipient for c in contracts if c.recipient})[:10]
            all_node_names = set()
            for rname in recipient_names:
                node_name = f"recipient:{rname}"
                if node_name in self.graph_engine._name_index:
                    subgraph = self.graph_engine.get_subgraph(node_name, hops=1)
                    all_node_names.update(n["name"] for n in subgraph["nodes"])
            if all_node_names:
                graph_paths = self.graph_engine.get_graph_paths(list(all_node_names))

        return HybridResults(
            contracts=contracts,
            retrieval_counts={
                "vector": len(vector_keys),
                "keyword": len(keyword_keys),
                "graph": len(graph_keys),
                "relationship": len(relationship_keys),
                "fused": len(scored),
            },
            graph_paths=graph_paths,
        )
