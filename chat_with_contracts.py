import sys
import ollama
import pandas as pd
from datastore_gateway import ContractDataStore

# Configure these to match your local setup
MODEL_NAME = "dolphin3" # or "llama3.1" or "doe-expert"
STORE = ContractDataStore()

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
    print(f"--- DOE Contract Chat System (Model: {MODEL_NAME}) ---")
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
        
        # 3. Stream Response
        print(f"[ASSISTANT]: ", end="", flush=True)
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            
            for chunk in response:
                print(chunk['message']['content'], end="", flush=True)
            print()
        except Exception as e:
            print(f"\nError communicating with Ollama: {str(e)}")
            print("Make sure 'ollama serve' is running and the model is pulled.")

if __name__ == "__main__":
    chat_loop()
