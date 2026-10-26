"""Re-embed contract descriptions into ChromaDB using Ollama nomic-embed-text.

The stored index is 768-d. This script is the re-index step; it does not
call a chat model.
"""
import argparse
import sqlite3
import chromadb
from backend.ollama_client import OllamaClient


def reingest(
    db_path: str,
    chroma_path: str,
    ollama_host: str = "http://localhost:11434",
    batch_size: int = 50,
):
    """Re-embed all contracts into ChromaDB using Ollama."""
    ollama = OllamaClient(base_url=ollama_host)

    # Read all contracts with descriptions
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT contract_transaction_unique_key, transaction_description "
        "FROM contracts WHERE transaction_description IS NOT NULL"
    ).fetchall()
    conn.close()
    print(f"Found {len(rows)} contracts with descriptions")

    # Delete old collection and create new one
    client = chromadb.PersistentClient(path=chroma_path)
    try:
        client.delete_collection("doe_contracts")
        print("Deleted old collection")
    except Exception:
        pass
    collection = client.create_collection("doe_contracts")
    print("Created new collection")

    # Process in batches
    total = len(rows)
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        ids = [r[0] for r in batch]
        docs = [r[1] for r in batch]

        # Get embeddings from Ollama
        embeddings = ollama.embed_sync(docs)

        # Add to ChromaDB
        collection.add(ids=ids, documents=docs, embeddings=embeddings)

        done = min(i + batch_size, total)
        pct = done / total * 100
        print(f"  [{done}/{total}] {pct:.1f}%", flush=True)

    print(f"Done. {total} embeddings stored in {chroma_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-embed contracts using Ollama")
    parser.add_argument("--db", default="doe_contracts.db")
    parser.add_argument("--chroma", default="./chroma_db")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    reingest(args.db, args.chroma, args.ollama_host, args.batch_size)
