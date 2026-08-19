"""Concrete finance briefing from workbook facts."""

from modules.analysis.finance_brief import build_finance_briefing
from modules.llm.gateway import _executive


def test_build_finance_briefing_explains_metrics():
    facts = [
        {
            "id": "1",
            "subject": "Выручка, всего, в т.ч.",
            "predicate": "finance_metric",
            "value_structured": {
                "value": 1000,
                "unit": "тыс. руб.",
                "system_origin": "1c",
                "months": {"2026-03": 200, "2026-04": 250, "2026-05": 260, "2026-06": 290},
            },
        },
        {
            "id": "2",
            "subject": "Чистая прибыль",
            "predicate": "finance_metric",
            "value_structured": {
                "value": 100,
                "unit": "тыс. руб.",
                "system_origin": "1c",
                "months": {"2026-03": 10, "2026-04": 20, "2026-05": 30, "2026-06": 40},
            },
        },
        {
            "id": "3",
            "subject": "Средний чек",
            "predicate": "ops_metric",
            "value_structured": {
                "value": 1587,
                "unit": "руб.",
                "system_origin": "1c",
                "months": {"2026-03": 1500, "2026-04": 1550, "2026-05": 1600, "2026-06": 1700},
            },
        },
        {
            "id": "4",
            "subject": "Фудкост Кухня",
            "predicate": "ops_metric",
            "value_structured": {"value": 0.4, "unit": "ratio", "system_origin": "rkeeper"},
        },
        {
            "id": "5",
            "subject": "Бенедикт / Выручка / Зал / Кухня",
            "predicate": "ops_metric",
            "value_structured": {"value": 800000, "unit": "руб.", "system_origin": "rkeeper"},
        },
        {
            "id": "6",
            "subject": "Бенедикт / Выручка / Зал / Бар",
            "predicate": "ops_metric",
            "value_structured": {"value": 200000, "unit": "руб.", "system_origin": "rkeeper"},
        },
        {
            "id": "7",
            "subject": "Фонд оплаты труда",
            "predicate": "expense_article",
            "value_structured": {"value": 500000, "unit": "руб.", "system_origin": "1c"},
        },
        {
            "id": "8",
            "subject": "Недовольный гость",
            "predicate": "expense_article",
            "value_structured": {"value": 25000, "unit": "руб.", "system_origin": "1c"},
        },
    ]
    brief = build_finance_briefing(facts)
    assert brief["kind"] == "finance_briefing"
    assert "выручка" in brief["summary"].lower()
    metrics = {m["metric"] for m in brief["meanings"]}
    assert "Выручка (YTD)" in metrics
    assert "Чистая прибыль" in metrics
    assert "Рентабельность (чистая / выручка)" in metrics
    assert any("фудкост" in r.lower() for r in brief["risks"])
    assert brief["actions"]
    assert "тыс" in brief["units_note"].lower()
    assert brief["demand_mix"]
    assert brief["profitability"]
    assert brief["top_expenses"]
    assert brief["money_leaks"]
    assert brief["dynamics"]
    assert any(item["metric"] == "Недовольный гость" and "₽" in item["value"] for item in brief["money_leaks"])
    assert any(item["metric"] == "Средний чек" and "2026-03" in item["value"] for item in brief["dynamics"])


def test_executive_attaches_finance_briefing():
    facts = [
        {
            "id": "1",
            "subject": "Выручка, всего, в т.ч.",
            "predicate": "finance_metric",
            "value_structured": {"value": 500, "unit": "тыс. руб."},
            "trust_index": 0.9,
        },
        {
            "id": "2",
            "subject": "Чистая прибыль",
            "predicate": "finance_metric",
            "value_structured": {"value": 40, "unit": "тыс. руб."},
            "trust_index": 0.9,
        },
        {
            "id": "3",
            "subject": "Средний чек",
            "predicate": "ops_metric",
            "value_structured": {"value": 1500, "unit": "руб."},
            "trust_index": 0.9,
        },
    ]
    out = _executive({"facts": facts, "knowledge": [], "alignment_issues": {}}, "Что с выручкой?")
    assert out.get("finance_briefing")
    assert out["finance_briefing"]["meanings"]
    assert out["recommendations"]
