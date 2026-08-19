import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import AppError
from modules.outbox.models import OutboxEvent, OutboxStatus


async def enqueue(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    commit: bool = False,
) -> OutboxEvent:
    """Добавить domain event в outbox в текущей транзакции (по умолчанию без commit)."""
    event = OutboxEvent(
        company_id=company_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        status=OutboxStatus.pending,
    )
    session.add(event)
    await session.flush()
    if commit:
        await session.commit()
        await session.refresh(event)
    return event


async def list_events(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    status: OutboxStatus | None = OutboxStatus.pending,
    limit: int = 50,
) -> list[OutboxEvent]:
    stmt = select(OutboxEvent).order_by(OutboxEvent.created_at.asc()).limit(limit)
    if company_id is not None:
        stmt = stmt.where(OutboxEvent.company_id == company_id)
    if status is not None:
        stmt = stmt.where(OutboxEvent.status == status)
    return list((await session.scalars(stmt)).all())


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> OutboxEvent:
    event = await session.get(OutboxEvent, event_id)
    if event is None:
        raise AppError("Outbox event not found", status_code=404, code="outbox_not_found")
    return event


async def mark_published(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> OutboxEvent:
    event = await get_event(session, event_id)
    if event.status == OutboxStatus.published:
        return event
    event.status = OutboxStatus.published
    event.published_at = datetime.now(timezone.utc)
    event.error_message = None
    await session.flush()
    await session.commit()
    await session.refresh(event)
    return event


async def mark_failed(
    session: AsyncSession,
    event_id: uuid.UUID,
    message: str,
) -> OutboxEvent:
    event = await get_event(session, event_id)
    event.status = OutboxStatus.failed
    event.error_message = message[:2000]
    await session.flush()
    await session.commit()
    await session.refresh(event)
    return event
