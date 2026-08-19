"""Конкретная финансовая сводка по метрикам workbook (Бистро)."""

from __future__ import annotations

from typing import Any


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_rows(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for f in facts:
        subject = str(f.get("subject") or "")
        predicate = str(f.get("predicate") or "")
        vs = f.get("value_structured") or f.get("value") or {}
        if not isinstance(vs, dict):
            vs = {"value": vs}
        if predicate not in {"finance_metric", "ops_metric", "expense_article", "workbook_marker"}:
            if not any(k in subject.lower() for k in ("выруч", "прибыл", "чек", "фудкост", "гост")):
                continue
        val = _as_float(vs.get("value"))
        if val is None:
            continue
        rows.append(
            {
                "subject": subject,
                "predicate": predicate,
                "value": val,
                "unit": str(vs.get("unit") or ""),
                "origin": str(vs.get("system_origin") or ""),
                "months": vs.get("months") or {},
                "fact_id": f.get("id"),
            }
        )
    return rows


def _find(rows: list[dict[str, Any]], *needles: str) -> dict[str, Any] | None:
    matches = [
        row
        for row in rows
        if all(n in row["subject"].lower() for n in needles)
    ]
    if not matches:
        return None
    # Prefer sane ratios / count units when several imports collide.
    if any(n in ("фудкост", "%") for n in needles):
        sane = [r for r in matches if r["unit"] == "ratio" and abs(r["value"]) <= 1.5]
        if sane:
            return min(sane, key=lambda r: abs(r["value"] - 0.3))
    return matches[0]


def _fmt(value: float, unit: str) -> str:
    unit_l = unit.lower()
    if unit_l in {"ratio", "flag"}:
        pct = value * 100 if abs(value) <= 1.5 else value
        return f"{pct:.1f}%"
    if unit_l in {"шт.", "шт", "guest", "guests"}:
        return f"{value:,.0f} шт.".replace(",", " ")
    if "тыс" in unit_l:
        rub = value * 1000
        if rub >= 1_000_000:
            return f"{value:,.1f} тыс. руб. (~{rub / 1_000_000:.1f} млн ₽)".replace(",", " ")
        return f"{value:,.1f} тыс. руб. (~{rub:,.0f} ₽)".replace(",", " ")
    if unit_l in {"руб.", "руб", "₽"} or unit == "":
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.2f} млн ₽"
        if abs(value) >= 1000:
            return f"{value:,.0f} ₽".replace(",", " ")
        return f"{value:,.2f} ₽".replace(",", " ")
    return f"{value:,.2f} {unit}".replace(",", " ")


def _months_delta(months: dict[str, Any]) -> tuple[str, str, float] | None:
    ru_order = {
        "январь": 1,
        "февраль": 2,
        "март": 3,
        "апрель": 4,
        "май": 5,
        "июнь": 6,
        "июль": 7,
        "август": 8,
        "сентябрь": 9,
        "октябрь": 10,
        "ноябрь": 11,
        "декабрь": 12,
    }

    def _month_sort_key(key: str) -> tuple[int, int]:
        text = str(key).strip().lower()
        if text in ru_order:
            return (2026, ru_order[text])
        if text.startswith("2026-"):
            try:
                return (2026, int(text.split("-", 1)[1]))
            except ValueError:
                return (9999, 99)
        return (9999, 99)

    pairs: list[tuple[str, float]] = []
    for key, raw in months.items():
        val = _as_float(raw)
        if val is not None:
            pairs.append((str(key), val))
    if len(pairs) < 2:
        return None
    pairs.sort(key=lambda item: _month_sort_key(item[0]))
    first_key, first_val = pairs[0]
    last_key, last_val = pairs[-1]
    if first_val == 0:
        return None
    return first_key, last_key, (last_val - first_val) / abs(first_val) * 100


def _top_rows(
    rows: list[dict[str, Any]],
    *,
    predicate: str,
    limit: int = 5,
    skip_needles: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        subject = row["subject"].lower()
        if row["predicate"] != predicate:
            continue
        if any(needle in subject for needle in skip_needles):
            continue
        filtered.append(row)
    return sorted(filtered, key=lambda row: float(row["value"]), reverse=True)[:limit]


def _coerce_unit(subject: str, unit: str) -> str:
    s = subject.lower()
    if "количество гостей" in s or "гостей/заказов" in s or "заказ" in s:
        return "шт."
    if "средний чек" in s:
        return "руб."
    if "фудкост" in s or "%" in s:
        return "ratio"
    return unit or ""


def build_finance_briefing(
    facts: list[dict[str, Any]],
    *,
    knowledge: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Вернуть краткую расшифровку: что значат цифры и что делать."""
    rows = _metric_rows(facts)
    # also pull from knowledge titles if facts thin
    if knowledge:
        for k in knowledge:
            title = str(k.get("title") or "")
            body = str(k.get("body") or "")
            if " = " in body:
                try:
                    tail = body.split(" = ", 1)[1].split(" ")[0].replace(",", ".")
                    val = _as_float(tail)
                except Exception:
                    val = None
                if val is not None and title:
                    rows.append(
                        {
                            "subject": title,
                            "predicate": "finance_metric",
                            "value": val,
                            "unit": "тыс. руб." if "тыс" in body else "",
                            "origin": "knowledge",
                            "months": {},
                            "fact_id": k.get("id"),
                        }
                    )

    for row in rows:
        row["unit"] = _coerce_unit(row["subject"], row.get("unit") or "")

    revenue = _find(rows, "выручка", "всего") or _find(rows, "выручка")
    guests = _find(rows, "количество гостей") or _find(rows, "гостей")
    avg_check = _find(rows, "средний чек")
    cogs = _find(rows, "себестоимость итого") or _find(rows, "себестоимость")
    gross = _find(rows, "валовая прибыль")
    opex = _find(rows, "операционные расходы")
    op_profit = _find(rows, "операционная прибыль")
    net = _find(rows, "чистая прибыль")
    foodcost_k = _find(rows, "фудкост", "кухн") or _find(rows, "фудкост")
    foodcost_b = _find(rows, "фудкост", "бар")
    shortage_k = _find(rows, "недостач", "кухн") or _find(rows, "недостач")
    payroll = _find(rows, "фонд оплаты") or _find(rows, "фот")
    rent = _find(rows, "аренда заведения")

    meanings: list[dict[str, str]] = []
    risks: list[str] = []
    actions: list[str] = []

    def add_meaning(title: str, row: dict[str, Any] | None, meaning: str) -> None:
        if not row:
            return
        meanings.append(
            {
                "metric": title,
                "value": _fmt(row["value"], row["unit"]),
                "meaning": meaning,
                "origin": row.get("origin") or "",
            }
        )

    add_meaning(
        "Выручка (YTD)",
        revenue,
        "сколько денег принесло заведение за период (в P&L обычно тыс. руб.)",
    )
    add_meaning(
        "Гости / заказы",
        guests,
        "трафик: сколько раз гости «прошли» через кассу",
    )
    add_meaning(
        "Средний чек",
        avg_check,
        "средний платёж одного гостя/заказа; рост чека или падение трафика читаются здесь",
    )
    add_meaning(
        "Себестоимость",
        cogs,
        "стоимость продуктов/товара, ушедшая в продажи",
    )
    add_meaning(
        "Валовая прибыль",
        gross,
        "выручка минус себестоимость — «грязная» маржа до аренды и ФОТ",
    )
    add_meaning(
        "Операционные расходы",
        opex,
        "текущие расходы заведения (персонал, аренда, хозяйство и т.п.)",
    )
    add_meaning(
        "Операционная прибыль",
        op_profit,
        "результат основной деятельности до налогов/неоперационки",
    )
    add_meaning(
        "Чистая прибыль",
        net,
        "итог для собственника после всех расходов",
    )
    add_meaning(
        "Фудкост кухня",
        foodcost_k,
        "доля себестоимости кухни в выручке кухни; ориентир ресторана часто 25–35%",
    )
    add_meaning(
        "Фудкост бар",
        foodcost_b,
        "доля себестоимости бара; обычно ниже кухни",
    )
    add_meaning(
        "Недостачи кухня",
        shortage_k,
        "потери/недостачи склада кухни — прямой риск к марже",
    )
    add_meaning(
        "ФОТ",
        payroll,
        "фонд оплаты труда — обычно крупнейшая статья расходов",
    )
    add_meaning(
        "Аренда",
        rent,
        "фиксированная нагрузка на точку",
    )

    if revenue and net:
        margin = (net["value"] / revenue["value"] * 100) if revenue["value"] else 0
        meanings.append(
            {
                "metric": "Рентабельность (чистая / выручка)",
                "value": f"{margin:.1f}%",
                "meaning": "сколько копеек чистой прибыли остаётся с каждого рубля выручки",
                "origin": "calc",
            }
        )
        if margin < 8:
            risks.append(
                f"Чистая рентабельность ~{margin:.1f}% — низковато для устойчивой точки; смотреть ФОТ, аренду и потери."
            )
        elif margin > 20:
            risks.append(
                f"Чистая рентабельность ~{margin:.1f}% — высокая; проверить, нет ли недоучёта расходов/инвестиций."
            )

    if foodcost_k and foodcost_k["value"] > 0.35:
        risks.append(
            f"Фудкост кухни {_fmt(foodcost_k['value'], foodcost_k['unit'])} выше комфортного коридора — проверить закупки, порции, списания."
        )
    if shortage_k and shortage_k["value"] > 0:
        risks.append(
            f"Недостачи кухни {_fmt(shortage_k['value'], shortage_k['unit'])} — нужен разбор инвентаризаций и ответственных."
        )
    if payroll and revenue and payroll["unit"] != revenue["unit"]:
        # payroll often руб., revenue тыс.
        pass
    if payroll and revenue:
        pay = payroll["value"]
        rev = revenue["value"] * (1000 if "тыс" in revenue["unit"] else 1)
        pay_rub = pay * (1000 if "тыс" in payroll["unit"] else 1)
        if rev > 0:
            share = pay_rub / rev * 100
            if share > 35:
                risks.append(
                    f"ФОТ ≈ {share:.0f}% выручки — тяжёлая нагрузка на персонал; смотреть графики и производительность."
                )

    if not risks:
        risks.append("Критических красных флагов в ключевых метриках не видно — держать контроль фудкоста и недостач.")

    actions = [
        "Зафиксировать 4 цифры на доске: выручка, средний чек, чистая прибыль, фудкост кухни.",
        "Сверить выручку 1C с RKeeper (бар+кухня) за те же месяцы — расхождение = проблема учёта.",
        "По недостачам/фудкосту: назначить владельца инвентаризации на кухне и баре.",
        "Топ расходов (ФОТ, аренда) не резать вслепую — сначала норма/час и заполняемость.",
    ]

    profitability: list[dict[str, str]] = []
    if gross and revenue and revenue["value"]:
        gross_margin = gross["value"] / revenue["value"] * 100
        profitability.append(
            {
                "metric": "Валовая маржа",
                "value": f"{gross_margin:.1f}%",
                "meaning": "сколько валовой прибыли остаётся после себестоимости",
            }
        )
    if op_profit and revenue and revenue["value"]:
        operating_margin = op_profit["value"] / revenue["value"] * 100
        profitability.append(
            {
                "metric": "Операционная маржа",
                "value": f"{operating_margin:.1f}%",
                "meaning": "сколько остаётся после операционных расходов",
            }
        )
    if net and revenue and revenue["value"]:
        net_margin = net["value"] / revenue["value"] * 100
        profitability.append(
            {
                "metric": "Чистая маржа",
                "value": f"{net_margin:.1f}%",
                "meaning": "итоговая доходность бизнеса для собственника",
            }
        )

    demand_mix: list[dict[str, str]] = []
    hall_kitchen = _find(rows, "выручка", "зал", "кухня")
    hall_bar = _find(rows, "выручка", "зал", "бар")
    delivery_kitchen = _find(rows, "выручка", "доставка", "кухня")
    delivery_bar = _find(rows, "выручка", "доставка", "бар")
    demand_rows = [
        ("Зал / Кухня", hall_kitchen),
        ("Зал / Бар", hall_bar),
        ("Доставка / Кухня", delivery_kitchen),
        ("Доставка / Бар", delivery_bar),
    ]
    total_demand = sum(float(row["value"]) for _, row in demand_rows if row and float(row["value"]) > 0)
    for label, row in demand_rows:
        if not row or float(row["value"]) <= 0:
            continue
        share = float(row["value"]) / total_demand * 100 if total_demand else 0.0
        demand_mix.append(
            {
                "metric": label,
                "value": f"{_fmt(float(row['value']), row['unit'])} · {share:.1f}%",
                "meaning": "доля в выручке по каналам/направлениям",
            }
        )

    top_expenses = []
    for row in _top_rows(
        rows,
        predicate="expense_article",
        limit=6,
        skip_needles=("текущие расходы заведения", "расходы на персонал", "неоперационные расходы"),
    ):
        top_expenses.append(
            {
                "metric": row["subject"],
                "value": _fmt(row["value"], row["unit"]),
                "meaning": "крупная статья расходов, которую руководитель должен контролировать отдельно",
            }
        )

    money_leaks = []
    shortage_bar = _find(rows, "недостач", "бар")
    surplus_k = _find(rows, "излишки", "кухн")
    surplus_b = _find(rows, "излишки", "бар")
    for title, row, meaning in (
        ("Недостачи кухня", shortage_k, "прямые потери на кухне"),
        ("Недостачи бар", shortage_bar, "потери на баре"),
        ("Излишки кухня", surplus_k, "несоответствие учёта/списаний на кухне"),
        ("Излишки бар", surplus_b, "несоответствие учёта/списаний на баре"),
        ("Недовольный гость", _find(rows, "недовольный гость"), "компенсации и потери сервиса"),
        ("Подарки гостям", _find(rows, "подарки гостям"), "компенсации и маркетинговые уступки"),
        ("Такси", _find(rows, "такси"), "сервисная/операционная утечка, если не под контролем"),
    ):
        if row and abs(float(row["value"])) > 0:
            money_leaks.append(
                {
                    "metric": title,
                    "value": _fmt(abs(float(row["value"])), row["unit"]),
                    "meaning": meaning,
                }
            )

    dynamics = []
    for title, row, meaning in (
        ("Выручка", revenue, "динамика продаж"),
        ("Средний чек", avg_check, "динамика монетизации гостя"),
        ("Чистая прибыль", net, "динамика доходности"),
    ):
        if not row:
            continue
        delta = _months_delta(row.get("months") or {})
        if delta:
            start, end, pct = delta
            dynamics.append(
                {
                    "metric": title,
                    "value": f"{pct:+.1f}% ({start} → {end})",
                    "meaning": meaning,
                }
            )

    if hall_kitchen and hall_bar and float(hall_kitchen["value"]) < float(hall_bar["value"]):
        risks.append("Бар зарабатывает больше кухни — проверьте, не проседает ли основное меню и загрузка кухни.")
    if shortage_k and float(shortage_k["value"]) > 300_000:
        actions.insert(0, "Сразу разобрать кухонные недостачи: инвентаризация, списания, ответственный смены.")
    if demand_mix and any("Доставка" in item["metric"] for item in demand_mix) is False:
        actions.append("Доставка не даёт заметной выручки — решить: развивать её отдельно или не распылять ресурсы.")

    summary = (
        "Коротко: "
        + (
            f"выручка {_fmt(revenue['value'], revenue['unit'])}, "
            if revenue
            else ""
        )
        + (f"средний чек {_fmt(avg_check['value'], avg_check['unit'])}, " if avg_check else "")
        + (f"чистая прибыль {_fmt(net['value'], net['unit'])}. " if net else "")
        + (risks[0] if risks else "")
    )

    return {
        "kind": "finance_briefing",
        "summary": summary,
        "meanings": meanings[:12],
        "risks": risks[:5],
        "actions": actions[:6],
        "demand_mix": demand_mix,
        "profitability": profitability,
        "top_expenses": top_expenses,
        "money_leaks": money_leaks[:6],
        "dynamics": dynamics,
        "units_note": (
            "В листе «Отчет о фин.рез.» суммы обычно в тыс. руб.; "
            "«Деление БарКухня» (RKeeper) — в рублях. Не складывать их напрямую без перевода."
        ),
    }


def briefing_as_observations(brief: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        {"text": brief.get("summary") or "", "verified": True, "kind": "summary"},
        {"text": brief.get("units_note") or "", "verified": True, "kind": "note"},
    ]
    for item in brief.get("meanings") or []:
        out.append(
            {
                "text": f"{item['metric']}: {item['value']} — {item['meaning']}",
                "verified": True,
                "kind": "meaning",
            }
        )
    for risk in brief.get("risks") or []:
        out.append({"text": f"Риск: {risk}", "verified": False, "kind": "risk"})
    return [o for o in out if o.get("text")]
