import os
import logging
from typing import List, Dict, Optional
from groq import Groq

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Groq client (singleton)
# ─────────────────────────────────────────────

_groq_client = None

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intelligent document assistant. 
You have been given context extracted from the user's uploaded Google Drive files.

Rules:
- Answer ONLY from the provided document context.
- If the answer is not in the context, say: "I couldn't find that information in the uploaded documents."
- DO NOT mention the source file name in your text (e.g., do not say "According to [filename]"). Citations are handled by the UI automatically.
- Provide a direct, conversational answer without preambles like "Based on the provided context...".
- Be concise, structured, and helpful.
- For tables or data, format your answer clearly.
- Never make up information not present in the context.
"""


# ─────────────────────────────────────────────
# Core chat function
# ─────────────────────────────────────────────

def chat_with_docs(
    question: str,
    chat_history: List[Dict[str, str]],
    persist_dir: str = "./chroma_db",
    model: str = "llama-3.3-70b-versatile",
    top_k: int = 5,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    filter_file: Optional[str] = None,
) -> Dict:
    """
    RAG-powered chat with Groq.
    """
    # ── Step 1: Retrieve relevant context ───────────────────
    from ingestion_pipeline import retrieve_context_for_query
    from vector_store import retrieve_top_k
    from embedder import embed_query

    query_emb = embed_query(question)
    raw_results = retrieve_top_k(
        query_embedding=query_emb,
        k=top_k,
        persist_dir=persist_dir,
        filter_file=filter_file,
    )

    # Do not pre-filter by score. The LLM is capable of deciding if the context is relevant,
    # and strict thresholding often blocks conversational queries with many stop words.
    relevant = raw_results

    if not relevant:
        context_str = "[No relevant content found in the uploaded documents.]"
        sources = []
    else:
        context_parts = []
        for i, r in enumerate(relevant, 1):
            context_parts.append(
                f"--- EXTRACT FROM FILE: {r['file_name']} ---\n{r['text']}\n"
            )
        context_str = "\n".join(context_parts)
        sources = list({r["file_name"] for r in relevant})

    # ── Step 2: Build messages ───────────────────────────────
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history (last 6 turns max to stay within context)
    for turn in chat_history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current question with context
    user_message = f"""Document Context:
{context_str}

Question: {question}"""

    messages.append({"role": "user", "content": user_message})

    # ── Step 3: Call Groq ────────────────────────────────────
    client = get_groq_client()

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    answer = response.choices[0].message.content.strip()

    return {
        "answer": answer,
        "sources": sources,
        "model": model,
        "chunks_used": len(relevant),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    }
