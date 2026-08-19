import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from infrastructure.storage import get_storage
from modules.documents.extraction import build_mock_extraction
from modules.documents.intelligence_models import (
    DocumentFragment,
    ExtractedStatement,
    FragmentType,
    StatementStatus,
    StatementType,
)
from modules.documents.intelligence_schemas import ManualStatementCreate
from modules.documents.models import Document, DocumentVersion
from modules.documents.service import _load_document


async def _get_version(
    session: AsyncSession,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> tuple[Document, DocumentVersion]:
    document = await _load_document(session, document_id)
    version = next((item for item in document.versions if item.id == version_id), None)
    if version is None or version.file is None:
        raise AppError("Document version not found", status_code=404, code="version_not_found")
    return document, version


def _primary_statement(statements: list[ExtractedStatement]) -> ExtractedStatement:
    for item in statements:
        if item.statement_type == StatementType.deadline:
            return item
    return statements[0]


async def run_mock_extraction(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> tuple[DocumentFragment, ExtractedStatement, list[ExtractedStatement]]:
    document, version = await _get_version(session, document_id, version_id)

    existing = list(
        (
            await session.scalars(
                select(ExtractedStatement)
                .where(ExtractedStatement.version_id == version_id)
                .order_by(ExtractedStatement.created_at)
            )
        ).all()
    )
    if existing:
        fragment = await session.get(DocumentFragment, existing[0].fragment_id)
        if fragment is None:
            raise AppError("Fragment missing for statement", status_code=500, code="fragment_missing")
        return fragment, _primary_statement(existing), existing

    file_bytes = get_storage().get_bytes(version.file.storage_key)
    mock = build_mock_extraction(file_bytes)

    fragment = DocumentFragment(
        version_id=version.id,
        ordinal=1,
        fragment_type=FragmentType.paragraph,
        text=mock.fragment_text,
        page_number=1,
        char_start=0,
        char_end=len(mock.fragment_text),
    )
    session.add(fragment)
    await session.flush()

    created: list[ExtractedStatement] = []
    for item in mock.statements:
        statement = ExtractedStatement(
            document_id=document.id,
            version_id=version.id,
            fragment_id=fragment.id,
            statement_type=StatementType(item.statement_type),
            value_text=item.statement_text,
            value_structured=item.statement_value,
            confidence=item.confidence,
            status=StatementStatus.proposed,
            source_anchor={
                "fragment_id": str(fragment.id),
                "quote": item.statement_text,
                "char_start": item.char_start,
                "char_end": item.char_end,
                "page_number": 1,
            },
        )
        session.add(statement)
        created.append(statement)

    await session.flush()
    primary = _primary_statement(created)
    await write_audit(
        session,
        action="document.extraction_completed",
        entity_type="document",
        entity_id=document.id,
        company_id=document.company_id,
        payload={
            "version_id": str(version.id),
            "statement_count": len(created),
            "statement_types": [item.statement_type.value for item in created],
            "primary_statement_id": str(primary.id),
        },
    )
    await session.commit()
    await session.refresh(fragment)
    for item in created:
        await session.refresh(item)
    return fragment, primary, created


async def list_fragments(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
) -> list[DocumentFragment]:
    await _get_version(session, document_id, version_id)
    result = await session.scalars(
        select(DocumentFragment)
        .where(DocumentFragment.version_id == version_id)
        .order_by(DocumentFragment.ordinal)
    )
    return list(result.all())


async def list_statements(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    status: StatementStatus | None = None,
) -> list[ExtractedStatement]:
    await _load_document(session, document_id)
    stmt = select(ExtractedStatement).where(ExtractedStatement.document_id == document_id)
    if status is not None:
        stmt = stmt.where(ExtractedStatement.status == status)
    stmt = stmt.order_by(ExtractedStatement.created_at)
    result = await session.scalars(stmt)
    return list(result.all())


async def create_manual_statement(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ManualStatementCreate,
) -> ExtractedStatement:
    document, version = await _get_version(session, document_id, version_id)
    fragment = await session.get(DocumentFragment, payload.fragment_id)
    if fragment is None or fragment.version_id != version.id:
        raise AppError("Fragment not found for version", status_code=404, code="fragment_not_found")

    statement = ExtractedStatement(
        document_id=document.id,
        version_id=version.id,
        fragment_id=fragment.id,
        statement_type=payload.statement_type,
        value_text=payload.value_text,
        value_structured=payload.value_structured,
        confidence=payload.confidence,
        status=StatementStatus.proposed,
        source_anchor={
            "fragment_id": str(fragment.id),
            "quote": payload.quote or payload.value_text,
            "char_start": payload.char_start,
            "char_end": payload.char_end,
            "page_number": fragment.page_number,
        },
    )
    session.add(statement)
    await write_audit(
        session,
        action="document.statement_created",
        entity_type="extracted_statement",
        entity_id=statement.id,
        company_id=document.company_id,
        payload={"statement_type": statement.statement_type.value},
    )
    await session.commit()
    await session.refresh(statement)
    return statement


async def confirm_statement(session: AsyncSession, statement_id: uuid.UUID) -> ExtractedStatement:
    statement = await session.get(ExtractedStatement, statement_id)
    if statement is None:
        raise AppError("Statement not found", status_code=404, code="statement_not_found")
    if statement.status != StatementStatus.proposed:
        raise AppError(
            "Only proposed statements can be confirmed",
            status_code=409,
            code="statement_not_proposed",
        )
    statement.status = StatementStatus.confirmed
    statement.reviewed_at = datetime.now(UTC)
    document = await session.get(Document, statement.document_id)
    await write_audit(
        session,
        action="document.statement_confirmed",
        entity_type="extracted_statement",
        entity_id=statement.id,
        company_id=document.company_id if document else None,
        payload={},
    )
    await session.commit()
    await session.refresh(statement)
    return statement


async def reject_statement(session: AsyncSession, statement_id: uuid.UUID) -> ExtractedStatement:
    statement = await session.get(ExtractedStatement, statement_id)
    if statement is None:
        raise AppError("Statement not found", status_code=404, code="statement_not_found")
    if statement.status != StatementStatus.proposed:
        raise AppError(
            "Only proposed statements can be rejected",
            status_code=409,
            code="statement_not_proposed",
        )
    statement.status = StatementStatus.rejected
    statement.reviewed_at = datetime.now(UTC)
    document = await session.get(Document, statement.document_id)
    await write_audit(
        session,
        action="document.statement_rejected",
        entity_type="extracted_statement",
        entity_id=statement.id,
        company_id=document.company_id if document else None,
        payload={},
    )
    await session.commit()
    await session.refresh(statement)
    return statement
