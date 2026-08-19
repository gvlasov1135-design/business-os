"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { BarChart, DonutChart, DotChart } from "@/components/charts";
import { fetchHealth, fetchReadiness } from "@/lib/api";
import type { ReadinessResponse, UiState } from "@/lib/types";

const STORAGE_KEY = "business-os-demo";

const STATE_LABEL: Record<UiState, string> = {
  loading: "загрузка",
  ready: "готово",
  partial: "частично",
  error: "ошибка",
};

export default function HomePage() {
  const [uiState, setUiState] = useState<UiState>("loading");
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [demo, setDemo] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) setDemo(JSON.parse(raw) as Record<string, unknown>);

    let active = true;
    async function load() {
      try {
        await fetchHealth();
        const data = await fetchReadiness();
        if (!active) return;
        setReadiness(data);
        if (data.status === "ready") setUiState("ready");
        else if (data.status === "partial") setUiState("partial");
        else setUiState("error");
      } catch {
        if (!active) return;
        setUiState("error");
      }
    }
    load();
    const interval = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const extras = (demo?.extras as Record<string, unknown> | undefined) ?? {};
  const deviation = Number(extras.deviation_minutes ?? 0);
  const componentsOk = useMemo(() => {
    if (!readiness) return 0;
    return Object.values(readiness.components).filter((item) => item.status === "ok").length;
  }, [readiness]);

  return (
    <main>
      <div className="page-toolbar">
        <Link href="/council" className="btn btn-primary">
          Заседание агентов
        </Link>
        <Link href="/executive" className="btn">
          Кабинет
        </Link>
        <Link href="/demo" className="btn">
          Демо-срез
        </Link>
      </div>

      <section className="metrics-row">
        <article className="metric-card">
          <div className="label">Подтверждённые утверждения</div>
          <div className="value">{demo ? Number(extras.statement_count ?? 1) : 0}</div>
          <div className="meta">⌕ {demo ? "1 фильтр" : "Без фильтров"}</div>
        </article>
        <article className="metric-card">
          <div className="label">Проблемы сверки</div>
          <div className="value">
            {demo
              ? Number(Boolean(extras.deviation_minutes)) +
                Number(Boolean(extras.responsible_issue_id)) +
                Number(Boolean(extras.stage_issue_id))
              : 0}
          </div>
          <div className="meta">
            срок / роль / этапы
            {extras.stages_skipped
              ? ` · пропуск: ${(extras.stages_skipped as string[]).join(", ")}`
              : ""}
          </div>
        </article>
        <article className="metric-card">
          <div className="label">Доля в SLA</div>
          <div className="value">
            {extras.share_kpi_actual != null ? `${extras.share_kpi_actual}%` : "—"}
          </div>
          <div className="meta">цель {String(extras.share_kpi_target ?? "90")}%</div>
        </article>
        <article className="metric-card">
          <div className="label">Здоровые сервисы</div>
          <div className="value">{componentsOk}</div>
          <div className="meta">⌕ Готовность системы</div>
        </article>
      </section>

      <section className="charts-row">
        <article className="chart-card">
          <h2>Отклонение SLA по лиду (минуты)</h2>
          <div className="chart-body single">
            <BarChart label="L-1001" value={deviation || 0} max={40} color="#f06a6a" />
          </div>
          <div className="chart-footer">1 фильтр · CRM против регламента</div>
        </article>
        <article className="chart-card">
          <h2>Статус пайплайна среза</h2>
          <div className="chart-body">
            <DonutChart
              center={String(demo ? 4 : 1)}
              segments={
                demo
                  ? [
                      { value: 1, color: "#4573d2" },
                      { value: 1, color: "#9db7ea" },
                      { value: 1, color: "#c9d7f2" },
                      { value: 1, color: "#e6eefc" },
                    ]
                  : [{ value: 1, color: "#cfcfcf" }]
              }
            />
            <div className="legend">
              <div className="legend-item">
                <span className="swatch" style={{ background: "#4573d2" }} />
                Документы
              </div>
              <div className="legend-item">
                <span className="swatch" style={{ background: "#9db7ea" }} />
                Факты
              </div>
              <div className="legend-item">
                <span className="swatch" style={{ background: "#c9d7f2" }} />
                Знания
              </div>
              <div className="legend-item">
                <span className="swatch" style={{ background: "#e6eefc" }} />
                Решения
              </div>
            </div>
          </div>
          <div className="chart-footer">1 фильтр · Модули вертикального среза</div>
        </article>
      </section>

      <section className="charts-row">
        <article className="chart-card">
          <h2>Открытые решения на неделе</h2>
          <div className="chart-body single">
            <DotChart value={demo ? 1 : 0} color="#a871e3" />
          </div>
        </article>
        <article className="chart-card">
          <h2>Готовность системы</h2>
          <div className="chart-body">
            <DonutChart
              center={String(componentsOk || 0)}
              segments={[
                { value: Math.max(componentsOk, 1), color: uiState === "ready" ? "#5da283" : "#cfcfcf" },
              ]}
            />
            <div className="legend">
              <div className="legend-item">
                <span className="swatch" style={{ background: "#5da283" }} />
                {STATE_LABEL[uiState]}
              </div>
              <div className="legend-item">
                <span className="swatch" style={{ background: "#cfcfcf" }} />
                Ожидание / недоступно
              </div>
            </div>
          </div>
          <div className="chart-footer">
            API {readiness?.components.api.status ?? "—"} · Postgres{" "}
            {readiness?.components.postgres.status ?? "—"} · Redis{" "}
            {readiness?.components.redis.status ?? "—"} · MinIO{" "}
            {readiness?.components.minio.status ?? "—"}
          </div>
        </article>
      </section>
    </main>
  );
}
