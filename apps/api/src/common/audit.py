import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from modules.identity.models import AuditEvent


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        company_id=company_id,
        actor_user_id=actor_user_id,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event
