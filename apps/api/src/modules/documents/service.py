import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.audit import write_audit
from common.errors import AppError
from infrastructure.storage import get_storage, sha256_hex, validate_upload
from modules.documents.models import Document, DocumentFile, DocumentStatus, DocumentVersion
from modules.identity.models import Company


async def _require_company(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await session.get(Company, company_id)
    if not company:
        raise AppError("Company not found", status_code=404, code="company_not_found")
    return company


async def _load_document(session: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await session.scalar(
        select(Document)
        .options(
            selectinload(Document.versions).selectinload(DocumentVersion.file),
        )
        .where(Document.id == document_id)
        .execution_options(populate_existing=True)
    )
    if not document:
        raise AppError("Document not found", status_code=404, code="document_not_found")
    return document


async def list_documents(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
) -> list[Document]:
    stmt = (
        select(Document)
        .options(selectinload(Document.versions).selectinload(DocumentVersion.file))
        .order_by(Document.created_at.desc())
    )
    if company_id is not None:
        stmt = stmt.where(Document.company_id == company_id)
    result = await session.scalars(stmt)
    return list(result.all())


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> Document:
    return await _load_document(session, document_id)


async def upload_document(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    title: str | None,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> tuple[Document, bool, uuid.UUID | None]:
    await _require_company(session, company_id)
    if not data:
        raise AppError("Empty file", status_code=400, code="empty_file")

    mime, _ext = validate_upload(filename, content_type)
    checksum = sha256_hex(data)

    existing_file = await session.scalar(
        select(DocumentFile).where(
            DocumentFile.company_id == company_id,
            DocumentFile.checksum_sha256 == checksum,
        )
    )
    if existing_file:
        existing_version = await session.get(DocumentVersion, existing_file.version_id)
        if existing_version is None:
            raise AppError("Corrupt duplicate reference", status_code=500, code="duplicate_corrupt")
        existing_document = await _load_document(session, existing_version.document_id)
        await write_audit(
            session,
            action="document.duplicate_detected",
            entity_type="document",
            entity_id=existing_document.id,
            company_id=company_id,
            payload={"checksum_sha256": checksum, "filename": filename},
        )
        await session.commit()
        reloaded = await _load_document(session, existing_document.id)
        return reloaded, True, existing_document.id

    document = Document(
        company_id=company_id,
        title=title or Path(filename).stem,
        status=DocumentStatus.uploaded,
    )
    session.add(document)
    await session.flush()

    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        original_filename=filename,
        content_type=mime,
    )
    session.add(version)
    await session.flush()

    storage_key = f"companies/{company_id}/documents/{document.id}/v{version.version_number}/{filename}"
    storage = get_storage()
    storage.put_bytes(storage_key, data, mime)

    file_row = DocumentFile(
        version_id=version.id,
        company_id=company_id,
        storage_key=storage_key,
        checksum_sha256=checksum,
        size_bytes=len(data),
    )
    session.add(file_row)
    document.status = DocumentStatus.stored

    await write_audit(
        session,
        action="document.uploaded",
        entity_type="document",
        entity_id=document.id,
        company_id=company_id,
        payload={
            "filename": filename,
            "checksum_sha256": checksum,
            "size_bytes": len(data),
            "version_number": 1,
        },
    )
    await session.commit()
    loaded = await _load_document(session, document.id)
    return loaded, False, None


async def add_document_version(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> tuple[Document, bool, uuid.UUID | None]:
    document = await _load_document(session, document_id)
    if not data:
        raise AppError("Empty file", status_code=400, code="empty_file")

    mime, _ext = validate_upload(filename, content_type)
    checksum = sha256_hex(data)

    existing_file = await session.scalar(
        select(DocumentFile).where(
            DocumentFile.company_id == document.company_id,
            DocumentFile.checksum_sha256 == checksum,
        )
    )
    if existing_file:
        existing_version = await session.get(DocumentVersion, existing_file.version_id)
        if existing_version is None:
            raise AppError("Corrupt duplicate reference", status_code=500, code="duplicate_corrupt")
        existing_document = await _load_document(session, existing_version.document_id)
        await write_audit(
            session,
            action="document.duplicate_detected",
            entity_type="document",
            entity_id=existing_document.id,
            company_id=document.company_id,
            payload={"checksum_sha256": checksum, "filename": filename, "source_document_id": str(document_id)},
        )
        await session.commit()
        return existing_document, True, existing_document.id

    next_number = await session.scalar(
        select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
            DocumentVersion.document_id == document_id
        )
    )
    version_number = int(next_number or 0) + 1

    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        original_filename=filename,
        content_type=mime,
    )
    session.add(version)
    await session.flush()

    storage_key = (
        f"companies/{document.company_id}/documents/{document.id}/v{version_number}/{filename}"
    )
    storage = get_storage()
    storage.put_bytes(storage_key, data, mime)

    file_row = DocumentFile(
        version_id=version.id,
        company_id=document.company_id,
        storage_key=storage_key,
        checksum_sha256=checksum,
        size_bytes=len(data),
    )
    session.add(file_row)
    document.status = DocumentStatus.stored

    await write_audit(
        session,
        action="document.version_uploaded",
        entity_type="document",
        entity_id=document.id,
        company_id=document.company_id,
        payload={
            "filename": filename,
            "checksum_sha256": checksum,
            "size_bytes": len(data),
            "version_number": version_number,
        },
    )
    await session.commit()
    loaded = await _load_document(session, document.id)
    return loaded, False, None


async def get_version_file_bytes(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> tuple[DocumentVersion, bytes]:
    document = await _load_document(session, document_id)
    version = next((item for item in document.versions if item.id == version_id), None)
    if version is None or version.file is None:
        raise AppError("Document version not found", status_code=404, code="version_not_found")

    storage = get_storage()
    data = storage.get_bytes(version.file.storage_key)
    await write_audit(
        session,
        action="document.file_downloaded",
        entity_type="document",
        entity_id=document.id,
        company_id=document.company_id,
        payload={"version_id": str(version_id)},
    )
    await session.commit()
    return version, data
