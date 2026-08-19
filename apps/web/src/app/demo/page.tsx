"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FieldGrid } from "@/components/ui-bits";
import { runDemo } from "@/lib/api";
import { getAccessToken, getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

export default function DemoPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) setResult(JSON.parse(raw) as Record<string, unknown>);
    setAuthed(Boolean(getAccessToken() && getAuthUser()));
  }, []);

  async function onRun() {
    setLoading(true);
    setError(null);
    try {
      const user = getAuthUser();
      const data = await runDemo(user?.company_id);
      setResult(data);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Демо не удалось выполнить");
    } finally {
      setLoading(false);
    }
  }

  const extras = (result?.extras as Record<string, unknown> | undefined) ?? {};
  const proposal = extras.proposed_change as { title?: string; summary?: string } | undefined;
  const stageProposal = extras.stage_proposed_change as
    | { title?: string; summary?: string }
    | undefined;

  return (
    <main>
      <div className="page-toolbar">
        <div className="page-head">
          <h1>Демо Sales SLA</h1>
          <p>Срок · ответственный · этапы · KPI % · предложение правки документа</p>
        </div>
        <button className="btn btn-primary" onClick={onRun} disabled={loading}>
          {loading ? "Выполняю…" : "+ Запустить полное демо"}
        </button>
      </div>

      {!authed && (
        <p className="muted-note">
          Если включён AUTH_REQUIRED, сначала <Link href="/login">войдите</Link> (bootstrap →
          admin@example.com; пароль — BOOTSTRAP_ADMIN_PASSWORD / локальный demo-admin).
        </p>
      )}

      {error && <p className="error-text">{error}</p>}

      {result && (
        <>
          <section className="metrics-row">
            <article className="metric-card">
              <div className="label">Срок (Δ мин)</div>
              <div className="value">{String(extras.deviation_minutes ?? 32)}</div>
              <div className="meta">severity: {String(extras.severity ?? "high")}</div>
            </article>
            <article className="metric-card">
              <div className="label">Ответственный</div>
              <div className="value" style={{ fontSize: 22 }}>
                {String(extras.responsible_status ?? "—")}
              </div>
              <div className="meta">
                {extras.responsible_mismatch ? "расхождение принято" : "совпало"}
              </div>
            </article>
            <article className="metric-card">
              <div className="label">Этапы</div>
              <div className="value" style={{ fontSize: 22 }}>
                {String(extras.stage_status ?? "—")}
              </div>
              <div className="meta">
                пропуск:{" "}
                {Array.isArray(extras.stages_skipped)
                  ? (extras.stages_skipped as string[]).join(", ") || "нет"
                  : "—"}
              </div>
            </article>
            <article className="metric-card">
              <div className="label">Доля в SLA</div>
              <div className="value">
                {extras.share_kpi_actual != null ? `${extras.share_kpi_actual}%` : "—"}
              </div>
              <div className="meta">цель {String(extras.share_kpi_target ?? 90)}%</div>
            </article>
          </section>

          <section className="panel" style={{ marginBottom: 16 }}>
            <h2>Куда дальше</h2>
            <p>
              Решение: <strong>{String(extras.decision_result_status ?? "—").toUpperCase()}</strong>
            </p>
            <div className="form-actions" style={{ marginTop: 12 }}>
              <Link href="/alignment" className="btn btn-primary">
                Сверка
              </Link>
              <Link href="/executive" className="btn">
                Кабинет
              </Link>
              <Link href="/decisions" className="btn">
                Решения
              </Link>
              <Link href="/kpi" className="btn">
                KPI
              </Link>
              <Link href="/quality" className="btn">
                Качество
              </Link>
              <Link href="/council" className="btn">
                Заседание
              </Link>
              <Link href="/analysis" className="btn">
                Анализ
              </Link>
              <Link href="/documents" className="btn">
                Документы
              </Link>
              <Link href="/knowledge" className="btn">
                Знания
              </Link>
            </div>
          </section>

          {(extras.silent_stage_skip_warned ||
            extras.justified_stage_skip_ok ||
            extras.needs_data_issue_id ||
            extras.rule_versions) && (
            <section className="panel" style={{ marginBottom: 16 }}>
              <h2>Пилот: provenance и DQ</h2>
              <FieldGrid
                items={[
                  {
                    label: "Silent stage skip",
                    value: extras.silent_stage_skip_warned ? (
                      <Link href="/quality">предупреждение → качество</Link>
                    ) : (
                      "нет"
                    ),
                  },
                  {
                    label: "Обоснованный skip",
                    value: extras.justified_stage_skip_ok ? "ok (с причиной)" : "—",
                  },
                  {
                    label: "needs_data",
                    value: extras.needs_data_issue_id
                      ? `${String(extras.needs_data_status || "needs_data")}`
                      : "—",
                  },
                  {
                    label: "Версия документа после apply",
                    value: extras.applied_document_version_id
                      ? String(extras.applied_document_version_id).slice(0, 8) + "…"
                      : "—",
                  },
                  {
                    label: "Связи знаний",
                    value: Array.isArray(extras.knowledge_relation_ids)
                      ? String((extras.knowledge_relation_ids as string[]).length)
                      : "0",
                  },
                ]}
              />
              {extras.rule_versions && typeof extras.rule_versions === "object" ? (
                <p className="muted-note" style={{ marginTop: 10 }}>
                  Правил в анализе:{" "}
                  {Object.keys(extras.rule_versions as Record<string, unknown>).join(", ")}.{" "}
                  <Link href="/analysis">Открыть анализ</Link>
                </p>
              ) : null}
            </section>
          )}

          {(proposal || stageProposal) && (
            <section className="panel" style={{ marginBottom: 16 }}>
              <h2>Предложения изменения документа</h2>
              {proposal && (
                <div className="row" style={{ marginBottom: 10 }}>
                  <strong>{proposal.title}</strong>
                  <span>{proposal.summary}</span>
                </div>
              )}
              {stageProposal && (
                <div className="row">
                  <strong>{stageProposal.title}</strong>
                  <span>{stageProposal.summary}</span>
                </div>
              )}
            </section>
          )}

          <details className="panel">
            <summary style={{ cursor: "pointer" }}>Технические идентификаторы</summary>
            <div className="field-grid" style={{ marginTop: 12 }}>
              {[
                ["company_id", result.company_id],
                ["issue_id", result.issue_id],
                ["decision_id", result.decision_id],
                ["analysis_id", result.analysis_id],
                ["share_kpi_id", extras.share_kpi_id],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <div className="k">{String(label)}</div>
                  <div className="v" style={{ fontSize: 13, wordBreak: "break-all" }}>
                    {String(value ?? "—")}
                  </div>
                </div>
              ))}
            </div>
          </details>
        </>
      )}
    </main>
  );
}
