"""Runtime graph engine: load, traverse, query the knowledge graph."""
import numpy as np
import igraph as ig
from typing import Callable


class GraphEngine:
    def __init__(self, pkl_path: str, embed_fn: Callable[[list[str]], list[list[float]]] | None = None):
        """Load graph and optionally build semantic search index.

        Args:
            pkl_path: Path to igraph pickle file.
            embed_fn: A callable that takes a list of strings and returns a list of float vectors.
                      Can be OllamaClient.embed_sync or SentenceTransformer.encode.
        """
        self.graph = ig.Graph.Read_Pickle(pkl_path)
        self._name_index: dict[str, int] = {
            v["name"]: v.index for v in self.graph.vs
        }
        self._embed_fn = embed_fn
        self._label_embeddings: np.ndarray | None = None
        self._label_to_idx: list[int] = []
        if embed_fn is not None:
            self._build_label_index()

    def _build_label_index(self):
        """Encode all node labels into embeddings for semantic search.

        Embedding is optional. If the embedder is unreachable the graph
        still loads and search falls back to substring match.
        """
        labels = []
        indices = []
        for v in self.graph.vs:
            label = v["label"]
            if label:
                labels.append(f"{v['type']}: {label}")
                indices.append(v.index)
        if not labels or not self._embed_fn:
            return
        try:
            # Batch in chunks of 100 to avoid overloading Ollama
            all_embeddings = []
            for i in range(0, len(labels), 100):
                batch = labels[i:i + 100]
                batch_embeddings = self._embed_fn(batch)
                all_embeddings.extend(batch_embeddings)
            self._label_embeddings = np.array(all_embeddings, dtype=np.float32)
            # L2-normalize for cosine similarity via dot product
            norms = np.linalg.norm(self._label_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self._label_embeddings = self._label_embeddings / norms
            self._label_to_idx = indices
        except Exception as e:
            print(f"[graph] label embeddings unavailable, using substring search: {e}")
            self._label_embeddings = None
            self._label_to_idx = []

    @property
    def node_count(self) -> int:
        return self.graph.vcount()

    @property
    def edge_count(self) -> int:
        return self.graph.ecount()

    def _vertex_to_dict(self, v) -> dict:
        return {
            "id": v.index,
            "name": v["name"],
            "label": v["label"],
            "type": v["type"],
            "community": v["community"],
            **{k: v[k] for k in v.attributes() if k not in ("name", "label", "type", "community")},
        }

    def _edge_to_dict(self, e) -> dict:
        return {
            "source": self.graph.vs[e.source]["name"],
            "target": self.graph.vs[e.target]["name"],
            "weight": e["weight"],
            "edge_type": e["edge_type"],
            "contract_count": e["contract_count"],
        }

    def get_subgraph(self, entity_name: str, hops: int = 1) -> dict:
        """Get subgraph around an entity within N hops."""
        idx = self._name_index.get(entity_name)
        if idx is None:
            return {"nodes": [], "edges": []}

        # BFS to collect vertices within hops
        visited = {idx}
        frontier = {idx}
        for _ in range(hops):
            next_frontier = set()
            for v in frontier:
                for neighbor in self.graph.neighbors(v):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier

        # Extract subgraph
        nodes = [self._vertex_to_dict(self.graph.vs[v]) for v in visited]
        edges = [
            self._edge_to_dict(e)
            for e in self.graph.es
            if e.source in visited and e.target in visited
        ]
        return {"nodes": nodes, "edges": edges}

    def get_neighbors(self, entity_name: str) -> list[dict]:
        """Get immediate neighbors of an entity."""
        idx = self._name_index.get(entity_name)
        if idx is None:
            return []
        return [self._vertex_to_dict(self.graph.vs[n]) for n in self.graph.neighbors(idx)]

    def search_nodes(self, query: str, limit: int = 20, min_similarity: float = 0.25) -> list[dict]:
        """Search nodes by semantic similarity using embeddings.
        Falls back to substring match if no embedding model is loaded."""
        # Semantic search if embeddings are available
        if self._embed_fn is not None and self._label_embeddings is not None:
            return self._search_nodes_semantic(query, limit, min_similarity)
        # Fallback: substring match
        return self._search_nodes_substring(query, limit)

    def _search_nodes_semantic(self, query: str, limit: int, min_similarity: float) -> list[dict]:
        """Find nodes whose labels are semantically similar to the query."""
        raw = self._embed_fn([query])
        query_embedding = np.array(raw, dtype=np.float32)
        # L2-normalize
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm
        # Cosine similarity (embeddings are L2-normalized, so dot product = cosine)
        similarities = (self._label_embeddings @ query_embedding.T).flatten()
        # Get top-K above threshold
        top_indices = np.argsort(similarities)[::-1]
        results = []
        for idx in top_indices:
            if similarities[idx] < min_similarity:
                break
            vertex_idx = self._label_to_idx[idx]
            result = self._vertex_to_dict(self.graph.vs[vertex_idx])
            result["similarity"] = float(similarities[idx])
            results.append(result)
            if len(results) >= limit:
                break
        return results

    def _search_nodes_substring(self, query: str, limit: int) -> list[dict]:
        """Fallback: search nodes by label substring match."""
        query_lower = query.lower()
        results = []
        for v in self.graph.vs:
            if query_lower in (v["label"] or "").lower():
                results.append(self._vertex_to_dict(v))
                if len(results) >= limit:
                    break
        return results

    def get_communities(self) -> list[dict]:
        """Return community summaries."""
        communities: dict[int, list] = {}
        for v in self.graph.vs:
            cid = v["community"]
            communities.setdefault(cid, []).append(v)

        result = []
        for cid, members in communities.items():
            types = {}
            for m in members:
                types.setdefault(m["type"], []).append(m["label"])
            total = sum(
                (m["total_obligated"] if "total_obligated" in m.attributes() else 0) or 0
                for m in members if m["type"] == "recipient"
            )
            result.append({
                "id": cid,
                "node_count": len(members),
                "types": {t: len(names) for t, names in types.items()},
                "top_recipients": sorted(
                    [m["label"] for m in members if m["type"] == "recipient"],
                    key=lambda x: x
                )[:5],
                "total_obligated": total,
            })
        return sorted(result, key=lambda c: c["total_obligated"], reverse=True)

    def get_graph_paths(self, node_names: list[str]) -> dict:
        """Given a set of node names, return the subgraph connecting them."""
        indices = [self._name_index[n] for n in node_names if n in self._name_index]
        if len(indices) < 2:
            return {"nodes": [], "edges": []}

        # Collect all edges between the given nodes and their shared neighbors
        visited = set(indices)
        edges = []
        for e in self.graph.es:
            if e.source in visited and e.target in visited:
                edges.append(self._edge_to_dict(e))

        nodes = [self._vertex_to_dict(self.graph.vs[v]) for v in visited]
        return {"nodes": nodes, "edges": edges}
