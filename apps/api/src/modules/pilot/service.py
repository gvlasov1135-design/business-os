"""Pilot: first analysis on real Бистро workbook (1C / RKeeper / Storyhouse)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import AppError
from modules.analysis import service as analysis_service
from modules.identity import service as identity_service
from modules.identity.models import Company
from modules.identity.schemas import CompanyCreate
from modules.ingestion import workbook_import
from modules.ingestion.models import ObservedFact
from modules.knowledge.models import KnowledgeRecord, KnowledgeRecordStatus, KnowledgeRecordType
from modules.kpi import service as kpi_service
from modules.rules import service as rules_service

DEFAULT_QUESTION = (
    "По загруженной отчётности: как выглядят выручка, средний чек, "
    "валовая и чистая прибыль, и где главные расходы и риски "
    "(фудкост, недостачи, ФОТ, аренда)?"
)


async def run_bistro_pilot(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None,
    data: bytes,
    filename: str | None = None,
    question: str | None = None,
    company_name: str | None = None,
) -> dict[str, Any]:
    company_id = await _resolve_company(session, company_id, company_name=company_name)

    assert company_id is not None
    await rules_service.ensure_default_rules(session, company_id)

    imported = await workbook_import.import_workbook(
        session,
        company_id=company_id,
        data=data,
        filename=filename,
    )
    if imported.get("fact_count", 0) < 1:
        raise AppError(
            "Workbook produced no metrics",
            status_code=400,
            code="workbook_empty_metrics",
        )

    knowledge_ids = await _ensure_finance_knowledge(session, company_id)
    kpi_ids = await _ensure_finance_kpis(session, company_id)

    analysis = await analysis_service.create_analysis(
        session,
        company_id,
        (question or DEFAULT_QUESTION).strip(),
    )
    recommendations = await analysis_service.list_recommendations(session, analysis.id)
    briefing = (analysis.output or {}).get("finance_briefing") if analysis.output else None

    return {
        "company_id": str(company_id),
        "import": imported,
        "knowledge_ids": knowledge_ids,
        "kpi_ids": kpi_ids,
        "analysis_id": str(analysis.id),
        "analysis_blocked": analysis.blocked,
        "analysis_status": analysis.status.value,
        "recommendation_id": str(recommendations[0].id) if recommendations else None,
        "question": analysis.question,
        "finance_briefing": briefing,
        "conclusions": briefing or {},
        "recommendations": [
            {
                "id": str(r.id),
                "title": r.title,
                "body": r.body,
                "priority": str(r.priority),
            }
            for r in recommendations[:6]
        ],
        "next_steps": [
            "Выводы ниже на этой странице — главный результат для руководителя",
            "При необходимости углубиться: /analysis или /council",
            "Принять решение: /decisions или кабинет /executive",
        ],
    }


async def _resolve_company(
    session: AsyncSession,
    company_id: uuid.UUID | None,
    *,
    company_name: str | None = None,
) -> uuid.UUID:
    """Use given company if it exists; otherwise named company or Бистро Benedict."""
    if company_id is not None:
        company = await session.get(Company, company_id)
        if company is not None:
            return company.id
        # Stale id from localStorage / old DB — do not fail the pilot

    name = (company_name or "").strip() or "Бистро Benedict"
    existing = await session.scalar(select(Company).where(Company.name == name))
    if existing is not None:
        return existing.id
    company = await identity_service.create_company(session, CompanyCreate(name=name))
    return company.id


async def _ensure_finance_knowledge(session: AsyncSession, company_id: uuid.UUID) -> list[str]:
    facts = list(
        (
            await session.scalars(
                select(ObservedFact)
                .where(ObservedFact.company_id == company_id)
                .order_by(ObservedFact.created_at.desc())
                .limit(200)
            )
        ).all()
    )
    key_facts = [
        f
        for f in facts
        if f.predicate in {"finance_metric", "ops_metric", "expense_article"}
        and any(
            k in f.subject.lower()
            for k in (
                "выручка",
                "чистая прибыль",
                "средний чек",
                "фудкост",
                "фонд оплаты",
                "аренда заведения",
                "недостач",
            )
        )
    ][:12]
    if not key_facts:
        key_facts = facts[:8]

    ids: list[str] = []
    for fact in key_facts:
        title = f"{fact.subject}"
        existing = await session.scalar(
            select(KnowledgeRecord).where(
                KnowledgeRecord.company_id == company_id,
                KnowledgeRecord.title == title[:500],
            )
        )
        if existing:
            if existing.status != KnowledgeRecordStatus.active:
                existing.status = KnowledgeRecordStatus.active
                await session.flush()
            ids.append(str(existing.id))
            continue
        unit = (fact.value_structured or {}).get("unit") or ""
        origin = (fact.value_structured or {}).get("system_origin") or "workbook"
        body = (
            f"Метрика из workbook ({origin}): {fact.subject} = {fact.value_text} {unit}. "
            f"Период: {(fact.value_structured or {}).get('period') or '—'}. "
            "Источник подтверждён импортом файла; для управленческих решений сверяйте с 1C/RKeeper."
        )
        record = KnowledgeRecord(
            company_id=company_id,
            title=title[:500],
            body=body,
            record_type=KnowledgeRecordType.fact,
            status=KnowledgeRecordStatus.active,
            trust_index=0.78,
            source_refs=[
                {
                    "type": "observed_fact",
                    "id": str(fact.id),
                    "system_origin": origin,
                }
            ],
        )
        session.add(record)
        await session.flush()
        ids.append(str(record.id))
    await session.commit()
    return ids


async def _ensure_finance_kpis(session: AsyncSession, company_id: uuid.UUID) -> list[str]:
    ids: list[str] = []
    existing = await kpi_service.list_kpis(session, company_id=company_id)
    by_code = {k.code: k for k in existing}

    specs = [
        (
            "bistro_metric_count",
            "Число финансовых метрик workbook",
            {"op": "count_facts"},
            {"predicate": "finance_metric"},
            50.0,
        ),
    ]
    for code, name, formula, mapping, target in specs:
        if code in by_code:
            ids.append(str(by_code[code].id))
            continue
        kpi = await kpi_service.create_kpi(
            session,
            company_id=company_id,
            code=code,
            name=name,
            description="Пилот Бистро: счётчик импортированных finance_metric",
            unit="count",
            owner_name="Управляющий",
            formula=formula,
            source_mapping=mapping,
            target_value=target,
            activate=True,
        )
        ids.append(str(kpi.id))
    return ids
