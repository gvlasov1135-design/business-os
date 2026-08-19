"""Заседание ИИ-агентов: общий стол + личные каналы."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.analysis import context_builder
from modules.analysis.models import AIAnalysis
from modules.council.models import (
    CouncilAgent,
    CouncilChannel,
    CouncilMessage,
    CouncilMessageRole,
    CouncilSession,
    CouncilSessionStatus,
)
from modules.council.schemas import CouncilMessageCreate, CouncilSessionCreate
from modules.identity.service import get_company
from modules.llm import AgentProfile, LLMRequest, get_llm_gateway

TABLE_AGENTS = (CouncilAgent.executive, CouncilAgent.sales, CouncilAgent.critic)

AGENT_LABELS = {
    CouncilAgent.executive: "Executive AI",
    CouncilAgent.sales: "Sales AI",
    CouncilAgent.critic: "Critic AI",
    CouncilAgent.data_doctor: "Data Doctor",
}


def _profile_for(agent: CouncilAgent) -> AgentProfile:
    return {
        CouncilAgent.executive: AgentProfile.executive,
        CouncilAgent.sales: AgentProfile.sales,
        CouncilAgent.critic: AgentProfile.critic,
        CouncilAgent.data_doctor: AgentProfile.data_doctor,
    }[agent]


def _reply_text(agent: CouncilAgent, content: dict[str, Any], user_message: str) -> str:
    if content.get("reply"):
        return str(content["reply"])
    if agent == CouncilAgent.critic:
        objections = content.get("objections") or []
        if objections:
            return "Critic: " + " ".join(str(o) for o in objections[:2])
        return "Critic: возражений по доказательности пока нет — решение за человеком."
    if agent == CouncilAgent.data_doctor:
        return str(
            content.get("explanation")
            or "Data Doctor: опишите код DQ-проблемы или пришлите симптомы данных."
        )
    recs = content.get("recommendations") or []
    obs = content.get("observations") or []
    parts: list[str] = []
    label = AGENT_LABELS[agent]
    if obs:
        first = obs[0]
        text = first.get("text") if isinstance(first, dict) else str(first)
        parts.append(str(text))
    if recs:
        first = recs[0]
        if isinstance(first, dict):
            parts.append(f"Рекомендую: {first.get('title') or first.get('body')}")
        else:
            parts.append(f"Рекомендую: {first}")
    if not parts:
        parts.append(f"Услышал вопрос «{user_message[:120]}». Опираюсь только на подтверждённый контекст.")
    return f"{label}: " + " ".join(parts)


async def get_session(session: AsyncSession, session_id: uuid.UUID) -> CouncilSession:
    row = await session.get(CouncilSession, session_id)
    if row is None:
        raise AppError("Council session not found", status_code=404, code="council_not_found")
    return row


async def list_messages(session: AsyncSession, session_id: uuid.UUID) -> list[CouncilMessage]:
    result = await session.scalars(
        select(CouncilMessage)
        .where(CouncilMessage.session_id == session_id)
        .order_by(CouncilMessage.created_at.asc())
    )
    return list(result.all())


async def list_sessions(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
) -> list[CouncilSession]:
    result = await session.scalars(
        select(CouncilSession)
        .where(CouncilSession.company_id == company_id)
        .order_by(CouncilSession.created_at.desc())
    )
    return list(result.all())


async def create_session(
    session: AsyncSession,
    payload: CouncilSessionCreate,
) -> CouncilSession:
    await get_company(session, payload.company_id)

    analysis: AIAnalysis | None = None
    if payload.analysis_id is not None:
        analysis = await session.get(AIAnalysis, payload.analysis_id)
        if analysis is None or analysis.company_id != payload.company_id:
            raise AppError(
                "Analysis not found for company",
                status_code=404,
                code="council_analysis_not_found",
            )

    context = await context_builder.build_executive_context(
        session,
        payload.company_id,
        question=payload.topic,
    )
    if analysis is not None:
        context = {
            **context,
            "analysis_id": str(analysis.id),
            "analysis_question": analysis.question,
            "analysis_output": analysis.output or {},
            "analysis_blocked": analysis.blocked,
        }

    topic = (payload.topic or "").strip() or (
        analysis.question if analysis is not None else "Заседание по Sales SLA"
    )

    row = CouncilSession(
        company_id=payload.company_id,
        analysis_id=payload.analysis_id,
        topic=topic[:500],
        status=CouncilSessionStatus.open,
        context_snapshot=context,
    )
    session.add(row)
    await session.flush()

    agenda = (
        f"Заседание открыто. Повестка: {topic}. "
        "Общий стол — Executive, Sales и Critic. "
        "Личные чаты — с каждым агентом и Data Doctor. "
        "Решения принимает человек."
    )
    session.add(
        CouncilMessage(
            session_id=row.id,
            company_id=payload.company_id,
            channel=CouncilChannel.table,
            role=CouncilMessageRole.system,
            agent=None,
            body=agenda,
        )
    )
    await write_audit(
        session,
        action="council.session_created",
        entity_type="council_session",
        entity_id=row.id,
        company_id=payload.company_id,
        payload={"analysis_id": str(payload.analysis_id) if payload.analysis_id else None},
    )
    await session.commit()
    await session.refresh(row)
    return row


async def _agent_reply(
    *,
    gateway,
    agent: CouncilAgent,
    user_message: str,
    context: dict[str, Any],
) -> str:
    response = gateway.complete(
        LLMRequest(
            agent=_profile_for(agent),
            prompt=user_message,
            context={
                **context,
                "council_mode": True,
                "council_agent": agent.value,
            },
        )
    )
    return _reply_text(agent, response.content, user_message)


async def post_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    payload: CouncilMessageCreate,
) -> list[CouncilMessage]:
    row = await get_session(session, session_id)
    if row.status != CouncilSessionStatus.open:
        raise AppError("Council session is closed", status_code=409, code="council_closed")

    body = payload.body.strip()
    if not body:
        raise AppError("Message body is required", status_code=400, code="council_empty_message")

    if payload.channel == CouncilChannel.private:
        if payload.agent is None:
            raise AppError(
                "Private channel requires agent",
                status_code=400,
                code="council_agent_required",
            )
    elif payload.agent is not None:
        raise AppError(
            "Table channel does not accept a single agent target",
            status_code=400,
            code="council_table_no_agent",
        )

    created: list[CouncilMessage] = []
    user_msg = CouncilMessage(
        session_id=row.id,
        company_id=row.company_id,
        channel=payload.channel,
        role=CouncilMessageRole.user,
        agent=payload.agent if payload.channel == CouncilChannel.private else None,
        body=body,
    )
    session.add(user_msg)
    await session.flush()
    created.append(user_msg)

    gateway = get_llm_gateway()
    context = dict(row.context_snapshot or {})
    recent = await list_messages(session, row.id)
    context["council_recent"] = [
        {
            "channel": m.channel.value,
            "role": m.role.value,
            "agent": m.agent.value if m.agent else None,
            "body": m.body[:400],
        }
        for m in recent[-12:]
    ]

    targets: list[CouncilAgent]
    if payload.channel == CouncilChannel.private:
        assert payload.agent is not None
        targets = [payload.agent]
    else:
        targets = list(TABLE_AGENTS)

    for agent in targets:
        reply = await _agent_reply(
            gateway=gateway,
            agent=agent,
            user_message=body,
            context=context,
        )
        agent_msg = CouncilMessage(
            session_id=row.id,
            company_id=row.company_id,
            channel=payload.channel,
            role=CouncilMessageRole.agent,
            agent=agent,
            body=reply,
        )
        session.add(agent_msg)
        await session.flush()
        created.append(agent_msg)

    await write_audit(
        session,
        action="council.message_posted",
        entity_type="council_session",
        entity_id=row.id,
        company_id=row.company_id,
        payload={
            "channel": payload.channel.value,
            "agent": payload.agent.value if payload.agent else None,
            "replies": len(created) - 1,
        },
    )
    await session.commit()
    for item in created:
        await session.refresh(item)
    return created


async def close_session(session: AsyncSession, session_id: uuid.UUID) -> CouncilSession:
    row = await get_session(session, session_id)
    if row.status == CouncilSessionStatus.closed:
        return row
    row.status = CouncilSessionStatus.closed
    session.add(
        CouncilMessage(
            session_id=row.id,
            company_id=row.company_id,
            channel=CouncilChannel.table,
            role=CouncilMessageRole.system,
            agent=None,
            body="Заседание закрыто. Итог фиксируется человеком в Решениях.",
        )
    )
    await write_audit(
        session,
        action="council.session_closed",
        entity_type="council_session",
        entity_id=row.id,
        company_id=row.company_id,
        payload={},
    )
    await session.commit()
    await session.refresh(row)
    return row
