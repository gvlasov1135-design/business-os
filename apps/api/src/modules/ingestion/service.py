import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.identity.service import get_company
from modules.ingestion.models import ObservedFact, RawRecord, RawRecordStatus, Source, SourceStatus, SourceType
from modules.ingestion.schemas import ImportResponse, ObservedFactRead, RawRecordRead, SourceCreate
from modules.quality import service as quality_service
from modules.quality.schemas import DataQualityIssueRead as DQIssueRead


def _canonical_checksum(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _external_id_from_payload(payload: dict[str, Any]) -> str:
    lead_id = payload.get("lead_id")
    if lead_id is not None and str(lead_id).strip():
        return str(lead_id)
    external_id = payload.get("external_id")
    if external_id is not None and str(external_id).strip():
        return str(external_id)
    raise AppError(
        "payload requires lead_id or external_id",
        status_code=400,
        code="missing_external_id",
    )


async def create_source(
    session: AsyncSession,
    company_id: uuid.UUID,
    code: str,
    name: str,
    source_type: SourceType,
    freshness_hours: int = 24,
) -> Source:
    await get_company(session, company_id)
    existing = await session.scalar(
        select(Source).where(Source.company_id == company_id, Source.code == code)
    )
    if existing:
        raise AppError("Source already exists", status_code=409, code="source_exists")

    source = Source(
        company_id=company_id,
        code=code,
        name=name,
        source_type=source_type,
        freshness_hours=freshness_hours,
        status=SourceStatus.active,
    )
    session.add(source)
    await session.flush()
    await write_audit(
        session,
        action="source.created",
        entity_type="source",
        entity_id=source.id,
        company_id=company_id,
        payload={"code": code, "name": name, "source_type": source_type.value},
    )
    await session.commit()
    await session.refresh(source)
    return source


async def create_source_from_schema(session: AsyncSession, payload: SourceCreate) -> Source:
    return await create_source(
        session,
        company_id=payload.company_id,
        code=payload.code,
        name=payload.name,
        source_type=payload.source_type,
        freshness_hours=payload.freshness_hours,
    )


async def list_sources(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
) -> list[Source]:
    stmt = select(Source).order_by(Source.code)
    if company_id is not None:
        stmt = stmt.where(Source.company_id == company_id)
    result = await session.scalars(stmt)
    return list(result.all())


async def get_source(session: AsyncSession, source_id: uuid.UUID) -> Source:
    source = await session.get(Source, source_id)
    if not source:
        raise AppError("Source not found", status_code=404, code="source_not_found")
    return source


async def mark_source_stale(
    session: AsyncSession,
    source_id: uuid.UUID,
    *,
    status: SourceStatus | None = None,
    commit: bool = True,
) -> Source:
    source = await get_source(session, source_id)

    if status is not None:
        source.status = status
    elif source.last_synced_at is not None:
        now = datetime.now(timezone.utc)
        last = source.last_synced_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last > timedelta(hours=source.freshness_hours):
            source.status = SourceStatus.stale

    await session.flush()
    await write_audit(
        session,
        action="source.status_updated",
        entity_type="source",
        entity_id=source.id,
        company_id=source.company_id,
        payload={"status": source.status.value},
    )
    if commit:
        await session.commit()
        await session.refresh(source)
    return source


async def get_raw_record(session: AsyncSession, raw_record_id: uuid.UUID) -> RawRecord:
    record = await session.get(RawRecord, raw_record_id)
    if not record:
        raise AppError("Raw record not found", status_code=404, code="raw_record_not_found")
    return record


async def get_fact(session: AsyncSession, fact_id: uuid.UUID) -> ObservedFact:
    fact = await session.get(ObservedFact, fact_id)
    if not fact:
        raise AppError("Observed fact not found", status_code=404, code="fact_not_found")
    return fact


async def list_facts(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
) -> list[ObservedFact]:
    stmt = select(ObservedFact).order_by(ObservedFact.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(ObservedFact.company_id == company_id)
    result = await session.scalars(stmt)
    return list(result.all())


async def _fact_for_raw_record(
    session: AsyncSession,
    raw_record_id: uuid.UUID,
) -> ObservedFact | None:
    return await session.scalar(
        select(ObservedFact).where(ObservedFact.raw_record_id == raw_record_id)
    )


async def import_record(
    session: AsyncSession,
    source_id: uuid.UUID,
    payload: dict[str, Any],
) -> ImportResponse:
    if payload.get("record_kind") == "metric" or payload.get("predicate") in {
        "finance_metric",
        "expense_article",
        "ops_metric",
        "workbook_marker",
    }:
        return await import_metric_record(session, source_id, payload)

    source = await get_source(session, source_id)
    await mark_source_stale(session, source.id, commit=False)
    await session.refresh(source)

    external_id = _external_id_from_payload(payload)
    checksum = _canonical_checksum(payload)

    existing = await session.scalar(
        select(RawRecord).where(
            RawRecord.source_id == source.id,
            or_(
                RawRecord.external_id == external_id,
                RawRecord.checksum_sha256 == checksum,
            ),
        )
    )
    if existing:
        fact = await _fact_for_raw_record(session, existing.id)
        await write_audit(
            session,
            action="ingestion.import_duplicate",
            entity_type="raw_record",
            entity_id=existing.id,
            company_id=source.company_id,
            payload={"external_id": external_id, "checksum_sha256": checksum},
        )
        await session.commit()
        return ImportResponse(
            raw_record=RawRecordRead.model_validate(existing),
            fact=ObservedFactRead.model_validate(fact) if fact else None,
            duplicate=True,
            blocked=existing.status == RawRecordStatus.quarantine,
            issues=[],
        )

    raw_record = RawRecord(
        source_id=source.id,
        company_id=source.company_id,
        external_id=external_id,
        payload=payload,
        checksum_sha256=checksum,
        status=RawRecordStatus.received,
    )
    session.add(raw_record)
    await session.flush()

    await write_audit(
        session,
        action="ingestion.raw_record_received",
        entity_type="raw_record",
        entity_id=raw_record.id,
        company_id=source.company_id,
        payload={"external_id": external_id},
    )

    issue_defs = quality_service.check_crm_lead_payload(payload, source)
    if quality_service.should_quarantine(issue_defs):
        raw_record.status = RawRecordStatus.quarantine
        created_issues = await quality_service.create_issues(
            session,
            company_id=source.company_id,
            source_id=source.id,
            raw_record_id=raw_record.id,
            issues=issue_defs,
        )
        await write_audit(
            session,
            action="ingestion.quarantined",
            entity_type="raw_record",
            entity_id=raw_record.id,
            company_id=source.company_id,
            payload={"issue_codes": [i.code for i in created_issues]},
        )
        await session.commit()
        await session.refresh(raw_record)
        return ImportResponse(
            raw_record=RawRecordRead.model_validate(raw_record),
            fact=None,
            duplicate=False,
            blocked=True,
            issues=[DQIssueRead.model_validate(i).model_dump(mode="json") for i in created_issues],
        )

    warning_defs = [i for i in issue_defs if not i.get("blocks_analysis")]
    warning_issues: list = []
    if warning_defs:
        warning_issues = await quality_service.create_issues(
            session,
            company_id=source.company_id,
            source_id=source.id,
            raw_record_id=raw_record.id,
            issues=warning_defs,
        )

    created_at = quality_service.parse_datetime(payload.get("created_at"))
    first_contact_at = quality_service.parse_datetime(payload.get("first_contact_at"))
    assert created_at is not None and first_contact_at is not None

    actual_minutes = (first_contact_at - created_at).total_seconds() / 60
    value_structured = {
        "minutes": actual_minutes,
        "created_at": created_at.isoformat(),
        "first_contact_at": first_contact_at.isoformat(),
        "assigned_position": payload.get("assigned_position"),
        "actual_actor": payload.get("actual_actor"),
        "stages_completed": payload.get("stages_completed") or [],
        "stages_skipped": payload.get("stages_skipped") or [],
    }
    fact = ObservedFact(
        company_id=source.company_id,
        source_id=source.id,
        raw_record_id=raw_record.id,
        subject=str(payload.get("lead_id") or external_id),
        predicate="actual_first_contact_minutes",
        value_text=str(int(actual_minutes) if actual_minutes == int(actual_minutes) else actual_minutes),
        value_structured=value_structured,
        observed_at=first_contact_at,
        trust_index=0.7,
        lineage={
            "raw_record_id": str(raw_record.id),
            "source_id": str(source.id),
            "external_id": external_id,
        },
    )
    session.add(fact)
    raw_record.status = RawRecordStatus.normalized
    source.last_synced_at = datetime.now(timezone.utc)
    source.status = SourceStatus.active

    await session.flush()
    await write_audit(
        session,
        action="ingestion.normalized",
        entity_type="observed_fact",
        entity_id=fact.id,
        company_id=source.company_id,
        payload={
            "raw_record_id": str(raw_record.id),
            "predicate": fact.predicate,
            "minutes": actual_minutes,
        },
    )
    from modules.resolution import service as resolution_service

    await resolution_service.resolve_raw_record(session, raw_record, commit=False)
    await session.commit()
    await session.refresh(raw_record)
    await session.refresh(fact)

    return ImportResponse(
        raw_record=RawRecordRead.model_validate(raw_record),
        fact=ObservedFactRead.model_validate(fact),
        duplicate=False,
        blocked=False,
        issues=[DQIssueRead.model_validate(i).model_dump(mode="json") for i in warning_issues],
    )


async def import_metric_record(
    session: AsyncSession,
    source_id: uuid.UUID,
    payload: dict[str, Any],
) -> ImportResponse:
    """Import finance/ops metric without CRM DQ gate."""
    source = await get_source(session, source_id)
    await mark_source_stale(session, source.id, commit=False)
    await session.refresh(source)

    external_id = str(payload.get("external_id") or "").strip()
    if not external_id:
        raise AppError("metric payload requires external_id", status_code=400, code="missing_external_id")

    checksum = _canonical_checksum(payload)
    existing = await session.scalar(
        select(RawRecord).where(
            RawRecord.source_id == source.id,
            or_(
                RawRecord.external_id == external_id,
                RawRecord.checksum_sha256 == checksum,
            ),
        )
    )
    if existing:
        fact = await _fact_for_raw_record(session, existing.id)
        new_checksum = checksum
        # Same external_id but changed metric values → refresh fact (pilot re-import).
        if existing.external_id == external_id and existing.checksum_sha256 != new_checksum and fact:
            value = payload.get("value")
            value_structured = {
                "value": value,
                "unit": payload.get("unit"),
                "period": payload.get("period"),
                "months": payload.get("months") or {},
                "sheet": payload.get("sheet"),
                "system_origin": payload.get("system_origin"),
                "metric_group": payload.get("metric_group"),
                "article_code": payload.get("article_code"),
                "venue": payload.get("venue"),
                "metric_name": payload.get("metric_name"),
                "channel": payload.get("channel"),
                "division": payload.get("division"),
            }
            existing.payload = payload
            existing.checksum_sha256 = new_checksum
            fact.subject = str(payload.get("subject") or external_id)[:500]
            fact.predicate = str(payload.get("predicate") or "finance_metric")[:200]
            fact.value_text = str(value)
            fact.value_structured = value_structured
            fact.observed_at = datetime.now(timezone.utc)
            source.last_synced_at = datetime.now(timezone.utc)
            source.status = SourceStatus.active
            await session.commit()
            await session.refresh(existing)
            await session.refresh(fact)
            return ImportResponse(
                raw_record=RawRecordRead.model_validate(existing),
                fact=ObservedFactRead.model_validate(fact),
                duplicate=False,
                blocked=False,
                issues=[],
            )
        await session.commit()
        return ImportResponse(
            raw_record=RawRecordRead.model_validate(existing),
            fact=ObservedFactRead.model_validate(fact) if fact else None,
            duplicate=True,
            blocked=False,
            issues=[],
        )

    raw_record = RawRecord(
        source_id=source.id,
        company_id=source.company_id,
        external_id=external_id,
        payload=payload,
        checksum_sha256=checksum,
        status=RawRecordStatus.received,
    )
    session.add(raw_record)
    await session.flush()

    value = payload.get("value")
    subject = str(payload.get("subject") or external_id)
    predicate = str(payload.get("predicate") or "finance_metric")
    value_structured = {
        "value": value,
        "unit": payload.get("unit"),
        "period": payload.get("period"),
        "months": payload.get("months") or {},
        "sheet": payload.get("sheet"),
        "system_origin": payload.get("system_origin"),
        "metric_group": payload.get("metric_group"),
        "article_code": payload.get("article_code"),
        "venue": payload.get("venue"),
        "metric_name": payload.get("metric_name"),
        "channel": payload.get("channel"),
        "division": payload.get("division"),
    }
    fact = ObservedFact(
        company_id=source.company_id,
        source_id=source.id,
        raw_record_id=raw_record.id,
        subject=subject[:500],
        predicate=predicate[:200],
        value_text=str(value),
        value_structured=value_structured,
        observed_at=datetime.now(timezone.utc),
        trust_index=0.75,
        lineage={
            "raw_record_id": str(raw_record.id),
            "source_id": str(source.id),
            "external_id": external_id,
            "system_origin": payload.get("system_origin"),
            "sheet": payload.get("sheet"),
        },
    )
    session.add(fact)
    raw_record.status = RawRecordStatus.normalized
    source.last_synced_at = datetime.now(timezone.utc)
    source.status = SourceStatus.active
    await session.flush()
    await write_audit(
        session,
        action="ingestion.metric_normalized",
        entity_type="observed_fact",
        entity_id=fact.id,
        company_id=source.company_id,
        payload={"predicate": predicate, "external_id": external_id},
    )
    await session.commit()
    await session.refresh(raw_record)
    await session.refresh(fact)
    return ImportResponse(
        raw_record=RawRecordRead.model_validate(raw_record),
        fact=ObservedFactRead.model_validate(fact),
        duplicate=False,
        blocked=False,
        issues=[],
    )


async def get_or_create_source(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    code: str,
    name: str,
    source_type: SourceType,
    freshness_hours: int = 24 * 30,
) -> Source:
    existing = await session.scalar(
        select(Source).where(Source.company_id == company_id, Source.code == code)
    )
    if existing:
        return existing
    return await create_source(
        session,
        company_id=company_id,
        code=code,
        name=name,
        source_type=source_type,
        freshness_hours=freshness_hours,
    )
