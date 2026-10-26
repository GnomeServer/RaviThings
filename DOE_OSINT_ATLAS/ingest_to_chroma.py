import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import pandas as pd
from tqdm import tqdm

def ingest_to_chroma(db_path="doe_contracts.db", chroma_path="./chroma_db"):
    print("Initializing ChromaDB and Embeddings Model...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.create_collection("doe_contracts", get_or_create=True)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    conn = sqlite3.connect(db_path)
    
    # Get count
    total_rows = pd.read_sql_query("SELECT count(*) FROM contracts WHERE transaction_description IS NOT NULL", conn).iloc[0,0]
    print(f"Total rows to embed: {total_rows}")
    
    batch_size = 1000
    
    # Process in batches
    for start in tqdm(range(0, total_rows, batch_size)):
        # Load batch from SQLite
        sql = f"SELECT contract_transaction_unique_key, transaction_description FROM contracts WHERE transaction_description IS NOT NULL LIMIT {batch_size} OFFSET {start}"
        batch_df = pd.read_sql_query(sql, conn)
        
        # Prepare for Chroma
        ids = batch_df['contract_transaction_unique_key'].astype(str).tolist()
        documents = batch_df['transaction_description'].astype(str).tolist()
        
        # Embed and add to Chroma
        embeddings = model.encode(documents).tolist()
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents
        )
        
    print("Vector ingestion complete.")
    conn.close()

if __name__ == "__main__":
    ingest_to_chroma()
