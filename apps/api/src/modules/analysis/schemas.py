import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.analysis.models import AIAnalysisStatus, RecommendationStatus


class AnalysisCreate(BaseModel):
    company_id: uuid.UUID
    question: str = Field(min_length=1)


class AnalysisOutput(BaseModel):
    facts: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    hypotheses: list[Any] = Field(default_factory=list)
    recommendations: list[Any] = Field(default_factory=list)
    missing_data: list[Any] = Field(default_factory=list)
    sources: list[Any] = Field(default_factory=list)
    trust_index: float = 0
    blocked: bool = False


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    title: str
    body: str
    priority: str
    status: RecommendationStatus
    created_at: datetime


class AIAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    question: str
    status: AIAnalysisStatus
    blocked: bool
    block_reasons: list[Any]
    context_snapshot: dict[str, Any]
    output: dict[str, Any] | None
    trust_index: float
    created_at: datetime
    recommendations: list[RecommendationRead] = Field(default_factory=list)
