import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.identity.service import get_company
from modules.ingestion.models import ObservedFact
from modules.kpi.models import (
    KpiDefinition,
    KpiSnapshot,
    KpiSnapshotStatus,
    KpiStatus,
    KpiVersion,
    KpiVersionStatus,
)

ALLOWED_OPS = {"avg_fact_minutes", "count_facts", "ratio_over_target", "share_within_target"}


def formula_text(formula: dict[str, Any], source_mapping: dict[str, Any]) -> str:
    op = str(formula.get("op") or "")
    predicate = source_mapping.get("predicate") or formula.get("predicate") or "*"
    if op == "avg_fact_minutes":
        return f"AVG(observed_facts.minutes WHERE predicate={predicate})"
    if op == "count_facts":
        return f"COUNT(observed_facts WHERE predicate={predicate})"
    if op == "ratio_over_target":
        return f"AVG(minutes)/target WHERE predicate={predicate}"
    if op == "share_within_target":
        threshold = formula.get("threshold_minutes") or "target"
        return f"SHARE(minutes<={threshold})% WHERE predicate={predicate}"
    return f"INVALID({op})"


def validate_formula(formula: dict[str, Any], source_mapping: dict[str, Any]) -> None:
    op = formula.get("op")
    if op not in ALLOWED_OPS:
        raise AppError(
            f"Unsupported KPI formula op: {op}",
            status_code=400,
            code="kpi_formula_invalid",
        )
    if op in ("avg_fact_minutes", "count_facts", "ratio_over_target", "share_within_target"):
        predicate = source_mapping.get("predicate") or formula.get("predicate")
        if not predicate:
            raise AppError(
                "KPI formula requires source_mapping.predicate",
                status_code=400,
                code="kpi_formula_invalid",
            )


async def get_kpi(session: AsyncSession, kpi_id: uuid.UUID) -> KpiDefinition:
    kpi = await session.get(KpiDefinition, kpi_id)
    if kpi is None:
        raise AppError("KPI not found", status_code=404, code="kpi_not_found")
    return kpi


async def get_version(session: AsyncSession, version_id: uuid.UUID) -> KpiVersion:
    version = await session.get(KpiVersion, version_id)
    if version is None:
        raise AppError("KPI version not found", status_code=404, code="kpi_version_not_found")
    return version


async def list_kpis(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
) -> list[KpiDefinition]:
    stmt = select(KpiDefinition).order_by(KpiDefinition.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(KpiDefinition.company_id == company_id)
    return list((await session.scalars(stmt)).all())


async def list_versions(session: AsyncSession, kpi_id: uuid.UUID) -> list[KpiVersion]:
    stmt = (
        select(KpiVersion)
        .where(KpiVersion.kpi_id == kpi_id)
        .order_by(KpiVersion.version_number.desc())
    )
    return list((await session.scalars(stmt)).all())


async def list_snapshots(
    session: AsyncSession,
    *,
    kpi_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
) -> list[KpiSnapshot]:
    stmt = select(KpiSnapshot).order_by(KpiSnapshot.calculated_at.desc())
    if kpi_id is not None:
        stmt = stmt.where(KpiSnapshot.kpi_id == kpi_id)
    if company_id is not None:
        stmt = stmt.where(KpiSnapshot.company_id == company_id)
    return list((await session.scalars(stmt)).all())


async def integrity_block_reasons(
    session: AsyncSession,
    company_id: uuid.UUID,
) -> list[str]:
    reasons: list[str] = []
    kpis = await list_kpis(session, company_id=company_id)
    for kpi in kpis:
        if kpi.status != KpiStatus.active:
            continue
        if kpi.current_version_id is None:
            reasons.append(f"KPI {kpi.code}: нет активной версии формулы")
            continue
        version = await session.get(KpiVersion, kpi.current_version_id)
        if version is None:
            reasons.append(f"KPI {kpi.code}: повреждена ссылка на версию формулы")
            continue
        op = (version.formula or {}).get("op")
        if op not in ALLOWED_OPS:
            reasons.append(f"KPI {kpi.code}: нарушена целостность формулы KPI")

    snapshots = await list_snapshots(session, company_id=company_id)
    for snap in snapshots:
        if snap.blocks_analysis and snap.conflict_flag:
            reasons.append(f"KPI snapshot {snap.id}: конфликт данных в показателе")
            break
    return reasons


async def create_kpi(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    code: str,
    name: str,
    owner_name: str,
    formula: dict[str, Any],
    source_mapping: dict[str, Any] | None = None,
    target_value: float | None = None,
    description: str | None = None,
    unit: str = "minutes",
    activate: bool = True,
) -> KpiDefinition:
    await get_company(session, company_id)
    source_mapping = source_mapping or {}
    validate_formula(formula, source_mapping)

    existing = await session.scalar(
        select(KpiDefinition).where(KpiDefinition.company_id == company_id, KpiDefinition.code == code)
    )
    if existing is not None:
        raise AppError("KPI code already exists", status_code=409, code="kpi_exists")

    kpi = KpiDefinition(
        company_id=company_id,
        code=code,
        name=name,
        description=description,
        unit=unit,
        owner_name=owner_name,
        status=KpiStatus.active if activate else KpiStatus.draft,
        trust_index=0.7,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(kpi)
    await session.flush()

    version = KpiVersion(
        kpi_id=kpi.id,
        company_id=company_id,
        version_number=1,
        status=KpiVersionStatus.active,
        formula=formula,
        source_mapping=source_mapping,
        target_value=target_value,
        formula_text=formula_text(formula, source_mapping),
        change_reason="initial",
    )
    session.add(version)
    await session.flush()
    kpi.current_version_id = version.id

    await write_audit(
        session,
        action="kpi.created",
        entity_type="kpi_definition",
        entity_id=kpi.id,
        company_id=company_id,
        payload={"code": code, "formula": formula, "version_id": str(version.id)},
    )
    await session.commit()
    await session.refresh(kpi)
    return kpi


async def create_version(
    session: AsyncSession,
    kpi_id: uuid.UUID,
    *,
    formula: dict[str, Any],
    source_mapping: dict[str, Any] | None = None,
    target_value: float | None = None,
    change_reason: str | None = None,
) -> KpiVersion:
    kpi = await get_kpi(session, kpi_id)
    source_mapping = source_mapping or {}
    validate_formula(formula, source_mapping)

    versions = await list_versions(session, kpi_id)
    next_number = (versions[0].version_number + 1) if versions else 1
    for old in versions:
        if old.status == KpiVersionStatus.active:
            old.status = KpiVersionStatus.superseded

    version = KpiVersion(
        kpi_id=kpi.id,
        company_id=kpi.company_id,
        version_number=next_number,
        status=KpiVersionStatus.active,
        formula=formula,
        source_mapping=source_mapping,
        target_value=target_value,
        formula_text=formula_text(formula, source_mapping),
        change_reason=change_reason or f"version {next_number}",
    )
    session.add(version)
    await session.flush()
    kpi.current_version_id = version.id
    kpi.updated_at = datetime.now(timezone.utc)

    await write_audit(
        session,
        action="kpi.version_created",
        entity_type="kpi_version",
        entity_id=version.id,
        company_id=kpi.company_id,
        payload={
            "kpi_id": str(kpi.id),
            "version_number": next_number,
            "formula": formula,
            "change_reason": change_reason,
        },
    )
    await session.commit()
    await session.refresh(version)
    return version


async def _facts_for_kpi(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    predicate: str,
    period_start: datetime,
    period_end: datetime,
) -> list[ObservedFact]:
    stmt = select(ObservedFact).where(
        ObservedFact.company_id == company_id,
        ObservedFact.predicate == predicate,
        ObservedFact.observed_at >= period_start,
        ObservedFact.observed_at <= period_end,
    )
    return list((await session.scalars(stmt)).all())


def _minutes_from_fact(fact: ObservedFact) -> float | None:
    structured = fact.value_structured or {}
    if "minutes" in structured:
        try:
            return float(structured["minutes"])
        except (TypeError, ValueError):
            return None
    try:
        return float(fact.value_text)
    except (TypeError, ValueError):
        return None


async def recalculate(
    session: AsyncSession,
    kpi_id: uuid.UUID,
    *,
    period_start: datetime,
    period_end: datetime,
) -> KpiSnapshot:
    kpi = await get_kpi(session, kpi_id)
    if kpi.current_version_id is None:
        raise AppError("KPI has no active formula version", status_code=400, code="kpi_no_version")
    version = await get_version(session, kpi.current_version_id)
    if version.status != KpiVersionStatus.active:
        raise AppError("Current KPI version is not active", status_code=400, code="kpi_version_inactive")

    formula = version.formula or {}
    mapping = version.source_mapping or {}
    validate_formula(formula, mapping)
    op = formula["op"]
    predicate = str(mapping.get("predicate") or formula.get("predicate"))

    facts = await _facts_for_kpi(
        session,
        company_id=kpi.company_id,
        predicate=predicate,
        period_start=period_start,
        period_end=period_end,
    )

    sources = [
        {
            "fact_id": str(f.id),
            "subject": f.subject,
            "trust_index": f.trust_index,
            "lineage": f.lineage,
            "value_structured": f.value_structured,
        }
        for f in facts
    ]

    conflict = False
    blocks = False
    status = KpiSnapshotStatus.calculated
    actual: float | None = None
    trust = 0.0

    if not facts:
        status = KpiSnapshotStatus.incomplete
        trust = 0.0
    else:
        minutes = [m for m in (_minutes_from_fact(f) for f in facts) if m is not None]
        trusts = [f.trust_index for f in facts]
        trust = round(sum(trusts) / len(trusts), 4) if trusts else 0.0

        # conflict: facts disagree strongly (>2x spread) or mixed low trust
        if len(minutes) >= 2:
            spread = max(minutes) - min(minutes)
            if spread > max(30.0, (sum(minutes) / len(minutes))):
                conflict = True
                status = KpiSnapshotStatus.conflict
        if any(t < 0.4 for t in trusts) and any(t >= 0.7 for t in trusts):
            conflict = True
            status = KpiSnapshotStatus.conflict
            blocks = True

        if op == "avg_fact_minutes":
            actual = round(sum(minutes) / len(minutes), 4) if minutes else None
        elif op == "count_facts":
            actual = float(len(facts))
        elif op == "ratio_over_target":
            avg = (sum(minutes) / len(minutes)) if minutes else None
            target = version.target_value
            if avg is None or not target:
                status = KpiSnapshotStatus.incomplete
                actual = None
            else:
                actual = round(avg / float(target), 4)
        elif op == "share_within_target":
            threshold = formula.get("threshold_minutes")
            if threshold is None:
                threshold = version.target_value
            if not minutes or threshold is None:
                status = KpiSnapshotStatus.incomplete
                actual = None
            else:
                ok = sum(1 for m in minutes if m <= float(threshold))
                actual = round(100.0 * ok / len(minutes), 4)

        if actual is None and status == KpiSnapshotStatus.calculated:
            status = KpiSnapshotStatus.incomplete

    snapshot = KpiSnapshot(
        kpi_id=kpi.id,
        version_id=version.id,
        company_id=kpi.company_id,
        period_start=period_start,
        period_end=period_end,
        target_value=version.target_value,
        actual_value=actual,
        trust_index=trust,
        status=status,
        conflict_flag=conflict,
        blocks_analysis=blocks,
        sources=sources,
        lineage={
            "formula": formula,
            "formula_text": version.formula_text,
            "source_mapping": mapping,
            "version_number": version.version_number,
            "fact_count": len(facts),
            "reproducible": True,
        },
        calculated_at=datetime.now(timezone.utc),
    )
    session.add(snapshot)
    kpi.trust_index = trust if facts else kpi.trust_index
    kpi.updated_at = datetime.now(timezone.utc)

    await session.flush()
    await write_audit(
        session,
        action="kpi.recalculated",
        entity_type="kpi_snapshot",
        entity_id=snapshot.id,
        company_id=kpi.company_id,
        payload={
            "kpi_id": str(kpi.id),
            "actual": actual,
            "target": version.target_value,
            "status": status.value,
            "conflict": conflict,
        },
    )
    await session.commit()
    await session.refresh(snapshot)
    return snapshot
