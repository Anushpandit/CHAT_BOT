"""
Citation Extractor
Modifies the Groq prompt to return structured citations:
  - answer text
  - list of exact quoted sentences from the source documents
  - which file each quote came from
  - which part of the answer each quote supports
"""

import os
import json
import logging
import re
from typing import List, Optional
from groq import Groq

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Groq client
# ─────────────────────────────────────────────

_client = None
def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


# ─────────────────────────────────────────────
# Prompt that forces citation output
# ─────────────────────────────────────────────

CITATION_SYSTEM_PROMPT = """You are a precise document assistant. 
When answering questions, you MUST respond in the following JSON format ONLY:

{
  "answer": "Your full answer here in plain text",
  "citations": [
    {
      "quote": "The EXACT sentence or phrase from the document that supports your answer",
      "file": "filename.pdf",
      "relevance": "Brief note on why this quote supports the answer"
    }
  ]
}

STRICT RULES:
1. "quote" must be copied VERBATIM from the provided document context — do not paraphrase it.
2. Only quote sentences that DIRECTLY support your answer.
3. Include 1–5 citations maximum.
4. If the answer is not in the documents, set citations to [] and say so in answer.
5. Never invent quotes. Only use text that appears word-for-word in the context.
6. Response must be valid JSON only — no markdown, no extra text outside the JSON.
"""


# ─────────────────────────────────────────────
# Citation data classes
# ─────────────────────────────────────────────

from dataclasses import dataclass, field

@dataclass
class Citation:
    quote: str          # exact text from document
    file: str           # source filename
    relevance: str      # why this supports the answer
    chunk_text: str = ""     # full chunk the quote came from (for highlighting)
    char_start: int = -1     # position in chunk_text where quote starts
    char_end: int   = -1     # position in chunk_text where quote ends

@dataclass
class CitedAnswer:
    answer: str
    citations: List[Citation] = field(default_factory=list)
    raw_json: str = ""
    parse_error: Optional[str] = None


# ─────────────────────────────────────────────
# Locate quote within chunk text
# ─────────────────────────────────────────────

def locate_quote_in_chunks(quote: str, retrieved_chunks: List[dict]) -> tuple[str, int, int]:
    """
    Find which chunk contains the quote and return its position.
    Returns (chunk_text, char_start, char_end).
    Uses fuzzy matching to handle minor whitespace/punctuation differences.
    """
    quote_clean = re.sub(r"\s+", " ", quote.strip())

    for chunk in retrieved_chunks:
        text = chunk.get("text", "")
        text_clean = re.sub(r"\s+", " ", text)

        # Exact match
        idx = text_clean.find(quote_clean)
        if idx != -1:
            return text, idx, idx + len(quote_clean)

        # Partial match: find longest matching substring (>60% of quote length)
        min_len = max(20, int(len(quote_clean) * 0.6))
        for length in range(len(quote_clean), min_len, -5):
            for start in range(len(quote_clean) - length + 1):
                sub = quote_clean[start:start+length]
                idx = text_clean.find(sub)
                if idx != -1:
                    return text, idx, idx + length

    return "", -1, -1


# ─────────────────────────────────────────────
# Main citation chat function
# ─────────────────────────────────────────────

def chat_with_citations(
    question: str,
    chat_history: List[dict],
    retrieved_chunks: List[dict],       # from vector_store.retrieve_top_k()
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 1500,
    temperature: float = 0.1,           # low temp = more faithful quotes
) -> CitedAnswer:
    """
    RAG chat that returns an answer with exact quoted citations.

    Args:
        question:         User's question.
        chat_history:     Previous turns.
        retrieved_chunks: Top-K chunks from ChromaDB (must include 'text' and 'file_name').
        model:            Groq model.
        max_tokens:       Max response tokens.
        temperature:      LLM temperature.

    Returns:
        CitedAnswer with answer text + citations with exact quotes.
    """
    if not retrieved_chunks:
        return CitedAnswer(
            answer="I couldn't find relevant information in the uploaded documents.",
            citations=[],
        )

    # Build context block
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_parts.append(
            f"[Document {i}: {chunk['file_name']} | Score: {chunk['score']:.2f}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Build messages
    messages = [{"role": "system", "content": CITATION_SYSTEM_PROMPT}]
    for turn in chat_history[-4:]:   # keep last 4 turns only
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": f"Document Context:\n{context}\n\nQuestion: {question}"
    })

    # Call Groq
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},   # force JSON output
    )

    raw = response.choices[0].message.content.strip()

    # Parse JSON
    try:
        data = json.loads(raw)
        answer = data.get("answer", "")
        raw_citations = data.get("citations", [])

        citations = []
        for c in raw_citations:
            quote     = c.get("quote", "").strip()
            file_name = c.get("file", "").strip()
            relevance = c.get("relevance", "").strip()

            if not quote:
                continue

            # Locate quote position in source chunks
            chunk_text, char_start, char_end = locate_quote_in_chunks(quote, retrieved_chunks)

            citations.append(Citation(
                quote=quote,
                file=file_name,
                relevance=relevance,
                chunk_text=chunk_text,
                char_start=char_start,
                char_end=char_end,
            ))

        return CitedAnswer(answer=answer, citations=citations, raw_json=raw)

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}\nRaw: {raw[:300]}")
        # Graceful fallback: return raw text as answer, no citations
        return CitedAnswer(
            answer=raw,
            citations=[],
            raw_json=raw,
            parse_error=str(e),
        )


# ─────────────────────────────────────────────
# Format citations for API response
# ─────────────────────────────────────────────

def format_citations(cited_answer: CitedAnswer) -> dict:
    """
    Convert CitedAnswer into a JSON-serializable dict for the API response.
    Includes highlight positions for the frontend.
    """
    return {
        "answer": cited_answer.answer,
        "citations": [
            {
                "quote":      c.quote,
                "file":       c.file,
                "relevance":  c.relevance,
                "chunk_text": c.chunk_text,
                "char_start": c.char_start,
                "char_end":   c.char_end,
                "found":      c.char_start != -1,
            }
            for c in cited_answer.citations
        ],
        "citation_count": len(cited_answer.citations),
        "parse_error": cited_answer.parse_error,
    }
