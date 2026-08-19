import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.alignment.models import AlignmentIssue, AlignmentIssueStatus
from modules.analysis.models import AIAnalysis
from modules.decisions.models import Decision
from modules.documents.intelligence_models import ExtractedStatement, StatementStatus
from modules.documents.models import Document
from modules.executive.schemas import ExecutiveReadinessResponse, MetricBlock
from modules.identity.service import get_company
from modules.ingestion.models import ObservedFact, Source
from modules.knowledge.models import KnowledgeRecord, KnowledgeRecordStatus
from modules.kpi import service as kpi_service
from modules.kpi.models import KpiStatus
from modules.quality import service as quality_service
from modules.quality.models import DataQualityIssue, IssueStatus
from modules.resolution.models import CandidateStatus, EntityMatchCandidate


def _status(score: float, *, blocked: bool = False) -> str:
    if blocked:
        return "blocked"
    if score >= 0.75:
        return "ready"
    if score >= 0.45:
        return "warn"
    return "blocked"


async def build_readiness(
    session: AsyncSession,
    company_id: uuid.UUID,
) -> ExecutiveReadinessResponse:
    await get_company(session, company_id)

    gate = await quality_service.evaluate_analysis_gate(session, company_id)

    sources = list(
        (await session.scalars(select(Source).where(Source.company_id == company_id))).all()
    )
    facts = list(
        (await session.scalars(select(ObservedFact).where(ObservedFact.company_id == company_id))).all()
    )
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
    documents = list(
        (await session.scalars(select(Document).where(Document.company_id == company_id))).all()
    )
    confirmed_statements = int(
        await session.scalar(
            select(func.count())
            .select_from(ExtractedStatement)
            .join(Document, Document.id == ExtractedStatement.document_id)
            .where(
                Document.company_id == company_id,
                ExtractedStatement.status == StatementStatus.confirmed,
            )
        )
        or 0
    )
    issues = list(
        (
            await session.scalars(select(AlignmentIssue).where(AlignmentIssue.company_id == company_id))
        ).all()
    )
    open_dq = int(
        await session.scalar(
            select(func.count())
            .select_from(DataQualityIssue)
            .where(
                DataQualityIssue.company_id == company_id,
                DataQualityIssue.status == IssueStatus.open,
            )
        )
        or 0
    )
    pending_er = int(
        await session.scalar(
            select(func.count())
            .select_from(EntityMatchCandidate)
            .where(
                EntityMatchCandidate.company_id == company_id,
                EntityMatchCandidate.status == CandidateStatus.pending,
                EntityMatchCandidate.blocks_analysis.is_(True),
            )
        )
        or 0
    )

    # Completeness: required pillars present
    pillars = {
        "source": bool(sources),
        "facts": bool(facts),
        "knowledge": bool(knowledge),
        "documents": bool(documents),
        "confirmed_statements": confirmed_statements > 0,
    }
    completeness_score = sum(1 for v in pillars.values() if v) / len(pillars)

    # Trust: average of knowledge + facts (+ kpi)
    trust_values = [float(k.trust_index) for k in knowledge] + [float(f.trust_index) for f in facts]
    kpis = [k for k in await kpi_service.list_kpis(session, company_id=company_id) if k.status == KpiStatus.active]
    trust_values.extend(float(k.trust_index) for k in kpis)
    trust_avg = sum(trust_values) / len(trust_values) if trust_values else 0.0

    # Alignment score: confirmed+accepted / all issues
    confirmed_align = [i for i in issues if i.status == AlignmentIssueStatus.confirmed]
    accepted_align = [i for i in issues if i.status == AlignmentIssueStatus.accepted_deviation]
    open_align = [i for i in issues if i.status == AlignmentIssueStatus.open]
    needs_data_align = [i for i in issues if i.status == AlignmentIssueStatus.needs_data]
    resolved = confirmed_align + accepted_align
    if issues:
        alignment_score = len(resolved) / len(issues)
    elif knowledge:
        alignment_score = 0.8
    else:
        alignment_score = 0.0

    # Document health: confirmed statements relative to documents
    if not documents:
        doc_health = 0.0
        doc_detail = "Нет документов"
    else:
        doc_health = min(1.0, confirmed_statements / max(len(documents), 1))
        doc_detail = f"{confirmed_statements} подтверждённых утверждений / {len(documents)} док."

    # KPI health
    if not kpis:
        kpi_score = 0.4
        kpi_detail = "KPI не определены"
        kpi_status = "warn"
    else:
        score_sum = 0.0
        for kpi in kpis:
            snaps = await kpi_service.list_snapshots(session, kpi_id=kpi.id)
            if not snaps or snaps[0].actual_value is None:
                continue
            score_sum += 0.55 if snaps[0].conflict_flag else 1.0
        kpi_score = score_sum / len(kpis)
        kpi_detail = f"{len(kpis)} KPI, взвешенный снимок={round(kpi_score, 2)}"
        kpi_status = _status(kpi_score)

    limitations: list[str] = list(gate.reasons)
    if open_align:
        limitations.append(f"Открытых alignment issues: {len(open_align)}")
    if needs_data_align:
        limitations.append(f"Запросов доп. данных (needs_data): {len(needs_data_align)}")
    if open_dq:
        limitations.append(f"Открытых DQ issues: {open_dq}")
    if pending_er:
        limitations.append(f"Неподтверждённый Entity Resolution: {pending_er}")

    def _sla_axis(issue: AlignmentIssue) -> dict[str, Any]:
        rule = (issue.evidence or {}).get("rule_code")
        proposal = (issue.evidence or {}).get("proposed_change")
        axis = "deadline"
        summary = ""
        if issue.normative_value.get("role") is not None or (rule and "responsible" in str(rule)):
            axis = "responsible"
            summary = (
                f"роль «{issue.normative_value.get('role')}» vs "
                f"исполнитель «{issue.actual_value.get('actual_actor')}»"
            )
        elif issue.normative_value.get("stages") is not None or (rule and "process" in str(rule)):
            axis = "stages"
            skipped = issue.actual_value.get("stages_skipped") or []
            summary = f"пропуск: {', '.join(skipped) or '—'}"
        elif issue.normative_value.get("minutes") is not None:
            axis = "deadline"
            summary = (
                f"{issue.actual_value.get('minutes')} vs {issue.normative_value.get('minutes')} мин "
                f"(Δ {issue.deviation_value.get('minutes')})"
            )
        return {
            "type": "sla_axis",
            "axis": axis,
            "id": str(issue.id),
            "status": issue.status.value,
            "severity": issue.severity.value,
            "summary": summary,
            "proposed_change_title": (proposal or {}).get("title") if proposal else None,
            "rule_code": rule,
        }

    evidence_preview: list[dict[str, Any]] = []
    for k in knowledge[:4]:
        evidence_preview.append(
            {
                "type": "knowledge",
                "id": str(k.id),
                "title": k.title,
                "trust_index": k.trust_index,
            }
        )
    for issue in resolved[:6]:
        evidence_preview.append(_sla_axis(issue))
    for issue in needs_data_align[:3]:
        item = _sla_axis(issue)
        item["data_request"] = (issue.evidence or {}).get("data_request")
        evidence_preview.append(item)

    sla_axes = {
        "deadline": sum(1 for i in resolved if _sla_axis(i)["axis"] == "deadline"),
        "responsible": sum(1 for i in resolved if _sla_axis(i)["axis"] == "responsible"),
        "stages": sum(1 for i in resolved if _sla_axis(i)["axis"] == "stages"),
        "proposed_changes": sum(
            1 for i in confirmed_align if (i.evidence or {}).get("proposed_change")
        ),
        "needs_data": len(needs_data_align),
    }

    latest_analysis = await session.scalar(
        select(AIAnalysis)
        .where(AIAnalysis.company_id == company_id)
        .order_by(AIAnalysis.created_at.desc())
        .limit(1)
    )
    latest_decision = await session.scalar(
        select(Decision)
        .where(Decision.company_id == company_id)
        .order_by(Decision.created_at.desc())
        .limit(1)
    )

    return ExecutiveReadinessResponse(
        company_id=company_id,
        analysis_ready=not gate.blocked,
        gate_reasons=list(gate.reasons),
        completeness=MetricBlock(
            score=round(completeness_score, 3),
            label="Completeness",
            detail=", ".join(k for k, v in pillars.items() if v) or "нет данных",
            status=_status(completeness_score, blocked=not pillars["facts"]),
        ),
        trust_index=MetricBlock(
            score=round(trust_avg, 3),
            label="Trust Index",
            detail=f"по {len(trust_values)} элементам",
            status=_status(trust_avg),
        ),
        alignment_score=MetricBlock(
            score=round(alignment_score, 3),
            label="Alignment Score",
            detail=f"закрыто {len(resolved)} / {len(issues)} (confirm+accept)",
            status=_status(alignment_score, blocked=bool(open_align) and not resolved),
        ),
        document_health=MetricBlock(
            score=round(doc_health, 3),
            label="Document health",
            detail=doc_detail,
            status=_status(doc_health),
        ),
        kpi_health=MetricBlock(
            score=round(kpi_score, 3),
            label="KPI health",
            detail=kpi_detail,
            status=kpi_status,
        ),
        counts={
            "sources": len(sources),
            "facts": len(facts),
            "knowledge": len(knowledge),
            "documents": len(documents),
            "confirmed_statements": confirmed_statements,
            "alignment_issues": len(issues),
            "open_dq": open_dq,
            "pending_er_blocking": pending_er,
            "kpis": len(kpis),
            "sla_deadline": sla_axes["deadline"],
            "sla_responsible": sla_axes["responsible"],
            "sla_stages": sla_axes["stages"],
            "proposed_doc_changes": sla_axes["proposed_changes"],
            "needs_data": sla_axes["needs_data"],
        },
        latest_analysis_id=latest_analysis.id if latest_analysis else None,
        latest_decision_id=latest_decision.id if latest_decision else None,
        limitations=limitations,
        evidence_preview=evidence_preview,
        sla_axes=sla_axes,
    )
