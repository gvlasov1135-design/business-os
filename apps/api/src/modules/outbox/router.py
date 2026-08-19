import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles, require_roles_or_worker
from modules.outbox import service
from modules.outbox.models import OutboxStatus
from modules.outbox.schemas import OutboxEventRead

router = APIRouter(prefix="/api/v1/outbox", tags=["outbox"])


@router.get("/events", response_model=list[OutboxEventRead])
async def list_outbox_events(
    company_id: uuid.UUID | None = Query(default=None),
    status: OutboxStatus | None = Query(default=OutboxStatus.pending),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "operator", "reviewer")),
) -> list[OutboxEventRead]:
    rows = await service.list_events(session, company_id=company_id, status=status, limit=limit)
    return [OutboxEventRead.model_validate(item) for item in rows]


@router.post("/events/{event_id}/publish", response_model=OutboxEventRead)
async def publish_outbox_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles_or_worker("admin", "operator")),
) -> OutboxEventRead:
    row = await service.mark_published(session, event_id)
    return OutboxEventRead.model_validate(row)


@router.post("/drain")
async def drain_outbox(
    limit: int = Query(default=20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles_or_worker("admin", "operator")),
) -> dict:
    """Worker/API: опубликовать пачку pending-событий (MVP: mark published)."""
    rows = await service.list_events(
        session, company_id=company_id, status=OutboxStatus.pending, limit=limit
    )
    published: list[str] = []
    for row in rows:
        event = await service.mark_published(session, row.id)
        published.append(str(event.id))
    return {"published": published, "count": len(published)}
