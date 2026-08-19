"use client";

import { FormEvent, useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import { fetchKnowledgeList, fetchKnowledgeRelations, searchKnowledge } from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type RecordItem = {
  id: string;
  title: string;
  body: string;
  record_type: string;
  status: string;
  trust_index: number;
};

type Relation = {
  id: string;
  from_record_id: string;
  to_record_id: string;
  relation_type: string;
};

export default function KnowledgePage() {
  const [companyId, setCompanyId] = useState("");
  const [query, setQuery] = useState("контакт");
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as { company_id?: string }) : {};
      const id = demo.company_id || auth?.company_id || "";
      setCompanyId(id);
      if (!id) return;
      try {
        setRecords((await fetchKnowledgeList(id)) as RecordItem[]);
        setRelations((await fetchKnowledgeRelations(id)) as Relation[]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить знания");
      }
    }
    load();
  }, []);

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!companyId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await searchKnowledge(companyId, query);
      setRecords(result.results as RecordItem[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка поиска");
    } finally {
      setBusy(false);
    }
  }

  function relationsFor(recordId: string): Relation[] {
    return relations.filter(
      (r) => r.from_record_id === recordId || r.to_record_id === recordId,
    );
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>База знаний</h1>
        <p>Подтверждённые Knowledge Records, связи и поиск.</p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Поиск</h2>
        <form onSubmit={onSearch} className="stack-form">
          <label>
            Запрос
            <input value={query} onChange={(e) => setQuery(e.target.value)} required />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !companyId}>
            {busy ? "Ищу…" : "Найти"}
          </button>
        </form>
      </section>

      {relations.length > 0 && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Связи ({relations.length})</h2>
          <div className="list-stack" style={{ marginTop: 10 }}>
            {relations.map((rel) => (
              <div className="row" key={rel.id}>
                <strong>{rel.relation_type}</strong>
                <span>
                  {rel.from_record_id.slice(0, 8)}… → {rel.to_record_id.slice(0, 8)}…
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="panel">
        <h2>Записи</h2>
        {records.length === 0 ? (
          <p>Записей нет</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {records.map((item) => {
              const linked = relationsFor(item.id);
              return (
                <div className="row" key={item.id}>
                  <strong>{item.title}</strong>
                  <p style={{ margin: "8px 0", color: "#1e1f21" }}>{item.body}</p>
                  <FieldGrid
                    items={[
                      { label: "Тип", value: item.record_type },
                      { label: "Статус", value: <StatusPill value={item.status} /> },
                      { label: "Trust", value: String(item.trust_index) },
                      {
                        label: "Связи",
                        value: linked.length
                          ? linked.map((r) => r.relation_type).join(", ")
                          : "—",
                      },
                      { label: "ID", value: item.id },
                    ]}
                  />
                </div>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
