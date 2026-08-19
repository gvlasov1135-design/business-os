"use client";

import { FormEvent, useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import { createSource, fetchFact, fetchRawRecord, importCsv, importRecord } from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

const DEFAULT_PAYLOAD = `{
  "lead_id": "L-1001",
  "created_at": "2026-08-01T09:00:00+03:00",
  "first_contact_at": "2026-08-01T09:47:00+03:00",
  "assigned_position": "Sales Manager",
  "actual_actor": "employee-17"
}`;

export default function SourcesPage() {
  const [companyId, setCompanyId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [payloadText, setPayloadText] = useState(DEFAULT_PAYLOAD);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [raw, setRaw] = useState<Record<string, unknown> | null>(null);
  const [fact, setFact] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const auth = getAuthUser();
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const demo = JSON.parse(stored) as {
        company_id?: string;
        source_id?: string;
        raw_record_id?: string;
        fact_id?: string;
      };
      if (demo.company_id) setCompanyId(demo.company_id);
      if (demo.source_id) setSourceId(demo.source_id);
      if (demo.raw_record_id) {
        fetchRawRecord(demo.raw_record_id).then(setRaw).catch(() => undefined);
      }
      if (demo.fact_id) {
        fetchFact(demo.fact_id).then(setFact).catch(() => undefined);
      }
    } else if (auth?.company_id) {
      setCompanyId(auth.company_id);
    }
  }, []);

  async function onCreateSource(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const source = await createSource({
        company_id: companyId,
        code: `crm-ui-${Date.now().toString(36)}`,
        name: "CRM импорт",
        source_type: "crm",
        freshness_hours: 24,
      });
      setSourceId(String(source.id));
      setNote(`Источник создан: ${source.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать источник");
    } finally {
      setBusy(false);
    }
  }

  async function onImport(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const payload = JSON.parse(payloadText) as Record<string, unknown>;
      const result = await importRecord(sourceId, payload);
      setRaw(result.raw_record);
      setFact(result.fact);
      const stored = window.localStorage.getItem(STORAGE_KEY);
      const demo = stored ? (JSON.parse(stored) as Record<string, unknown>) : {};
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          ...demo,
          company_id: companyId,
          source_id: sourceId,
          raw_record_id: result.raw_record.id,
          fact_id: result.fact?.id,
        }),
      );
      setNote(
        result.duplicate
          ? "Повторный импорт — возвращена существующая raw-запись"
          : result.blocked
            ? "Импорт отправлен в карантин качества данных"
            : "Импорт выполнен",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка импорта");
    } finally {
      setBusy(false);
    }
  }

  async function onCsvImport(event: FormEvent) {
    event.preventDefault();
    if (!csvFile || !sourceId) {
      setError("Нужны ID источника и CSV-файл");
      return;
    }
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const rows = await importCsv(sourceId, csvFile);
      const last = rows[rows.length - 1];
      if (last?.raw_record) setRaw(last.raw_record as Record<string, unknown>);
      if (last?.fact) setFact(last.fact as Record<string, unknown>);
      setNote(`CSV импортирован: ${rows.length} строк(и)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка CSV-импорта");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Импорт источника</h1>
        <p>Регистрация CRM, импорт записи лида, просмотр raw и lineage факта.</p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}
      {note && <p className="ok-text">{note}</p>}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Создать источник</h2>
        <form onSubmit={onCreateSource} className="stack-form">
          <label>
            ID компании
            <input value={companyId} onChange={(e) => setCompanyId(e.target.value)} required />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !companyId}>
            Создать CRM-источник
          </button>
        </form>
      </section>

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Импорт JSON-записи</h2>
        <form onSubmit={onImport} className="stack-form">
          <label>
            ID источника
            <input value={sourceId} onChange={(e) => setSourceId(e.target.value)} required />
          </label>
          <label>
            Полезная нагрузка
            <textarea
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              rows={10}
              required
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !sourceId}>
            Импортировать
          </button>
        </form>
      </section>

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Импорт CSV</h2>
        <form onSubmit={onCsvImport} className="stack-form">
          <label>
            CSV-файл
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !sourceId}>
            Импортировать CSV
          </button>
        </form>
      </section>

      {raw && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Сырая запись</h2>
          <FieldGrid
            items={[
              { label: "Внешний ID", value: String(raw.external_id) },
              { label: "Статус", value: <StatusPill value={String(raw.status)} /> },
              { label: "Контрольная сумма", value: String(raw.checksum_sha256).slice(0, 16) + "…" },
              { label: "ID raw", value: String(raw.id) },
            ]}
          />
        </section>
      )}

      {fact && (
        <section className="panel">
          <h2>Наблюдаемый факт</h2>
          <FieldGrid
            items={[
              { label: "Субъект", value: String(fact.subject) },
              { label: "Предикат", value: String(fact.predicate) },
              { label: "Значение", value: String(fact.value_text) },
              { label: "Trust", value: String(fact.trust_index) },
            ]}
          />
        </section>
      )}
    </main>
  );
}
