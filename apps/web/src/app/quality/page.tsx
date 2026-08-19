"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import {
  explainQualityIssue,
  fetchQualityGate,
  fetchQualityIssues,
  resolveQualityIssue,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Issue = {
  id: string;
  code: string;
  message: string;
  severity: string;
  status: string;
  blocks_analysis: boolean;
};

export default function QualityPage() {
  const [companyId, setCompanyId] = useState("");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [gate, setGate] = useState<{ blocked: boolean; reasons: string[] } | null>(null);
  const [explanation, setExplanation] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resolveReason, setResolveReason] = useState(
    "Повторное обращение — квалификация уже в карточке",
  );

  async function reload(id: string) {
    setIssues((await fetchQualityIssues(id, "open")) as Issue[]);
    setGate(await fetchQualityGate(id));
  }

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as { company_id?: string }) : {};
      const id = demo.company_id || auth?.company_id || "";
      setCompanyId(id);
      if (!id) return;
      try {
        await reload(id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить качество данных");
      }
    }
    load();
  }, []);

  async function onExplain(issueId: string) {
    setBusy(true);
    setError(null);
    try {
      setExplanation(await explainQualityIssue(issueId));
      if (companyId) setGate(await fetchQualityGate(companyId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Data Doctor недоступен");
    } finally {
      setBusy(false);
    }
  }

  async function onResolve(issueId: string) {
    if (!resolveReason.trim()) {
      setError("Укажите stage_skip_reason / причину");
      return;
    }
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await resolveQualityIssue(issueId, resolveReason.trim());
      if (companyId) await reload(companyId);
      setNote("Проблема закрыта с указанием причины");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось закрыть проблему");
    } finally {
      setBusy(false);
    }
  }

  const silentSkips = issues.filter((i) => i.code === "silent_stage_skip");

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Качество данных</h1>
        <p>
          Data Quality Engine блокирует анализ детерминированно. Silent stage skip — предупреждение;
          Data Doctor только объясняет.
        </p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}
      {note && <p className="ok-text">{note}</p>}

      {gate && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Analysis Gate</h2>
          <FieldGrid
            items={[
              {
                label: "Статус",
                value: <StatusPill value={gate.blocked ? "blocked" : "ready"} />,
              },
              {
                label: "Причины",
                value: gate.reasons.length ? gate.reasons.join("; ") : "—",
              },
            ]}
          />
        </section>
      )}

      {silentSkips.length > 0 && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Silent stage skip</h2>
          <p style={{ marginBottom: 10 }}>
            Этапы пропущены без причины. Закройте с явным <code>stage_skip_reason</code> или
            исправьте импорт.
          </p>
          <label className="stack-form" style={{ marginBottom: 12 }}>
            Причина закрытия
            <input
              value={resolveReason}
              onChange={(e) => setResolveReason(e.target.value)}
            />
          </label>
          <div className="list-stack">
            {silentSkips.map((issue) => (
              <div className="row" key={issue.id}>
                <strong>
                  {issue.code} · {issue.severity}
                </strong>
                <span>{issue.message}</span>
                <div className="form-actions" style={{ marginTop: 8 }}>
                  <button
                    className="btn"
                    type="button"
                    disabled={busy}
                    onClick={() => onExplain(issue.id)}
                  >
                    Объяснить
                  </button>
                  <button
                    className="btn btn-primary"
                    type="button"
                    disabled={busy}
                    onClick={() => onResolve(issue.id)}
                  >
                    Закрыть с причиной
                  </button>
                </div>
              </div>
            ))}
          </div>
          <p className="muted-note" style={{ marginTop: 10 }}>
            <Link href="/alignment">Сверка</Link> · <Link href="/demo">Демо</Link>
          </p>
        </section>
      )}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Открытые проблемы DQ</h2>
        {issues.length === 0 ? (
          <p>Открытых проблем нет</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {issues.map((issue) => (
              <div className="row" key={issue.id}>
                <strong>
                  {issue.code} · {issue.severity}
                  {issue.code === "silent_stage_skip" ? " · silent skip" : ""}
                </strong>
                <span>{issue.message}</span>
                <FieldGrid
                  items={[
                    { label: "Статус", value: <StatusPill value={issue.status} /> },
                    {
                      label: "Блокирует анализ",
                      value: issue.blocks_analysis ? "да" : "нет",
                    },
                  ]}
                />
                <button
                  className="btn"
                  type="button"
                  style={{ marginTop: 8 }}
                  disabled={busy}
                  onClick={() => onExplain(issue.id)}
                >
                  Объяснить (Data Doctor)
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {explanation && (
        <section className="panel">
          <h2>Объяснение Data Doctor</h2>
          <FieldGrid
            items={[
              { label: "Пояснение", value: String(explanation.explanation) },
              { label: "Вероятная причина", value: String(explanation.likely_cause) },
              { label: "Как исправить", value: String(explanation.suggested_fix) },
              { label: "Владелец", value: String(explanation.suggested_owner) },
              { label: "Задача", value: String(explanation.prepared_task) },
              {
                label: "Снимает блокировку?",
                value: explanation.can_unblock_analysis ? "да" : "нет (запрещено)",
              },
            ]}
          />
        </section>
      )}
    </main>
  );
}
