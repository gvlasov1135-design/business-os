import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.audit import service
from modules.audit.schemas import AuditEventRead
from modules.auth.deps import require_roles

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/events", response_model=list[AuditEventRead])
async def list_audit_events(
    company_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> list[AuditEventRead]:
    events = await service.list_audit_events(session, company_id=company_id, limit=limit)
    return [AuditEventRead.model_validate(item) for item in events]
