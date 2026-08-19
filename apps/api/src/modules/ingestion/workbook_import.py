"""Import multi-sheet Excel workbook into ObservedFacts by logical source (1C / RKeeper / Storyhouse)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from modules.ingestion import service
from modules.ingestion.models import SourceType
from modules.ingestion.workbook_parse import parse_bistro_workbook

ORIGIN_SOURCES = {
    "1c": ("1c-finance", "1C — финансы и расходы"),
    "rkeeper": ("rkeeper-ops", "RKeeper — бар / кухня"),
    "storyhouse": ("storyhouse-analytics", "Storyhouse — аналитика"),
    "workbook": ("workbook-other", "Workbook — прочее"),
}


async def import_workbook(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    data: bytes,
    filename: str | None = None,
) -> dict[str, Any]:
    parsed = parse_bistro_workbook(data)
    metrics: list[dict[str, Any]] = list(parsed.get("metrics") or [])

    source_ids: dict[str, str] = {}
    for origin, (code, name) in ORIGIN_SOURCES.items():
        src = await service.get_or_create_source(
            session,
            company_id=company_id,
            code=code,
            name=name,
            source_type=SourceType.workbook,
            freshness_hours=24 * 90,
        )
        source_ids[origin] = str(src.id)

    imported = 0
    duplicates = 0
    fact_ids: list[str] = []
    by_origin: dict[str, int] = {}

    for metric in metrics:
        origin = str(metric.get("system_origin") or "workbook")
        source_id = uuid.UUID(source_ids.get(origin) or source_ids["workbook"])
        result = await service.import_metric_record(session, source_id, metric)
        if result.duplicate:
            duplicates += 1
        else:
            imported += 1
        if result.fact:
            fact_ids.append(str(result.fact.id))
        by_origin[origin] = by_origin.get(origin, 0) + 1

    return {
        "filename": filename,
        "workbook_kind": parsed.get("workbook_kind"),
        "notes": parsed.get("notes") or [],
        "sheets": parsed.get("sheets") or [],
        "source_ids": source_ids,
        "metrics_total": len(metrics),
        "imported": imported,
        "duplicates": duplicates,
        "by_origin": by_origin,
        "fact_ids": fact_ids[:50],
        "fact_count": len(fact_ids),
    }
