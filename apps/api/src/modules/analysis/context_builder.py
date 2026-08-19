"""Context Builder — собирает доказательный контекст для управленческих агентов.

Граница доступа AI (A-006): только Knowledge Records, Observed Facts,
Alignment Evidence и ссылки. Без прямой выгрузки сырой CRM.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.alignment.models import AlignmentIssue, AlignmentIssueStatus
from modules.ingestion.models import ObservedFact
from modules.knowledge.models import KnowledgeRecord, KnowledgeRecordStatus
from modules.kpi.models import KpiStatus
from modules.kpi import service as kpi_service


async def build_executive_context(
    session: AsyncSession,
    company_id: uuid.UUID,
    question: str | None = None,
) -> dict[str, Any]:
    knowledge = list(
        (
            await session.scalars(
                select(KnowledgeRecord).where(
                    KnowledgeRecord.company_id == company_id,
                    KnowledgeRecord.status == KnowledgeRecordStatus.active,
                )
            )
        ).all()
    )
    facts = list(
        (await session.scalars(select(ObservedFact).where(ObservedFact.company_id == company_id))).all()
    )
    issues = list(
        (await session.scalars(select(AlignmentIssue).where(AlignmentIssue.company_id == company_id))).all()
    )
    confirmed = [i for i in issues if i.status == AlignmentIssueStatus.confirmed]
    accepted = [i for i in issues if i.status == AlignmentIssueStatus.accepted_deviation]
    open_issues = [i for i in issues if i.status == AlignmentIssueStatus.open]
    needs_data = [i for i in issues if i.status == AlignmentIssueStatus.needs_data]

    def _issue_payload(i: AlignmentIssue) -> dict[str, Any]:
        return {
            "id": str(i.id),
            "status": i.status.value,
            "normative_value": i.normative_value,
            "actual_value": i.actual_value,
            "deviation_value": i.deviation_value,
            "severity": i.severity.value,
            "evidence": i.evidence,
            "rule_code": (i.evidence or {}).get("rule_code"),
            "proposed_change": (i.evidence or {}).get("proposed_change"),
            "data_request": (i.evidence or {}).get("data_request"),
        }

    kpis = [
        k
        for k in await kpi_service.list_kpis(session, company_id=company_id)
        if k.status == KpiStatus.active
    ]
    kpi_payload: list[dict[str, Any]] = []
    for kpi in kpis:
        versions = await kpi_service.list_versions(session, kpi.id)
        current = next((v for v in versions if str(v.id) == str(kpi.current_version_id)), None)
        snaps = await kpi_service.list_snapshots(session, kpi_id=kpi.id)
        latest = snaps[0] if snaps else None
        kpi_payload.append(
            {
                "id": str(kpi.id),
                "code": kpi.code,
                "name": kpi.name,
                "unit": kpi.unit,
                "owner_name": kpi.owner_name,
                "trust_index": kpi.trust_index,
                "formula_text": current.formula_text if current else None,
                "formula": current.formula if current else None,
                "source_mapping": current.source_mapping if current else None,
                "target": current.target_value if current else None,
                "latest_snapshot": (
                    {
                        "id": str(latest.id),
                        "actual": latest.actual_value,
                        "target": latest.target_value,
                        "status": latest.status.value,
                        "conflict_flag": latest.conflict_flag,
                        "trust_index": latest.trust_index,
                        "sources": latest.sources,
                        "lineage": latest.lineage,
                    }
                    if latest
                    else None
                ),
            }
        )

    from modules.knowledge import service as knowledge_service

    relations = await knowledge_service.list_relations(session, company_id=company_id)
    relation_payload = [
        {
            "id": str(r.id),
            "from_record_id": str(r.from_record_id),
            "to_record_id": str(r.to_record_id),
            "relation_type": r.relation_type.value,
        }
        for r in relations
    ]

    search_hits: list[dict[str, Any]] = []
    if question:
        tokens = [t for t in re.findall(r"[A-Za-zА-Яа-я0-9\-]+", question) if len(t) >= 4]
        for token in tokens[:3]:
            hits = await knowledge_service.search_knowledge(
                session, company_id=company_id, query=token, limit=5
            )
            for hit in hits:
                search_hits.append(
                    {
                        "id": str(hit.id),
                        "title": hit.title,
                        "body": hit.body[:240],
                        "query_token": token,
                        "trust_index": hit.trust_index,
                    }
                )
        # de-dupe by id keeping first
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in search_hits:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            unique.append(item)
        search_hits = unique

    pending_data_requests = [
        str((i.evidence or {}).get("data_request", {}).get("message") or "Запрошены дополнительные данные")
        for i in needs_data
    ]

    return {
        "knowledge": [
            {
                "id": str(k.id),
                "title": k.title,
                "body": k.body,
                "status": k.status.value,
                "trust_index": k.trust_index,
                "record_type": k.record_type.value,
                "source_refs": k.source_refs or [],
                "verified": True,
            }
            for k in knowledge
        ],
        "knowledge_relations": relation_payload,
        "knowledge_search_hits": search_hits,
        "facts": [
            {
                "id": str(f.id),
                "subject": f.subject,
                "predicate": f.predicate,
                "value_text": f.value_text,
                "value_structured": f.value_structured,
                "trust_index": f.trust_index,
                "lineage": f.lineage,
            }
            for f in facts
        ],
        "kpis": kpi_payload,
        "alignment_issues": {
            "verified": [_issue_payload(i) for i in confirmed],
            "accepted_deviations": [_issue_payload(i) for i in accepted],
            "needs_data": [_issue_payload(i) for i in needs_data],
            "unverified_evidence": [
                {
                    "id": str(i.id),
                    "status": i.status.value,
                    "deviation_value": i.deviation_value,
                    "marked": "unverified_evidence",
                    "rule_code": (i.evidence or {}).get("rule_code"),
                }
                for i in open_issues
            ],
        },
        "pending_data_requests": pending_data_requests,
        "access_policy": {
            "raw_crm_allowed": False,
            "original_documents_for_agents": False,
            "source_links_allowed": True,
        },
    }


def missing_context_reasons(context: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not context.get("knowledge"):
        missing.append("Нет активных KnowledgeRecord")
    if not context.get("facts"):
        missing.append("Нет ObservedFact")
    return missing
