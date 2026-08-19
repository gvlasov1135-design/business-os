"""Decision DNA и оркестрация независимых AI-агентов (debate → synthesis)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from modules.llm import AgentProfile

# Fallback DNA — если правил ещё нет
DECISION_DNA: dict[str, dict[str, Any]] = {
    AgentProfile.executive.value: {
        "role": "executive",
        "priorities": ["evidence", "accountability", "controlled_change"],
        "risk_tolerance": "low",
        "bias": "confirm_before_act",
        "language": "ru",
    },
    AgentProfile.sales.value: {
        "role": "sales",
        "priorities": ["sla", "conversion", "queue_throughput"],
        "risk_tolerance": "medium",
        "bias": "operational_fix_now",
        "language": "ru",
    },
    AgentProfile.critic.value: {
        "role": "critic",
        "priorities": ["source_integrity", "no_hallucination"],
        "risk_tolerance": "low",
        "bias": "challenge_unverified",
        "language": "ru",
    },
}

DNA_RULE_CODES = {
    "executive": "dna_executive",
    "sales": "dna_sales",
    "critic": "dna_critic",
}
PROMPT_RULE_CODES = {
    "executive": "prompt_executive",
    "sales": "prompt_sales",
}


def decision_dna(agent: AgentProfile | str) -> dict[str, Any]:
    key = agent.value if isinstance(agent, AgentProfile) else str(agent)
    return dict(DECISION_DNA.get(key) or {"role": key})


async def load_decision_dna(
    session: AsyncSession,
    company_id: uuid.UUID,
    agent: AgentProfile | str,
) -> dict[str, Any]:
    """Загружает DNA из versioned rules (agent_profile), иначе fallback."""
    from modules.rules import service as rules_service

    key = agent.value if isinstance(agent, AgentProfile) else str(agent)
    code = DNA_RULE_CODES.get(key)
    base = decision_dna(key)
    if not code:
        return base
    await rules_service.ensure_default_rules(session, company_id)
    version = await rules_service.get_active_version(session, company_id, code)
    if version is None or not version.body:
        return base
    merged = dict(base)
    merged.update(version.body)
    merged["rule_version_id"] = str(version.id)
    merged["rule_version_number"] = version.version_number
    merged["rule_code"] = code
    return merged


async def render_agent_prompt(
    session: AsyncSession,
    company_id: uuid.UUID,
    agent: AgentProfile | str,
    question: str,
) -> dict[str, Any]:
    """Версионированный prompt template + metadata."""
    from modules.rules import service as rules_service

    key = agent.value if isinstance(agent, AgentProfile) else str(agent)
    code = PROMPT_RULE_CODES.get(key)
    default = question
    meta: dict[str, Any] = {"prompt": default, "rule_code": code}
    if not code:
        return meta
    await rules_service.ensure_default_rules(session, company_id)
    version = await rules_service.get_active_version(session, company_id, code)
    if version is None or not version.body:
        return meta
    template = str(version.body.get("template") or "{question}")
    meta["prompt"] = template.format(question=question)
    meta["rule_version_id"] = str(version.id)
    meta["rule_version_number"] = version.version_number
    return meta


def extract_rec_titles(opinion: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for item in opinion.get("recommendations") or []:
        if isinstance(item, dict):
            titles.append(str(item.get("title") or item.get("body") or ""))
        else:
            titles.append(str(item))
    return [t for t in titles if t]


def detect_disagreements(
    opinions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Сравнивает независимые мнения до synthesis — не смешивает тексты."""
    disagreements: list[dict[str, Any]] = []
    agents = list(opinions.keys())
    if len(agents) < 2:
        return disagreements

    exec_op = opinions.get("executive") or {}
    sales_op = opinions.get("sales") or {}

    exec_titles = extract_rec_titles(exec_op)
    sales_titles = extract_rec_titles(sales_op)
    if exec_titles and sales_titles and exec_titles[0] != sales_titles[0]:
        disagreements.append(
            {
                "topic": "recommendation_approach",
                "agents": ["executive", "sales"],
                "executive_view": exec_titles[0],
                "sales_view": sales_titles[0],
                "severity": "medium",
            }
        )

    exec_pri = None
    sales_pri = None
    if exec_op.get("recommendations"):
        first = exec_op["recommendations"][0]
        if isinstance(first, dict):
            exec_pri = first.get("priority")
    if sales_op.get("recommendations"):
        first = sales_op["recommendations"][0]
        if isinstance(first, dict):
            sales_pri = first.get("priority")
    if exec_pri and sales_pri and exec_pri != sales_pri:
        disagreements.append(
            {
                "topic": "priority",
                "agents": ["executive", "sales"],
                "executive_view": exec_pri,
                "sales_view": sales_pri,
                "severity": "low",
            }
        )

    dna_e = decision_dna("executive")
    dna_s = decision_dna("sales")
    if dna_e.get("bias") != dna_s.get("bias"):
        disagreements.append(
            {
                "topic": "decision_dna_bias",
                "agents": ["executive", "sales"],
                "executive_view": dna_e.get("bias"),
                "sales_view": dna_s.get("bias"),
                "severity": "low",
            }
        )

    return disagreements


def synthesize(
    *,
    question: str,
    opinions: dict[str, dict[str, Any]],
    disagreements: list[dict[str, Any]],
    critic: dict[str, Any],
) -> dict[str, Any]:
    """Синтез после независимых прогонов. Не затирает исходные opinions."""
    executive = opinions.get("executive") or {}
    sales = opinions.get("sales") or {}

    facts = list(executive.get("facts") or [])
    # dedupe by id if present
    seen: set[str] = set()
    merged_facts: list[Any] = []
    for item in facts + list(sales.get("facts") or []):
        key = str((item or {}).get("id") or (item or {}).get("fact_id") or item)
        if key in seen:
            continue
        seen.add(key)
        merged_facts.append(item)

    observations = list(executive.get("observations") or []) + [
        {"text": o.get("text") if isinstance(o, dict) else str(o), "agent": "sales"}
        for o in (sales.get("observations") or [])
    ]
    hypotheses = list(executive.get("hypotheses") or []) + list(sales.get("hypotheses") or [])
    missing = list(dict.fromkeys([*(executive.get("missing_data") or []), *(sales.get("missing_data") or [])]))

    sources = list(executive.get("sources") or []) + list(sales.get("sources") or [])

    recommendations: list[dict[str, Any]] = []
    if disagreements:
        recommendations.append(
            {
                "title": "Учесть разногласие Executive и Sales перед решением",
                "body": (
                    "Агенты проанализировали вопрос независимо и не сошлись в подходе. "
                    f"Executive: «{(extract_rec_titles(executive) or ['—'])[0]}». "
                    f"Sales: «{(extract_rec_titles(sales) or ['—'])[0]}». "
                    "Человек выбирает действие; AI не меняет процесс автоматически."
                ),
                "priority": "high",
                "from_synthesis": True,
            }
        )
    # keep both agent proposals visible as secondary
    for agent_name, opinion in (("executive", executive), ("sales", sales)):
        for rec in opinion.get("recommendations") or []:
            if isinstance(rec, dict):
                recommendations.append({**rec, "agent": agent_name, "from_synthesis": False})
            else:
                recommendations.append(
                    {"title": str(rec)[:120], "body": str(rec), "priority": "medium", "agent": agent_name}
                )

    trusts = [
        float(executive.get("trust_index") or 0),
        float(sales.get("trust_index") or 0),
    ]
    trust = round(sum(trusts) / len(trusts), 3) if trusts else 0.0

    finance_briefing = executive.get("finance_briefing") or sales.get("finance_briefing")
    if finance_briefing:
        # Prefer concrete briefing over raw fact dump
        observations = list(executive.get("observations") or [])[:14]
        hypotheses = list(executive.get("hypotheses") or [])[:2]
        merged_facts = [
            {
                "text": f"{m['metric']}: {m['value']}",
                "meaning": m.get("meaning"),
            }
            for m in (finance_briefing.get("meanings") or [])[:10]
        ]
        recommendations = []
        recommendations.append(
            {
                "title": "Главный вывод по цифрам Бистро",
                "body": str(finance_briefing.get("summary") or ""),
                "priority": "critical",
                "from_synthesis": True,
            }
        )
        for action in (finance_briefing.get("actions") or [])[:3]:
            recommendations.append(
                {
                    "title": action[:120],
                    "body": action,
                    "priority": "high",
                    "from_synthesis": True,
                }
            )
        for agent_name, opinion in (("executive", executive), ("sales", sales)):
            for rec in (opinion.get("recommendations") or [])[:1]:
                if isinstance(rec, dict):
                    recommendations.append({**rec, "agent": agent_name, "from_synthesis": False})

    return {
        "facts": merged_facts,
        "observations": observations,
        "hypotheses": hypotheses,
        "recommendations": recommendations,
        "missing_data": missing,
        "sources": sources[:15],
        "trust_index": trust,
        "blocked": bool(missing and not (executive.get("recommendations") or sales.get("recommendations"))),
        "question": question,
        "disagreements": disagreements,
        "critic": critic,
        "synthesis": {
            "method": "finance_briefing" if finance_briefing else "debate_then_merge",
            "agents": list(opinions.keys()),
            "disagreement_count": len(disagreements),
            "briefing": finance_briefing,
        },
        "finance_briefing": finance_briefing,
        "agent": "synthesis",
    }
