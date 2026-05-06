import logging
from typing import List, Optional
from dataclasses import dataclass

from chunker import chunk_all_files, TextChunk
from embedder import embed_chunks
from vector_store import store_chunks, get_store_stats

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

@dataclass
class IngestionConfig:
    chunk_size: int   = 400     # words per chunk
    overlap: int      = 80      # overlapping words between chunks
    batch_size: int   = 64      # embedding batch size
    persist_dir: str  = "./chroma_db"
    model_name: str   = "all-MiniLM-L6-v2"
    reset_store: bool = False   # wipe existing data before ingesting


# ─────────────────────────────────────────────
# Main ingestion function
# ─────────────────────────────────────────────

def ingest_extracted_contents(
    extracted_contents,                    # List[ExtractedContent] from Phase 2
    config: Optional[IngestionConfig] = None,
) -> dict:
    """
    Full Phase 3 pipeline:
      1. Chunk all extracted documents
      2. Embed chunks with sentence-transformers
      3. Store in ChromaDB
    """
    if config is None:
        config = IngestionConfig()

    print("\n" + "=" * 55)
    print("PHASE 3 — INGESTION PIPELINE")
    print("=" * 55)

    # ── Step 1: Chunk ────────────────────────────────────────
    print("\n[1/3] Chunking documents...")
    all_chunks: List[TextChunk] = chunk_all_files(
        extracted_contents=extracted_contents,
        chunk_size=config.chunk_size,
        overlap=config.overlap,
    )

    if not all_chunks:
        print("⚠ No chunks produced. Check that extracted_contents has text.")
        return {"status": "empty", "chunks": 0, "stored": 0}

    # ── Step 2: Embed ────────────────────────────────────────
    print(f"\n[2/3] Embedding {len(all_chunks)} chunks (model: {config.model_name})...")
    chunk_embedding_pairs = embed_chunks(
        chunks=all_chunks,
        model_name=config.model_name,
        batch_size=config.batch_size,
        show_progress=True,
    )

    # ── Step 3: Store ─────────────────────────────────────────
    print(f"\n[3/3] Storing in ChromaDB at '{config.persist_dir}'...")
    stored = store_chunks(
        chunk_embedding_pairs=chunk_embedding_pairs,
        persist_dir=config.persist_dir,
        batch_size=100,
        reset=config.reset_store,
    )

    # ── Summary ───────────────────────────────────────────────
    stats = get_store_stats(config.persist_dir)
    stats["chunks_this_run"] = len(all_chunks)
    stats["stored_this_run"] = stored

    print("\n" + "=" * 55)
    print("INGESTION COMPLETE")
    print(f"  Chunks produced : {len(all_chunks)}")
    print(f"  Chunks stored   : {stored}")
    print(f"  Total in store  : {stats['total_chunks']}")
    print(f"  Files indexed   : {stats['total_files']}")
    for f in stats["files"]:
        print(f"    • {f}")
    print("=" * 55 + "\n")

    return stats


# ─────────────────────────────────────────────
# Retrieval helper (used by Phase 4 chatbot)
# ─────────────────────────────────────────────

def retrieve_context_for_query(
    question: str,
    k: int = 5,
    persist_dir: str = "./chroma_db",
    model_name: str = "all-MiniLM-L6-v2",
    filter_file: Optional[str] = None,
    score_threshold: float = 0.30,        # discard chunks below this similarity
) -> str:
    """
    Embed a question and retrieve the top-K relevant chunks as a context string.
    Called by Phase 4 (chatbot) before sending to Groq.
    """
    from embedder import embed_query
    from vector_store import retrieve_top_k

    query_emb = embed_query(question, model_name)
    results   = retrieve_top_k(query_emb, k=k, persist_dir=persist_dir, filter_file=filter_file)

    # Filter low-relevance chunks
    relevant = [r for r in results if r["score"] >= score_threshold]

    if not relevant:
        return "[No relevant content found in the uploaded documents.]"

    # Build context block
    context_parts = []
    for i, r in enumerate(relevant, 1):
        context_parts.append(
            f"[Source {i}: {r['file_name']} | Chunk {r['chunk_index']} | Relevance: {r['score']:.2f}]\n"
            f"{r['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    """
    Example: ingest local text files for quick testing.
    Replace with real ExtractedContent objects from Phase 2.
    """
    import sys
    import os

    # Simulate Phase 2 ExtractedContent with a simple namespace
    from types import SimpleNamespace

    sample_docs = [
        SimpleNamespace(
            file_name="sample.txt",
            file_type="text",
            text="Artificial intelligence is transforming industries. "
                 "Machine learning models can now process text, images, and speech "
                 "with superhuman accuracy in many benchmarks.\n\n"
                 "Groq provides ultra-fast LLM inference using their custom LPU hardware. "
                 "This makes real-time chatbot applications significantly faster than "
                 "traditional GPU-based inference.\n\n"
                 "Vector databases like ChromaDB store embeddings and enable semantic search "
                 "across large document collections without needing exact keyword matches.",
            error=None,
        ),
        SimpleNamespace(
            file_name="faq.txt",
            file_type="text",
            text="Q: What is a vector embedding?\n"
                 "A: A vector embedding is a numerical representation of text in high-dimensional space "
                 "where semantically similar texts are placed closer together.\n\n"
                 "Q: What is RAG?\n"
                 "A: Retrieval-Augmented Generation (RAG) is a technique where relevant document chunks "
                 "are retrieved from a vector store and injected into the LLM prompt as context, "
                 "so the model can answer questions grounded in your specific documents.\n\n"
                 "Q: Why use ChromaDB?\n"
                 "A: ChromaDB is a lightweight, open-source vector database that runs locally "
                 "with zero configuration. Perfect for prototyping and small-to-medium projects.",
            error=None,
        ),
    ]

    print("Running Phase 3 ingestion with sample data...\n")
    stats = ingest_extracted_contents(sample_docs)

    print("\nTesting retrieval...")
    context = retrieve_context_for_query("What is RAG and how does it work?", k=3)
    print("\n--- Retrieved Context ---")
    print(context)
