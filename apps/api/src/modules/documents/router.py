import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles, require_roles_or_worker
from modules.audit.schemas import JobEnqueueResponse
from modules.documents import intelligence_service, service
from modules.documents.intelligence_models import StatementStatus
from modules.documents.intelligence_schemas import (
    DocumentFragmentRead,
    ExtractedStatementRead,
    ExtractionRunResult,
    ManualStatementCreate,
)
from modules.documents.schemas import DocumentRead, DocumentUploadResult
from config.settings import get_settings
from infrastructure.queue import enqueue_extraction

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
statements_router = APIRouter(prefix="/api/v1/statements", tags=["statements"])


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[DocumentRead]:
    documents = await service.list_documents(session, company_id=company_id)
    return [DocumentRead.model_validate(item) for item in documents]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    document = await service.get_document(session, document_id)
    return DocumentRead.model_validate(document)


@router.post("", response_model=DocumentUploadResult, status_code=201)
async def upload_document(
    company_id: uuid.UUID = Form(...),
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> DocumentUploadResult | JSONResponse:
    data = await file.read()
    document, duplicate, existing_id = await service.upload_document(
        session,
        company_id=company_id,
        title=title,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        data=data,
    )
    payload = DocumentUploadResult(
        document=DocumentRead.model_validate(document),
        duplicate=duplicate,
        existing_document_id=existing_id,
    )
    if duplicate:
        return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))
    return payload


@router.post("/{document_id}/versions", response_model=DocumentUploadResult, status_code=201)
async def upload_document_version(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> DocumentUploadResult | JSONResponse:
    data = await file.read()
    document, duplicate, existing_id = await service.add_document_version(
        session,
        document_id=document_id,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        data=data,
    )
    payload = DocumentUploadResult(
        document=DocumentRead.model_validate(document),
        duplicate=duplicate,
        existing_document_id=existing_id,
    )
    if duplicate:
        return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))
    return payload


@router.get("/{document_id}/versions/{version_id}/file")
async def download_document_file(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> Response:
    version, data = await service.get_version_file_bytes(
        session,
        document_id=document_id,
        version_id=version_id,
    )
    return Response(
        content=data,
        media_type=version.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{version.original_filename}"',
        },
    )


@router.post(
    "/{document_id}/versions/{version_id}/extract",
    response_model=ExtractionRunResult,
    status_code=201,
)
async def extract_document_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles_or_worker("admin", "reviewer")),
) -> ExtractionRunResult:
    fragment, statement, statements = await intelligence_service.run_mock_extraction(
        session,
        document_id=document_id,
        version_id=version_id,
    )
    return ExtractionRunResult(
        fragment=DocumentFragmentRead.model_validate(fragment),
        statement=ExtractedStatementRead.model_validate(statement),
        statements=[ExtractedStatementRead.model_validate(item) for item in statements],
    )


@router.post(
    "/{document_id}/versions/{version_id}/extract-async",
    response_model=JobEnqueueResponse,
    status_code=202,
)
async def extract_document_version_async(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> JobEnqueueResponse:
    # Ensure document/version exist before enqueue
    await service.get_version_file_bytes(session, document_id=document_id, version_id=version_id)
    try:
        job_id = enqueue_extraction(
            document_id=str(document_id),
            version_id=str(version_id),
            settings=get_settings(),
        )
    except Exception as exc:  # noqa: BLE001
        from common.errors import AppError

        raise AppError(
            "Failed to enqueue extraction job",
            status_code=503,
            code="queue_unavailable",
        ) from exc
    return JobEnqueueResponse(job_id=job_id, type="extract_document")


@router.get(
    "/{document_id}/versions/{version_id}/fragments",
    response_model=list[DocumentFragmentRead],
)
async def list_document_fragments(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[DocumentFragmentRead]:
    fragments = await intelligence_service.list_fragments(
        session,
        document_id=document_id,
        version_id=version_id,
    )
    return [DocumentFragmentRead.model_validate(item) for item in fragments]


@router.get("/{document_id}/statements", response_model=list[ExtractedStatementRead])
async def list_document_statements(
    document_id: uuid.UUID,
    status: StatementStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[ExtractedStatementRead]:
    statements = await intelligence_service.list_statements(
        session,
        document_id=document_id,
        status=status,
    )
    return [ExtractedStatementRead.model_validate(item) for item in statements]


@router.post(
    "/{document_id}/versions/{version_id}/statements",
    response_model=ExtractedStatementRead,
    status_code=201,
)
async def create_manual_statement(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ManualStatementCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> ExtractedStatementRead:
    statement = await intelligence_service.create_manual_statement(
        session,
        document_id=document_id,
        version_id=version_id,
        payload=payload,
    )
    return ExtractedStatementRead.model_validate(statement)


@statements_router.post("/{statement_id}/confirm", response_model=ExtractedStatementRead)
async def confirm_statement(
    statement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> ExtractedStatementRead:
    statement = await intelligence_service.confirm_statement(session, statement_id)
    return ExtractedStatementRead.model_validate(statement)


@statements_router.post("/{statement_id}/reject", response_model=ExtractedStatementRead)
async def reject_statement(
    statement_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> ExtractedStatementRead:
    statement = await intelligence_service.reject_statement(session, statement_id)
    return ExtractedStatementRead.model_validate(statement)
