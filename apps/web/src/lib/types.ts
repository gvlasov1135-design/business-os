export type ComponentStatus = "ok" | "degraded" | "down";

export type AggregateStatus = "ready" | "partial" | "error";

export type UiState = "loading" | "ready" | "partial" | "error";

export interface ComponentHealth {
  status: ComponentStatus;
  latency_ms?: number | null;
  error?: string | null;
}

export interface ReadinessResponse {
  status: AggregateStatus;
  components: {
    api: ComponentHealth;
    postgres: ComponentHealth;
    redis: ComponentHealth;
    minio: ComponentHealth;
  };
  checked_at: string;
}

export interface HealthResponse {
  status: "ok";
}
