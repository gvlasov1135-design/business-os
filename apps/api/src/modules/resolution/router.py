import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.resolution import service
from modules.resolution.models import CandidateStatus
from modules.resolution.schemas import (
    CanonicalEntityRead,
    ConfirmCandidateRequest,
    EntityMatchCandidateRead,
    EntityMembershipRead,
    EntityMergeEventRead,
    ResolveRawRecordResponse,
    SplitMembershipRequest,
)

router = APIRouter(prefix="/api/v1/resolution", tags=["resolution"])


@router.get("/entities", response_model=list[CanonicalEntityRead])
async def list_entities(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[CanonicalEntityRead]:
    rows = await service.list_entities(session, company_id=company_id)
    return [CanonicalEntityRead.model_validate(item) for item in rows]


@router.get("/entities/{entity_id}", response_model=CanonicalEntityRead)
async def get_entity(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> CanonicalEntityRead:
    entity = await service.get_entity(session, entity_id)
    return CanonicalEntityRead.model_validate(entity)


@router.get("/entities/{entity_id}/memberships", response_model=list[EntityMembershipRead])
async def list_entity_memberships(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[EntityMembershipRead]:
    rows = await service.list_memberships(session, entity_id=entity_id)
    return [EntityMembershipRead.model_validate(item) for item in rows]


@router.get("/candidates", response_model=list[EntityMatchCandidateRead])
async def list_candidates(
    company_id: uuid.UUID | None = Query(default=None),
    status: CandidateStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[EntityMatchCandidateRead]:
    rows = await service.list_candidates(session, company_id=company_id, status=status)
    return [EntityMatchCandidateRead.model_validate(item) for item in rows]


@router.post("/candidates/{candidate_id}/confirm", response_model=EntityMatchCandidateRead)
async def confirm_candidate(
    candidate_id: uuid.UUID,
    payload: ConfirmCandidateRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> EntityMatchCandidateRead:
    note = payload.note if payload else None
    row = await service.confirm_candidate(session, candidate_id, note=note)
    return EntityMatchCandidateRead.model_validate(row)


@router.post("/candidates/{candidate_id}/reject", response_model=EntityMatchCandidateRead)
async def reject_candidate(
    candidate_id: uuid.UUID,
    payload: ConfirmCandidateRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> EntityMatchCandidateRead:
    note = payload.note if payload else None
    row = await service.reject_candidate(session, candidate_id, note=note)
    return EntityMatchCandidateRead.model_validate(row)


@router.post("/memberships/{membership_id}/split", response_model=CanonicalEntityRead)
async def split_membership(
    membership_id: uuid.UUID,
    payload: SplitMembershipRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> CanonicalEntityRead:
    note = payload.note if payload else None
    entity = await service.split_membership(session, membership_id, note=note)
    return CanonicalEntityRead.model_validate(entity)


@router.get("/merges", response_model=list[EntityMergeEventRead])
async def list_merges(
    company_id: uuid.UUID | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[EntityMergeEventRead]:
    rows = await service.list_merge_events(session, company_id=company_id, entity_id=entity_id)
    return [EntityMergeEventRead.model_validate(item) for item in rows]


@router.post("/raw-records/{raw_record_id}/resolve", response_model=ResolveRawRecordResponse)
async def resolve_raw_record(
    raw_record_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "operator")),
) -> ResolveRawRecordResponse:
    from modules.ingestion import service as ingestion_service

    raw = await ingestion_service.get_raw_record(session, raw_record_id)
    return await service.resolve_raw_record(session, raw, commit=True)


@router.post("/scan")
async def scan_company(
    company_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> dict:
    return await service.scan_company(session, company_id)
