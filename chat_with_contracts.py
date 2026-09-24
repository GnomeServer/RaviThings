import asyncio
import pandas as pd
from backend.glm_client import GLMClient
from datastore_gateway import ContractDataStore

STORE = ContractDataStore()
LLM = GLMClient()

def get_context(query, n_results=5):
    """Retrieve relevant contracts from both Chroma (semantic) and SQLite."""
    try:
        # 1. Semantic Search
        results = STORE.search_semantic(query, n_results=n_results)
        
        if isinstance(results, str):
            return f"Error retrieving context: {results}"
            
        # 2. Format Context
        context_lines = []
        for idx, row in results.iterrows():
            context_lines.append(
                f"- RECIPIENT: {row['recipient_name']} ({row['recipient_state_name']})\n"
                f"  AMOUNT: ${row['federal_action_obligation']:,.2f} | FY: {row['action_date_fiscal_year']}\n"
                f"  DESCRIPTION: {row['transaction_description']}\n"
                f"  ---"
            )
        return "\n".join(context_lines)
    except Exception as e:
        return f"Error building context: {str(e)}"

def chat_loop():
    if not LLM.is_available():
        print("OPENROUTER_API_KEY is not set.")
        return
    print("--- DOE Contract Chat System (Model: GLM-5.3) ---")
    print("Type 'exit' or 'quit' to end.")

    messages = [
        {"role": "system", "content": "You are a DOE analyst. Use the provided context to answer questions accurately. If the context doesn't contain the answer, say you don't know based on the current records."}
    ]

    while True:
        query = input("\n[USER]: ").strip()
        if not query: continue
        if query.lower() in ['exit', 'quit']: break

        # 1. Retrieve Context
        print(f"   (Searching datastore for '{query}'...)", flush=True)
        context = get_context(query)
        
        # 2. Prepare Augmented Prompt
        prompt = f"""
        ### DOE CONTRACT RECORDS:
        {context}

        ### USER QUESTION:
        {query}

        ---
        Please answer the question based on the records above.
        """
        
        print("[ASSISTANT]: ", end="", flush=True)
        try:
            async def _stream():
                async for token in LLM.chat_stream(
                    messages + [{"role": "user", "content": prompt}]
                ):
                    print(token, end="", flush=True)
            asyncio.run(_stream())
            print()
        except Exception as e:
            print(f"\nError communicating with OpenRouter: {e}")

if __name__ == "__main__":
    chat_loop()
