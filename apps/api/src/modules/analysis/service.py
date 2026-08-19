import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.analysis import agents as agent_orchestrator
from modules.analysis import context_builder
from modules.analysis.models import (
    AIAnalysis,
    AIAnalysisStatus,
    AgentOpinion,
    Recommendation,
    RecommendationStatus,
)
from modules.analysis.schemas import AnalysisOutput
from modules.identity.service import get_company
from modules.llm import AgentProfile, LLMRequest, get_llm_gateway
from modules.quality import service as quality_service


def _recommendation_items(raw: list[Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in raw:
        if isinstance(entry, dict):
            title = str(entry.get("title") or entry.get("summary") or "Рекомендация")
            body = str(entry.get("body") or entry.get("text") or entry.get("detail") or title)
            priority = str(entry.get("priority") or "medium")
            items.append({"title": title, "body": body, "priority": priority})
        else:
            text = str(entry)
            items.append({"title": text[:120], "body": text, "priority": "medium"})
    return items


def _persist_opinion(
    session: AsyncSession,
    *,
    analysis: AIAnalysis,
    agent: str,
    content: dict[str, Any],
) -> AgentOpinion:
    dna = content.get("decision_dna") or agent_orchestrator.decision_dna(agent)
    row = AgentOpinion(
        analysis_id=analysis.id,
        company_id=analysis.company_id,
        agent=agent,
        decision_dna=dna,
        opinion=content,
        evidence=list(content.get("sources") or []),
        missing_data=list(content.get("missing_data") or []),
        trust_index=float(content.get("trust_index") or 0),
    )
    session.add(row)
    return row


async def create_analysis(
    session: AsyncSession,
    company_id: uuid.UUID,
    question: str,
) -> AIAnalysis:
    await get_company(session, company_id)

    gate = await quality_service.evaluate_analysis_gate(session, company_id)
    if gate.blocked:
        analysis = AIAnalysis(
            company_id=company_id,
            question=question,
            status=AIAnalysisStatus.blocked,
            blocked=True,
            block_reasons=list(gate.reasons),
            context_snapshot={"gate": gate.model_dump()},
            output=AnalysisOutput(
                facts=[],
                observations=[],
                hypotheses=[],
                recommendations=[],
                missing_data=[],
                sources=[],
                trust_index=0,
                blocked=True,
            ).model_dump(),
            trust_index=0.0,
        )
        session.add(analysis)
        await session.flush()
        await write_audit(
            session,
            action="analysis.blocked",
            entity_type="ai_analysis",
            entity_id=analysis.id,
            company_id=company_id,
            payload={"reasons": list(gate.reasons)},
        )
        await session.commit()
        await session.refresh(analysis)
        return analysis

    context_snapshot = await context_builder.build_executive_context(
        session, company_id, question=question
    )
    missing = context_builder.missing_context_reasons(context_snapshot)
    if missing:
        analysis = AIAnalysis(
            company_id=company_id,
            question=question,
            status=AIAnalysisStatus.blocked,
            blocked=True,
            block_reasons=missing,
            context_snapshot={"missing_data": missing, **context_snapshot},
            output=AnalysisOutput(
                facts=[],
                observations=[],
                hypotheses=[],
                recommendations=[],
                missing_data=missing,
                sources=[],
                trust_index=0,
                blocked=True,
            ).model_dump(),
            trust_index=0.0,
        )
        session.add(analysis)
        await session.flush()
        await write_audit(
            session,
            action="analysis.blocked_missing_data",
            entity_type="ai_analysis",
            entity_id=analysis.id,
            company_id=company_id,
            payload={"missing": missing},
        )
        await session.commit()
        await session.refresh(analysis)
        return analysis

    gateway = get_llm_gateway()

    exec_prompt = await agent_orchestrator.render_agent_prompt(
        session, company_id, AgentProfile.executive, question
    )
    sales_prompt = await agent_orchestrator.render_agent_prompt(
        session, company_id, AgentProfile.sales, question
    )
    exec_dna = await agent_orchestrator.load_decision_dna(
        session, company_id, AgentProfile.executive
    )
    sales_dna = await agent_orchestrator.load_decision_dna(session, company_id, AgentProfile.sales)
    critic_dna = await agent_orchestrator.load_decision_dna(session, company_id, AgentProfile.critic)

    # Независимые прогоны: агенты не видят выводы друг друга; context проходит redaction в Gateway
    executive = gateway.complete(
        LLMRequest(
            agent=AgentProfile.executive,
            prompt=exec_prompt["prompt"],
            context={**context_snapshot, "decision_dna": exec_dna},
        )
    )
    sales = gateway.complete(
        LLMRequest(
            agent=AgentProfile.sales,
            prompt=sales_prompt["prompt"],
            context={**context_snapshot, "decision_dna": sales_dna},
        )
    )

    opinions = {
        "executive": dict(executive.content),
        "sales": dict(sales.content),
    }
    opinions["executive"]["decision_dna"] = exec_dna
    opinions["sales"]["decision_dna"] = sales_dna
    disagreements = agent_orchestrator.detect_disagreements(opinions)

    critic = gateway.complete(
        LLMRequest(
            agent=AgentProfile.critic,
            prompt="Проверь доказательность независимых мнений",
            context={
                "opinions": opinions,
                "disagreements": disagreements,
                "decision_dna": critic_dna,
                "analysis_output": {
                    "sources": (executive.content.get("sources") or [])
                    + (sales.content.get("sources") or []),
                    "hypotheses": (executive.content.get("hypotheses") or [])
                    + (sales.content.get("hypotheses") or []),
                    "missing_data": (executive.content.get("missing_data") or [])
                    + (sales.content.get("missing_data") or []),
                },
            },
        )
    )

    synthesized = agent_orchestrator.synthesize(
        question=question,
        opinions=opinions,
        disagreements=disagreements,
        critic=critic.content,
    )

    try:
        validated = AnalysisOutput.model_validate(
            {
                k: synthesized[k]
                for k in (
                    "facts",
                    "observations",
                    "hypotheses",
                    "recommendations",
                    "missing_data",
                    "sources",
                    "trust_index",
                    "blocked",
                )
                if k in synthesized
            }
        )
    except ValidationError as exc:
        raise AppError(
            f"Analysis output schema invalid: {exc}",
            status_code=500,
            code="analysis_output_invalid",
        ) from exc

    output_payload = validated.model_dump()
    pending_requests = list(context_snapshot.get("pending_data_requests") or [])
    if pending_requests:
        merged_missing = list(output_payload.get("missing_data") or [])
        for item in pending_requests:
            if item not in merged_missing:
                merged_missing.append(item)
        output_payload["missing_data"] = merged_missing
        # Soft signal: analysis continues, but trust reflects open data requests
        output_payload["trust_index"] = round(min(float(output_payload.get("trust_index") or 0), 0.72), 3)
    output_payload["critic"] = critic.content
    output_payload["disagreements"] = disagreements
    output_payload["synthesis"] = synthesized.get("synthesis")
    output_payload["finance_briefing"] = synthesized.get("finance_briefing") or (
        opinions.get("executive") or {}
    ).get("finance_briefing")
    output_payload["rule_versions"] = {
        "prompt_executive": {
            "rule_code": exec_prompt.get("rule_code"),
            "rule_version_id": exec_prompt.get("rule_version_id"),
            "rule_version_number": exec_prompt.get("rule_version_number"),
        },
        "prompt_sales": {
            "rule_code": sales_prompt.get("rule_code"),
            "rule_version_id": sales_prompt.get("rule_version_id"),
            "rule_version_number": sales_prompt.get("rule_version_number"),
        },
        "dna_executive": {
            "rule_code": exec_dna.get("rule_code"),
            "rule_version_id": exec_dna.get("rule_version_id"),
            "rule_version_number": exec_dna.get("rule_version_number"),
        },
        "dna_sales": {
            "rule_code": sales_dna.get("rule_code"),
            "rule_version_id": sales_dna.get("rule_version_id"),
            "rule_version_number": sales_dna.get("rule_version_number"),
        },
        "dna_critic": {
            "rule_code": critic_dna.get("rule_code"),
            "rule_version_id": critic_dna.get("rule_version_id"),
            "rule_version_number": critic_dna.get("rule_version_number"),
        },
    }
    output_payload["agent_opinions"] = {
        name: {
            "agent": name,
            "decision_dna": content.get("decision_dna") or agent_orchestrator.decision_dna(name),
            "recommendations": content.get("recommendations"),
            "observations": content.get("observations"),
            "hypotheses": content.get("hypotheses"),
            "missing_data": content.get("missing_data"),
            "sources": content.get("sources"),
            "trust_index": content.get("trust_index"),
        }
        for name, content in opinions.items()
    }

    analysis = AIAnalysis(
        company_id=company_id,
        question=question,
        status=AIAnalysisStatus.ready,
        blocked=False,
        block_reasons=[],
        context_snapshot=context_snapshot,
        output=output_payload,
        trust_index=float(output_payload.get("trust_index") or validated.trust_index),
    )
    session.add(analysis)
    await session.flush()

    _persist_opinion(session, analysis=analysis, agent="executive", content=opinions["executive"])
    _persist_opinion(session, analysis=analysis, agent="sales", content=opinions["sales"])
    _persist_opinion(
        session,
        analysis=analysis,
        agent="critic",
        content={**critic.content, "decision_dna": agent_orchestrator.decision_dna("critic")},
    )

    # В Decision Memory попадает синтезированная рекомендация (первая), затем агентские
    for item in _recommendation_items(validated.recommendations):
        session.add(
            Recommendation(
                analysis_id=analysis.id,
                title=item["title"],
                body=item["body"],
                priority=item["priority"],
                status=RecommendationStatus.proposed,
            )
        )

    await session.flush()
    await write_audit(
        session,
        action="analysis.created",
        entity_type="ai_analysis",
        entity_id=analysis.id,
        company_id=company_id,
        payload={
            "status": analysis.status.value,
            "trust_index": analysis.trust_index,
            "via": "llm_gateway",
            "agents": ["executive", "sales", "critic"],
            "disagreement_count": len(disagreements),
            "independent_runs": True,
        },
    )
    from modules.outbox import service as outbox_service

    await outbox_service.enqueue(
        session,
        event_type="analysis.ready",
        aggregate_type="ai_analysis",
        aggregate_id=analysis.id,
        company_id=company_id,
        payload={
            "question": question,
            "trust_index": analysis.trust_index,
            "disagreement_count": len(disagreements),
        },
    )
    await session.commit()
    await session.refresh(analysis)
    return analysis


async def get_analysis(session: AsyncSession, analysis_id: uuid.UUID) -> AIAnalysis:
    analysis = await session.get(AIAnalysis, analysis_id)
    if analysis is None:
        raise AppError("Analysis not found", status_code=404, code="analysis_not_found")
    return analysis


async def list_recommendations(
    session: AsyncSession,
    analysis_id: uuid.UUID,
) -> list[Recommendation]:
    result = await session.scalars(
        select(Recommendation)
        .where(Recommendation.analysis_id == analysis_id)
        .order_by(Recommendation.created_at)
    )
    return list(result.all())


async def list_agent_opinions(
    session: AsyncSession,
    analysis_id: uuid.UUID,
) -> list[AgentOpinion]:
    result = await session.scalars(
        select(AgentOpinion)
        .where(AgentOpinion.analysis_id == analysis_id)
        .order_by(AgentOpinion.created_at)
    )
    return list(result.all())
