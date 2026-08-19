from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.demo import service
from modules.demo.schemas import DemoRunRequest, DemoRunResponse

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/run", response_model=DemoRunResponse)
async def run_demo(
    payload: DemoRunRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin")),
) -> DemoRunResponse:
    body = payload or DemoRunRequest()
    return await service.run_demo(session, company_id=body.company_id)
