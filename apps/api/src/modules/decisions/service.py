import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.analysis.models import AIAnalysis, Recommendation
from modules.decisions.models import (
    Decision,
    DecisionLesson,
    DecisionResult,
    DecisionResultStatus,
    DecisionTask,
    DecisionTaskStatus,
)
from modules.decisions.schemas import DecisionCreate
from modules.identity.service import get_company


def compare_results(expected: str, actual: str) -> tuple[DecisionResultStatus, str | None]:
    exp = expected.strip().lower()
    act = actual.strip().lower()
    if exp == act:
        return DecisionResultStatus.met, None
    if exp in act or act in exp:
        return DecisionResultStatus.partial, f"Partial match: expected '{expected}' vs actual '{actual}'"
    return DecisionResultStatus.missed, f"Mismatch: expected '{expected}' vs actual '{actual}'"


async def create_decision(session: AsyncSession, payload: DecisionCreate) -> Decision:
    await get_company(session, payload.company_id)

    selected_option = payload.selected_option
    if payload.analysis_id is not None:
        analysis = await session.get(AIAnalysis, payload.analysis_id)
        if analysis is None:
            raise AppError("Analysis not found", status_code=404, code="analysis_not_found")
        if analysis.company_id != payload.company_id:
            raise AppError("Analysis company mismatch", status_code=400, code="analysis_company_mismatch")

    if payload.recommendation_id is not None:
        recommendation = await session.get(Recommendation, payload.recommendation_id)
        if recommendation is None:
            raise AppError("Recommendation not found", status_code=404, code="recommendation_not_found")
        if not selected_option:
            selected_option = recommendation.title

    decision = Decision(
        company_id=payload.company_id,
        analysis_id=payload.analysis_id,
        recommendation_id=payload.recommendation_id,
        status=payload.status,
        selected_option=selected_option,
        rationale=payload.rationale,
        owner_name=payload.owner_name,
        checkpoint_at=payload.checkpoint_at,
        expected_result=payload.expected_result,
    )
    session.add(decision)
    await session.flush()

    if payload.create_followup_task and payload.status.value != "rejected":
        session.add(
            DecisionTask(
                decision_id=decision.id,
                company_id=payload.company_id,
                title=f"Контроль: {payload.expected_result[:180]}",
                assignee_name=payload.owner_name,
                due_at=payload.checkpoint_at,
                status=DecisionTaskStatus.open,
            )
        )
        await session.flush()

    await write_audit(
        session,
        action="decision.created",
        entity_type="decision",
        entity_id=decision.id,
        company_id=payload.company_id,
        payload={
            "status": decision.status.value,
            "owner_name": decision.owner_name,
            "selected_option": selected_option,
            "analysis_id": str(decision.analysis_id) if decision.analysis_id else None,
            "recommendation_id": str(decision.recommendation_id) if decision.recommendation_id else None,
        },
    )
    from modules.outbox import service as outbox_service

    await outbox_service.enqueue(
        session,
        event_type="decision.created",
        aggregate_type="decision",
        aggregate_id=decision.id,
        company_id=payload.company_id,
        payload={
            "status": decision.status.value,
            "owner_name": decision.owner_name,
            "selected_option": selected_option,
        },
    )
    await session.commit()
    await session.refresh(decision)
    return decision


async def list_decisions(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
) -> list[Decision]:
    stmt = select(Decision).order_by(Decision.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(Decision.company_id == company_id)
    return list((await session.scalars(stmt)).all())


async def get_decision(session: AsyncSession, decision_id: uuid.UUID) -> Decision:
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise AppError("Decision not found", status_code=404, code="decision_not_found")
    return decision


async def get_decision_result(
    session: AsyncSession,
    decision_id: uuid.UUID,
) -> DecisionResult | None:
    return await session.scalar(
        select(DecisionResult).where(DecisionResult.decision_id == decision_id)
    )


async def list_tasks(session: AsyncSession, decision_id: uuid.UUID) -> list[DecisionTask]:
    return list(
        (
            await session.scalars(
                select(DecisionTask)
                .where(DecisionTask.decision_id == decision_id)
                .order_by(DecisionTask.created_at)
            )
        ).all()
    )


async def list_lessons(session: AsyncSession, decision_id: uuid.UUID) -> list[DecisionLesson]:
    return list(
        (
            await session.scalars(
                select(DecisionLesson)
                .where(DecisionLesson.decision_id == decision_id)
                .order_by(DecisionLesson.created_at)
            )
        ).all()
    )


async def add_task(
    session: AsyncSession,
    decision_id: uuid.UUID,
    *,
    title: str,
    assignee_name: str,
    due_at: datetime | None = None,
) -> DecisionTask:
    decision = await get_decision(session, decision_id)
    task = DecisionTask(
        decision_id=decision.id,
        company_id=decision.company_id,
        title=title,
        assignee_name=assignee_name,
        due_at=due_at,
        status=DecisionTaskStatus.open,
    )
    session.add(task)
    await session.flush()
    await write_audit(
        session,
        action="decision.task_created",
        entity_type="decision_task",
        entity_id=task.id,
        company_id=decision.company_id,
        payload={"decision_id": str(decision.id), "title": title},
    )
    await session.commit()
    await session.refresh(task)
    return task


async def update_task_status(
    session: AsyncSession,
    task_id: uuid.UUID,
    status: DecisionTaskStatus,
) -> DecisionTask:
    task = await session.get(DecisionTask, task_id)
    if task is None:
        raise AppError("Decision task not found", status_code=404, code="decision_task_not_found")
    task.status = status
    await session.flush()
    await write_audit(
        session,
        action="decision.task_updated",
        entity_type="decision_task",
        entity_id=task.id,
        company_id=task.company_id,
        payload={"status": status.value},
    )
    await session.commit()
    await session.refresh(task)
    return task


async def add_lesson(
    session: AsyncSession,
    decision_id: uuid.UUID,
    *,
    body: str,
    category: str = "general",
    commit: bool = True,
) -> DecisionLesson:
    decision = await get_decision(session, decision_id)
    lesson = DecisionLesson(
        decision_id=decision.id,
        company_id=decision.company_id,
        body=body,
        category=category,
    )
    session.add(lesson)
    await session.flush()
    await write_audit(
        session,
        action="decision.lesson_created",
        entity_type="decision_lesson",
        entity_id=lesson.id,
        company_id=decision.company_id,
        payload={"decision_id": str(decision.id), "category": category},
    )
    from modules.outbox import service as outbox_service

    await outbox_service.enqueue(
        session,
        event_type="decision.lesson_created",
        aggregate_type="decision",
        aggregate_id=decision.id,
        company_id=decision.company_id,
        payload={"lesson_id": str(lesson.id), "category": category},
    )
    if commit:
        await session.commit()
        await session.refresh(lesson)
    return lesson


async def record_result(
    session: AsyncSession,
    decision_id: uuid.UUID,
    *,
    actual_result: str,
    checked_at: datetime,
    comment: str | None = None,
) -> DecisionResult:
    decision = await get_decision(session, decision_id)
    existing = await get_decision_result(session, decision_id)
    if existing is not None:
        raise AppError("Decision result already recorded", status_code=409, code="decision_result_exists")

    status, deviation_note = compare_results(decision.expected_result, actual_result)
    result = DecisionResult(
        decision_id=decision.id,
        actual_result=actual_result,
        checked_at=checked_at,
        comment=comment,
        deviation_note=deviation_note,
        status=status,
    )
    session.add(result)
    await session.flush()

    # закрыть follow-up задачиски при met
    if status == DecisionResultStatus.met:
        tasks = await list_tasks(session, decision.id)
        for task in tasks:
            if task.status == DecisionTaskStatus.open:
                task.status = DecisionTaskStatus.done

    await write_audit(
        session,
        action="decision.result_recorded",
        entity_type="decision_result",
        entity_id=result.id,
        company_id=decision.company_id,
        payload={
            "decision_id": str(decision.id),
            "status": status.value,
            "expected_result": decision.expected_result,
            "actual_result": actual_result,
            "deviation_note": deviation_note,
        },
    )
    from modules.outbox import service as outbox_service

    await outbox_service.enqueue(
        session,
        event_type="decision.result_recorded",
        aggregate_type="decision",
        aggregate_id=decision.id,
        company_id=decision.company_id,
        payload={"result_status": status.value, "result_id": str(result.id)},
    )
    await session.commit()
    await session.refresh(result)
    return result


async def review_result(
    session: AsyncSession,
    decision_id: uuid.UUID,
    *,
    review_notes: str,
    lesson_body: str | None = None,
    lesson_category: str = "outcome",
) -> DecisionResult:
    decision = await get_decision(session, decision_id)
    result = await get_decision_result(session, decision_id)
    if result is None:
        raise AppError("Decision result required before review", status_code=400, code="result_required")
    if result.reviewed_at is not None:
        raise AppError("Result already reviewed", status_code=409, code="result_already_reviewed")

    result.review_notes = review_notes
    result.reviewed_at = datetime.now(timezone.utc)
    await session.flush()

    if lesson_body:
        await add_lesson(
            session,
            decision.id,
            body=lesson_body,
            category=lesson_category,
            commit=False,
        )

    await write_audit(
        session,
        action="decision.result_reviewed",
        entity_type="decision_result",
        entity_id=result.id,
        company_id=decision.company_id,
        payload={"decision_id": str(decision.id), "with_lesson": bool(lesson_body)},
    )
    from modules.outbox import service as outbox_service

    await outbox_service.enqueue(
        session,
        event_type="decision.result_reviewed",
        aggregate_type="decision",
        aggregate_id=decision.id,
        company_id=decision.company_id,
        payload={"result_id": str(result.id)},
    )
    await session.commit()
    await session.refresh(result)
    return result
