"""Unit tests for document extraction, hashing, and chunking."""

from __future__ import annotations

import io

import pytest
from app.documents.extractor import (
    DocumentExtractionError,
    chunk_document_text,
    compute_sha256,
    extract_text_from_bytes,
)
from pypdf import PdfWriter


@pytest.mark.unit
def test_sha256_repeatability() -> None:
    data = b"Hello, Shared AI Intelligence!"
    hash1 = compute_sha256(data)
    hash2 = compute_sha256(data)
    assert hash1 == hash2
    assert len(hash1) == 64


@pytest.mark.unit
def test_extract_txt() -> None:
    content = "This is a test document with sufficient text to pass the minimum character threshold easily."
    doc = extract_text_from_bytes("test.txt", content.encode("utf-8"))
    assert doc.filename == "test.txt"
    assert doc.text == content
    assert doc.content_length_chars == len(content)
    assert len(doc.version_hash) == 64


@pytest.mark.unit
def test_extract_markdown() -> None:
    content = "# Research Plan\n\nThis is a markdown document describing the experimental methodology."
    doc = extract_text_from_bytes("plan.md", content.encode("utf-8"))
    assert doc.filename == "plan.md"
    assert "Research Plan" in doc.text


@pytest.mark.unit
def test_extract_pdf_synthetic() -> None:
    # Create a synthetic PDF with text using pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Write synthetic PDF bytes
    buf = io.BytesIO()
    # If blank page has no text, it should raise DocumentExtractionError (scanned/empty PDF)
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    with pytest.raises(DocumentExtractionError) as exc_info:
        extract_text_from_bytes("empty.pdf", pdf_bytes, "application/pdf")
    assert "insufficient text" in str(exc_info.value) or "fewer than" in str(exc_info.value)


@pytest.mark.unit
def test_extract_unsupported_format() -> None:
    with pytest.raises(DocumentExtractionError) as exc:
        extract_text_from_bytes("data.bin", b"some binary data without proper format extension")
    assert "Unsupported file format" in str(exc.value)


@pytest.mark.unit
def test_chunking_boundaries() -> None:
    text = "A" * 1000
    chunks = chunk_document_text(text, chunk_size=300, chunk_overlap=50)

    assert len(chunks) == 4
    assert chunks[0]["chunk_id"] == "c_0"
    assert chunks[0]["start_char"] == 0
    assert chunks[0]["end_char"] == 300

    # Overlap check: second chunk starts at 300 - 50 = 250
    assert chunks[1]["start_char"] == 250
    assert chunks[1]["end_char"] == 550


@pytest.mark.unit
def test_chunking_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        chunk_document_text("test", chunk_size=0)

    with pytest.raises(ValueError):
        chunk_document_text("test", chunk_size=100, chunk_overlap=100)
