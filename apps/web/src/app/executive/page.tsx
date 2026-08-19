"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import {
  createAnalysis,
  createDecision,
  fetchAnalysis,
  fetchExecutiveReadiness,
  fetchOutboxEvents,
  publishOutboxEvent,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Readiness = {
  analysis_ready: boolean;
  gate_reasons: string[];
  completeness: { score: number; label: string; detail: string; status: string };
  trust_index: { score: number; label: string; detail: string; status: string };
  alignment_score: { score: number; label: string; detail: string; status: string };
  document_health: { score: number; label: string; detail: string; status: string };
  kpi_health: { score: number; label: string; detail: string; status: string };
  counts: Record<string, number>;
  limitations: string[];
  evidence_preview: Record<string, unknown>[];
  latest_analysis_id?: string | null;
  latest_decision_id?: string | null;
  sla_axes?: Record<string, number>;
};

type Recommendation = {
  id: string;
  title: string;
  body: string;
  priority: string;
};

type Analysis = {
  id: string;
  company_id?: string;
  question: string;
  status: string;
  blocked: boolean;
  trust_index: number;
  output?: {
    agent_opinions?: Record<string, unknown>;
    disagreements?: unknown[];
    critic?: unknown;
    missing_data?: unknown[];
  };
  recommendations?: Recommendation[];
};

export default function ExecutivePage() {
  const [companyId, setCompanyId] = useState("");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [outbox, setOutbox] = useState<Record<string, unknown>[]>([]);
  const [question, setQuestion] = useState(
    "Есть ли подтвержденное нарушение Sales SLA по L-1001 (срок, ответственный, этапы) и что править в регламенте?",
  );
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async (cid: string) => {
    const ready = (await fetchExecutiveReadiness(cid)) as Readiness;
    setReadiness(ready);
    if (ready.latest_analysis_id) {
      setAnalysis((await fetchAnalysis(ready.latest_analysis_id)) as Analysis);
    }
    try {
      setOutbox(await fetchOutboxEvents(cid, "pending"));
    } catch {
      setOutbox([]);
    }
  }, []);

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as { company_id?: string; analysis_id?: string }) : {};
      const id = demo.company_id || auth?.company_id || "";
      setCompanyId(id);
      if (!id) return;
      try {
        await reload(id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить кабинет");
      }
    }
    load();
  }, [reload]);

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    if (!companyId) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const created = (await createAnalysis(companyId, question)) as Analysis;
      setAnalysis(created);
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ...demo, company_id: companyId, analysis_id: created.id }),
      );
      await reload(companyId);
      setNote(created.blocked ? "Анализ заблокирован ограничениями данных" : "Анализ готов");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка анализа");
    } finally {
      setBusy(false);
    }
  }

  async function onDecide(rec: Recommendation, status: "accepted" | "rejected") {
    if (!analysis || !companyId) return;
    setBusy(true);
    setError(null);
    try {
      const decision = await createDecision({
        company_id: companyId,
        analysis_id: analysis.id,
        recommendation_id: rec.id,
        status,
        rationale: `${status === "accepted" ? "Принято" : "Отклонено"}: ${rec.title}`,
        owner_name: getAuthUser()?.full_name || "Руководитель",
        checkpoint_at: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
        expected_result: rec.body,
      });
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ...demo, decision_id: decision.id }),
      );
      await reload(companyId);
      setNote(
        status === "accepted"
          ? `Решение принято — откройте «Решения»`
          : `Решение отклонено`,
      );    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить решение");
    } finally {
      setBusy(false);
    }
  }

  async function onPublish(id: string) {
    setBusy(true);
    try {
      await publishOutboxEvent(id);
      if (companyId) await reload(companyId);
      setNote("Событие outbox опубликовано");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка outbox");
    } finally {
      setBusy(false);
    }
  }

  const metrics = readiness
    ? [
        readiness.completeness,
        readiness.trust_index,
        readiness.alignment_score,
        readiness.document_health,
        readiness.kpi_health,
      ]
    : [];

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Кабинет руководителя</h1>
        <p>
          Готовность, качество данных, доказательства и решение по рекомендации — без обхода gate.
        </p>
        <p style={{ marginTop: 8 }}>
          <Link href="/reports">Загрузить свою отчётность → получить выводы</Link>
        </p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}
      {note && <p className="ok-text">{note}</p>}

      {readiness && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Готовность</h2>
          <FieldGrid
            items={[
              {
                label: "Анализ разрешён",
                value: readiness.analysis_ready ? "да" : "нет",
              },
              {
                label: "Статус gate",
                value: (
                  <StatusPill value={readiness.analysis_ready ? "ready" : "blocked"} />
                ),
              },
            ]}
          />
          <div className="metrics-row" style={{ marginTop: 12 }}>
            {metrics.map((m) => (
              <article className="metric-card" key={m.label}>
                <div className="label">{m.label}</div>
                <div className="value">{Math.round(m.score * 100)}%</div>
                <div className="meta">
                  <StatusPill value={m.status} /> · {m.detail}
                </div>
              </article>
            ))}
          </div>
          {readiness.limitations.length > 0 && (
            <p style={{ marginTop: 12 }}>
              Ограничения: {readiness.limitations.join("; ")}
            </p>
          )}
        </section>
      )}

      {readiness && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Sales SLA — оси</h2>
          <FieldGrid
            items={[
              {
                label: "Срок",
                value: String(readiness.sla_axes?.deadline ?? readiness.counts?.sla_deadline ?? 0),
              },
              {
                label: "Ответственный",
                value: String(
                  readiness.sla_axes?.responsible ?? readiness.counts?.sla_responsible ?? 0,
                ),
              },
              {
                label: "Этапы",
                value: String(readiness.sla_axes?.stages ?? readiness.counts?.sla_stages ?? 0),
              },
              {
                label: "Предложения правок",
                value: String(
                  readiness.sla_axes?.proposed_changes ??
                    readiness.counts?.proposed_doc_changes ??
                    0,
                ),
              },
              {
                label: "needs_data",
                value: String(
                  readiness.sla_axes?.needs_data ?? readiness.counts?.needs_data ?? 0,
                ),
              },
            ]}
          />
        </section>
      )}

      {readiness && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Доказательства</h2>
          {readiness.evidence_preview.length === 0 ? (
            <p>Пока нет — запустите демо</p>
          ) : (
            <div className="list-stack" style={{ marginTop: 10 }}>
              {readiness.evidence_preview.map((item) => (
                <div className="row" key={`${String(item.type)}-${String(item.id)}`}>
                  <strong>
                    {item.type === "sla_axis"
                      ? `SLA · ${String(item.axis)} · ${String(item.status)}`
                      : String(item.type)}
                  </strong>
                  <span>
                    {item.type === "knowledge"
                      ? String(item.title)
                      : item.type === "sla_axis"
                        ? `${String(item.summary || "")}${
                            item.proposed_change_title
                              ? ` · правка: ${String(item.proposed_change_title)}`
                              : ""
                          }`
                        : JSON.stringify(item)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Вопрос</h2>
        <form onSubmit={onAsk} className="stack-form">
          <label>
            ID компании
            <input value={companyId} onChange={(e) => setCompanyId(e.target.value)} required />
          </label>
          <label>
            Вопрос руководителю AI
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={3} required />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !companyId}>
            {busy ? "Выполняю…" : "Запустить анализ"}
          </button>
        </form>
      </section>

      {analysis && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Анализ и рекомендации</h2>
          <FieldGrid
            items={[
              { label: "Статус", value: <StatusPill value={analysis.status} /> },
              { label: "Trust", value: String(analysis.trust_index) },
              {
                label: "Разногласия агентов",
                value: String(
                  Array.isArray(analysis.output?.disagreements)
                    ? analysis.output?.disagreements.length
                    : 0,
                ),
              },
            ]}
          />
          <p style={{ marginTop: 10 }}>{analysis.question}</p>
          <div className="list-stack" style={{ marginTop: 12 }}>
            {(analysis.recommendations ?? []).slice(0, 4).map((rec) => (
              <div className="row" key={rec.id}>
                <strong>
                  {rec.title} · {rec.priority}
                </strong>
                <span>{rec.body}</span>
                {!analysis.blocked && (
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <button
                      className="btn btn-primary"
                      type="button"
                      disabled={busy}
                      onClick={() => onDecide(rec, "accepted")}
                    >
                      Принять
                    </button>
                    <button
                      className="btn"
                      type="button"
                      disabled={busy}
                      onClick={() => onDecide(rec, "rejected")}
                    >
                      Отклонить
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
          <p style={{ marginTop: 12 }}>
            <a href="/decisions" className="btn">
              Открыть решения
            </a>
          </p>
        </section>
      )}

      <section className="panel">
        <h2>Очередь событий (outbox)</h2>
        {outbox.length === 0 ? (
          <p>Нет ожидающих событий</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {outbox.map((ev) => (
              <div className="row" key={String(ev.id)}>
                <strong>
                  {String(ev.event_type)} · {String(ev.aggregate_type)}
                </strong>
                <button
                  className="btn"
                  type="button"
                  style={{ marginTop: 8 }}
                  disabled={busy}
                  onClick={() => onPublish(String(ev.id))}
                >
                  Опубликовать
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
