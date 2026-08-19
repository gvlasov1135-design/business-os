import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.ingestion.models import Source, SourceStatus
from modules.quality.models import DataQualityIssue, IssueSeverity, IssueStatus
from modules.quality.schemas import AnalysisGateResponse


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def check_crm_lead_payload(payload: dict[str, Any], source: Source) -> list[dict[str, Any]]:
    """Validate CRM lead payload; return issue descriptors (not persisted)."""
    issues: list[dict[str, Any]] = []

    lead_id = payload.get("lead_id")
    if lead_id is None or (isinstance(lead_id, str) and not lead_id.strip()):
        issues.append(
            {
                "code": "missing_lead_id",
                "message": "lead_id is required",
                "severity": IssueSeverity.critical,
                "blocks_analysis": True,
            }
        )

    created_raw = payload.get("created_at")
    created_at = _parse_datetime(created_raw)
    if created_raw is None or created_raw == "":
        issues.append(
            {
                "code": "missing_created_at",
                "message": "created_at is required",
                "severity": IssueSeverity.high,
                "blocks_analysis": True,
            }
        )
    elif created_at is None:
        issues.append(
            {
                "code": "invalid_created_at",
                "message": "created_at is not a parseable datetime",
                "severity": IssueSeverity.high,
                "blocks_analysis": True,
            }
        )

    contact_raw = payload.get("first_contact_at")
    first_contact_at = _parse_datetime(contact_raw)
    if contact_raw is None or contact_raw == "":
        issues.append(
            {
                "code": "missing_first_contact_at",
                "message": "first_contact_at is required",
                "severity": IssueSeverity.high,
                "blocks_analysis": True,
            }
        )
    elif first_contact_at is None:
        issues.append(
            {
                "code": "invalid_first_contact_at",
                "message": "first_contact_at is not a parseable datetime",
                "severity": IssueSeverity.high,
                "blocks_analysis": True,
            }
        )

    if created_at is not None and first_contact_at is not None and first_contact_at < created_at:
        issues.append(
            {
                "code": "first_contact_before_created",
                "message": "first_contact_at must be greater than or equal to created_at",
                "severity": IssueSeverity.high,
                "blocks_analysis": True,
            }
        )

    if source.status == SourceStatus.stale:
        issues.append(
            {
                "code": "source_stale",
                "message": "source is stale and cannot be used for normalization",
                "severity": IssueSeverity.critical,
                "blocks_analysis": True,
            }
        )

    skipped = payload.get("stages_skipped") or []
    if isinstance(skipped, list) and any(str(s).strip() for s in skipped):
        reason = payload.get("stage_skip_reason") or payload.get("skip_reason")
        if not reason or (isinstance(reason, str) and not str(reason).strip()):
            issues.append(
                {
                    "code": "silent_stage_skip",
                    "message": (
                        "Этапы пропущены без stage_skip_reason — silent skip запрещён для Sales SLA"
                    ),
                    "severity": IssueSeverity.medium,
                    "blocks_analysis": False,
                }
            )

    return issues


def should_quarantine(issues: list[dict[str, Any]]) -> bool:
    return any(
        issue.get("blocks_analysis")
        and issue.get("severity") in (IssueSeverity.high, IssueSeverity.critical, "high", "critical")
        for issue in issues
    )


async def create_issues(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    source_id: uuid.UUID | None,
    raw_record_id: uuid.UUID | None,
    issues: list[dict[str, Any]],
) -> list[DataQualityIssue]:
    created: list[DataQualityIssue] = []
    for issue in issues:
        severity = issue["severity"]
        if isinstance(severity, str):
            severity = IssueSeverity(severity)
        row = DataQualityIssue(
            company_id=company_id,
            source_id=source_id,
            raw_record_id=raw_record_id,
            code=issue["code"],
            message=issue["message"],
            severity=severity,
            status=IssueStatus.open,
            blocks_analysis=bool(issue.get("blocks_analysis", True)),
        )
        session.add(row)
        created.append(row)
    if created:
        await session.flush()
    return created


async def list_issues(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    status: IssueStatus | None = None,
) -> list[DataQualityIssue]:
    stmt = select(DataQualityIssue).order_by(DataQualityIssue.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(DataQualityIssue.company_id == company_id)
    if status is not None:
        stmt = stmt.where(DataQualityIssue.status == status)
    result = await session.scalars(stmt)
    return list(result.all())


async def evaluate_analysis_gate(
    session: AsyncSession,
    company_id: uuid.UUID,
) -> AnalysisGateResponse:
    stmt = select(DataQualityIssue).where(
        DataQualityIssue.company_id == company_id,
        DataQualityIssue.status == IssueStatus.open,
        DataQualityIssue.blocks_analysis.is_(True),
    )
    result = await session.scalars(stmt)
    issues = list(result.all())
    reasons = [issue.message for issue in issues]

    from modules.resolution import service as resolution_service

    reasons.extend(await resolution_service.pending_blocking_reasons(session, company_id))

    from modules.kpi import service as kpi_service

    reasons.extend(await kpi_service.integrity_block_reasons(session, company_id))
    return AnalysisGateResponse(blocked=bool(reasons), reasons=reasons)


async def get_issue(session: AsyncSession, issue_id: uuid.UUID) -> DataQualityIssue:
    issue = await session.get(DataQualityIssue, issue_id)
    if issue is None:
        from common.errors import AppError

        raise AppError("Data quality issue not found", status_code=404, code="dq_issue_not_found")
    return issue


async def explain_issue(session: AsyncSession, issue_id: uuid.UUID) -> dict:
    """Data Doctor AI: только объяснение. Не меняет данные и не снимает блокировку."""
    from common.audit import write_audit
    from modules.llm import AgentProfile, LLMRequest, get_llm_gateway
    from modules.quality.schemas import DataDoctorExplanation

    issue = await get_issue(session, issue_id)
    gateway = get_llm_gateway()
    response = gateway.complete(
        LLMRequest(
            agent=AgentProfile.data_doctor,
            prompt="Объясни проблему качества данных",
            context={
                "issue": {
                    "id": str(issue.id),
                    "code": issue.code,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "blocks_analysis": issue.blocks_analysis,
                }
            },
        )
    )
    content = response.content
    explanation = DataDoctorExplanation(
        issue_id=issue.id,
        explanation=str(content.get("explanation") or ""),
        likely_cause=str(content.get("likely_cause") or issue.message),
        suggested_fix=str(content.get("suggested_fix") or ""),
        suggested_owner=str(content.get("suggested_owner") or ""),
        prepared_task=str(content.get("prepared_task") or ""),
        read_only=True,
        can_unblock_analysis=False,
        provider=response.provider,
    )
    await write_audit(
        session,
        action="quality.data_doctor_explained",
        entity_type="data_quality_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload={"read_only": True, "can_unblock_analysis": False},
    )
    await session.commit()
    return explanation.model_dump(mode="json")


async def resolve_issue(
    session: AsyncSession,
    issue_id: uuid.UUID,
    *,
    reason: str,
) -> DataQualityIssue:
    """Acknowledge non-blocking DQ (e.g. silent_stage_skip) with an explicit reason."""
    from common.audit import write_audit
    from common.errors import AppError

    issue = await get_issue(session, issue_id)
    if issue.status == IssueStatus.resolved:
        return issue
    if issue.blocks_analysis:
        raise AppError(
            "Blocking DQ issues cannot be resolved by acknowledgment — fix the source data",
            status_code=409,
            code="dq_blocking_not_ackable",
        )
    cleaned = reason.strip()
    if not cleaned:
        raise AppError("resolution reason is required", status_code=400, code="dq_reason_required")
    if issue.code == "silent_stage_skip" and len(cleaned) < 3:
        raise AppError(
            "stage_skip_reason required to resolve silent_stage_skip",
            status_code=400,
            code="dq_stage_skip_reason_required",
        )

    issue.status = IssueStatus.resolved
    await write_audit(
        session,
        action="quality.issue_resolved",
        entity_type="data_quality_issue",
        entity_id=issue.id,
        company_id=issue.company_id,
        payload={"code": issue.code, "reason": cleaned, "blocks_analysis": False},
    )
    await session.commit()
    await session.refresh(issue)
    return issue


parse_datetime = _parse_datetime
