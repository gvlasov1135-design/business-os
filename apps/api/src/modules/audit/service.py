import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.identity.models import AuditEvent


async def list_audit_events(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(max(limit, 1), 200))
    if company_id is not None:
        stmt = stmt.where(AuditEvent.company_id == company_id)
    result = await session.scalars(stmt)
    return list(result.all())
