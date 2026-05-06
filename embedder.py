import logging
from typing import List, Tuple
import numpy as np

from chunker import TextChunk

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Model loader (singleton — load once)
# ─────────────────────────────────────────────

_model = None

def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Load sentence-transformer model once and cache it."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {model_name} ...")
            _model = SentenceTransformer(model_name)
            logger.info("Embedding model loaded.")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed.\n"
                "Run: pip install sentence-transformers"
            )
    return _model


# ─────────────────────────────────────────────
# Embed a single text
# ─────────────────────────────────────────────

def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """Return embedding vector for a single string."""
    model = get_embedding_model(model_name)
    embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return embedding.tolist()


# ─────────────────────────────────────────────
# Embed a list of chunks (batched for speed)
# ─────────────────────────────────────────────

def embed_chunks(
    chunks: List[TextChunk],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 64,
    show_progress: bool = True,
) -> List[Tuple[TextChunk, List[float]]]:
    """
    Embed all chunks in batches.
    """
    model = get_embedding_model(model_name)

    texts = [chunk.text for chunk in chunks]
    logger.info(f"Embedding {len(texts)} chunks in batches of {batch_size}...")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-normalize → cosine sim = dot product
    )

    logger.info("Embedding complete.")
    return list(zip(chunks, embeddings.tolist()))


# ─────────────────────────────────────────────
# Embed a query string (for retrieval at Q&A time)
# ─────────────────────────────────────────────

def embed_query(query: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """
    Embed a user question for similarity search.
    """
    return embed_text(query, model_name)
