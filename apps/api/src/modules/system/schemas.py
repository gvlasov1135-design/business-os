from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponentStatus = Literal["ok", "degraded", "down"]
AggregateStatus = Literal["ready", "partial", "error"]


class ComponentHealth(BaseModel):
    status: ComponentStatus
    latency_ms: int | None = None
    error: str | None = None


class PilotFlags(BaseModel):
    auth_required: bool
    docs_enabled: bool
    bootstrap_enabled: bool
    pilot_mode: bool
    secrets_insecure: bool
    rate_limit_per_minute: int


class ReadinessResponse(BaseModel):
    status: AggregateStatus
    components: dict[str, ComponentHealth]
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    pilot: PilotFlags | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
