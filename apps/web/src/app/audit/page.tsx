"use client";

import { useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import { fetchAuditEvents } from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type AuditEvent = {
  id: string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  created_at: string;
  payload?: Record<string, unknown> | null;
};

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as { company_id?: string }) : {};
      const companyId = demo.company_id || auth?.company_id;
      if (!companyId && !auth) setEmpty(true);
      try {
        setEvents((await fetchAuditEvents(companyId)) as AuditEvent[]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить аудит");
      }
    }
    load();
  }, []);

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Журнал аудита</h1>
        <p>Недавние действия по identity, документам, импорту, сверке и решениям.</p>
      </div>
      {error && <p className="error-text">{error}</p>}
      {empty && events.length === 0 && <EmptyDemoHint />}

      <section className="panel">
        <h2>События</h2>
        {events.length === 0 ? (
          <p>Пока нет событий аудита.</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {events.map((event) => (
              <div className="row" key={event.id}>
                <strong>
                  {event.action} · {event.entity_type}
                </strong>
                <FieldGrid
                  items={[
                    {
                      label: "Когда",
                      value: new Date(event.created_at).toLocaleString("ru-RU"),
                    },
                    { label: "Сущность", value: event.entity_id || "—" },
                    {
                      label: "Данные",
                      value: event.payload ? JSON.stringify(event.payload) : "—",
                    },
                    { label: "Статус", value: <StatusPill value="recorded" /> },
                  ]}
                />
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
