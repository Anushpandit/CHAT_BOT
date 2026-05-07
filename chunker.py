import re
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────
# Chunk data class
# ─────────────────────────────────────────────

@dataclass
class TextChunk:
    chunk_id: str           # unique id e.g. "report.pdf_chunk_003"
    file_name: str          # source file
    file_type: str          # pdf / text / docx / spreadsheet / image
    text: str               # chunk content
    chunk_index: int        # position in file
    total_chunks: int = 0   # filled after all chunks are created
    metadata: dict = field(default_factory=dict)


# ─────────────────────────────────────────────
# Core chunking helpers
# ─────────────────────────────────────────────

def _split_by_tokens_approx(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into chunks of ~chunk_size words with overlap.
    Word-count is a close proxy for tokens (1 token ≈ 0.75 words).
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap          # slide forward by (size - overlap)

    return [c.strip() for c in chunks if c.strip()]


def _split_by_paragraphs(text: str, max_words: int = 400) -> List[str]:
    """
    Split on double newlines (paragraphs). Merge short paragraphs,
    split long ones so no chunk exceeds max_words.
    """
    raw_paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    buffer = []
    buffer_len = 0

    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())

        # Para fits in buffer
        if buffer_len + para_words <= max_words:
            buffer.append(para)
            buffer_len += para_words
        else:
            # Flush buffer
            if buffer:
                chunks.append("\n\n".join(buffer))
            # If this single para is too big, hard-split it
            if para_words > max_words:
                sub = _split_by_tokens_approx(para, max_words, overlap=50)
                chunks.extend(sub)
                buffer, buffer_len = [], 0
            else:
                buffer = [para]
                buffer_len = para_words

    if buffer:
        chunks.append("\n\n".join(buffer))

    return [c.strip() for c in chunks if c.strip()]


def _split_spreadsheet(text: str, rows_per_chunk: int = 50) -> List[str]:
    """
    Split spreadsheet text (one row per line) into fixed-row chunks.
    Keeps the header row in every chunk.
    """
    lines = text.strip().splitlines()
    if not lines:
        return []

    # Detect header lines (sheet labels or column headers)
    header = lines[0]
    data_lines = lines[1:]

    chunks = []
    for i in range(0, len(data_lines), rows_per_chunk):
        batch = data_lines[i : i + rows_per_chunk]
        chunks.append(header + "\n" + "\n".join(batch))

    return [c.strip() for c in chunks if c.strip()]


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

import hashlib

def chunk_content(
    file_name: str,
    file_type: str,
    text: str,
    chunk_size: int = 400,      # words per chunk  (~500 tokens)
    overlap: int = 80,          # word overlap between consecutive chunks
    rows_per_chunk: int = 50,   # for spreadsheets only
) -> List[TextChunk]:
    """
    Chunk extracted text into overlapping segments.
    """
    if not text or not text.strip():
        return []

    # Choose strategy
    if file_type == "spreadsheet":
        raw_chunks = _split_spreadsheet(text, rows_per_chunk=rows_per_chunk)
    elif file_type in ("pdf", "docx", "gdoc"):
        raw_chunks = _split_by_paragraphs(text, max_words=chunk_size)
    else:
        # text, image descriptions, unknown
        raw_chunks = _split_by_tokens_approx(text, chunk_size, overlap)

    # Build TextChunk objects
    result: List[TextChunk] = []
    total = len(raw_chunks)
    
    # Hash the text to ensure uniqueness if multiple files have the same name
    file_hash = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()[:6]

    for idx, chunk_text in enumerate(raw_chunks):
        chunk_id = f"{file_name}_{file_hash}_chunk_{idx:04d}"
        result.append(
            TextChunk(
                chunk_id=chunk_id,
                file_name=file_name,
                file_type=file_type,
                text=chunk_text,
                chunk_index=idx,
                total_chunks=total,
                metadata={
                    "source": file_name,
                    "file_type": file_type,
                    "chunk_index": idx,
                    "total_chunks": total,
                },
            )
        )

    return result


def chunk_all_files(
    extracted_contents,          # List[ExtractedContent] from Phase 2
    chunk_size: int = 400,
    overlap: int = 80,
) -> List[TextChunk]:
    """
    Chunk all extracted files and return a flat list of TextChunk objects.
    extracted_contents: list of ExtractedContent from Phase 2.
    """
    all_chunks: List[TextChunk] = []

    for content in extracted_contents:
        if content.error or not content.text.strip():
            continue

        chunks = chunk_content(
            file_name=content.file_name,
            file_type=content.file_type,
            text=content.text,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        all_chunks.extend(chunks)
        print(f"  ✓ {content.file_name} → {len(chunks)} chunks")

    print(f"\nTotal chunks produced: {len(all_chunks)}")
    return all_chunks
