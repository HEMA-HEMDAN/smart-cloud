"""Document storage and database lifecycle service."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentVersion
from app.documents.extractor import ExtractedDocument

logger = structlog.get_logger(__name__)

DOCUMENTS_STORAGE_DIR = Path(os.environ.get("DOCUMENTS_STORAGE_PATH", "data/documents")).resolve()


def ensure_storage_dir() -> Path:
    """Ensure the documents storage directory exists."""
    DOCUMENTS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return DOCUMENTS_STORAGE_DIR


async def save_document(
    session: AsyncSession,
    extracted: ExtractedDocument,
    raw_data: bytes,
) -> tuple[DocumentVersion, bool]:
    """
    Persist document file to disk and record metadata in PostgreSQL.

    If a DocumentVersion with the same version_hash already exists, returns
    (existing_version, False) without duplicating file storage.
    Otherwise saves file, creates DocumentVersion, and returns (new_version, True).
    """
    storage_dir = ensure_storage_dir()

    # Check for existing version by content hash
    result = await session.execute(
        select(DocumentVersion).where(DocumentVersion.version_hash == extracted.version_hash)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        logger.info(
            "document.version.deduplicated",
            version_hash=extracted.version_hash,
            document_id=existing.document_id,
            id=str(existing.id),
        )
        return existing, False

    # Derive file extension safely
    suffix = Path(extracted.filename).suffix.lower() or ".txt"
    file_path = storage_dir / f"{extracted.version_hash}{suffix}"

    # Save raw bytes if not already present
    if not file_path.exists():
        with open(file_path, "wb") as f:
            f.write(raw_data)

    # Save extracted plain text companion for instant reading without re-parsing
    text_path = storage_dir / f"{extracted.version_hash}.txt"
    if not text_path.exists():
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(extracted.text)

    # Clean document identifier
    doc_id = Path(extracted.filename).stem.replace(" ", "_")

    doc_version = DocumentVersion(
        document_id=doc_id,
        version_hash=extracted.version_hash,
        title=extracted.filename,
        source_path=str(file_path),
        content_length_chars=extracted.content_length_chars,
    )
    session.add(doc_version)
    await session.commit()
    await session.refresh(doc_version)

    logger.info(
        "document.version.saved",
        id=str(doc_version.id),
        document_id=doc_version.document_id,
        version_hash=doc_version.version_hash,
        chars=doc_version.content_length_chars,
    )
    return doc_version, True


async def get_document_text(doc_version: DocumentVersion) -> str:
    """Retrieve the plain extracted text of a stored document version."""
    storage_dir = ensure_storage_dir()
    text_path = storage_dir / f"{doc_version.version_hash}.txt"

    if text_path.exists():
        with open(text_path, encoding="utf-8") as f:
            return f.read()

    # Fallback to source_path if companion text file missing
    if doc_version.source_path and Path(doc_version.source_path).exists():
        with open(doc_version.source_path, "rb") as f:
            raw = f.read()
        from app.documents.extractor import extract_text_from_bytes
        extracted = extract_text_from_bytes(doc_version.title or "doc", raw)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(extracted.text)
        return extracted.text

    raise FileNotFoundError(
        f"Document content for version {doc_version.version_hash} not found on disk."
    )


async def list_document_versions(session: AsyncSession) -> list[DocumentVersion]:
    """List all registered document versions ordered by creation date desc."""
    result = await session.execute(
        select(DocumentVersion).order_by(DocumentVersion.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document_version(
    session: AsyncSession, doc_version_id: uuid.UUID
) -> DocumentVersion | None:
    """Get single document version by UUID."""
    return await session.get(DocumentVersion, doc_version_id)
