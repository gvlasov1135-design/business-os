import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import AppError
from modules.alignment import service as alignment_service
from modules.analysis import service as analysis_service
from modules.decisions import service as decisions_service
from modules.decisions.models import DecisionStatus
from modules.decisions.schemas import DecisionCreate
from modules.demo.schemas import DemoRunResponse
from modules.documents import intelligence_service
from modules.documents import service as documents_service
from modules.identity import service as identity_service
from modules.identity.models import Company
from modules.identity.schemas import CompanyCreate
from modules.ingestion import service as ingestion_service
from modules.ingestion.models import SourceType
from modules.knowledge.models import KnowledgeRecord

DEMO_POLICY_TEXT = (
    "Менеджер по продажам обязан связаться с новым лидом "
    "не позднее 15 минут после его создания. "
    "KPI: доля лидов с первым контактом ≤ 15 минут не ниже 90%. "
    "Обязательные этапы: создание лида → квалификация → первый контакт."
)

DEMO_JOB_DESCRIPTION_TEXT = (
    "Должностная инструкция менеджера по продажам. "
    "Менеджер по продажам отвечает за первый контакт с новым лидом "
    "и соблюдение SLA очереди. "
    "KPI: доля лидов с первым контактом ≤ 15 минут не ниже 90%."
)

DEMO_CRM_PAYLOAD = {
    "lead_id": "L-1001",
    "created_at": "2026-08-01T09:00:00+03:00",
    "first_contact_at": "2026-08-01T09:47:00+03:00",
    "assigned_position": "Sales Manager",
    "actual_actor": "employee-17",
    "email": "lead1001@example.com",
    "counterparty_name": "ООО Ромашка",
    "stages_completed": ["создание лида", "первый контакт"],
    "stages_skipped": ["квалификация"],
}

DEMO_CRM_JUSTIFIED_PAYLOAD = {
    "lead_id": "L-JUSTIFIED",
    "created_at": "2026-08-01T10:00:00+03:00",
    "first_contact_at": "2026-08-01T10:08:00+03:00",
    "assigned_position": "Sales Manager",
    "actual_actor": "employee-17",
    "email": "lead-justified@example.com",
    "counterparty_name": "ООО Василёк",
    "stages_completed": ["создание лида", "первый контакт"],
    "stages_skipped": ["квалификация"],
    "stage_skip_reason": "Повторное обращение — квалификация уже в карточке клиента",
}

DEMO_CRM_NEEDS_PAYLOAD = {
    "lead_id": "L-NEEDS",
    "created_at": "2026-08-01T11:00:00+03:00",
    "first_contact_at": "2026-08-01T11:40:00+03:00",
    "assigned_position": "Sales Manager",
    "actual_actor": "employee-21",
    "email": "lead-needs@example.com",
    "counterparty_name": "ООО Незавершённый",
    "stages_completed": ["создание лида", "квалификация", "первый контакт"],
    "stages_skipped": [],
}

DEMO_CRM_DUP_PAYLOAD = {
    "lead_id": "L-1001-DUP",
    "created_at": "2026-08-01T09:05:00+03:00",
    "first_contact_at": "2026-08-01T09:20:00+03:00",
    "assigned_position": "Sales Manager",
    "actual_actor": "employee-17",
    "email": "lead1001@example.com",
    "counterparty_name": "ООО Ромашка",
    "stages_completed": ["создание лида", "квалификация", "первый контакт"],
    "stages_skipped": [],
}

DEMO_QUESTION = (
    "Есть ли подтвержденное нарушение SLA первого контакта по L-1001, "
    "расхождение по ответственному и пропуск этапов — и что можно сделать?"
)


async def run_demo(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
) -> DemoRunResponse:
    if company_id is None:
        existing = await session.scalar(select(Company).where(Company.name == "Demo Company"))
        if existing is not None:
            company_id = existing.id
        else:
            try:
                bootstrap = await identity_service.bootstrap_identity(session)
                company_id = bootstrap.company.id
            except AppError:
                company = await identity_service.create_company(
                    session, CompanyCreate(name=f"Demo Slice {uuid.uuid4().hex[:8]}")
                )
                company_id = company.id
    else:
        await identity_service.get_company(session, company_id)

    unique = uuid.uuid4().hex[:8]
    policy_bytes = f"{DEMO_POLICY_TEXT}\n\n# demo-run {unique}".encode("utf-8")
    document, _duplicate, _existing = await documents_service.upload_document(
        session,
        company_id=company_id,
        title=f"Sales Policy — Demo {unique}",
        filename=f"policy-{unique}.pdf",
        content_type="application/pdf",
        data=policy_bytes,
    )
    job_bytes = f"{DEMO_JOB_DESCRIPTION_TEXT}\n\n# job-demo {unique}".encode("utf-8")
    job_doc, _jd, _je = await documents_service.upload_document(
        session,
        company_id=company_id,
        title=f"Job Description — Demo {unique}",
        filename=f"job-{unique}.pdf",
        content_type="application/pdf",
        data=job_bytes,
    )
    job_doc = await documents_service.get_document(session, job_doc.id)
    job_version_id = job_doc.versions[0].id
    await intelligence_service.run_mock_extraction(
        session, document_id=job_doc.id, version_id=job_version_id
    )
    from modules.documents.intelligence_models import StatementStatus, StatementType

    job_proposed = await intelligence_service.list_statements(
        session, document_id=job_doc.id, status=StatementStatus.proposed
    )
    for item in job_proposed:
        await intelligence_service.confirm_statement(session, item.id)
    job_confirmed = await intelligence_service.list_statements(
        session, document_id=job_doc.id, status=StatementStatus.confirmed
    )
    job_responsible = next(
        (item for item in job_confirmed if item.statement_type == StatementType.responsible),
        None,
    )
    document = await documents_service.get_document(session, document.id)
    version_id = document.versions[0].id

    _fragment, statement, statements = await intelligence_service.run_mock_extraction(
        session, document_id=document.id, version_id=version_id
    )

    proposed = await intelligence_service.list_statements(
        session, document_id=document.id, status=StatementStatus.proposed
    )
    for item in proposed:
        await intelligence_service.confirm_statement(session, item.id)

    confirmed = await intelligence_service.list_statements(
        session, document_id=document.id, status=StatementStatus.confirmed
    )
    statement = next(
        (item for item in confirmed if item.statement_type == StatementType.deadline),
        None,
    )
    responsible_statement = job_responsible or next(
        (item for item in confirmed if item.statement_type == StatementType.responsible),
        None,
    )
    kpi_statement = next(
        (item for item in confirmed if item.statement_type == StatementType.kpi),
        None,
    )
    stage_statement = next(
        (item for item in confirmed if item.statement_type == StatementType.process_stage),
        None,
    )
    if statement is None:
        raise AppError("Demo deadline statement missing", status_code=500, code="demo_statement_missing")

    source = await ingestion_service.create_source(
        session,
        company_id=company_id,
        code=f"crm-demo-{uuid.uuid4().hex[:6]}",
        name="Demo CRM",
        source_type=SourceType.crm,
        freshness_hours=24,
    )
    imported = await ingestion_service.import_record(session, source.id, DEMO_CRM_PAYLOAD)
    if imported.fact is None:
        raise AppError("Demo import failed to create fact", status_code=500, code="demo_import_failed")

    justified_imported = await ingestion_service.import_record(
        session, source.id, DEMO_CRM_JUSTIFIED_PAYLOAD
    )
    if justified_imported.fact is None:
        raise AppError(
            "Demo justified import failed",
            status_code=500,
            code="demo_justified_import_failed",
        )
    justified_skip_ok = not any(
        (i.get("code") if isinstance(i, dict) else getattr(i, "code", None)) == "silent_stage_skip"
        for i in (justified_imported.issues or [])
    )

    needs_imported = await ingestion_service.import_record(session, source.id, DEMO_CRM_NEEDS_PAYLOAD)
    if needs_imported.fact is None:
        raise AppError("Demo needs-data import failed", status_code=500, code="demo_needs_import_failed")

    dup_imported = await ingestion_service.import_record(session, source.id, DEMO_CRM_DUP_PAYLOAD)
    if dup_imported.fact is None:
        raise AppError("Demo duplicate import failed", status_code=500, code="demo_dup_import_failed")

    from modules.resolution import service as resolution_service
    from modules.resolution.models import CandidateStatus

    pending = await resolution_service.list_candidates(
        session, company_id=company_id, status=CandidateStatus.pending
    )
    blocking = [c for c in pending if c.blocks_analysis]
    confirmed_candidate_id = None
    entity_id = None
    if blocking:
        confirmed = await resolution_service.confirm_candidate(
            session, blocking[0].id, note="Демо: подтверждение объединения по email"
        )
        confirmed_candidate_id = confirmed.id
        entity_id = confirmed.proposed_entity_id
    elif pending:
        confirmed = await resolution_service.confirm_candidate(
            session, pending[0].id, note="Демо: подтверждение кандидата"
        )
        confirmed_candidate_id = confirmed.id
        entity_id = confirmed.proposed_entity_id

    entities = await resolution_service.list_entities(session, company_id=company_id)
    if entity_id is None and entities:
        entity_id = entities[0].id

    fact_id = imported.fact.id
    issue = await alignment_service.run_lead_deadline_check(
        session,
        company_id=company_id,
        statement_id=statement.id,
        fact_id=fact_id,
    )
    issue = await alignment_service.confirm_issue(session, issue.id)
    deadline_proposed_change = (issue.evidence or {}).get("proposed_change")
    issue = await alignment_service.apply_proposed_change(session, issue.id)
    deadline_proposed_change = (issue.evidence or {}).get("proposed_change")
    applied_version_id = (deadline_proposed_change or {}).get("applied_version_id")

    responsible_issue_id = None
    responsible_mismatch = None
    responsible_status = None
    if responsible_statement is not None:
        responsible_issue = await alignment_service.run_responsible_actor_check(
            session,
            company_id=company_id,
            statement_id=responsible_statement.id,
            fact_id=fact_id,
        )
        # Sales SLA: исполнитель-сотрудник под ролью — принимаем как operational exception
        responsible_issue = await alignment_service.accept_deviation(session, responsible_issue.id)
        responsible_issue_id = responsible_issue.id
        responsible_mismatch = bool(responsible_issue.deviation_value.get("mismatch"))
        responsible_status = responsible_issue.status.value

    stage_issue_id = None
    stages_skipped = None
    stage_status = None
    stage_proposed_change = None
    if stage_statement is not None:
        stage_issue = await alignment_service.run_process_stage_check(
            session,
            company_id=company_id,
            statement_id=stage_statement.id,
            fact_id=fact_id,
        )
        stage_issue = await alignment_service.confirm_issue(session, stage_issue.id)
        stage_issue_id = stage_issue.id
        stages_skipped = stage_issue.actual_value.get("stages_skipped")
        stage_status = stage_issue.status.value
        stage_proposed_change = (stage_issue.evidence or {}).get("proposed_change")

    knowledge = await session.scalar(
        select(KnowledgeRecord).where(KnowledgeRecord.alignment_issue_id == issue.id)
    )
    if knowledge is None:
        raise AppError("Demo knowledge missing after confirm", status_code=500, code="demo_knowledge_missing")

    responsible_knowledge = None
    if responsible_issue_id:
        responsible_knowledge = await session.scalar(
            select(KnowledgeRecord).where(KnowledgeRecord.alignment_issue_id == responsible_issue_id)
        )
    stage_knowledge = None
    if stage_issue_id:
        stage_knowledge = await session.scalar(
            select(KnowledgeRecord).where(KnowledgeRecord.alignment_issue_id == stage_issue_id)
        )

    needs_data_issue = await alignment_service.run_lead_deadline_check(
        session,
        company_id=company_id,
        statement_id=statement.id,
        fact_id=needs_imported.fact.id,
    )
    needs_data_issue = await alignment_service.request_data(session, needs_data_issue.id)

    from modules.knowledge import service as knowledge_service
    from modules.knowledge.models import KnowledgeRelationType
    from modules.knowledge.schemas import KnowledgeRelationCreate

    relation_ids: list[str] = []
    if responsible_knowledge is not None:
        rel = await knowledge_service.ensure_relation(
            session,
            KnowledgeRelationCreate(
                company_id=company_id,
                from_record_id=knowledge.id,
                to_record_id=responsible_knowledge.id,
                relation_type=KnowledgeRelationType.relates_to,
            ),
        )
        relation_ids.append(str(rel.id))
    if stage_knowledge is not None:
        rel = await knowledge_service.ensure_relation(
            session,
            KnowledgeRelationCreate(
                company_id=company_id,
                from_record_id=knowledge.id,
                to_record_id=stage_knowledge.id,
                relation_type=KnowledgeRelationType.supports,
            ),
        )
        relation_ids.append(str(rel.id))

    from modules.kpi import service as kpi_service

    target_minutes = 15.0
    share_target = 90.0
    if kpi_statement and isinstance(kpi_statement.value_structured, dict):
        pct = kpi_statement.value_structured.get("target_pct")
        if pct is not None:
            share_target = float(pct)

    kpi_code = f"first_contact_avg_{uuid.uuid4().hex[:6]}"
    kpi = await kpi_service.create_kpi(
        session,
        company_id=company_id,
        code=kpi_code,
        name="Среднее время первого контакта",
        description=(
            "AVG минут до первого контакта по CRM-лидам. "
            + (
                f"Из регламента: {kpi_statement.value_text}"
                if kpi_statement
                else "Целевой SLA 15 минут."
            )
        ),
        unit="minutes",
        owner_name="Руководитель продаж",
        formula={"op": "avg_fact_minutes"},
        source_mapping={"predicate": "actual_first_contact_minutes", "source_type": "crm"},
        target_value=target_minutes,
        activate=True,
    )
    kpi_snapshot = await kpi_service.recalculate(
        session,
        kpi.id,
        period_start=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
        period_end=datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc),
    )

    share_kpi = await kpi_service.create_kpi(
        session,
        company_id=company_id,
        code=f"first_contact_share_{uuid.uuid4().hex[:6]}",
        name="Доля лидов в SLA первого контакта",
        description="SHARE % лидов с first_contact ≤ 15 минут (из KPI регламента).",
        unit="%",
        owner_name="Руководитель продаж",
        formula={"op": "share_within_target", "threshold_minutes": target_minutes},
        source_mapping={"predicate": "actual_first_contact_minutes", "source_type": "crm"},
        target_value=share_target,
        activate=True,
    )
    share_snapshot = await kpi_service.recalculate(
        session,
        share_kpi.id,
        period_start=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
        period_end=datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc),
    )

    analysis = await analysis_service.create_analysis(session, company_id, DEMO_QUESTION)
    recommendations = await analysis_service.list_recommendations(session, analysis.id)
    recommendation_id = recommendations[0].id if recommendations else None

    decision = await decisions_service.create_decision(
        session,
        DecisionCreate(
            company_id=company_id,
            analysis_id=analysis.id,
            recommendation_id=recommendation_id,
            status=DecisionStatus.accepted,
            rationale=(
                "Принять проверку Sales SLA по L-1001: подтвердить нарушение срока, "
                "принять отклонение по исполнителю (очередь под ролью), "
                "закрыть пропуск квалификации задачей процесса."
            ),
            owner_name="Демо-руководитель",
            checkpoint_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
            expected_result="SLA и этапы лида проверены, владелец очереди и квалификация назначены",
        ),
    )
    result = await decisions_service.record_result(
        session,
        decision.id,
        actual_result="SLA и этапы лида проверены, владелец очереди и квалификация назначены",
        checked_at=datetime(2026, 8, 16, 10, 0, tzinfo=timezone.utc),
        comment="Контрольная точка пройдена в демо-прогоне Sales SLA",
    )
    reviewed = await decisions_service.review_result(
        session,
        decision.id,
        review_notes=(
            "Срок подтверждён, исполнитель принят как исключение, пропуск квалификации — в работу."
        ),
        lesson_body=(
            "Для Sales SLA фиксировать три оси: срок, роль/исполнитель (accept deviation при "
            "очереди), обязательные этапы без silent skip."
        ),
        lesson_category="sla_ops",
    )
    tasks = await decisions_service.list_tasks(session, decision.id)
    lessons = await decisions_service.list_lessons(session, decision.id)

    return DemoRunResponse(
        company_id=company_id,
        document_id=document.id,
        version_id=version_id,
        statement_id=statement.id,
        source_id=source.id,
        raw_record_id=imported.raw_record.id,
        fact_id=fact_id,
        check_id=issue.check_id,
        issue_id=issue.id,
        knowledge_id=knowledge.id,
        analysis_id=analysis.id,
        recommendation_id=recommendation_id,
        decision_id=decision.id,
        extras={
            "deviation_minutes": issue.deviation_value.get("minutes"),
            "severity": issue.severity.value,
            "severity_from_rule": bool((issue.evidence or {}).get("severity_bands")),
            "analysis_status": analysis.status.value,
            "analysis_blocked": analysis.blocked,
            "decision_result_status": result.status.value,
            "statement_count": len(statements),
            "kpi_statement_id": str(kpi_statement.id) if kpi_statement else None,
            "responsible_issue_id": str(responsible_issue_id) if responsible_issue_id else None,
            "responsible_mismatch": responsible_mismatch,
            "responsible_status": responsible_status,
            "responsible_knowledge_id": str(responsible_knowledge.id) if responsible_knowledge else None,
            "stage_issue_id": str(stage_issue_id) if stage_issue_id else None,
            "stage_status": stage_status,
            "stages_skipped": stages_skipped,
            "stage_knowledge_id": str(stage_knowledge.id) if stage_knowledge else None,
            "entity_id": str(entity_id) if entity_id else None,
            "resolution_candidate_id": str(confirmed_candidate_id) if confirmed_candidate_id else None,
            "dup_raw_record_id": str(dup_imported.raw_record.id),
            "kpi_id": str(kpi.id),
            "kpi_code": kpi.code,
            "kpi_actual": kpi_snapshot.actual_value,
            "kpi_target": kpi_snapshot.target_value,
            "kpi_formula": kpi_snapshot.lineage.get("formula_text"),
            "kpi_snapshot_id": str(kpi_snapshot.id),
            "share_kpi_id": str(share_kpi.id),
            "share_kpi_actual": share_snapshot.actual_value,
            "share_kpi_target": share_snapshot.target_value,
            "proposed_change": deadline_proposed_change,
            "applied_document_version_id": applied_version_id,
            "stage_proposed_change": stage_proposed_change,
            "job_document_id": str(job_doc.id),
            "responsible_from_job_description": bool(job_responsible),
            "silent_stage_skip_warned": any(
                (i.get("code") if isinstance(i, dict) else getattr(i, "code", None))
                == "silent_stage_skip"
                for i in (imported.issues or [])
            ),
            "justified_stage_skip_ok": justified_skip_ok,
            "justified_fact_id": str(justified_imported.fact.id),
            "needs_data_issue_id": str(needs_data_issue.id),
            "needs_data_status": needs_data_issue.status.value,
            "knowledge_relation_ids": relation_ids,
            "agents": ["executive", "sales", "critic"],
            "rule_versions": (analysis.output or {}).get("rule_versions"),
            "disagreement_count": len((analysis.output or {}).get("disagreements") or []),
            "decision_selected_option": decision.selected_option,
            "decision_task_count": len(tasks),
            "decision_lesson_count": len(lessons),
            "decision_reviewed": reviewed.reviewed_at is not None,
            "analysis_missing_data": (analysis.output or {}).get("missing_data"),
        },
    )
