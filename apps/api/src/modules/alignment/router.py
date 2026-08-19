import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.alignment import service
from modules.alignment.models import AlignmentIssueStatus
from modules.alignment.schemas import (
    AlignmentCheckRead,
    AlignmentCheckRequest,
    AlignmentCheckResponse,
    AlignmentIssueRead,
)
from modules.auth.deps import require_roles

router = APIRouter(prefix="/api/v1/alignment", tags=["alignment"])


@router.post("/checks", response_model=AlignmentCheckResponse, status_code=201)
async def create_alignment_check(
    payload: AlignmentCheckRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> AlignmentCheckResponse:
    if payload.check_type == "responsible":
        issue = await service.run_responsible_actor_check(
            session,
            company_id=payload.company_id,
            statement_id=payload.statement_id,
            fact_id=payload.fact_id,
        )
    elif payload.check_type == "process_stage":
        issue = await service.run_process_stage_check(
            session,
            company_id=payload.company_id,
            statement_id=payload.statement_id,
            fact_id=payload.fact_id,
        )
    else:
        issue = await service.run_lead_deadline_check(
            session,
            company_id=payload.company_id,
            statement_id=payload.statement_id,
            fact_id=payload.fact_id,
        )
    check = await service.get_check(session, issue.check_id)
    return AlignmentCheckResponse(
        check=AlignmentCheckRead.model_validate(check),
        issue=AlignmentIssueRead.model_validate(issue),
    )


@router.get("/issues", response_model=list[AlignmentIssueRead])
async def list_alignment_issues(
    company_id: uuid.UUID = Query(...),
    status: AlignmentIssueStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[AlignmentIssueRead]:
    issues = await service.list_issues(session, company_id=company_id, status=status)
    return [AlignmentIssueRead.model_validate(item) for item in issues]


@router.get("/issues/{issue_id}", response_model=AlignmentIssueRead)
async def get_alignment_issue(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> AlignmentIssueRead:
    issue = await service.get_issue(session, issue_id)
    return AlignmentIssueRead.model_validate(issue)


@router.post("/issues/{issue_id}/confirm", response_model=AlignmentIssueRead)
async def confirm_alignment_issue(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> AlignmentIssueRead:
    issue = await service.confirm_issue(session, issue_id)
    return AlignmentIssueRead.model_validate(issue)


@router.post("/issues/{issue_id}/reject", response_model=AlignmentIssueRead)
async def reject_alignment_issue(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> AlignmentIssueRead:
    issue = await service.reject_issue(session, issue_id)
    return AlignmentIssueRead.model_validate(issue)


@router.post("/issues/{issue_id}/accept-deviation", response_model=AlignmentIssueRead)
async def accept_alignment_deviation(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive")),
) -> AlignmentIssueRead:
    issue = await service.accept_deviation(session, issue_id)
    return AlignmentIssueRead.model_validate(issue)


@router.post("/issues/{issue_id}/request-data", response_model=AlignmentIssueRead)
async def request_alignment_data(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> AlignmentIssueRead:
    issue = await service.request_data(session, issue_id)
    return AlignmentIssueRead.model_validate(issue)


@router.post("/issues/{issue_id}/apply-proposed-change", response_model=AlignmentIssueRead)
async def apply_alignment_proposed_change(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive")),
) -> AlignmentIssueRead:
    issue = await service.apply_proposed_change(session, issue_id)
    return AlignmentIssueRead.model_validate(issue)
