"""Единый LLM Gateway — единственная точка вызова AI-провайдеров.

Архитектура (A-006, AUDIT §34):
- управленческие агенты не ходят напрямую во внешние системы;
- критические данные не изменяются AI;
- output проходит schema validation на стороне вызывающего модуля.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from common.redaction import redact_context


class AgentProfile(str, Enum):
    executive = "executive"
    sales = "sales"
    data_doctor = "data_doctor"
    critic = "critic"
    document = "document"


@dataclass
class LLMRequest:
    agent: AgentProfile
    prompt: str
    context: dict[str, Any] = field(default_factory=dict)
    language: str = "ru"


@dataclass
class LLMResponse:
    agent: AgentProfile
    provider: str
    content: dict[str, Any]
    raw_text: str = ""


class LLMGateway:
    """Интерфейс gateway. MVP: mock provider без внешнего LLM."""

    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self.provider != "mock":
            raise NotImplementedError(f"Provider '{self.provider}' not configured for MVP")
        safe = LLMRequest(
            agent=request.agent,
            prompt=request.prompt,
            context=redact_context(request.context),
            language=request.language,
        )
        return _mock_complete(safe)


def get_llm_gateway() -> LLMGateway:
    return LLMGateway(provider="mock")


def _mock_complete(request: LLMRequest) -> LLMResponse:
    if request.context.get("council_mode"):
        content = _council_reply(request)
    elif request.agent == AgentProfile.data_doctor:
        content = _data_doctor(request.context)
    elif request.agent == AgentProfile.critic:
        content = _critic(request.context)
    elif request.agent == AgentProfile.executive:
        content = _executive(request.context, request.prompt)
    elif request.agent == AgentProfile.sales:
        content = _sales(request.context, request.prompt)
    else:
        content = {"message": "Document agent mock — extraction handled elsewhere"}

    return LLMResponse(
        agent=request.agent,
        provider="mock",
        content=content,
        raw_text=str(content),
    )


def _council_reply(request: LLMRequest) -> dict[str, Any]:
    """Короткие реплики для заседания (общий стол / личный чат)."""
    agent = request.agent
    prompt = (request.prompt or "").strip()
    facts = request.context.get("facts") or []
    knowledge = request.context.get("knowledge") or []
    alignment = request.context.get("alignment_issues") or {}
    verified = alignment.get("verified") or []
    needs = alignment.get("needs_data") or []
    pending = request.context.get("pending_data_requests") or []
    analysis_q = request.context.get("analysis_question")

    if agent == AgentProfile.data_doctor:
        if pending or needs:
            return {
                "reply": (
                    "Data Doctor: есть открытые запросы данных / needs_data. "
                    "Сначала закройте silent skip или догрузите CRM-поля, иначе анализ будет с ограничениями."
                )
            }
        return {
            "reply": (
                "Data Doctor: критических сигналов в контексте не вижу. "
                "Если есть код DQ — пришлите, разберу причину без снятия блокировок."
            )
        }

    if agent == AgentProfile.critic:
        bits = []
        if not verified and not knowledge:
            bits.append("мало подтверждённых знаний")
        if needs or pending:
            bits.append("есть незакрытые запросы данных")
        if not bits:
            bits.append("доказательная база есть, но итог — за человеком")
        return {"reply": "Critic: " + "; ".join(bits) + f". Вопрос: «{prompt[:80]}»."}

    if agent == AgentProfile.sales:
        if verified:
            return {
                "reply": (
                    f"Sales AI: по подтверждённой сверке вижу {len(verified)} закрытых оси. "
                    "На столе предлагаю зафиксировать владельца очереди и запрет silent skip. "
                    f"К вопросу: «{prompt[:80]}»."
                )
            }
        return {
            "reply": (
                "Sales AI: операционных подтверждений мало — не эскалирую очередь вслепую. "
                f"Уточните SLA-контекст. «{prompt[:80]}»"
            )
        }

    # executive
    finance_facts = [
        f
        for f in facts
        if (f.get("predicate") in {"finance_metric", "ops_metric", "expense_article"})
        or "выруч" in str(f.get("subject") or "").lower()
    ]
    if finance_facts and any(x in prompt.lower() for x in ("выруч", "прибыл", "бистро", "фудкост", "расход")):
        top = finance_facts[0]
        vs = top.get("value_structured") or top.get("value") or {}
        val = vs.get("value") if isinstance(vs, dict) else vs
        return {
            "reply": (
                f"Executive AI: в контексте {len(finance_facts)} финансовых/ops метрик. "
                f"Пример: {top.get('subject')} = {val}. "
                "Решение по Бистро принимает руководитель на основании 1C/RKeeper фактов."
            )
        }

    base = analysis_q or prompt
    return {
        "reply": (
            f"Executive AI: опираюсь на {len(knowledge)} знаний и {len(facts)} фактов. "
            + (
                f"Есть подтверждённые расхождения ({len(verified)}). "
                if verified
                else "Подтверждённых расхождений в контексте нет. "
            )
            + f"Повестка/вопрос: «{str(base)[:100]}». Решение принимает руководитель."
        )
    }


def _data_doctor(context: dict[str, Any]) -> dict[str, Any]:
    issue = context.get("issue") or {}
    code = str(issue.get("code") or "unknown")
    message = str(issue.get("message") or "")
    explanations = {
        "missing_lead_id": "В записи нет идентификатора лида — вероятно, выгрузка без ключа или ошибка маппинга полей.",
        "missing_created_at": "Отсутствует дата создания лида — без неё нельзя посчитать SLA первого контакта.",
        "missing_first_contact_at": "Нет времени первого контакта — либо контакт не зафиксирован в CRM, либо поле не выгружено.",
        "invalid_created_at": "Дата создания не разбирается как datetime — проверьте формат источника.",
        "invalid_first_contact_at": "Дата первого контакта невалидна — возможна ошибка коннектора или локали.",
        "contact_before_created": "Первый контакт раньше создания лида — нарушена последовательность дат.",
        "stale_source": "Источник устарел — обновите синхронизацию CRM перед критическим анализом.",
    }
    explanation = explanations.get(code, f"Проблема качества данных: {message or code}.")
    owner = "Владелец источника / Data Steward"
    if "contact" in code or "created" in code:
        owner = "Ответственный за CRM / Sales Ops"
    return {
        "explanation": explanation,
        "likely_cause": message or code,
        "suggested_fix": "Исправить запись в источнике и повторно импортировать; не обходить карантин вручную.",
        "suggested_owner": owner,
        "prepared_task": f"Исправить DQ issue `{code}` и подтвердить повторный импорт.",
        "read_only": True,
        "can_unblock_analysis": False,
    }


def _critic(context: dict[str, Any]) -> dict[str, Any]:
    output = context.get("analysis_output") or {}
    opinions = context.get("opinions") or {}
    objections: list[str] = []
    if not output.get("sources") and not any((o or {}).get("sources") for o in opinions.values()):
        objections.append("Нет явных ссылок на источники — вывод нельзя считать доказательным.")
    if output.get("hypotheses") or any((o or {}).get("hypotheses") for o in opinions.values()):
        objections.append("Есть гипотезы: не принимать их как подтверждённые факты.")
    if output.get("missing_data") or any((o or {}).get("missing_data") for o in opinions.values()):
        objections.append("Есть недостающие данные — решение должно учитывать ограничения.")
    if context.get("disagreements"):
        objections.append("Агенты расходятся во мнениях — нужен человеческий арбитраж.")
    if not objections:
        objections.append("Критических возражений нет, но операционные выводы требуют человеческого подтверждения.")
    return {
        "objections": objections,
        "risk_level": "medium" if len(objections) > 1 else "low",
        "verified_claims_only": True,
        "agent": "critic",
    }


def _sales(context: dict[str, Any], question: str) -> dict[str, Any]:
    """Профильный Sales AI — независимый прогон, без доступа к выводу Executive."""
    knowledge = context.get("knowledge") or []
    facts = context.get("facts") or []
    kpis = context.get("kpis") or []
    alignment = context.get("alignment_issues") or {}
    verified = alignment.get("verified") or []
    accepted = alignment.get("accepted_deviations") or []
    unverified = alignment.get("unverified_evidence") or []

    fact_entries = [
        {
            "subject": f.get("subject"),
            "predicate": f.get("predicate"),
            "value": f.get("value_structured") or f.get("value_text"),
            "fact_id": f.get("id"),
            "trust_index": f.get("trust_index"),
        }
        for f in facts
    ]
    sources: list[dict[str, Any]] = []
    for k in knowledge:
        sources.append({"type": "knowledge_record", "id": k.get("id")})
    for f in facts:
        sources.append({"type": "observed_fact", "id": f.get("id"), "lineage": f.get("lineage")})
    for kpi in kpis:
        sources.append({"type": "kpi", "id": kpi.get("id"), "code": kpi.get("code")})

    observations: list[Any] = []
    hypotheses: list[Any] = []
    recommendations: list[Any] = []
    missing_data: list[Any] = []

    q_lower = question.lower()
    sales_relevant = any(
        x in q_lower for x in ("лид", "l-1001", "sla", "контакт", "продаж", "этап", "ответствен")
    )
    finance_relevant = any(
        x in q_lower for x in ("выруч", "прибыл", "фудкост", "чек", "бистро", "1c", "rkeeper", "расход")
    )
    finance_facts = [
        f
        for f in facts
        if f.get("predicate") in {"finance_metric", "ops_metric", "expense_article"}
        or "выруч" in str(f.get("subject") or "").lower()
    ]

    finance_briefing: dict[str, Any] | None = None
    if (finance_relevant or finance_facts) and finance_facts:
        from modules.analysis.finance_brief import build_finance_briefing

        finance_briefing = build_finance_briefing(facts)
        risks = finance_briefing.get("risks") or []
        observations.append(
            {
                "text": finance_briefing.get("summary") or "Финансовая сводка по workbook.",
                "verified": True,
            }
        )
        for risk in risks[:3]:
            observations.append({"text": f"Ops-риск: {risk}", "verified": False})
        recommendations.append(
            {
                "title": "Сверить 1C и RKeeper и закрыть утечки маржи",
                "body": (
                    "Sales/Ops: "
                    + (risks[0] if risks else "держать контроль фудкоста.")
                    + " Сверить выручку кассы с P&L; по недостачам — владелец инвентаризации."
                ),
                "priority": "high",
            }
        )
    elif sales_relevant and (verified or accepted):
        for v in verified:
            rule = v.get("rule_code") or (v.get("evidence") or {}).get("rule_code")
            minutes = (v.get("deviation_value") or {}).get("minutes")
            skipped = (v.get("actual_value") or {}).get("stages_skipped")
            if minutes is not None:
                observations.append(
                    {
                        "text": (
                            f"SalesOps: подтверждённый срыв первого контакта "
                            f"(+{minutes} мин к нормативу), severity={v.get('severity')}."
                        ),
                        "alignment_issue_id": v.get("id"),
                        "verified": True,
                    }
                )
            elif skipped:
                observations.append(
                    {
                        "text": (
                            f"SalesOps: подтверждён пропуск этапов процесса "
                            f"({', '.join(skipped)}), severity={v.get('severity')}."
                        ),
                        "alignment_issue_id": v.get("id"),
                        "rule_code": rule,
                        "verified": True,
                    }
                )
            else:
                observations.append(
                    {
                        "text": f"SalesOps: подтверждённое расхождение ({rule}), severity={v.get('severity')}.",
                        "alignment_issue_id": v.get("id"),
                        "verified": True,
                    }
                )
            proposal = v.get("proposed_change") or {}
            if proposal.get("title"):
                observations.append(
                    {
                        "text": f"Черновик правки регламента: {proposal.get('title')}.",
                        "alignment_issue_id": v.get("id"),
                        "proposed_change": True,
                        "verified": True,
                    }
                )
        for a in accepted:
            role = (a.get("normative_value") or {}).get("role")
            actor = (a.get("actual_value") or {}).get("actual_actor")
            observations.append(
                {
                    "text": (
                        f"Принятое отклонение: роль «{role}», исполнитель «{actor}» — "
                        "очередь работает под ролью без смены норматива."
                    ),
                    "alignment_issue_id": a.get("id"),
                    "accepted_deviation": True,
                    "verified": True,
                }
            )
        if kpis:
            snap = (kpis[0].get("latest_snapshot") or {})
            observations.append(
                {
                    "text": (
                        f"KPI «{kpis[0].get('name')}»: actual={snap.get('actual')}, "
                        f"target={snap.get('target') or kpis[0].get('target')}."
                    ),
                    "kpi_id": kpis[0].get("id"),
                    "verified": True,
                }
            )
        hypotheses.append(
            {
                "text": (
                    "Вероятна перегрузка очереди, silent skip квалификации "
                    "или задержка назначения владельца лида."
                ),
                "confidence": "medium",
            }
        )
        recommendations.append(
            {
                "title": "Перебалансировать очередь и закрыть пропуск квалификации",
                "body": (
                    "С точки зрения Sales: закрепить дежурного владельца очереди, "
                    "эскалировать лиды старше SLA, запретить silent skip этапа квалификации "
                    "и опираться на подтверждённые факты + принятые отклонения."
                ),
                "priority": "critical",
            }
        )
    elif sales_relevant and not verified and not accepted:
        missing_data.append("Нет подтверждённого Alignment Issue для Sales-действия")
        recommendations.append(
            {
                "title": "Не менять очередь до подтверждения evidence",
                "body": "Sales AI не рекомендует операционные изменения без подтверждённой сверки.",
                "priority": "medium",
            }
        )
    else:
        observations.append({"text": "Sales AI: вопрос вне явного контура SLA/лидов — ограниченный ответ."})
        recommendations.append(
            {
                "title": "Уточнить sales-контекст вопроса",
                "body": "Сформулируйте вопрос про SLA, конверсию или очередь лидов.",
                "priority": "low",
            }
        )

    if unverified:
        observations.append(
            {
                "text": f"Непроверенные evidence ({len(unverified)}) не использовать для эскалации.",
                "verified": False,
            }
        )
    trust_values = [float(f.get("trust_index") or 0) for f in facts] + [
        float(k.get("trust_index") or 0) for k in knowledge
    ]
    for kpi in kpis:
        trust_values.append(float(kpi.get("trust_index") or 0))
    trust = sum(trust_values) / len(trust_values) if trust_values else 0.0

    return {
        "facts": fact_entries,
        "observations": observations,
        "hypotheses": hypotheses,
        "recommendations": recommendations,
        "missing_data": missing_data,
        "sources": sources,
        "trust_index": round(trust, 3),
        "blocked": False,
        "agent": "sales",
        "finance_briefing": finance_briefing,
        "decision_dna": {
            "role": "sales",
            "priorities": ["sla", "conversion", "queue_throughput"],
            "risk_tolerance": "medium",
            "bias": "operational_fix_now",
        },
    }


def _executive(context: dict[str, Any], question: str) -> dict[str, Any]:
    knowledge = context.get("knowledge") or []
    facts = context.get("facts") or []
    verified = (context.get("alignment_issues") or {}).get("verified") or []
    unverified = (context.get("alignment_issues") or {}).get("unverified_evidence") or []

    fact_entries = [
        {
            "subject": f.get("subject"),
            "predicate": f.get("predicate"),
            "value": f.get("value_structured") or f.get("value_text"),
            "fact_id": f.get("id"),
            "trust_index": f.get("trust_index"),
        }
        for f in facts
    ]
    knowledge_entries = [
        {
            "id": k.get("id"),
            "title": k.get("title"),
            "body": k.get("body"),
            "trust_index": k.get("trust_index"),
            "record_type": k.get("record_type"),
        }
        for k in knowledge
    ]
    sources: list[dict[str, Any]] = []
    for k in knowledge:
        sources.append({"type": "knowledge_record", "id": k.get("id")})
        for ref in k.get("source_refs") or []:
            sources.append(ref)
    for f in facts:
        sources.append({"type": "observed_fact", "id": f.get("id"), "lineage": f.get("lineage")})

    q_lower = question.lower()
    mentions_l1001 = "l-1001" in q_lower or "лид" in q_lower
    finance_facts = [
        f
        for f in facts
        if (f.get("predicate") in {"finance_metric", "ops_metric", "expense_article"})
        or "выруч" in str(f.get("subject") or "").lower()
        or "прибыл" in str(f.get("subject") or "").lower()
    ]
    finance_question = any(
        x in q_lower for x in ("выруч", "прибыл", "фудкост", "чек", "бистро", "1c", "rkeeper", "расход")
    )

    observations: list[Any] = []
    hypotheses: list[Any] = []
    recommendations: list[Any] = []
    missing_data: list[Any] = []
    finance_briefing: dict[str, Any] | None = None

    if (finance_question or len(finance_facts) >= 3) and finance_facts:
        from modules.analysis.finance_brief import briefing_as_observations, build_finance_briefing

        finance_briefing = build_finance_briefing(facts, knowledge=knowledge)
        observations.extend(briefing_as_observations(finance_briefing))
        hypotheses.append(
            {
                "text": (
                    "Если средний чек растёт при падении гостей — гости дороже, но трафик слабее; "
                    "если фудкост и недостачи высоки — маржа утекает на кухне/складе."
                ),
                "confidence": "medium",
            }
        )
        top_actions = (finance_briefing.get("actions") or [])[:2]
        recommendations.append(
            {
                "title": "Принять финансовую сводку Бистро и назначить 3 контроля",
                "body": (
                    (finance_briefing.get("summary") or "")
                    + " "
                    + " ".join(top_actions)
                ).strip(),
                "priority": "high",
                "briefing": finance_briefing,
            }
        )
    elif mentions_l1001 and verified:
        issue = verified[0]
        observations.append(
            {
                "text": (
                    f"Подтверждённое расхождение по лиду: норматив "
                    f"{(issue.get('normative_value') or issue.get('deviation_value') or {}).get('minutes', issue.get('deviation_value', {}).get('minutes'))} "
                    f"против факта (severity={issue.get('severity')})."
                ),
                "alignment_issue_id": issue.get("id"),
                "verified": True,
            }
        )
        # Prefer structured normative/actual if present in context
        for v in verified:
            observations[-1] = {
                "text": (
                    f"Подтверждено расхождение SLA: отклонение "
                    f"{(v.get('deviation_value') or {}).get('minutes')} мин., "
                    f"severity={v.get('severity')}."
                ),
                "alignment_issue_id": v.get("id"),
                "verified": True,
            }
            break
        hypotheses.append(
            {
                "text": (
                    "Возможные причины: нехватка мощности, задержка маршрутизации или "
                    "неясный владелец очереди — это гипотеза до операционной проверки."
                ),
                "confidence": "low",
            }
        )
        recommendations.append(
            {
                "title": "Аккуратно проверить нарушение SLA первого контакта L-1001",
                "body": (
                    "Есть человечески подтверждённая запись сверки: первый контакт превысил "
                    "нормативный срок. Рекомендуется уточнить владельца, проверить ёмкость очереди "
                    "и поставить контрольную точку. Не выдумывать факты сверх указанных источников."
                ),
                "priority": "high",
            }
        )
    elif mentions_l1001 and not verified:
        missing_data.append("Нет подтверждённого Alignment Issue по L-1001")
        recommendations.append(
            {
                "title": "Сначала подтвердить evidence сверки",
                "body": (
                    "Есть наблюдаемые факты, но нет подтверждённого знания по расхождению. "
                    "Подтвердите Alignment Issue до операционных изменений."
                ),
                "priority": "medium",
            }
        )
    else:
        observations.append({"text": "Анализ собран только из активных Knowledge Records и Observed Facts."})
        if knowledge and facts:
            recommendations.append(
                {
                    "title": "Просмотреть указанные знания и факты",
                    "body": "Используйте только переданные записи знаний и факты; не изобретайте данные.",
                    "priority": "medium",
                }
            )

    if unverified:
        observations.append(
            {
                "text": f"Есть непроверенные evidence ({len(unverified)}) — помечены как unverified.",
                "verified": False,
            }
        )

    trust_values = [float(k.get("trust_index") or 0) for k in knowledge] + [
        float(f.get("trust_index") or 0) for f in facts
    ]
    trust = sum(trust_values) / len(trust_values) if trust_values else 0.0

    return {
        "facts": fact_entries[:12] if finance_briefing else (fact_entries + knowledge_entries),
        "observations": observations,
        "hypotheses": hypotheses,
        "recommendations": recommendations,
        "missing_data": missing_data,
        "sources": sources[:20],
        "trust_index": round(trust, 3),
        "blocked": False,
        "agent": "executive",
        "finance_briefing": finance_briefing,
        "decision_dna": {
            "role": "executive",
            "priorities": ["evidence", "accountability", "controlled_change"],
            "risk_tolerance": "low",
            "bias": "confirm_before_act",
        },
    }
