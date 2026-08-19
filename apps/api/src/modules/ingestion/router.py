import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.ingestion import csv_import, service, workbook_import
from modules.ingestion.schemas import (
    ImportRequest,
    ImportResponse,
    ObservedFactRead,
    RawRecordRead,
    SourceCreate,
    SourceRead,
    SourceStatusUpdate,
    WorkbookImportResponse,
)

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/sources", response_model=SourceRead, status_code=201)
async def create_source(
    payload: SourceCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> SourceRead:
    source = await service.create_source_from_schema(session, payload)
    return SourceRead.model_validate(source)


@router.get("/sources", response_model=list[SourceRead])
async def list_sources(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[SourceRead]:
    sources = await service.list_sources(session, company_id=company_id)
    return [SourceRead.model_validate(item) for item in sources]


@router.post("/sources/{source_id}/status", response_model=SourceRead)
async def update_source_status(
    source_id: uuid.UUID,
    payload: SourceStatusUpdate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> SourceRead:
    source = await service.mark_source_stale(session, source_id, status=payload.status)
    return SourceRead.model_validate(source)


@router.post("/ingestion/import", response_model=ImportResponse)
async def import_record(
    payload: ImportRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> ImportResponse:
    return await service.import_record(session, payload.source_id, payload.payload)


@router.post("/ingestion/import-csv", response_model=list[ImportResponse])
async def import_csv(
    source_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> list[ImportResponse]:
    data = await file.read()
    return await csv_import.import_csv(session, source_id, data)


@router.post("/ingestion/import-workbook", response_model=WorkbookImportResponse)
async def import_workbook(
    company_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> WorkbookImportResponse:
    data = await file.read()
    payload = await workbook_import.import_workbook(
        session,
        company_id=company_id,
        data=data,
        filename=file.filename,
    )
    return WorkbookImportResponse.model_validate(payload)


@router.get("/raw-records/{raw_record_id}", response_model=RawRecordRead)
async def get_raw_record(
    raw_record_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> RawRecordRead:
    record = await service.get_raw_record(session, raw_record_id)
    return RawRecordRead.model_validate(record)


@router.get("/facts/{fact_id}", response_model=ObservedFactRead)
async def get_fact(
    fact_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ObservedFactRead:
    fact = await service.get_fact(session, fact_id)
    return ObservedFactRead.model_validate(fact)


@router.get("/facts", response_model=list[ObservedFactRead])
async def list_facts(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[ObservedFactRead]:
    facts = await service.list_facts(session, company_id=company_id)
    return [ObservedFactRead.model_validate(item) for item in facts]
