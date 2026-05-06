import logging
import os
from typing import List, Tuple, Optional

from chunker import TextChunk

logger = logging.getLogger(__name__)

# Collection name used in ChromaDB
COLLECTION_NAME = "drive_chatbot_docs"


# ─────────────────────────────────────────────
# ChromaDB client (persistent, disk-backed)
# ─────────────────────────────────────────────

_chroma_client = None
_collection = None


def get_collection(persist_dir: str = "./chroma_db", reset: bool = False):
    """
    Get (or create) the ChromaDB collection.
    """
    global _chroma_client, _collection

    try:
        import chromadb
    except ImportError:
        raise ImportError("chromadb not installed.\nRun: pip install chromadb")

    if _chroma_client is None:
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"ChromaDB initialized at: {persist_dir}")

    if reset and _collection is not None:
        _chroma_client.delete_collection(COLLECTION_NAME)
        _collection = None
        logger.info("Collection reset.")

    if _collection is None:
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},   # cosine similarity
        )
        logger.info(f"Collection '{COLLECTION_NAME}' ready. Count: {_collection.count()}")

    return _collection


# ─────────────────────────────────────────────
# Store chunks + embeddings
# ─────────────────────────────────────────────

def store_chunks(
    chunk_embedding_pairs: List[Tuple[TextChunk, List[float]]],
    persist_dir: str = "./chroma_db",
    batch_size: int = 100,
    reset: bool = False,
) -> int:
    """
    Store TextChunk + embedding vectors into ChromaDB.
    """
    collection = get_collection(persist_dir, reset=reset)

    # Collect all IDs already in the collection to skip duplicates
    existing_ids = set()
    if collection.count() > 0:
        existing = collection.get(include=[])
        existing_ids = set(existing["ids"])

    ids, texts, embeddings, metadatas = [], [], [], []
    skipped = 0

    for chunk, embedding in chunk_embedding_pairs:
        if chunk.chunk_id in existing_ids:
            skipped += 1
            continue
        ids.append(chunk.chunk_id)
        texts.append(chunk.text)
        embeddings.append(embedding)
        metadatas.append(chunk.metadata)

    if skipped:
        logger.info(f"Skipped {skipped} already-stored chunks.")

    if not ids:
        logger.info("Nothing new to store.")
        return 0

    # Batch insert
    total_inserted = 0
    for i in range(0, len(ids), batch_size):
        batch_ids   = ids[i : i + batch_size]
        batch_texts = texts[i : i + batch_size]
        batch_embs  = embeddings[i : i + batch_size]
        batch_meta  = metadatas[i : i + batch_size]

        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=batch_embs,
            metadatas=batch_meta,
        )
        total_inserted += len(batch_ids)
        logger.info(f"  Stored batch {i//batch_size + 1}: {total_inserted}/{len(ids)} chunks")

    logger.info(f"✓ Store complete. Total in collection: {collection.count()}")
    return total_inserted


# ─────────────────────────────────────────────
# Retrieve top-K similar chunks
# ─────────────────────────────────────────────

def retrieve_top_k(
    query_embedding: List[float],
    k: int = 5,
    persist_dir: str = "./chroma_db",
    filter_file: Optional[str] = None,    # restrict search to one file
) -> List[dict]:
    """
    Retrieve the top-K most semantically similar chunks for a query.
    """
    collection = get_collection(persist_dir)

    if collection.count() == 0:
        logger.warning("Vector store is empty! Run the ingestion pipeline first.")
        return []

    # Build optional where filter
    where = {"source": filter_file} if filter_file else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
        where=where,
    )

    top_chunks = []
    ids       = results["ids"][0]
    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
        top_chunks.append({
            "chunk_id":    chunk_id,
            "text":        doc,
            "score":       round(1 - dist, 4),   # cosine similarity (0→1, higher=better)
            "file_name":   meta.get("source", ""),
            "file_type":   meta.get("file_type", ""),
            "chunk_index": meta.get("chunk_index", 0),
        })

    return top_chunks


# ─────────────────────────────────────────────
# Utility: list all stored files
# ─────────────────────────────────────────────

def list_stored_files(persist_dir: str = "./chroma_db") -> List[str]:
    """Return list of unique file names currently in the vector store."""
    collection = get_collection(persist_dir)
    if collection.count() == 0:
        return []

    all_meta = collection.get(include=["metadatas"])["metadatas"]
    files = sorted(set(m.get("source", "") for m in all_meta))
    return files


def delete_file_chunks(file_name: str, persist_dir: str = "./chroma_db") -> int:
    """Delete all chunks belonging to a specific file."""
    collection = get_collection(persist_dir)
    before = collection.count()
    collection.delete(where={"source": file_name})
    after = collection.count()
    deleted = before - after
    logger.info(f"Deleted {deleted} chunks for file: {file_name}")
    return deleted


def get_store_stats(persist_dir: str = "./chroma_db") -> dict:
    """Return basic statistics about the vector store."""
    collection = get_collection(persist_dir)
    count = collection.count()

    if count == 0:
        return {"total_chunks": 0, "total_files": 0, "files": []}

    all_meta  = collection.get(include=["metadatas"])["metadatas"]
    files     = sorted(set(m.get("source", "") for m in all_meta))
    file_types = sorted(set(m.get("file_type", "") for m in all_meta))

    return {
        "total_chunks": count,
        "total_files":  len(files),
        "files":        files,
        "file_types":   file_types,
    }
