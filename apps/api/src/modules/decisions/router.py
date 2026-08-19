import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.decisions import service
from modules.decisions.schemas import (
    DecisionCreate,
    DecisionLessonCreate,
    DecisionLessonRead,
    DecisionRead,
    DecisionResultCreate,
    DecisionResultRead,
    DecisionResultReviewCreate,
    DecisionTaskCreate,
    DecisionTaskRead,
    DecisionTaskUpdate,
)

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


async def _decision_read(session: AsyncSession, decision_id: uuid.UUID) -> DecisionRead:
    decision = await service.get_decision(session, decision_id)
    result = await service.get_decision_result(session, decision_id)
    tasks = await service.list_tasks(session, decision_id)
    lessons = await service.list_lessons(session, decision_id)
    return DecisionRead(
        **DecisionRead.model_validate(decision).model_dump(exclude={"result", "tasks", "lessons"}),
        result=DecisionResultRead.model_validate(result) if result else None,
        tasks=[DecisionTaskRead.model_validate(t) for t in tasks],
        lessons=[DecisionLessonRead.model_validate(item) for item in lessons],
    )


@router.get("", response_model=list[DecisionRead])
async def list_decisions(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[DecisionRead]:
    rows = await service.list_decisions(session, company_id=company_id)
    return [await _decision_read(session, row.id) for row in rows]


@router.post("", response_model=DecisionRead, status_code=201)
async def create_decision(
    payload: DecisionCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive")),
) -> DecisionRead:
    decision = await service.create_decision(session, payload)
    return await _decision_read(session, decision.id)


@router.get("/{decision_id}", response_model=DecisionRead)
async def get_decision(
    decision_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DecisionRead:
    return await _decision_read(session, decision_id)


@router.post("/{decision_id}/result", response_model=DecisionResultRead, status_code=201)
async def record_decision_result(
    decision_id: uuid.UUID,
    payload: DecisionResultCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> DecisionResultRead:
    result = await service.record_result(
        session,
        decision_id,
        actual_result=payload.actual_result,
        checked_at=payload.checked_at,
        comment=payload.comment,
    )
    return DecisionResultRead.model_validate(result)


@router.post("/{decision_id}/review", response_model=DecisionResultRead)
async def review_decision_result(
    decision_id: uuid.UUID,
    payload: DecisionResultReviewCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> DecisionResultRead:
    result = await service.review_result(
        session,
        decision_id,
        review_notes=payload.review_notes,
        lesson_body=payload.lesson_body,
        lesson_category=payload.lesson_category,
    )
    return DecisionResultRead.model_validate(result)


@router.post("/{decision_id}/tasks", response_model=DecisionTaskRead, status_code=201)
async def create_decision_task(
    decision_id: uuid.UUID,
    payload: DecisionTaskCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> DecisionTaskRead:
    task = await service.add_task(
        session,
        decision_id,
        title=payload.title,
        assignee_name=payload.assignee_name,
        due_at=payload.due_at,
    )
    return DecisionTaskRead.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=DecisionTaskRead)
async def update_decision_task(
    task_id: uuid.UUID,
    payload: DecisionTaskUpdate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer", "operator")),
) -> DecisionTaskRead:
    task = await service.update_task_status(session, task_id, payload.status)
    return DecisionTaskRead.model_validate(task)


@router.post("/{decision_id}/lessons", response_model=DecisionLessonRead, status_code=201)
async def create_decision_lesson(
    decision_id: uuid.UUID,
    payload: DecisionLessonCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> DecisionLessonRead:
    lesson = await service.add_lesson(
        session,
        decision_id,
        body=payload.body,
        category=payload.category,
    )
    return DecisionLessonRead.model_validate(lesson)
