from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponentStatus = Literal["ok", "degraded", "down"]
AggregateStatus = Literal["ready", "partial", "error"]


class ComponentHealth(BaseModel):
    status: ComponentStatus
    latency_ms: int | None = None
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: AggregateStatus
    components: dict[str, ComponentHealth]
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
