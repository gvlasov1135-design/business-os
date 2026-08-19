import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from common.audit import write_audit
from common.errors import AppError
from modules.alignment.models import (
    AlignmentCheck,
    AlignmentCheckStatus,
    AlignmentIssue,
    AlignmentIssueSeverity,
    AlignmentIssueStatus,
)
from modules.documents.intelligence_models import ExtractedStatement, StatementStatus, StatementType
from modules.identity.service import get_company
from modules.ingestion.models import ObservedFact
from modules.knowledge.models import KnowledgeRecord, KnowledgeRecordStatus, KnowledgeRecordType


def _minutes_from_structured(value: dict[str, Any] | None, *keys: str) -> float:
    if not value:
        raise AppError("Missing structured value", status_code=400, code="missing_structured_value")
    for key in keys:
        if key in value and value[key] is not None:
            return float(value[key])
    raise AppError("Minutes value not found", status_code=400, code="minutes_not_found")


def _severity_for_deviation(
    deviation: float,
    bands: dict[str, Any] | None = None,
) -> AlignmentIssueSeverity:
    """Severity from rule severity_bands (minutes thresholds) or defaults."""
    bands = bands or {}
    critical = float(bands.get("critical", 60))
    high = float(bands.get("high", 30))
    medium = float(bands.get("medium", 0))
    if deviation > critical:
        return AlignmentIssueSeverity.critical
    if deviation > high:
        return AlignmentIssueSeverity.high
    if deviation > medium:
        return AlignmentIssueSeverity.medium
    return AlignmentIssueSeverity.low


def _knowledge_body_for_issue(issue: AlignmentIssue, *, accepted: bool) -> tuple[str, str]:
    """Title + body for KnowledgeRecord from an alignment issue."""
    subject = issue.actual_value.get("subject") or "lead"
    if issue.normative_value.get("minutes") is not None:
        normative = issue.normative_value.get("minutes")
        actual = issue.actual_value.get("minutes")
        deviation = issue.deviation_value.get("minutes")
        if accepted:
            return (
                f"Принято отклонение SLA первого контакта: {subject}",
                (
                    f"Норматив {normative} мин.; факт {actual} мин.; отклонение {deviation} мин. "
                    f"Принято как operational exception (severity={issue.severity.value})."
                ),
            )
        return (
            f"Подтверждено нарушение срока первого контакта: {subject}",
            (
                f"Нормативный срок {normative} мин.; фактический первый контакт {actual} мин.; "
                f"отклонение {deviation} мин. (severity={issue.severity.value})."
            ),
        )
    if issue.normative_value.get("role") is not None:
        role = issue.normative_value.get("role")
        assigned = issue.actual_value.get("assigned_position")
        actor = issue.actual_value.get("actual_actor")
        if accepted:
            return (
                f"Принято отклонение по ответственному: {subject}",
                (
                    f"Нормативная роль «{role}»; назначено «{assigned}»; исполнитель «{actor}». "
                    f"Принято как отклонение Sales SLA (очередь ведёт сотрудник под ролью)."
                ),
            )
        return (
            f"Подтверждено расхождение ответственного: {subject}",
            (
                f"Нормативная роль «{role}»; назначено «{assigned}»; "
                f"фактический исполнитель «{actor}» (severity={issue.severity.value})."
            ),
        )
    if issue.normative_value.get("stages") is not None:
        required = issue.normative_value.get("stages") or []
        skipped = issue.actual_value.get("stages_skipped") or []
        if accepted:
            return (
                f"Принято отклонение по этапам процесса: {subject}",
                (
                    f"Обязательные этапы: {', '.join(required)}. "
                    f"Пропущено: {', '.join(skipped) or '—'}. Принято как отклонение процесса."
                ),
            )
        return (
            f"Подтверждён пропуск этапов процесса: {subject}",
            (
                f"Обязательные этапы: {', '.join(required)}. "
                f"Пропущено: {', '.join(skipped) or '—'} (severity={issue.severity.value})."
            ),
        )
    return (
        f"{'Принято отклонение' if accepted else 'Подтверждено расхождение'}: {subject}",
        f"Alignment issue {issue.id} ({issue.severity.value}).",
    )


async def _attach_knowledge(
    session: AsyncSession,
    issue: AlignmentIssue,
    *,
    accepted: bool,
) -> KnowledgeRecord:
    title, body = _knowledge_body_for_issue(issue, accepted=accepted)
    trust = 0.7 if accepted else 0.85
    record = KnowledgeRecord(
        company_id=issue.company_id,
        title=title,
        body=body,
        record_type=KnowledgeRecordType.alignment,
        status=KnowledgeRecordStatus.active,
        trust_index=trust,
        source_refs=[
            ref
            for ref in [
                {"type": "alignment_issue", "id": str(issue.id)},
                {"type": "extracted_statement", "id": str(issue.statement_id)}
                if issue.statement_id
                else None,
                {"type": "observed_fact", "id": str(issue.fact_id)} if issue.fact_id else None,
                {"type": "accepted_deviation", "value": True} if accepted else None,
            ]
            if ref is not None
        ],
        alignment_issue_id=issue.id,
        statement_id=issue.statement_id,
        valid_from=datetime.now(UTC),
    )
    session.add(record)
    await session.flush()
    return record


def build_proposed_document_change(issue: AlignmentIssue) -> dict[str, Any]:
    """Draft proposal to update the normative document after confirmed deviation."""
    rule = (issue.evidence or {}).get("rule_code") or "alignment"
    if issue.normative_value.get("minutes") is not None:
        normative = issue.normative_value.get("minutes")
        actual = issue.actual_value.get("minutes")
        return {
            "status": "proposed",
            "document_id": str(issue.document_id) if issue.document_id else None,
            "statement_id": str(issue.statement_id) if issue.statement_id else None,
            "rule_code": rule,
            "title": "Уточнить SLA первого контакта в регламенте",
            "summary": (
                f"Факт {actual} мин. против норматива {normative} мин. "
                "Предложить: либо усилить контроль очереди, либо пересмотреть норматив с обоснованием."
            ),
            "suggested_text": (
                f"Менеджер по продажам обязан связаться с новым лидом не позднее {normative} минут "
                "после создания. Контроль: дежурный владелец очереди; эскалация при превышении."
            ),
            "rationale": "Подтверждённое отклонение Sales SLA по сроку первого контакта.",
        }
    if issue.normative_value.get("role") is not None:
        role = issue.normative_value.get("role")
        return {
            "status": "proposed",
            "document_id": str(issue.document_id) if issue.document_id else None,
            "statement_id": str(issue.statement_id) if issue.statement_id else None,
            "rule_code": rule,
            "title": "Уточнить роль и исполнителя в регламенте",
            "summary": (
                f"Нормативная роль «{role}» расходится с фактическим исполнителем. "
                "Предложить явно разрешить делегирование сотруднику очереди."
            ),
            "suggested_text": (
                f"Ответственная роль: {role}. Допускается исполнение дежурным сотрудником очереди "
                "с фиксацией actual_actor в CRM."
            ),
            "rationale": "Подтверждённое расхождение ответственного vs исполнителя.",
        }
    if issue.normative_value.get("stages") is not None:
        stages = issue.normative_value.get("stages") or []
        skipped = issue.actual_value.get("stages_skipped") or []
        return {
            "status": "proposed",
            "document_id": str(issue.document_id) if issue.document_id else None,
            "statement_id": str(issue.statement_id) if issue.statement_id else None,
            "rule_code": rule,
            "title": "Зафиксировать обязательные этапы без silent skip",
            "summary": (
                f"Пропущены этапы: {', '.join(skipped) or '—'}. "
                "Предложить запрет перехода к первому контакту без квалификации."
            ),
            "suggested_text": (
                "Обязательные этапы: "
                + " → ".join(str(s) for s in stages)
                + ". Пропуск этапа допускается только с accepted deviation и причиной в CRM."
            ),
            "rationale": "Подтверждённый пропуск обязательных этапов обработки лида.",
        }
    return {
        "status": "proposed",
        "document_id": str(issue.document_id) if issue.document_id else None,
        "statement_id": str(issue.statement_id) if issue.statement_id else None,
        "rule_code": rule,
        "title": "Предложение изменения документа",
        "summary": "Уточнить норматив по итогам подтверждённой сверки.",
        "suggested_text": "",
        "rationale": f"Alignment issue {issue.id}",
    }


def _store_proposed_change(issue: AlignmentIssue) -> dict[str, Any]:
    proposal = build_proposed_document_change(issue)
    evidence = dict(issue.evidence or {})
    evidence["proposed_change"] = proposal
    issue.evidence = evidence
    flag_modified(issue, "evidence")
    return proposal


async def run_lead_deadline_check(
    session: AsyncSession,
    company_id: uuid.UUID,
    statement_id: uuid.UUID,
    fact_id: uuid.UUID,
) -> AlignmentIssue:
    await get_company(session, company_id)

    from modules.rules import service as rules_service

    await rules_service.ensure_default_rules(session, company_id)
    rule_version = await rules_service.get_active_version(
        session, company_id, "lead_first_contact_deadline"
    )
    rule_body = (rule_version.body if rule_version else {}) or {}
    substantial_threshold = float(rule_body.get("substantial_deviation_minutes") or 30)
    severity_bands = rule_body.get("severity_bands") if isinstance(rule_body.get("severity_bands"), dict) else None

    statement = await session.get(ExtractedStatement, statement_id)
    if statement is None:
        raise AppError("Statement not found", status_code=404, code="statement_not_found")
    if statement.status != StatementStatus.confirmed:
        raise AppError(
            "Cannot run alignment on unconfirmed statement",
            status_code=409,
            code="statement_unconfirmed",
        )
    if statement.statement_type != StatementType.deadline:
        raise AppError(
            "Statement must be of type deadline",
            status_code=400,
            code="statement_not_deadline",
        )

    fact = await session.get(ObservedFact, fact_id)
    if fact is None:
        raise AppError("Observed fact not found", status_code=404, code="fact_not_found")
    if fact.company_id != company_id:
        raise AppError("Fact does not belong to company", status_code=400, code="fact_company_mismatch")
    if fact.predicate != "actual_first_contact_minutes":
        raise AppError(
            "Fact predicate must be actual_first_contact_minutes",
            status_code=400,
            code="fact_predicate_mismatch",
        )

    normative_minutes = _minutes_from_structured(statement.value_structured, "amount", "minutes")
    actual_minutes = _minutes_from_structured(fact.value_structured, "minutes", "amount")
    deviation = actual_minutes - normative_minutes
    severity = _severity_for_deviation(deviation, severity_bands)
    substantial = deviation > substantial_threshold

    check = AlignmentCheck(
        company_id=company_id,
        name="Срок первого контакта с лидом",
        rule_code="lead_first_contact_deadline",
        rule_version_id=rule_version.id if rule_version else None,
        status=AlignmentCheckStatus.completed,
    )
    session.add(check)
    await session.flush()

    evidence = {
        "statement_id": str(statement.id),
        "fact_id": str(fact.id),
        "source_anchors": {
            "statement": statement.source_anchor,
            "fact_lineage": fact.lineage,
        },
        "rule_code": "lead_first_contact_deadline",
        "rule_version_id": str(rule_version.id) if rule_version else None,
        "rule_version_number": rule_version.version_number if rule_version else None,
        "severity_bands": severity_bands,
        "subject": fact.subject,
    }

    issue = AlignmentIssue(
        check_id=check.id,
        company_id=company_id,
        document_id=statement.document_id,
        statement_id=statement.id,
        fact_id=fact.id,
        normative_value={"minutes": normative_minutes, "unit": "minutes"},
        actual_value={"minutes": actual_minutes, "unit": "minutes", "subject": fact.subject},
        deviation_value={
            "minutes": deviation,
            "substantial": substantial,
            "label": "substantial" if substantial else ("over" if deviation > 0 else "within"),
        },
        severity=severity,
        trust_index=0.55,
        status=AlignmentIssueStatus.open,
        evidence=evidence,
    )
    session.add(issue)
    await session.flush()
    await write_audit(
        session,
        action="alignment.check_completed",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=company_id,
        payload={
            "check_id": str(check.id),
            "deviation_minutes": deviation,
            "severity": severity.value,
            "statement_id": str(statement.id),
            "fact_id": str(fact.id),
        },
    )
    await session.commit()
    await session.refresh(issue)
    await session.refresh(check)
    return issue


async def run_responsible_actor_check(
    session: AsyncSession,
    company_id: uuid.UUID,
    statement_id: uuid.UUID,
    fact_id: uuid.UUID,
) -> AlignmentIssue:
    """Сравнивает нормативного ответственного с фактическим исполнителем/позицией."""
    await get_company(session, company_id)

    statement = await session.get(ExtractedStatement, statement_id)
    if statement is None:
        raise AppError("Statement not found", status_code=404, code="statement_not_found")
    if statement.status != StatementStatus.confirmed:
        raise AppError(
            "Cannot run alignment on unconfirmed statement",
            status_code=409,
            code="statement_unconfirmed",
        )
    if statement.statement_type != StatementType.responsible:
        raise AppError(
            "Statement must be of type responsible",
            status_code=400,
            code="statement_not_responsible",
        )

    fact = await session.get(ObservedFact, fact_id)
    if fact is None:
        raise AppError("Observed fact not found", status_code=404, code="fact_not_found")
    if fact.company_id != company_id:
        raise AppError("Fact does not belong to company", status_code=400, code="fact_company_mismatch")

    normative_role = str(
        (statement.value_structured or {}).get("role") or statement.value_text
    ).strip()
    assigned = str((fact.value_structured or {}).get("assigned_position") or "").strip()
    actual_actor = str((fact.value_structured or {}).get("actual_actor") or "").strip()

    role_norm = normative_role.casefold()
    assigned_match = bool(assigned) and (
        assigned.casefold() == role_norm
        or role_norm in assigned.casefold()
        or assigned.casefold() in role_norm
    )
    # Исполнитель-сотрудник (employee-*) не равен роли — это расхождение назначения.
    actor_is_person = actual_actor.lower().startswith("employee") or (
        actual_actor and actual_actor.casefold() != role_norm
    )
    mismatch = (not assigned_match) or actor_is_person

    severity = AlignmentIssueSeverity.medium if mismatch else AlignmentIssueSeverity.low
    if mismatch and not assigned_match:
        severity = AlignmentIssueSeverity.high

    check = AlignmentCheck(
        company_id=company_id,
        name="Ответственный vs фактический исполнитель",
        rule_code="lead_responsible_vs_actor",
        status=AlignmentCheckStatus.completed,
    )
    session.add(check)
    await session.flush()

    evidence = {
        "statement_id": str(statement.id),
        "fact_id": str(fact.id),
        "source_anchors": {
            "statement": statement.source_anchor,
            "fact_lineage": fact.lineage,
        },
        "rule_code": "lead_responsible_vs_actor",
        "subject": fact.subject,
    }

    issue = AlignmentIssue(
        check_id=check.id,
        company_id=company_id,
        document_id=statement.document_id,
        statement_id=statement.id,
        fact_id=fact.id,
        normative_value={"role": normative_role},
        actual_value={
            "assigned_position": assigned or None,
            "actual_actor": actual_actor or None,
            "subject": fact.subject,
        },
        deviation_value={
            "mismatch": mismatch,
            "assigned_matches_role": assigned_match,
            "actor_differs_from_role": actor_is_person,
            "label": "mismatch" if mismatch else "match",
        },
        severity=severity,
        trust_index=0.6,
        status=AlignmentIssueStatus.open,
        evidence=evidence,
    )
    session.add(issue)
    await session.flush()
    await write_audit(
        session,
        action="alignment.check_completed",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=company_id,
        payload={
            "check_id": str(check.id),
            "rule_code": "lead_responsible_vs_actor",
            "mismatch": mismatch,
            "severity": severity.value,
        },
    )
    await session.commit()
    await session.refresh(issue)
    return issue


async def run_process_stage_check(
    session: AsyncSession,
    company_id: uuid.UUID,
    statement_id: uuid.UUID,
    fact_id: uuid.UUID,
) -> AlignmentIssue:
    """Сравнивает обязательные этапы регламента с фактически пройденными/пропущенными."""
    await get_company(session, company_id)

    statement = await session.get(ExtractedStatement, statement_id)
    if statement is None:
        raise AppError("Statement not found", status_code=404, code="statement_not_found")
    if statement.status != StatementStatus.confirmed:
        raise AppError(
            "Cannot run alignment on unconfirmed statement",
            status_code=409,
            code="statement_unconfirmed",
        )
    if statement.statement_type != StatementType.process_stage:
        raise AppError(
            "Statement must be of type process_stage",
            status_code=400,
            code="statement_not_process_stage",
        )

    fact = await session.get(ObservedFact, fact_id)
    if fact is None:
        raise AppError("Observed fact not found", status_code=404, code="fact_not_found")
    if fact.company_id != company_id:
        raise AppError("Fact does not belong to company", status_code=400, code="fact_company_mismatch")

    required = [
        str(s).strip()
        for s in (statement.value_structured or {}).get("stages") or []
        if str(s).strip()
    ]
    if not required and statement.value_text:
        required = [part.strip() for part in re.split(r"→|->|,|;", statement.value_text) if part.strip()]

    completed = [
        str(s).strip()
        for s in (fact.value_structured or {}).get("stages_completed") or []
        if str(s).strip()
    ]
    skipped = [
        str(s).strip()
        for s in (fact.value_structured or {}).get("stages_skipped") or []
        if str(s).strip()
    ]
    if not skipped and required:
        completed_cf = {c.casefold() for c in completed}
        skipped = [r for r in required if r.casefold() not in completed_cf]

    mismatch = bool(skipped)
    severity = AlignmentIssueSeverity.high if mismatch else AlignmentIssueSeverity.low
    if mismatch and len(skipped) >= 2:
        severity = AlignmentIssueSeverity.critical

    check = AlignmentCheck(
        company_id=company_id,
        name="Обязательные этапы обработки лида",
        rule_code="lead_process_stages",
        status=AlignmentCheckStatus.completed,
    )
    session.add(check)
    await session.flush()

    evidence = {
        "statement_id": str(statement.id),
        "fact_id": str(fact.id),
        "source_anchors": {
            "statement": statement.source_anchor,
            "fact_lineage": fact.lineage,
        },
        "rule_code": "lead_process_stages",
        "subject": fact.subject,
    }

    issue = AlignmentIssue(
        check_id=check.id,
        company_id=company_id,
        document_id=statement.document_id,
        statement_id=statement.id,
        fact_id=fact.id,
        normative_value={"stages": required},
        actual_value={
            "stages_completed": completed,
            "stages_skipped": skipped,
            "subject": fact.subject,
        },
        deviation_value={
            "mismatch": mismatch,
            "skipped_count": len(skipped),
            "label": "stages_skipped" if mismatch else "stages_ok",
        },
        severity=severity,
        trust_index=0.58,
        status=AlignmentIssueStatus.open,
        evidence=evidence,
    )
    session.add(issue)
    await session.flush()
    await write_audit(
        session,
        action="alignment.check_completed",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=company_id,
        payload={
            "check_id": str(check.id),
            "rule_code": "lead_process_stages",
            "skipped": skipped,
            "severity": severity.value,
        },
    )
    await session.commit()
    await session.refresh(issue)
    return issue


async def get_issue(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    issue = await session.get(AlignmentIssue, issue_id)
    if issue is None:
        raise AppError("Alignment issue not found", status_code=404, code="alignment_issue_not_found")
    return issue


async def list_issues(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    status: AlignmentIssueStatus | None = None,
) -> list[AlignmentIssue]:
    from sqlalchemy import select

    stmt = (
        select(AlignmentIssue)
        .where(AlignmentIssue.company_id == company_id)
        .order_by(AlignmentIssue.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(AlignmentIssue.status == status)
    return list((await session.scalars(stmt)).all())


async def get_check(session: AsyncSession, check_id: uuid.UUID) -> AlignmentCheck:
    check = await session.get(AlignmentCheck, check_id)
    if check is None:
        raise AppError("Alignment check not found", status_code=404, code="alignment_check_not_found")
    return check


async def _require_open_issue(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    issue = await get_issue(session, issue_id)
    if issue.status != AlignmentIssueStatus.open:
        raise AppError(
            "Only open alignment issues can be reviewed",
            status_code=409,
            code="alignment_issue_not_open",
        )
    return issue


async def confirm_issue(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    issue = await _require_open_issue(session, issue_id)

    if issue.statement_id is None:
        raise AppError("Issue missing statement", status_code=400, code="issue_missing_statement")
    statement = await session.get(ExtractedStatement, issue.statement_id)
    if statement is None or statement.status != StatementStatus.confirmed:
        raise AppError(
            "Cannot create knowledge from unverified statement",
            status_code=409,
            code="statement_unconfirmed",
        )

    record = await _attach_knowledge(session, issue, accepted=False)
    proposal = _store_proposed_change(issue)
    issue.status = AlignmentIssueStatus.confirmed
    issue.reviewed_at = datetime.now(UTC)
    issue.trust_index = 0.85
    await session.flush()
    await write_audit(
        session,
        action="alignment.issue_confirmed",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload={
            "knowledge_record_id": str(record.id),
            "proposed_change_title": proposal.get("title"),
        },
    )
    await write_audit(
        session,
        action="alignment.document_change_proposed",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload=proposal,
    )
    await write_audit(
        session,
        action="knowledge.created",
        entity_type="knowledge_record",
        entity_id=record.id,
        company_id=issue.company_id,
        payload={"alignment_issue_id": str(issue.id), "via": "alignment_confirm"},
    )
    await session.commit()
    await session.refresh(issue)
    return issue


async def reject_issue(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    issue = await _require_open_issue(session, issue_id)
    issue.status = AlignmentIssueStatus.rejected
    issue.reviewed_at = datetime.now(UTC)
    await write_audit(
        session,
        action="alignment.issue_rejected",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload={},
    )
    await session.commit()
    await session.refresh(issue)
    return issue


async def accept_deviation(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    issue = await _require_open_issue(session, issue_id)
    if issue.statement_id is None:
        raise AppError("Issue missing statement", status_code=400, code="issue_missing_statement")
    statement = await session.get(ExtractedStatement, issue.statement_id)
    if statement is None or statement.status != StatementStatus.confirmed:
        raise AppError(
            "Cannot accept deviation without confirmed statement",
            status_code=409,
            code="statement_unconfirmed",
        )

    record = await _attach_knowledge(session, issue, accepted=True)
    issue.status = AlignmentIssueStatus.accepted_deviation
    issue.reviewed_at = datetime.now(UTC)
    issue.trust_index = 0.7
    await session.flush()
    await write_audit(
        session,
        action="alignment.deviation_accepted",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload={"knowledge_record_id": str(record.id)},
    )
    await write_audit(
        session,
        action="knowledge.created",
        entity_type="knowledge_record",
        entity_id=record.id,
        company_id=issue.company_id,
        payload={"alignment_issue_id": str(issue.id), "via": "accepted_deviation"},
    )
    await session.commit()
    await session.refresh(issue)
    return issue


async def request_data(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    issue = await _require_open_issue(session, issue_id)
    issue.status = AlignmentIssueStatus.needs_data
    issue.reviewed_at = datetime.now(UTC)
    evidence = dict(issue.evidence or {})
    evidence["data_request"] = {
        "status": "requested",
        "message": (
            "Нужны дополнительные CRM-данные для закрытия сверки Sales SLA "
            "(этапы, исполнитель или точное время первого контакта)."
        ),
        "requested_at": datetime.now(UTC).isoformat(),
    }
    issue.evidence = evidence
    flag_modified(issue, "evidence")
    await write_audit(
        session,
        action="alignment.data_requested",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload=evidence["data_request"],
    )
    await session.commit()
    await session.refresh(issue)
    return issue


async def apply_proposed_change(session: AsyncSession, issue_id: uuid.UUID) -> AlignmentIssue:
    """Materialize proposed_change as a new document version (draft text file)."""
    issue = await get_issue(session, issue_id)
    if issue.status != AlignmentIssueStatus.confirmed:
        raise AppError(
            "Proposed change can be applied only for confirmed issues",
            status_code=409,
            code="issue_not_confirmed",
        )
    proposal = (issue.evidence or {}).get("proposed_change")
    if not proposal:
        raise AppError("No proposed change on issue", status_code=404, code="proposed_change_missing")
    if proposal.get("status") == "applied":
        raise AppError("Proposed change already applied", status_code=409, code="proposed_change_applied")
    if not issue.document_id:
        raise AppError("Issue has no document", status_code=400, code="issue_missing_document")

    from modules.documents import service as documents_service

    body = str(proposal.get("suggested_text") or proposal.get("summary") or "").strip()
    if not body:
        raise AppError("Proposed change has empty text", status_code=400, code="proposed_change_empty")
    unique = uuid.uuid4().hex[:6]
    header = (
        f"# Draft revision from alignment {issue.id}\n"
        f"# {proposal.get('title') or 'Document change'}\n\n"
    )
    data = f"{header}{body}\n".encode("utf-8")
    document, duplicate, _existing = await documents_service.add_document_version(
        session,
        document_id=issue.document_id,
        filename=f"sla-revision-{unique}.pdf",
        content_type="application/pdf",
        data=data,
    )
    if duplicate:
        raise AppError(
            "Draft revision duplicates an existing file",
            status_code=409,
            code="proposed_change_duplicate",
        )
    # Reload issue after document service commit
    issue = await get_issue(session, issue_id)
    document = await documents_service.get_document(session, issue.document_id)
    version = max(document.versions, key=lambda v: v.version_number) if document.versions else None

    evidence = dict(issue.evidence or {})
    updated = dict(proposal)
    updated["status"] = "applied"
    updated["applied_version_id"] = str(version.id) if version else None
    updated["applied_at"] = datetime.now(UTC).isoformat()
    evidence["proposed_change"] = updated
    issue.evidence = evidence
    flag_modified(issue, "evidence")
    await write_audit(
        session,
        action="alignment.document_change_applied",
        entity_type="alignment_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload={
            "document_id": str(issue.document_id),
            "version_id": str(version.id) if version else None,
            "title": updated.get("title"),
        },
    )
    await session.commit()
    await session.refresh(issue)
    return issue
