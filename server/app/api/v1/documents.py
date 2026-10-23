"""Documents API router for uploading, listing, and previewing document chunks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.documents.extractor import (
    DocumentExtractionError,
    chunk_document_text,
    extract_text_from_bytes,
)
from app.documents.service import (
    get_document_text,
    get_document_version,
    list_document_versions,
    save_document,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: str
    version_hash: str
    title: str | None
    content_length_chars: int | None
    created_at: datetime


class DocumentPreviewOut(BaseModel):
    id: uuid.UUID
    document_id: str
    version_hash: str
    title: str | None
    content_length_chars: int
    text_preview: str
    chunk_size: int
    chunk_overlap: int
    total_chunks: int
    chunks: list[dict[str, Any]]


@router.post(
    "/upload",
    response_model=DocumentVersionOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
) -> DocumentVersionOut:
    """
    Upload a document (.pdf, .txt, .md), validate, extract text, hash, and persist.

    Rejects files > 10MB or scanned PDFs lacking extractable text with HTTP 422.
    Deduplicates identical files based on SHA-256 hash.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        ) from exc

    try:
        extracted = extract_text_from_bytes(
            filename=file.filename,
            data=content,
            content_type=file.content_type,
        )
    except DocumentExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    doc_version, is_new = await save_document(session, extracted, content)
    logger.info(
        "document.upload.processed",
        id=str(doc_version.id),
        filename=file.filename,
        is_new=is_new,
        chars=doc_version.content_length_chars,
    )
    return DocumentVersionOut.model_validate(doc_version)


@router.get("", response_model=list[DocumentVersionOut])
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> list[DocumentVersionOut]:
    """List all registered document versions."""
    versions = await list_document_versions(session)
    return [DocumentVersionOut.model_validate(v) for v in versions]


@router.get("/{document_id}", response_model=DocumentVersionOut)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DocumentVersionOut:
    """Retrieve document version metadata."""
    doc = await get_document_version(session, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document version {document_id} not found",
        )
    return DocumentVersionOut.model_validate(doc)


@router.get("/{document_id}/preview", response_model=DocumentPreviewOut)
async def preview_document_chunks(
    document_id: uuid.UUID,
    chunk_size: int = Query(default=512, ge=100, le=4000),
    chunk_overlap: int = Query(default=64, ge=0, le=1000),
    session: AsyncSession = Depends(get_session),
) -> DocumentPreviewOut:
    """
    Preview extracted text and derived chunks using configured chunk parameters.

    Returns the chunk list with positional offsets and text for benchmark definition.
    """
    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_overlap must be less than chunk_size",
        )

    doc = await get_document_version(session, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document version {document_id} not found",
        )

    try:
        text = await get_document_text(doc)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    chunks = chunk_document_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    preview_slice = text[:1500] + ("..." if len(text) > 1500 else "")

    return DocumentPreviewOut(
        id=doc.id,
        document_id=doc.document_id,
        version_hash=doc.version_hash,
        title=doc.title,
        content_length_chars=len(text),
        text_preview=preview_slice,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        total_chunks=len(chunks),
        chunks=chunks,
    )
