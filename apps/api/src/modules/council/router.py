import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.council import service
from modules.council.schemas import (
    CouncilMessageCreate,
    CouncilMessageRead,
    CouncilSessionCreate,
    CouncilSessionRead,
    CouncilSessionSummary,
)

router = APIRouter(prefix="/api/v1/council", tags=["council"])


@router.post("/sessions", response_model=CouncilSessionRead, status_code=201)
async def create_council_session(
    payload: CouncilSessionCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> CouncilSessionRead:
    row = await service.create_session(session, payload)
    messages = await service.list_messages(session, row.id)
    return CouncilSessionRead(
        id=row.id,
        company_id=row.company_id,
        analysis_id=row.analysis_id,
        topic=row.topic,
        status=row.status,
        context_snapshot=row.context_snapshot or {},
        created_at=row.created_at,
        messages=[CouncilMessageRead.model_validate(m) for m in messages],
    )


@router.get("/sessions", response_model=list[CouncilSessionSummary])
async def list_council_sessions(
    company_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> list[CouncilSessionSummary]:
    rows = await service.list_sessions(session, company_id=company_id)
    return [CouncilSessionSummary.model_validate(r) for r in rows]


@router.get("/sessions/{session_id}", response_model=CouncilSessionRead)
async def get_council_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> CouncilSessionRead:
    row = await service.get_session(session, session_id)
    messages = await service.list_messages(session, row.id)
    return CouncilSessionRead(
        id=row.id,
        company_id=row.company_id,
        analysis_id=row.analysis_id,
        topic=row.topic,
        status=row.status,
        context_snapshot=row.context_snapshot or {},
        created_at=row.created_at,
        messages=[CouncilMessageRead.model_validate(m) for m in messages],
    )


@router.post("/sessions/{session_id}/messages", response_model=list[CouncilMessageRead])
async def post_council_message(
    session_id: uuid.UUID,
    payload: CouncilMessageCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> list[CouncilMessageRead]:
    created = await service.post_message(session, session_id, payload)
    return [CouncilMessageRead.model_validate(m) for m in created]


@router.post("/sessions/{session_id}/close", response_model=CouncilSessionRead)
async def close_council_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> CouncilSessionRead:
    row = await service.close_session(session, session_id)
    messages = await service.list_messages(session, row.id)
    return CouncilSessionRead(
        id=row.id,
        company_id=row.company_id,
        analysis_id=row.analysis_id,
        topic=row.topic,
        status=row.status,
        context_snapshot=row.context_snapshot or {},
        created_at=row.created_at,
        messages=[CouncilMessageRead.model_validate(m) for m in messages],
    )
