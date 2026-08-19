import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.kpi import service
from modules.kpi.schemas import (
    KpiCreate,
    KpiDefinitionRead,
    KpiRecalculateRequest,
    KpiSnapshotRead,
    KpiVersionCreate,
    KpiVersionRead,
)

router = APIRouter(prefix="/api/v1/kpis", tags=["kpi"])


@router.get("", response_model=list[KpiDefinitionRead])
async def list_kpis(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[KpiDefinitionRead]:
    rows = await service.list_kpis(session, company_id=company_id)
    return [KpiDefinitionRead.model_validate(item) for item in rows]


@router.post("", response_model=KpiDefinitionRead, status_code=201)
async def create_kpi(
    payload: KpiCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> KpiDefinitionRead:
    kpi = await service.create_kpi(
        session,
        company_id=payload.company_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        unit=payload.unit,
        owner_name=payload.owner_name,
        formula=payload.formula,
        source_mapping=payload.source_mapping,
        target_value=payload.target_value,
        activate=payload.activate,
    )
    return KpiDefinitionRead.model_validate(kpi)


@router.get("/{kpi_id}", response_model=KpiDefinitionRead)
async def get_kpi(
    kpi_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> KpiDefinitionRead:
    kpi = await service.get_kpi(session, kpi_id)
    return KpiDefinitionRead.model_validate(kpi)


@router.get("/{kpi_id}/versions", response_model=list[KpiVersionRead])
async def list_versions(
    kpi_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[KpiVersionRead]:
    await service.get_kpi(session, kpi_id)
    rows = await service.list_versions(session, kpi_id)
    return [KpiVersionRead.model_validate(item) for item in rows]


@router.post("/{kpi_id}/versions", response_model=KpiVersionRead, status_code=201)
async def create_version(
    kpi_id: uuid.UUID,
    payload: KpiVersionCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> KpiVersionRead:
    version = await service.create_version(
        session,
        kpi_id,
        formula=payload.formula,
        source_mapping=payload.source_mapping,
        target_value=payload.target_value,
        change_reason=payload.change_reason,
    )
    return KpiVersionRead.model_validate(version)


@router.post("/{kpi_id}/recalculate", response_model=KpiSnapshotRead)
async def recalculate_kpi(
    kpi_id: uuid.UUID,
    payload: KpiRecalculateRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer", "operator")),
) -> KpiSnapshotRead:
    snapshot = await service.recalculate(
        session,
        kpi_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return KpiSnapshotRead.model_validate(snapshot)


@router.get("/{kpi_id}/snapshots", response_model=list[KpiSnapshotRead])
async def list_snapshots(
    kpi_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[KpiSnapshotRead]:
    await service.get_kpi(session, kpi_id)
    rows = await service.list_snapshots(session, kpi_id=kpi_id)
    return [KpiSnapshotRead.model_validate(item) for item in rows]
