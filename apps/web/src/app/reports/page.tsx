"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { FieldGrid, StatusPill } from "@/components/ui-bits";
import { runReportingUpload } from "@/lib/api";
import { getAccessToken, getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Meaning = { metric?: string; value?: string; meaning?: string };
type Conclusions = {
  summary?: string;
  units_note?: string;
  meanings?: Meaning[];
  risks?: string[];
  actions?: string[];
  demand_mix?: Meaning[];
  profitability?: Meaning[];
  top_expenses?: Meaning[];
  money_leaks?: Meaning[];
  dynamics?: Meaning[];
};
type Rec = { id: string; title: string; body: string; priority: string };

type UploadResult = {
  company_id: string;
  analysis_id: string;
  analysis_status?: string;
  analysis_blocked?: boolean;
  question?: string;
  conclusions?: Conclusions;
  finance_briefing?: Conclusions;
  recommendations?: Rec[];
  import?: Record<string, unknown>;
};

export default function ReportsPage() {
  const [companyId, setCompanyId] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [question, setQuestion] = useState(
    "Что значат ключевые цифры в этой отчётности и что сделать в первую очередь?",
  );
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  useEffect(() => {
    const auth = getAuthUser();
    if (auth?.company_id) {
      setCompanyId(auth.company_id);
      setHint("Компания взята из вашего входа. Можно оставить как есть или указать название.");
    }
  }, []);

  async function onRun(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Выберите Excel (.xlsx) с отчётностью");
      return;
    }
    if (!getAccessToken()) {
      setError("Сначала войдите (/login)");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const trimmed = companyId.trim();
      const data = (await runReportingUpload({
        file,
        companyId: trimmed || undefined,
        companyName: companyName.trim() || undefined,
        question: question.trim() || undefined,
      })) as UploadResult;
      setResult(data);
      const cid = String(data.company_id || trimmed);
      setCompanyId(cid);
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          company_id: cid,
          analysis_id: data.analysis_id,
          extras: { flow: "reports", import: data.import },
        }),
      );
      setHint(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось разобрать отчётность";
      setError(message);
      if (/company not found/i.test(message)) {
        setCompanyId("");
        setHint("Старый ID очищен. Укажите название компании или оставьте пустым.");
      }
    } finally {
      setBusy(false);
    }
  }

  const conclusions = result?.conclusions || result?.finance_briefing;
  const imported = result?.import ?? {};

  function renderMeaningList(title: string, items?: Meaning[]) {
    if (!items?.length) return null;
    return (
      <div style={{ marginTop: 16 }}>
        <h2>{title}</h2>
        <div className="list-stack" style={{ marginTop: 8 }}>
          {items.map((item) => (
            <div className="row" key={`${title}-${item.metric}-${item.value}`}>
              <strong>
                {item.metric}: {item.value}
              </strong>
              <span>{item.meaning}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Моя отчётность</h1>
        <p>
          Загрузите Excel (финрез, расходы, бар/кухня) — получите выводы: что значат цифры, где
          риски и что сделать.
        </p>
      </div>

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Загрузить файл</h2>
        <form onSubmit={onRun} className="stack-form">
          <label>
            Название компании (если ID пустой)
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="например, Бистро Benedict"
            />
          </label>
          <label>
            ID компании (необязательно)
            <input
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              placeholder="пусто = создать/найти по названию"
            />
          </label>
          <label>
            На что смотреть
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} />
          </label>
          <label>
            Файл отчётности (.xlsx)
            <input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Разбираю отчётность…" : "Получить выводы"}
          </button>
        </form>
        {hint && <p className="muted-note">{hint}</p>}
        {error && <p className="error-text">{error}</p>}
      </section>

      {result && conclusions && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Выводы по вашей отчётности</h2>
          <p style={{ marginTop: 8, marginBottom: 12, fontSize: 17, lineHeight: 1.45 }}>
            {conclusions.summary}
          </p>
          {conclusions.units_note && (
            <p className="muted-note" style={{ marginBottom: 12 }}>
              {conclusions.units_note}
            </p>
          )}

          <h2 style={{ marginTop: 8 }}>Что значат цифры</h2>
          <div className="list-stack" style={{ marginTop: 10 }}>
            {(conclusions.meanings || []).map((item) => (
              <div className="row" key={`${item.metric}-${item.value}`}>
                <strong>
                  {item.metric}: {item.value}
                </strong>
                <span>{item.meaning}</span>
              </div>
            ))}
            {!conclusions.meanings?.length && <p>Метрики не распознаны — проверьте структуру файла.</p>}
          </div>

          {renderMeaningList("Что заказывают чаще", conclusions.demand_mix)}
          {renderMeaningList("Что рентабельнее", conclusions.profitability)}
          {renderMeaningList("Главные статьи расходов", conclusions.top_expenses)}
          {renderMeaningList("Где деньги утекают", conclusions.money_leaks)}
          {renderMeaningList("Динамика по месяцам", conclusions.dynamics)}

          {(conclusions.risks || []).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h2>Риски</h2>
              <div className="list-stack" style={{ marginTop: 8 }}>
                {(conclusions.risks || []).map((risk) => (
                  <div className="row" key={risk}>
                    <span>{risk}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(conclusions.actions || []).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h2>Что сделать</h2>
              <div className="list-stack" style={{ marginTop: 8 }}>
                {(conclusions.actions || []).map((action) => (
                  <div className="row" key={action}>
                    <span>{action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(result.recommendations || []).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h2>Рекомендации к решению</h2>
              <div className="list-stack" style={{ marginTop: 8 }}>
                {(result.recommendations || []).slice(0, 4).map((rec) => (
                  <div className="row" key={rec.id}>
                    <strong>
                      {rec.title} · {rec.priority}
                    </strong>
                    <span>{rec.body}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="form-actions" style={{ marginTop: 16 }}>
            <Link href="/decisions" className="btn btn-primary">
              Зафиксировать решение
            </Link>
            <Link href="/council" className="btn">
              Обсудить за столом
            </Link>
            <Link href="/analysis" className="btn">
              Подробный анализ
            </Link>
            <Link href="/executive" className="btn">
              Кабинет
            </Link>
          </div>
        </section>
      )}

      {result && !conclusions && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Анализ создан</h2>
          <p>Выводы не собрались автоматически. Откройте подробный анализ.</p>
          <Link href="/analysis" className="btn btn-primary">
            Открыть анализ
          </Link>
        </section>
      )}

      {result && (
        <details className="panel">
          <summary style={{ cursor: "pointer" }}>Технические детали импорта</summary>
          <div style={{ marginTop: 12 }}>
            <FieldGrid
              items={[
                { label: "Компания", value: String(result.company_id) },
                {
                  label: "Анализ",
                  value: <StatusPill value={String(result.analysis_status || "—")} />,
                },
                {
                  label: "Метрик / фактов",
                  value: `${imported.metrics_total ?? "—"} / ${imported.fact_count ?? "—"}`,
                },
                {
                  label: "По системам",
                  value: imported.by_origin ? JSON.stringify(imported.by_origin) : "—",
                },
              ]}
            />
          </div>
        </details>
      )}
    </main>
  );
}
