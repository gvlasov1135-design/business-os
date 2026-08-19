import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.executive import service
from modules.executive.schemas import ExecutiveReadinessResponse

router = APIRouter(prefix="/api/v1/executive", tags=["executive"])


@router.get("/readiness", response_model=ExecutiveReadinessResponse)
async def get_executive_readiness(
    company_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
) -> ExecutiveReadinessResponse:
    return await service.build_readiness(session, company_id)
