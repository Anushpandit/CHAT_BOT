"""
Citation Chat Endpoint
Add this to your existing main.py (Phase 4/6 backend).

New endpoints:
  POST /chat/cited          → RAG answer with exact quoted citations
  GET  /chunks/{file_name}  → retrieve all stored chunks for a file (for highlight panel)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
from sqlalchemy.orm import Session

router = APIRouter()


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class CitedChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    history: List[Dict[str, str]] = []
    model: str = "llama-3.3-70b-versatile"
    top_k: int = 6
    filter_file: Optional[str] = None
    enable_followups: bool = True
    followup_model: str = "llama-3.1-8b-instant"

class CitationOut(BaseModel):
    quote: str
    file: str
    relevance: str
    chunk_text: str
    char_start: int
    char_end: int
    found: bool

class CitedChatResponse(BaseModel):
    answer: str
    citations: List[CitationOut]
    citation_count: int
    sources: List[str]
    chunks_used: int
    model: str
    followups: List[str] = []


# ─────────────────────────────────────────────
# POST /chat/cited
# ─────────────────────────────────────────────

@router.post("/chat/cited", response_model=CitedChatResponse)
async def chat_with_citations_endpoint(req: CitedChatRequest):
    """
    RAG Q&A that returns:
    - Full answer text
    - Exact quoted sentences from source documents
    - Character positions of each quote in its chunk (for frontend highlighting)
    """
    from vector_store import retrieve_top_k, get_store_stats
    from embedder import embed_query
    from citation_extractor import chat_with_citations, format_citations

    # Check store has data
    if get_store_stats()["total_chunks"] == 0:
        raise HTTPException(400, "No documents indexed. POST to /ingest first.")

    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    # Retrieve relevant chunks
    query_emb = embed_query(req.question)
    chunks = retrieve_top_k(
        query_embedding=query_emb,
        k=req.top_k,
        filter_file=req.filter_file,
    )
    relevant = [c for c in chunks if c["score"] >= 0.25]

    # Run main citation and follow-ups in parallel
    loop = asyncio.get_event_loop()
    from followup_generator import generate_followup_suggestions

    main_task = loop.run_in_executor(
        None,
        lambda: chat_with_citations(
            question=req.question,
            chat_history=req.history,
            retrieved_chunks=relevant,
            model=req.model,
        )
    )

    followup_task = loop.run_in_executor(
        None,
        lambda: generate_followup_suggestions(
            question=req.question,
            answer="",
            context_chunks=relevant,
            model=req.followup_model,
        )
    ) if req.enable_followups else None

    cited = await main_task
    
    if req.enable_followups:
        # regenerate with the actual answer for better quality
        followups = await loop.run_in_executor(
            None,
            lambda: generate_followup_suggestions(
                question=req.question,
                answer=cited.answer,
                context_chunks=relevant,
                model=req.followup_model,
            )
        )
    else:
        followups = []

    formatted = format_citations(cited)
    sources = list({c["file"] for c in formatted["citations"]})

    return CitedChatResponse(
        answer=formatted["answer"],
        citations=formatted["citations"],
        citation_count=formatted["citation_count"],
        sources=sources,
        chunks_used=len(relevant),
        model=req.model,
        followups=followups,
    )


# ─────────────────────────────────────────────
# GET /chunks/{file_name}
# Returns all stored chunks for a file so the
# frontend can render the full document with highlights
# ─────────────────────────────────────────────

@router.get("/chunks/{file_name}")
async def get_file_chunks(file_name: str):
    """
    Return all stored text chunks for a specific file.
    Frontend uses this to render the full document panel
    and overlay citation highlights.
    """
    from vector_store import get_collection

    collection = get_collection()
    if collection.count() == 0:
        raise HTTPException(404, "Vector store is empty.")

    results = collection.get(
        where={"source": file_name},
        include=["documents", "metadatas"],
    )

    if not results["ids"]:
        raise HTTPException(404, f"No chunks found for file: {file_name}")

    chunks = []
    for chunk_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
        chunks.append({
            "chunk_id":    chunk_id,
            "text":        doc,
            "chunk_index": meta.get("chunk_index", 0),
            "file_name":   meta.get("source", file_name),
            "file_type":   meta.get("file_type", ""),
        })

    # Sort by chunk index
    chunks.sort(key=lambda x: x["chunk_index"])

    return {
        "file_name":   file_name,
        "total_chunks": len(chunks),
        "chunks":       chunks,
    }
