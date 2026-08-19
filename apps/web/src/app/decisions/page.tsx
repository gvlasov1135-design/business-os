"use client";

import { FormEvent, useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import {
  fetchDecision,
  recordDecisionResult,
  reviewDecisionResult,
  updateDecisionTask,
} from "@/lib/api";

const STORAGE_KEY = "business-os-demo";

type Decision = {
  id: string;
  status: string;
  selected_option?: string | null;
  rationale: string;
  owner_name: string;
  checkpoint_at?: string | null;
  expected_result: string;
  result?: {
    actual_result: string;
    checked_at: string;
    comment?: string | null;
    deviation_note?: string | null;
    status: string;
    review_notes?: string | null;
    reviewed_at?: string | null;
  } | null;
  tasks?: Array<{
    id: string;
    title: string;
    assignee_name: string;
    status: string;
    due_at?: string | null;
  }>;
  lessons?: Array<{ id: string; body: string; category: string }>;
};

export default function DecisionsPage() {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);
  const [actualResult, setActualResult] = useState("");
  const [comment, setComment] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [lessonBody, setLessonBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  async function reload(decisionId: string) {
    const data = (await fetchDecision(decisionId)) as Decision;
    setDecision(data);
    setActualResult(data.expected_result);
    setEmpty(false);
  }

  useEffect(() => {
    async function load() {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setEmpty(true);
        return;
      }
      const demo = JSON.parse(raw) as { decision_id?: string };
      if (!demo.decision_id) {
        setEmpty(true);
        return;
      }
      try {
        await reload(demo.decision_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить решение");
      }
    }
    load();
  }, []);

  async function onRecordResult(event: FormEvent) {
    event.preventDefault();
    if (!decision) return;
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      await recordDecisionResult(decision.id, {
        actual_result: actualResult,
        checked_at: new Date().toISOString(),
        comment: comment || undefined,
      });
      await reload(decision.id);
      setNote("Результат зафиксирован — видна разница с ожиданием");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось зафиксировать результат");
    } finally {
      setSaving(false);
    }
  }

  async function onReview(event: FormEvent) {
    event.preventDefault();
    if (!decision) return;
    setSaving(true);
    setError(null);
    try {
      await reviewDecisionResult(decision.id, {
        review_notes: reviewNotes,
        lesson_body: lessonBody || undefined,
        lesson_category: "outcome",
      });
      await reload(decision.id);
      setNote("Review и урок сохранены в Память решений");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить review");
    } finally {
      setSaving(false);
    }
  }

  async function onDoneTask(taskId: string) {
    if (!decision) return;
    setSaving(true);
    try {
      await updateDecisionTask(taskId, "done");
      await reload(decision.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка задачи");
    } finally {
      setSaving(false);
    }
  }

  if (empty) {
    return (
      <main>
        <div className="page-head" style={{ marginBottom: 16 }}>
          <h1>Память решений</h1>
          <p>Решение, задачи, контроль результата и уроки.</p>
        </div>
        <EmptyDemoHint />
      </main>
    );
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Память решений</h1>
        <p>Выбранная опция, ответственный, checkpoint, факт vs прогноз, review и lessons.</p>
      </div>
      {error && <p className="error-text">{error}</p>}
      {note && <p className="ok-text">{note}</p>}

      {decision && (
        <>
          <section className="panel" style={{ marginBottom: 16 }}>
            <h2>Решение</h2>
            <p style={{ color: "#1e1f21", marginBottom: 12 }}>{decision.rationale}</p>
            <FieldGrid
              items={[
                { label: "Статус", value: <StatusPill value={decision.status} /> },
                { label: "Выбранная опция", value: decision.selected_option || "—" },
                { label: "Владелец", value: decision.owner_name },
                {
                  label: "Контрольная дата",
                  value: decision.checkpoint_at
                    ? new Date(decision.checkpoint_at).toLocaleString("ru-RU")
                    : "—",
                },
                { label: "ID", value: decision.id },
              ]}
            />
          </section>

          <section className="panel" style={{ marginBottom: 16 }}>
            <h2>Задачи</h2>
            {(decision.tasks ?? []).length === 0 ? (
              <p>Задач нет</p>
            ) : (
              <div className="list-stack" style={{ marginTop: 10 }}>
                {(decision.tasks ?? []).map((task) => (
                  <div className="row" key={task.id}>
                    <strong>{task.title}</strong>
                    <FieldGrid
                      items={[
                        { label: "Исполнитель", value: task.assignee_name },
                        { label: "Статус", value: <StatusPill value={task.status} /> },
                        {
                          label: "Срок",
                          value: task.due_at
                            ? new Date(task.due_at).toLocaleString("ru-RU")
                            : "—",
                        },
                      ]}
                    />
                    {task.status === "open" && (
                      <button
                        className="btn"
                        type="button"
                        style={{ marginTop: 8 }}
                        disabled={saving}
                        onClick={() => onDoneTask(task.id)}
                      >
                        Отметить выполненной
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="charts-row">
            <article className="panel">
              <h2>Ожидаемый результат</h2>
              <p style={{ color: "#1e1f21" }}>{decision.expected_result}</p>
            </article>
            <article className="panel">
              <h2>Фактический результат</h2>
              {decision.result ? (
                <>
                  <p style={{ color: "#1e1f21", marginBottom: 12 }}>
                    {decision.result.actual_result}
                  </p>
                  <FieldGrid
                    items={[
                      {
                        label: "Статус сравнения",
                        value: <StatusPill value={decision.result.status} />,
                      },
                      {
                        label: "Проверено",
                        value: new Date(decision.result.checked_at).toLocaleString("ru-RU"),
                      },
                      {
                        label: "Отклонение",
                        value: decision.result.deviation_note || "нет (совпало)",
                      },
                      {
                        label: "Разбор",
                        value: decision.result.review_notes || "ещё не сделан",
                      },
                    ]}
                  />
                </>
              ) : (
                <form onSubmit={onRecordResult} className="stack-form">
                  <label>
                    Фактический результат
                    <textarea
                      value={actualResult}
                      onChange={(e) => setActualResult(e.target.value)}
                      rows={3}
                      required
                    />
                  </label>
                  <label>
                    Комментарий
                    <input value={comment} onChange={(e) => setComment(e.target.value)} />
                  </label>
                  <button className="btn btn-primary" type="submit" disabled={saving}>
                    {saving ? "Сохраняю…" : "Зафиксировать результат"}
                  </button>
                </form>
              )}
            </article>
          </section>

          {decision.result && !decision.result.reviewed_at && (
            <section className="panel" style={{ marginTop: 16 }}>
              <h2>Разбор результата</h2>
              <form onSubmit={onReview} className="stack-form">
                <label>
                  Итог review
                  <textarea
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    rows={3}
                    required
                  />
                </label>
                <label>
                  Урок (lesson)
                  <textarea
                    value={lessonBody}
                    onChange={(e) => setLessonBody(e.target.value)}
                    rows={2}
                    placeholder="Что сохранить в память организации"
                  />
                </label>
                <button className="btn btn-primary" type="submit" disabled={saving}>
                  Сохранить review
                </button>
              </form>
            </section>
          )}

          {(decision.lessons ?? []).length > 0 && (
            <section className="panel" style={{ marginTop: 16 }}>
              <h2>Уроки</h2>
              <div className="list-stack" style={{ marginTop: 10 }}>
                {(decision.lessons ?? []).map((lesson) => (
                  <div className="row" key={lesson.id}>
                    <strong>{lesson.category}</strong>
                    <span>{lesson.body}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </main>
  );
}
