import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.rules import service
from modules.rules.schemas import (
    RuleCreate,
    RuleDefinitionRead,
    RuleVersionCreate,
    RuleVersionRead,
)

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("", response_model=list[RuleDefinitionRead])
async def list_rules(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[RuleDefinitionRead]:
    rows = await service.list_rules(session, company_id=company_id)
    return [RuleDefinitionRead.model_validate(item) for item in rows]


@router.post("", response_model=RuleDefinitionRead, status_code=201)
async def create_rule(
    payload: RuleCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> RuleDefinitionRead:
    rule = await service.create_rule(
        session,
        company_id=payload.company_id,
        code=payload.code,
        name=payload.name,
        kind=payload.kind,
        body=payload.body,
        description=payload.description,
    )
    return RuleDefinitionRead.model_validate(rule)


@router.post("/bootstrap")
async def bootstrap_default_rules(
    company_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> dict:
    rows = await service.ensure_default_rules(session, company_id)
    return {"count": len(rows), "codes": [r.code for r in rows]}


@router.get("/{rule_id}/versions", response_model=list[RuleVersionRead])
async def list_rule_versions(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[RuleVersionRead]:
    await service.get_rule(session, rule_id)
    rows = await service.list_versions(session, rule_id)
    return [RuleVersionRead.model_validate(item) for item in rows]


@router.post("/{rule_id}/versions", response_model=RuleVersionRead, status_code=201)
async def create_rule_version(
    rule_id: uuid.UUID,
    payload: RuleVersionCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer")),
) -> RuleVersionRead:
    version = await service.create_version(
        session,
        rule_id,
        body=payload.body,
        change_reason=payload.change_reason,
    )
    return RuleVersionRead.model_validate(version)
