# backend/reranker.py
"""Re-rank retrieval results using embedding similarity."""
import numpy as np
from backend.hybrid_retriever import ContractResult


def rerank(
    query: str,
    results: list,
    embed_fn,
    limit: int = 10,
) -> list:
    """Re-score retrieval results using embedding similarity.

    Computes cosine similarity between query embedding and each result's
    text embedding. Results are re-sorted by similarity score.

    Args:
        query: The search query string.
        results: List of ContractResult objects (from hybrid_retriever.py).
            Each has: key, description, recipient, obligation, psc, naics, rrf_score
        embed_fn: Callable that takes list[str] and returns list[list[float]].
            Typically OllamaClient.embed_sync.
        limit: Maximum number of results to return.

    Returns:
        List of ContractResult objects, re-sorted by reranker score.
        Each result gets a new attribute 'rerank_score' (float, 0-1).
    """
    if not results:
        return []

    # Build text for each result
    result_texts = [
        f"{r.recipient}: {r.description} ({r.psc})" for r in results
    ]

    # Embed the query and all result texts in a single batch call
    embeddings = embed_fn([query] + result_texts)

    # Handle edge case: embed_fn returns empty or None
    if not embeddings:
        return results[:limit]

    embeddings = np.array(embeddings, dtype=np.float64)

    # Handle edge case: all embeddings are zero vectors
    norms = np.linalg.norm(embeddings, axis=1)
    if np.all(norms == 0):
        return results[:limit]

    # L2-normalize embeddings (avoid division by zero for individual vectors)
    safe_norms = np.where(norms == 0, 1.0, norms)
    normed = embeddings / safe_norms[:, np.newaxis]

    query_vec = normed[0]
    result_vecs = normed[1:]

    # Cosine similarity between query and each result
    similarities = result_vecs @ query_vec  # dot product of normalized vectors

    # Clip to [0, 1] range for safety
    similarities = np.clip(similarities, 0.0, 1.0)

    # Normalize RRF scores to 0-1 range by dividing by max
    rrf_scores = np.array([r.rrf_score for r in results], dtype=np.float64)
    max_rrf = rrf_scores.max()
    if max_rrf > 0:
        normalized_rrf = rrf_scores / max_rrf
    else:
        normalized_rrf = rrf_scores

    # Combine: final_score = 0.4 * normalized_rrf + 0.6 * cosine_similarity
    final_scores = 0.4 * normalized_rrf + 0.6 * similarities

    # Attach rerank_score and sort
    for i, result in enumerate(results):
        result.rerank_score = float(final_scores[i])

    # Sort by final_score descending
    ranked = sorted(results, key=lambda r: r.rerank_score, reverse=True)

    return ranked[:limit]
