import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.quality import service
from modules.quality.models import IssueStatus
from modules.quality.schemas import (
    AnalysisGateResponse,
    DataDoctorExplanation,
    DataQualityIssueRead,
    ResolveIssueRequest,
    ResolveIssueResponse,
)

router = APIRouter(prefix="/api/v1", tags=["quality"])


@router.get("/data-quality/issues", response_model=list[DataQualityIssueRead])
async def list_data_quality_issues(
    company_id: uuid.UUID | None = Query(default=None),
    status: IssueStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[DataQualityIssueRead]:
    issues = await service.list_issues(session, company_id=company_id, status=status)
    return [DataQualityIssueRead.model_validate(item) for item in issues]


@router.get("/data-quality/gate", response_model=AnalysisGateResponse)
async def get_analysis_gate(
    company_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> AnalysisGateResponse:
    return await service.evaluate_analysis_gate(session, company_id)


@router.post(
    "/data-quality/issues/{issue_id}/explain",
    response_model=DataDoctorExplanation,
)
async def explain_data_quality_issue(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> DataDoctorExplanation:
    payload = await service.explain_issue(session, issue_id)
    return DataDoctorExplanation.model_validate(payload)


@router.post(
    "/data-quality/issues/{issue_id}/resolve",
    response_model=ResolveIssueResponse,
)
async def resolve_data_quality_issue(
    issue_id: uuid.UUID,
    payload: ResolveIssueRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> ResolveIssueResponse:
    issue = await service.resolve_issue(session, issue_id, reason=payload.reason)
    return ResolveIssueResponse(
        **DataQualityIssueRead.model_validate(issue).model_dump(),
        resolution_reason=payload.reason.strip(),
    )
