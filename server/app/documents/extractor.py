"""Document text extraction and content hashing utilities.

Supports UTF-8 text (.txt), Markdown (.md), and text-extractable PDF (.pdf).
Scanned or image-only PDFs are explicitly rejected with a clear error
as OCR is not supported in this milestone.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Any

from pypdf import PdfReader

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB default limit
MIN_EXTRACTED_CHARS = 20


@dataclass
class ExtractedDocument:
    filename: str
    content_type: str
    version_hash: str
    text: str
    content_length_chars: int
    page_count: int | None = None


class DocumentExtractionError(Exception):
    """Raised when document extraction fails due to format, encoding, or OCR limitations."""


def compute_sha256(data: bytes) -> str:
    """Compute the hexadecimal SHA-256 digest of raw file bytes."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


def extract_text_from_bytes(
    filename: str,
    data: bytes,
    content_type: str | None = None,
) -> ExtractedDocument:
    """
    Extract plain text from uploaded document bytes and compute content hash.

    Raises DocumentExtractionError if the document cannot be read or yields
    insufficient text (e.g. scanned image-only PDF).
    """
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise DocumentExtractionError(
            f"File size ({len(data)} bytes) exceeds limit of {MAX_FILE_SIZE_BYTES} bytes."
        )

    version_hash = compute_sha256(data)
    lower_name = filename.lower()
    page_count: int | None = None

    if lower_name.endswith(".pdf") or content_type == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            page_count = len(reader.pages)
            extracted_pages: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                extracted_pages.append(page_text.strip())
            full_text = "\n\n".join(filter(bool, extracted_pages))
        except Exception as exc:
            raise DocumentExtractionError(f"Failed to parse PDF file '{filename}': {exc}") from exc

        if len(full_text.strip()) < MIN_EXTRACTED_CHARS:
            raise DocumentExtractionError(
                f"PDF '{filename}' yielded fewer than {MIN_EXTRACTED_CHARS} text characters. "
                "The file may be a scanned image or empty. OCR is not supported; "
                "please upload a text-searchable PDF, .txt, or .md file."
            )

    elif lower_name.endswith((".txt", ".md", ".markdown")) or (
        content_type and "text" in content_type
    ):
        try:
            full_text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                full_text = data.decode("latin-1")
            except Exception as exc:
                raise DocumentExtractionError(
                    f"Failed to decode text file '{filename}' with UTF-8 or Latin-1: {exc}"
                ) from exc

        if len(full_text.strip()) < MIN_EXTRACTED_CHARS:
            chars_len = len(full_text.strip())
            raise DocumentExtractionError(
                f"Text file '{filename}' has insufficient text ({chars_len} chars)."
            )
    else:
        raise DocumentExtractionError(
            f"Unsupported file format for '{filename}'. Supported formats: .pdf, .txt, .md."
        )

    return ExtractedDocument(
        filename=filename,
        content_type=content_type or "application/octet-stream",
        version_hash=version_hash,
        text=full_text,
        content_length_chars=len(full_text),
        page_count=page_count,
    )


def chunk_document_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict[str, Any]]:
    """
    Produce deterministic text chunks with positional metadata and stable chunk IDs.

    Each chunk has:
      - chunk_id: c_{index}
      - chunk_index: integer index
      - start_char: character offset start
      - end_char: character offset end
      - text: chunk text
      - token_estimate: approximate token count (chars // 4)
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    chunks: list[dict[str, Any]] = []
    start = 0
    total_len = len(text)
    step = chunk_size - chunk_overlap
    idx = 0

    while start < total_len:
        end = min(start + chunk_size, total_len)
        chunk_text = text[start:end]
        chunks.append(
            {
                "chunk_id": f"c_{idx}",
                "chunk_index": idx,
                "start_char": start,
                "end_char": end,
                "text": chunk_text,
                "token_estimate": max(1, len(chunk_text) // 4),
            }
        )
        idx += 1
        start += step

    return chunks
