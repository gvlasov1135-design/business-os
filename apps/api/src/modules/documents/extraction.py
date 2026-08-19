from __future__ import annotations

import re
from dataclasses import dataclass


DEMO_POLICY_TEXT = (
    "Менеджер по продажам обязан связаться с новым лидом "
    "не позднее 15 минут после его создания. "
    "KPI: доля лидов с первым контактом ≤ 15 минут не ниже 90%. "
    "Обязательные этапы: создание лида → квалификация → первый контакт."
)

_DEADLINE_RE = re.compile(
    r"не\s+позднее\s+(\d+)\s+(минут[уы]?|час(?:а|ов)?|дн(?:я|ей)|day|hours?|minutes?)",
    re.IGNORECASE,
)
_RESPONSIBLE_RE = re.compile(
    r"(Менеджер по продажам|Sales Manager)",
    re.IGNORECASE,
)
_KPI_RE = re.compile(
    r"KPI[:\s]+([^\n.]+)",
    re.IGNORECASE,
)
_STAGES_RE = re.compile(
    r"Обязательные этапы:\s*([^\n.]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MockStatement:
    statement_type: str
    statement_text: str
    statement_value: dict
    confidence: float
    char_start: int
    char_end: int


@dataclass(frozen=True)
class MockExtractionResult:
    fragment_text: str
    statements: list[MockStatement]

    @property
    def statement_text(self) -> str:
        return self.primary.statement_text

    @property
    def statement_value(self) -> dict:
        return self.primary.statement_value

    @property
    def confidence(self) -> float:
        return self.primary.confidence

    @property
    def char_start(self) -> int:
        return self.primary.char_start

    @property
    def char_end(self) -> int:
        return self.primary.char_end

    @property
    def primary(self) -> MockStatement:
        for item in self.statements:
            if item.statement_type == "deadline":
                return item
        return self.statements[0]


def build_mock_extraction(file_bytes: bytes) -> MockExtractionResult:
    decoded = file_bytes.decode("utf-8", errors="ignore").strip()
    text = decoded if decoded else DEMO_POLICY_TEXT
    if DEMO_POLICY_TEXT.split(".")[0] not in text and "не позднее" not in text.lower():
        text = f"{text}\n\n{DEMO_POLICY_TEXT}".strip()

    statements: list[MockStatement] = []

    responsible = _RESPONSIBLE_RE.search(text)
    if responsible:
        role = responsible.group(1)
        statements.append(
            MockStatement(
                statement_type="responsible",
                statement_text=role,
                statement_value={"role": role, "raw": role},
                confidence=0.8,
                char_start=responsible.start(),
                char_end=responsible.end(),
            )
        )
        obligation_quote = text[max(0, responsible.start()) : responsible.end() + 40].strip()
        statements.append(
            MockStatement(
                statement_type="obligation",
                statement_text=obligation_quote or "обязан связаться с новым лидом",
                statement_value={"action": "first_contact", "subject": "new_lead", "raw": obligation_quote},
                confidence=0.78,
                char_start=responsible.start(),
                char_end=min(len(text), responsible.end() + 40),
            )
        )

    deadline = _DEADLINE_RE.search(text)
    if deadline:
        amount = int(deadline.group(1))
        unit = _normalize_unit(deadline.group(2).lower())
        quote = deadline.group(0)
        statements.append(
            MockStatement(
                statement_type="deadline",
                statement_text=quote,
                statement_value={"amount": amount, "unit": unit, "raw": quote},
                confidence=0.82,
                char_start=deadline.start(),
                char_end=deadline.end(),
            )
        )
    else:
        fragment = f"{text}\n\n{DEMO_POLICY_TEXT}".strip()
        deadline = _DEADLINE_RE.search(fragment)
        assert deadline is not None
        text = fragment
        statements.append(
            MockStatement(
                statement_type="deadline",
                statement_text=deadline.group(0),
                statement_value={
                    "amount": int(deadline.group(1)),
                    "unit": "minutes",
                    "raw": deadline.group(0),
                },
                confidence=0.55,
                char_start=deadline.start(),
                char_end=deadline.end(),
            )
        )

    kpi = _KPI_RE.search(text)
    if kpi:
        quote = kpi.group(0).strip()
        statements.append(
            MockStatement(
                statement_type="kpi",
                statement_text=quote,
                statement_value={"metric": "first_contact_sla_share", "target_pct": 90, "raw": quote},
                confidence=0.7,
                char_start=kpi.start(),
                char_end=kpi.end(),
            )
        )

    stages = _STAGES_RE.search(text)
    if stages:
        raw_stages = stages.group(1).strip()
        stage_list = [part.strip() for part in re.split(r"→|->|,", raw_stages) if part.strip()]
        statements.append(
            MockStatement(
                statement_type="process_stage",
                statement_text=stages.group(0).strip(),
                statement_value={"stages": stage_list, "raw": raw_stages},
                confidence=0.72,
                char_start=stages.start(),
                char_end=stages.end(),
            )
        )

    return MockExtractionResult(fragment_text=text, statements=statements)


def _normalize_unit(unit_raw: str) -> str:
    if unit_raw.startswith("мин") or unit_raw.startswith("min"):
        return "minutes"
    if unit_raw.startswith("час") or unit_raw.startswith("hour"):
        return "hours"
    if unit_raw.startswith("дн") or unit_raw.startswith("day"):
        return "days"
    return unit_raw
