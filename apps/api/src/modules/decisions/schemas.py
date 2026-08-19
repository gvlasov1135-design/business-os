import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from modules.decisions.models import (
    DecisionResultStatus,
    DecisionStatus,
    DecisionTaskStatus,
)


class DecisionCreate(BaseModel):
    company_id: uuid.UUID
    analysis_id: uuid.UUID | None = None
    recommendation_id: uuid.UUID | None = None
    status: DecisionStatus
    selected_option: str | None = None
    rationale: str = Field(min_length=1)
    owner_name: str = Field(min_length=1, max_length=255)
    checkpoint_at: datetime | None = None
    expected_result: str = Field(min_length=1)
    create_followup_task: bool = True


class DecisionResultCreate(BaseModel):
    actual_result: str = Field(min_length=1)
    checked_at: datetime
    comment: str | None = None


class DecisionResultReviewCreate(BaseModel):
    review_notes: str = Field(min_length=1)
    lesson_body: str | None = None
    lesson_category: str = "outcome"


class DecisionTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    assignee_name: str = Field(min_length=1, max_length=255)
    due_at: datetime | None = None


class DecisionTaskUpdate(BaseModel):
    status: DecisionTaskStatus


class DecisionLessonCreate(BaseModel):
    body: str = Field(min_length=1)
    category: str = "general"


class DecisionResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    actual_result: str
    checked_at: datetime
    comment: str | None
    deviation_note: str | None
    status: DecisionResultStatus
    review_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class DecisionTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    company_id: uuid.UUID
    title: str
    assignee_name: str
    due_at: datetime | None
    status: DecisionTaskStatus
    created_at: datetime


class DecisionLessonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    company_id: uuid.UUID
    body: str
    category: str
    created_at: datetime


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    analysis_id: uuid.UUID | None
    recommendation_id: uuid.UUID | None
    status: DecisionStatus
    selected_option: str | None = None
    rationale: str
    owner_name: str
    checkpoint_at: datetime | None
    expected_result: str
    created_at: datetime
    result: DecisionResultRead | None = None
    tasks: list[DecisionTaskRead] = Field(default_factory=list)
    lessons: list[DecisionLessonRead] = Field(default_factory=list)
