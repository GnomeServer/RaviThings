# backend/hybrid_retriever.py
"""Hybrid retrieval: vector + keyword + graph, fused with RRF."""
import sqlite3
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
        embedding = self.ollama.embed_sync([query])[0]
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

    def search(self, query: str, n_results: int = 15) -> HybridResults:
        """Full hybrid search with RRF fusion."""
        # 1. Parallel retrieval (sequential in sync code, async in server)
        vector_keys = self.search_vector(query, limit=20)
        keyword_results = self.search_keyword(query, limit=20)
        keyword_keys = [r["contract_transaction_unique_key"] for r in keyword_results]
        graph_result = self.search_graph(query, hops=1)
        graph_keys = graph_result["contracts"]

        # 2. Build ranked lists for RRF
        rankings = {}  # key -> {source: rank}
        for rank, key in enumerate(vector_keys):
            rankings.setdefault(key, {})["vector"] = rank + 1
        for rank, key in enumerate(keyword_keys):
            rankings.setdefault(key, {})["keyword"] = rank + 1
        for rank, key in enumerate(graph_keys):
            rankings.setdefault(key, {})["graph"] = rank + 1

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

        # 6. Build graph paths from result recipients (always populate graph)
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
                "fused": len(scored),
            },
            graph_paths=graph_paths,
        )
