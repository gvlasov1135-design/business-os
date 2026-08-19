"use client";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import { createAnalysis, createDecision, fetchAnalysis } from "@/lib/api";
import { getAuthUser } from "@/lib/auth";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

const STORAGE_KEY = "business-os-demo";

type Recommendation = {
  id: string;
  title: string;
  body: string;
  priority: string;
  status: string;
};

type Analysis = {
  id: string;
  company_id?: string;
  question: string;
  status: string;
  blocked: boolean;
  trust_index: number;
  block_reasons?: unknown[];
  output?: {
    facts?: unknown[];
    observations?: unknown[];
    hypotheses?: unknown[];
    recommendations?: unknown[];
    missing_data?: unknown[];
    sources?: unknown[];
    critic?: unknown;
    disagreements?: unknown[];
    synthesis?: unknown;
    finance_briefing?: {
      summary?: string;
      units_note?: string;
      meanings?: { metric?: string; value?: string; meaning?: string }[];
      risks?: string[];
      actions?: string[];
    };
    agent_opinions?: Record<string, unknown>;
    rule_versions?: Record<
      string,
      { rule_code?: string; rule_version_id?: string; rule_version_number?: number }
    >;
  };
  recommendations?: Recommendation[];
};

function asLines(items: unknown[] | undefined): string[] {
  if (!items?.length) return [];
  return items.map((item) => {
    if (typeof item === "string") return item;
    if (item && typeof item === "object") {
      const record = item as Record<string, unknown>;
      if (record.text && record.meaning) {
        return `${record.text} — ${record.meaning}`;
      }
      if (record.metric && record.value) {
        return `${record.metric}: ${record.value}${
          record.meaning ? ` — ${record.meaning}` : ""
        }`;
      }
      return String(record.text ?? record.title ?? record.body ?? JSON.stringify(item));
    }
    return String(item);
  });
}

export default function AnalysisPage() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [question, setQuestion] = useState(
    "Что значат ключевые цифры Бистро: выручка, средний чек, чистая прибыль и фудкост?",
  );
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const demo = JSON.parse(raw) as { analysis_id?: string; company_id?: string };
        if (demo.company_id) setCompanyId(demo.company_id);
        if (demo.analysis_id) {
          try {
            setAnalysis((await fetchAnalysis(demo.analysis_id)) as Analysis);
            return;
          } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось загрузить анализ");
            return;
          }
        }
      }
      if (auth?.company_id) setCompanyId(auth.company_id);
      setEmpty(true);
    }
    load();
  }, []);

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    if (!companyId) {
      setError("Нужен ID компании");
      return;
    }
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const created = (await createAnalysis(companyId, question)) as Analysis;
      setAnalysis(created);
      setEmpty(false);
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ...demo, company_id: companyId, analysis_id: created.id }),
      );
      setNote("Анализ создан");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка анализа");
    } finally {
      setBusy(false);
    }
  }

  async function onAccept(recommendation: Recommendation) {
    if (!analysis) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const decision = await createDecision({
        company_id: String(analysis.company_id || companyId),
        analysis_id: analysis.id,
        recommendation_id: recommendation.id,
        status: "accepted",
        rationale: `Принято: ${recommendation.title}`,
        owner_name: getAuthUser()?.full_name || "Руководитель",
        checkpoint_at: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
        expected_result: recommendation.body,
      });
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ...demo, decision_id: decision.id }),
      );
      setNote(`Решение сохранено: ${decision.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить решение");
    } finally {
      setBusy(false);
    }
  }

  const output = analysis?.output;
  const briefing = output?.finance_briefing;
  const facts = asLines(output?.facts);
  const observations = asLines(output?.observations);
  const hypotheses = asLines(output?.hypotheses);
  const missing = asLines(output?.missing_data);

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Анализ</h1>
        <p>
          Независимые агенты (Executive + Sales), затем Critic и синтез. Разногласия сохраняются —
          решение принимает человек.
        </p>
      </div>

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Задать вопрос</h2>
        <form onSubmit={onAsk} className="stack-form">
          <label>
            ID компании
            <input value={companyId} onChange={(e) => setCompanyId(e.target.value)} required />
          </label>
          <label>
            Вопрос
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={3} required />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Выполняю…" : "Запустить анализ"}
          </button>
        </form>
      </section>

      {error && <p className="error-text">{error}</p>}
      {note && <p className="ok-text">{note}</p>}
      {empty && !analysis && <EmptyDemoHint />}

      {analysis && (
        <>
          <section className="panel" style={{ marginBottom: 16 }}>
            <h2>Вопрос</h2>
            <p style={{ color: "#1e1f21", marginBottom: 12 }}>{analysis.question}</p>
            <FieldGrid
              items={[
                { label: "Статус", value: <StatusPill value={analysis.status} /> },
                { label: "Заблокирован", value: analysis.blocked ? "да" : "нет" },
                { label: "Trust", value: String(analysis.trust_index) },
                {
                  label: "Причины блокировки",
                  value: analysis.block_reasons?.length
                    ? JSON.stringify(analysis.block_reasons)
                    : "—",
                },
              ]}
            />
            <div className="form-actions" style={{ marginTop: 12 }}>
              <Link
                href="/council"
                className="btn btn-primary"
                onClick={() => {
                  const raw = window.localStorage.getItem(STORAGE_KEY);
                  const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
                  window.localStorage.setItem(
                    STORAGE_KEY,
                    JSON.stringify({
                      ...demo,
                      company_id: analysis.company_id || companyId,
                      analysis_id: analysis.id,
                    }),
                  );
                }}
              >
                Продолжить за столом
              </Link>
            </div>
          </section>

          {briefing && (
            <section className="panel" style={{ marginBottom: 16 }}>
              <h2>Что значат цифры</h2>
              <p style={{ marginTop: 8, marginBottom: 12, fontSize: 17, lineHeight: 1.45 }}>
                {briefing.summary}
              </p>
              {briefing.units_note && (
                <p className="muted-note" style={{ marginBottom: 12 }}>
                  {briefing.units_note}
                </p>
              )}
              <div className="list-stack">
                {(briefing.meanings || []).map((item) => (
                  <div className="row" key={`${item.metric}-${item.value}`}>
                    <strong>
                      {item.metric}: {item.value}
                    </strong>
                    <span>{item.meaning}</span>
                  </div>
                ))}
              </div>
              {(briefing.risks || []).length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <h2>Риски</h2>
                  <div className="list-stack" style={{ marginTop: 8 }}>
                    {(briefing.risks || []).map((risk) => (
                      <div className="row" key={risk}>
                        <span>{risk}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(briefing.actions || []).length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <h2>Что сделать</h2>
                  <div className="list-stack" style={{ marginTop: 8 }}>
                    {(briefing.actions || []).map((action) => (
                      <div className="row" key={action}>
                        <span>{action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {analysis.output?.rule_versions && (
            <details className="panel" style={{ marginBottom: 16 }}>
              <summary style={{ cursor: "pointer" }}>Технические версии правил</summary>
              <div className="list-stack" style={{ marginTop: 10 }}>
                {Object.entries(analysis.output.rule_versions).map(([key, ver]) => (
                  <div className="row" key={key}>
                    <strong>{key}</strong>
                    <span>
                      {String(ver.rule_code ?? "—")} · v{String(ver.rule_version_number ?? "—")}
                    </span>
                  </div>
                ))}
              </div>
            </details>
          )}

          {!briefing && (
          <section className="charts-row">
            <article className="panel">
              <h2>Факты</h2>
              <div className="list-stack">
                {facts.length ? (
                  facts.map((line) => (
                    <div className="row" key={line}>
                      <span>{line}</span>
                    </div>
                  ))
                ) : (
                  <p>Фактов в ответе нет</p>
                )}
              </div>
            </article>
            <article className="panel">
              <h2>Наблюдения</h2>
              <div className="list-stack">
                {observations.length ? (
                  observations.map((line) => (
                    <div className="row" key={line}>
                      <span>{line}</span>
                    </div>
                  ))
                ) : (
                  <p>Наблюдений нет</p>
                )}
              </div>
            </article>
          </section>
          )}

          {briefing && hypotheses.length > 0 && (
            <section className="panel" style={{ marginBottom: 16 }}>
              <h2>Как читать дальше</h2>
              <div className="list-stack" style={{ marginTop: 10 }}>
                {hypotheses.map((line) => (
                  <div className="row" key={line}>
                    <span>{line}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {!briefing && (
          <section className="charts-row" style={{ marginTop: 16 }}>
            <article className="panel">
              <h2>Гипотезы</h2>
              <div className="list-stack">
                {hypotheses.length ? (
                  hypotheses.map((line) => (
                    <div className="row" key={line}>
                      <span>{line}</span>
                    </div>
                  ))
                ) : (
                  <p>Гипотез нет</p>
                )}
              </div>
            </article>
            <article className="panel">
              <h2>Недостающие данные</h2>
              <div className="list-stack">
                {missing.length ? (
                  missing.map((line) => (
                    <div className="row" key={line}>
                      <span>{line}</span>
                    </div>
                  ))
                ) : (
                  <p>Пробелов не отмечено</p>
                )}
              </div>
            </article>
          </section>
          )}

          <details className="panel" style={{ marginTop: 16 }}>
            <summary style={{ cursor: "pointer" }}>Мнения агентов (подробно)</summary>
            {analysis.output?.agent_opinions ? (
              <div className="list-stack" style={{ marginTop: 10 }}>
                {Object.entries(analysis.output.agent_opinions).map(([name, opinion]) => {
                  const op = opinion as {
                    decision_dna?: Record<string, unknown>;
                    recommendations?: unknown[];
                    trust_index?: number;
                  };
                  const recs = asLines(op.recommendations);
                  return (
                    <div className="row" key={name}>
                      <strong>{name}</strong>
                      <FieldGrid
                        items={[
                          {
                            label: "Decision DNA",
                            value: op.decision_dna
                              ? `${op.decision_dna.bias} · risk ${op.decision_dna.risk_tolerance}`
                              : "—",
                          },
                          { label: "Trust", value: String(op.trust_index ?? "—") },
                          {
                            label: "Рекомендации",
                            value: recs.length ? recs.join(" · ") : "—",
                          },
                        ]}
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              <p>Мнения агентов отсутствуют</p>
            )}
          </details>

          <section className="panel" style={{ marginTop: 16 }}>
            <h2>Рекомендации</h2>
            <div className="list-stack" style={{ marginTop: 10 }}>
              {(analysis.recommendations ?? []).map((item) => (
                <div className="row" key={item.id}>
                  <strong>
                    {item.title} · {item.priority}
                  </strong>
                  <span>{item.body}</span>
                  {!analysis.blocked && (
                    <button
                      className="btn btn-primary"
                      type="button"
                      style={{ marginTop: 8 }}
                      disabled={busy}
                      onClick={() => onAccept(item)}
                    >
                      Принять как решение
                    </button>
                  )}
                </div>
              ))}
              {!analysis.recommendations?.length && <p>Рекомендаций нет</p>}
            </div>
            {missing.length > 0 && (
              <p style={{ marginTop: 12 }}>Недостающие данные: {missing.join("; ")}</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
