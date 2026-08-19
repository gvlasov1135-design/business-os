import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.identity.service import get_company
from modules.rules.models import RuleDefinition, RuleKind, RuleVersion, RuleVersionStatus

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "code": "lead_first_contact_deadline",
        "name": "Срок первого контакта с лидом",
        "kind": RuleKind.alignment,
        "body": {
            "predicate": "actual_first_contact_minutes",
            "statement_type": "deadline",
            "substantial_deviation_minutes": 30,
            "severity_bands": {"medium": 0, "high": 30, "critical": 60},
        },
    },
    {
        "code": "trust_default",
        "name": "Trust Policy по умолчанию",
        "kind": RuleKind.trust,
        "body": {"min_trust_for_analysis": 0.4, "blend": "avg"},
    },
    {
        "code": "freshness_default",
        "name": "Freshness Policy по умолчанию",
        "kind": RuleKind.freshness,
        "body": {"max_age_hours": 24, "block_if_stale": True},
    },
    {
        "code": "dna_executive",
        "name": "Decision DNA — Executive",
        "kind": RuleKind.agent_profile,
        "body": {
            "role": "executive",
            "priorities": ["evidence", "accountability", "controlled_change"],
            "risk_tolerance": "low",
            "bias": "confirm_before_act",
            "language": "ru",
        },
    },
    {
        "code": "dna_sales",
        "name": "Decision DNA — Sales",
        "kind": RuleKind.agent_profile,
        "body": {
            "role": "sales",
            "priorities": ["sla", "conversion", "queue_throughput"],
            "risk_tolerance": "medium",
            "bias": "operational_fix_now",
            "language": "ru",
        },
    },
    {
        "code": "dna_critic",
        "name": "Decision DNA — Critic",
        "kind": RuleKind.agent_profile,
        "body": {
            "role": "critic",
            "priorities": ["source_integrity", "no_hallucination"],
            "risk_tolerance": "low",
            "bias": "challenge_unverified",
            "language": "ru",
        },
    },
    {
        "code": "prompt_executive",
        "name": "Prompt — Executive",
        "kind": RuleKind.prompt,
        "body": {
            "template": (
                "Ответь как руководитель: опирайся только на подтверждённые знания и сверку. "
                "Вопрос: {question}"
            ),
            "agent": "executive",
        },
    },
    {
        "code": "prompt_sales",
        "name": "Prompt — Sales",
        "kind": RuleKind.prompt,
        "body": {
            "template": (
                "Ответь как SalesOps по SLA лидов: очередь, этапы, доля в SLA. "
                "Вопрос: {question}"
            ),
            "agent": "sales",
        },
    },
]


async def get_rule(session: AsyncSession, rule_id: uuid.UUID) -> RuleDefinition:
    rule = await session.get(RuleDefinition, rule_id)
    if rule is None:
        raise AppError("Rule not found", status_code=404, code="rule_not_found")
    return rule


async def get_rule_by_code(
    session: AsyncSession,
    company_id: uuid.UUID,
    code: str,
) -> RuleDefinition | None:
    return await session.scalar(
        select(RuleDefinition).where(
            RuleDefinition.company_id == company_id,
            RuleDefinition.code == code,
        )
    )


async def list_rules(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
) -> list[RuleDefinition]:
    stmt = select(RuleDefinition).order_by(RuleDefinition.code)
    if company_id is not None:
        stmt = stmt.where(RuleDefinition.company_id == company_id)
    return list((await session.scalars(stmt)).all())


async def list_versions(session: AsyncSession, rule_id: uuid.UUID) -> list[RuleVersion]:
    return list(
        (
            await session.scalars(
                select(RuleVersion)
                .where(RuleVersion.rule_id == rule_id)
                .order_by(RuleVersion.version_number.desc())
            )
        ).all()
    )


async def get_active_version(
    session: AsyncSession,
    company_id: uuid.UUID,
    code: str,
) -> RuleVersion | None:
    rule = await get_rule_by_code(session, company_id, code)
    if rule is None or rule.current_version_id is None:
        return None
    return await session.get(RuleVersion, rule.current_version_id)


async def create_rule(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    code: str,
    name: str,
    kind: RuleKind,
    body: dict[str, Any],
    description: str | None = None,
) -> RuleDefinition:
    await get_company(session, company_id)
    existing = await get_rule_by_code(session, company_id, code)
    if existing is not None:
        raise AppError("Rule already exists", status_code=409, code="rule_exists")

    rule = RuleDefinition(
        company_id=company_id,
        code=code,
        name=name,
        kind=kind,
        description=description,
    )
    session.add(rule)
    await session.flush()
    version = RuleVersion(
        rule_id=rule.id,
        company_id=company_id,
        version_number=1,
        status=RuleVersionStatus.active,
        body=body,
        change_reason="initial",
    )
    session.add(version)
    await session.flush()
    rule.current_version_id = version.id
    await write_audit(
        session,
        action="rule.created",
        entity_type="rule_definition",
        entity_id=rule.id,
        company_id=company_id,
        payload={"code": code, "kind": kind.value, "version_id": str(version.id)},
    )
    await session.commit()
    await session.refresh(rule)
    return rule


async def create_version(
    session: AsyncSession,
    rule_id: uuid.UUID,
    *,
    body: dict[str, Any],
    change_reason: str | None = None,
) -> RuleVersion:
    rule = await get_rule(session, rule_id)
    versions = await list_versions(session, rule_id)
    next_number = (versions[0].version_number + 1) if versions else 1
    for old in versions:
        if old.status == RuleVersionStatus.active:
            old.status = RuleVersionStatus.superseded
    version = RuleVersion(
        rule_id=rule.id,
        company_id=rule.company_id,
        version_number=next_number,
        status=RuleVersionStatus.active,
        body=body,
        change_reason=change_reason or f"version {next_number}",
    )
    session.add(version)
    await session.flush()
    rule.current_version_id = version.id
    await write_audit(
        session,
        action="rule.version_created",
        entity_type="rule_version",
        entity_id=version.id,
        company_id=rule.company_id,
        payload={"rule_id": str(rule.id), "version_number": next_number},
    )
    await session.commit()
    await session.refresh(version)
    return version


async def ensure_default_rules(
    session: AsyncSession,
    company_id: uuid.UUID,
) -> list[RuleDefinition]:
    created: list[RuleDefinition] = []
    for spec in DEFAULT_RULES:
        existing = await get_rule_by_code(session, company_id, spec["code"])
        if existing is not None:
            created.append(existing)
            continue
        rule = await create_rule(
            session,
            company_id=company_id,
            code=spec["code"],
            name=spec["name"],
            kind=spec["kind"],
            body=spec["body"],
        )
        created.append(rule)
    return created
