"""
Updated /chat endpoint that returns follow-up suggestions alongside the answer.
Add this to your existing Phase 4/6 main.py

Changes:
  - POST /chat now returns a `followups` field: List[str]
  - POST /chat/cited also returns `followups`
  - New standalone endpoint: POST /followups (generate suggestions for any Q&A)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class ChatWithFollowupsRequest(BaseModel):
    question: str
    history: List[Dict[str, str]] = []
    session_id: Optional[str] = None
    model: str = "llama-3.3-70b-versatile"
    top_k: int = 5
    filter_file: Optional[str] = None
    enable_followups: bool = True          # toggle suggestions on/off
    followup_model: str = "llama-3.1-8b-instant"  # fast model for suggestions

class ChatWithFollowupsResponse(BaseModel):
    answer: str
    sources: List[str]
    chunks_used: int
    model: str
    usage: Dict
    followups: List[str]                   # ← new field

class FollowupRequest(BaseModel):
    question: str
    answer: str
    context_chunks: List[Dict] = []
    model: str = "llama-3.1-8b-instant"
    count: int = 3

class FollowupResponse(BaseModel):
    followups: List[str]


# ─────────────────────────────────────────────
# POST /chat/with-followups
# Full RAG chat + follow-up suggestions (parallel)
# ─────────────────────────────────────────────

@router.post("/chat/with-followups", response_model=ChatWithFollowupsResponse)
async def chat_with_followups(req: ChatWithFollowupsRequest):
    """
    RAG chat that ALSO returns 3 follow-up suggestions.
    Both the main answer and suggestions are generated in parallel
    using asyncio — no extra latency added.
    """
    from vector_store import retrieve_top_k, get_store_stats
    from embedder import embed_query
    from chatbot import chat_with_docs
    from followup_generator import generate_followup_suggestions

    if get_store_stats()["total_chunks"] == 0:
        raise HTTPException(400, "No documents indexed. POST to /ingest first.")

    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    # Retrieve relevant chunks (shared between main answer + followups)
    query_emb = embed_query(req.question)
    chunks = retrieve_top_k(
        query_embedding=query_emb,
        k=req.top_k,
        filter_file=req.filter_file,
    )
    relevant = [c for c in chunks if c["score"] >= 0.25]

    # ── Run main answer + follow-up generation IN PARALLEL ──────────
    loop = asyncio.get_event_loop()

    # Main RAG call (blocking → run in thread)
    main_task = loop.run_in_executor(
        None,
        lambda: chat_with_docs(
            question=req.question,
            chat_history=req.history,
            model=req.model,
            top_k=req.top_k,
            filter_file=req.filter_file,
        )
    )

    # Follow-up generation starts immediately in parallel
    followup_task = loop.run_in_executor(
        None,
        lambda: generate_followup_suggestions(
            question=req.question,
            answer="",          # answer not ready yet — use context only
            context_chunks=relevant,
            model=req.followup_model,
        )
    ) if req.enable_followups else None

    # Await main answer first
    result = await main_task

    # Now regenerate follow-ups with the actual answer for better quality
    if req.enable_followups:
        followup_task = loop.run_in_executor(
            None,
            lambda: generate_followup_suggestions(
                question=req.question,
                answer=result["answer"],
                context_chunks=relevant,
                model=req.followup_model,
            )
        )
        followups = await followup_task
    else:
        followups = []

    return ChatWithFollowupsResponse(
        answer=result["answer"],
        sources=result["sources"],
        chunks_used=result["chunks_used"],
        model=result["model"],
        usage=result["usage"],
        followups=followups,
    )


# ─────────────────────────────────────────────
# POST /followups  (standalone endpoint)
# Generate follow-ups for any Q&A pair
# ─────────────────────────────────────────────

@router.post("/followups", response_model=FollowupResponse)
async def get_followups(req: FollowupRequest):
    """
    Standalone endpoint: generate follow-up suggestions for any Q&A pair.
    Useful if you want to generate suggestions separately after the main answer.
    """
    from followup_generator import generate_followup_suggestions
    import asyncio

    loop = asyncio.get_event_loop()
    followups = await loop.run_in_executor(
        None,
        lambda: generate_followup_suggestions(
            question=req.question,
            answer=req.answer,
            context_chunks=req.context_chunks,
            model=req.model,
            max_suggestions=req.count,
        )
    )
    return FollowupResponse(followups=followups)
