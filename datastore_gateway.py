import sqlite3
import pandas as pd
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class ContractDataStore:
    def __init__(self, db_path="doe_contracts.db", chroma_path="./chroma_db"):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.sql_conn = sqlite3.connect(db_path)
        
        if CHROMA_AVAILABLE:
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            # This will download the model on first run (~80MB)
            self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
            try:
                self.collection = self.chroma_client.get_collection("doe_contracts")
            except:
                self.collection = None

    def query_sql(self, sql):
        """Execute arbitrary SQL and return a dataframe."""
        return pd.read_sql_query(sql, self.sql_conn)

    def search_semantic(self, query, n_results=5):
        """Search by meaning using embeddings."""
        if not CHROMA_AVAILABLE or not self.collection:
            return "Semantic search not initialized or ChromaDB not found."
        
        query_embeddings = self.embed_model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embeddings],
            n_results=n_results
        )
        
        # Get the full records from SQLite using the IDs found
        ids = results['ids'][0]
        id_str = ",".join([f"'{i}'" for i in ids])
        return self.query_sql(f"SELECT * FROM contracts WHERE contract_transaction_unique_key IN ({id_str})")

    def search_text(self, keyword):
        """Fast keyword search using SQL LIKE."""
        sql = f"SELECT * FROM contracts WHERE transaction_description LIKE '%{keyword}%' LIMIT 10"
        return self.query_sql(sql)

# Example Usage:
# store = ContractDataStore()
# print(store.query_sql("SELECT sum(federal_action_obligation) FROM contracts WHERE action_date_fiscal_year = 2024"))
