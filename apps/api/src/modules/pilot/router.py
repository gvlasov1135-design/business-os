import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.pilot import service as pilot_service

router = APIRouter(prefix="/api/v1/pilot", tags=["pilot"])


@router.post("/bistro/run")
async def run_bistro_pilot(
    company_id: uuid.UUID | None = Form(default=None),
    company_name: str | None = Form(default=None),
    question: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> dict:
    data = await file.read()
    if not data:
        from common.errors import AppError

        raise AppError("Empty workbook", status_code=400, code="workbook_empty")
    return await pilot_service.run_bistro_pilot(
        session,
        company_id=company_id,
        data=data,
        filename=file.filename,
        question=question,
        company_name=company_name,
    )


@router.post("/reports/run")
async def run_reporting_upload(
    company_id: uuid.UUID | None = Form(default=None),
    company_name: str | None = Form(default=None),
    question: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> dict:
    """Alias for executives: upload reporting → conclusions."""
    data = await file.read()
    if not data:
        from common.errors import AppError

        raise AppError("Empty workbook", status_code=400, code="workbook_empty")
    return await pilot_service.run_bistro_pilot(
        session,
        company_id=company_id,
        data=data,
        filename=file.filename,
        question=question,
        company_name=company_name,
    )


@router.get("/bistro/status")
async def bistro_pilot_hint(
    company_id: uuid.UUID | None = Query(default=None),
) -> dict:
    return {
        "expected_file": "Excel отчётность (листы: финрез, расходы, бар/кухня, аналитика)",
        "origins": ["1c", "rkeeper", "storyhouse"],
        "endpoint": "POST /api/v1/pilot/reports/run",
        "company_id": str(company_id) if company_id else None,
        "note": "Загрузите свою отчётность — получите выводы: что значат цифры, риски и что сделать.",
    }
