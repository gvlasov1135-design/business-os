import type { ComponentHealth, UiState } from "@/lib/types";

interface SystemStatusProps {
  uiState: UiState;
  apiReachable: boolean;
  components?: {
    api: ComponentHealth;
    postgres: ComponentHealth;
    redis: ComponentHealth;
    minio: ComponentHealth;
  };
  errorMessage?: string;
}

const LABELS: Record<string, string> = {
  api: "API",
  postgres: "PostgreSQL",
  redis: "Redis",
  minio: "MinIO",
};

function statusColor(status: string): string {
  if (status === "ok") return "#16a34a";
  if (status === "degraded") return "#ca8a04";
  return "#dc2626";
}

export function SystemStatus({
  uiState,
  apiReachable,
  components,
  errorMessage,
}: SystemStatusProps) {
  const bannerColor =
    uiState === "ready"
      ? "#16a34a"
      : uiState === "partial"
        ? "#ca8a04"
        : uiState === "loading"
          ? "#64748b"
          : "#dc2626";

  return (
    <div>
      <div
        style={{
          background: bannerColor,
          color: "#fff",
          padding: "12px 16px",
          borderRadius: 8,
          marginBottom: 24,
          fontWeight: 600,
        }}
      >
        Состояние системы: {
          uiState === "ready"
            ? "ГОТОВО"
            : uiState === "partial"
              ? "ЧАСТИЧНО"
              : uiState === "loading"
                ? "ЗАГРУЗКА"
                : "ОШИБКА"
        }

      </div>

      {errorMessage && (
        <p style={{ color: "#dc2626", marginBottom: 16 }}>{errorMessage}</p>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
        }}
      >
        <ComponentCard
          label="API"
          status={apiReachable ? "ok" : "down"}
          error={apiReachable ? undefined : "API недоступен"}
        />

        {components &&
          (["postgres", "redis", "minio"] as const).map((key) => (
            <ComponentCard
              key={key}
              label={LABELS[key]}
              status={components[key].status}
              latencyMs={components[key].latency_ms}
              error={components[key].error}
            />
          ))}

        {uiState === "loading" && !components && (
          <>
            <ComponentCard label="PostgreSQL" status="degraded" />
            <ComponentCard label="Redis" status="degraded" />
            <ComponentCard label="MinIO" status="degraded" />
          </>
        )}
      </div>
    </div>
  );
}

function ComponentCard({
  label,
  status,
  latencyMs,
  error,
}: {
  label: string;
  status: string;
  latencyMs?: number | null;
  error?: string | null;
}) {
  return (
    <div
      style={{
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: 16,
        background: "#fff",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{label}</div>
      <div style={{ color: statusColor(status), fontWeight: 600 }}>{status}</div>
      {latencyMs != null && (
        <div style={{ fontSize: 14, color: "#64748b", marginTop: 4 }}>
          {latencyMs} ms
        </div>
      )}
      {error && (
        <div style={{ fontSize: 13, color: "#dc2626", marginTop: 8 }}>{error}</div>
      )}
    </div>
  );
}
