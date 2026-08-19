"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import {
  createKpiVersion,
  fetchKpiSnapshots,
  fetchKpiVersions,
  fetchKpis,
  recalculateKpi,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Kpi = {
  id: string;
  code: string;
  name: string;
  unit: string;
  owner_name: string;
  trust_index: number;
  status: string;
  current_version_id?: string;
};

export default function KpiPage() {
  const [companyId, setCompanyId] = useState("");
  const [kpis, setKpis] = useState<Kpi[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [versions, setVersions] = useState<Record<string, unknown>[]>([]);
  const [snapshots, setSnapshots] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async (cid: string) => {
    setKpis((await fetchKpis(cid)) as Kpi[]);
  }, []);

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
        setError(err instanceof Error ? err.message : "Не удалось загрузить KPI");
      }
    }
    load();
  }, [reload]);

  async function onSelect(kpiId: string) {
    setSelected(kpiId);
    setError(null);
    try {
      setVersions(await fetchKpiVersions(kpiId));
      setSnapshots(await fetchKpiSnapshots(kpiId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки версий");
    }
  }

  async function onRecalc(kpiId: string) {
    setBusy(true);
    setError(null);
    try {
      await recalculateKpi(kpiId, "2026-08-01T00:00:00+00:00", "2026-08-31T23:59:59+00:00");
      setSnapshots(await fetchKpiSnapshots(kpiId));
      if (companyId) await reload(companyId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка пересчёта");
    } finally {
      setBusy(false);
    }
  }

  async function onNewVersion(kpiId: string) {
    setBusy(true);
    setError(null);
    try {
      const current = versions[0];
      await createKpiVersion(kpiId, {
        formula: (current?.formula as Record<string, unknown>) || { op: "avg_fact_minutes" },
        source_mapping:
          (current?.source_mapping as Record<string, unknown>) || {
            predicate: "actual_first_contact_minutes",
          },
        target_value: Number(current?.target_value ?? 15),
        change_reason: "Новая версия из UI (формула сохранена, история версий)",
      });
      setVersions(await fetchKpiVersions(kpiId));
      if (companyId) await reload(companyId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка версии");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>KPI</h1>
        <p>
          Воспроизводимые показатели: формула и источники видны, смена формулы создаёт версию,
          конфликт данных маркируется.
        </p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Определения</h2>
        {kpis.length === 0 ? (
          <p>Нет KPI — запустите демо</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {kpis.map((kpi) => (
              <div className="row" key={kpi.id}>
                <button className="btn" type="button" onClick={() => onSelect(kpi.id)}>
                  {kpi.name}
                </button>
                <FieldGrid
                  items={[
                    { label: "Код", value: kpi.code },
                    { label: "Владелец", value: kpi.owner_name },
                    { label: "Ед.", value: kpi.unit },
                    { label: "Trust", value: String(kpi.trust_index) },
                    { label: "Статус", value: <StatusPill value={kpi.status} /> },
                  ]}
                />
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button
                    className="btn btn-primary"
                    type="button"
                    disabled={busy}
                    onClick={() => onRecalc(kpi.id)}
                  >
                    Пересчитать
                  </button>
                  <button className="btn" type="button" disabled={busy} onClick={() => onNewVersion(kpi.id)}>
                    Новая версия
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selected && (
        <>
          <section className="panel" style={{ marginBottom: 16 }}>
            <h2>Версии формулы</h2>
            {versions.map((v) => (
              <div className="row" key={String(v.id)} style={{ marginTop: 8 }}>
                <strong>
                  v{String(v.version_number)} · <StatusPill value={String(v.status)} />
                </strong>
                <p style={{ marginTop: 6 }}>{String(v.formula_text)}</p>
                <FieldGrid
                  items={[
                    { label: "Формула", value: String(v.formula_text || "—") },
                    {
                      label: "Источник",
                      value: String(
                        ((v.source_mapping as Record<string, unknown>) || {}).predicate ?? "—",
                      ),
                    },
                    { label: "Цель", value: String(v.target_value ?? "—") },
                    {
                      label: "Причина смены",
                      value: String(v.change_reason || "—"),
                    },
                  ]}
                />
              </div>
            ))}
          </section>

          <section className="panel">
            <h2>Снимки (actual / target)</h2>
            {snapshots.length === 0 ? (
              <p>Ещё не пересчитывали</p>
            ) : (
              snapshots.map((s) => (
                <div className="row" key={String(s.id)} style={{ marginTop: 8 }}>
                  <FieldGrid
                    items={[
                      { label: "Факт", value: String(s.actual_value ?? "—") },
                      { label: "Цель", value: String(s.target_value ?? "—") },
                      { label: "Статус", value: <StatusPill value={String(s.status)} /> },
                      {
                        label: "Конфликт",
                        value: s.conflict_flag ? "да" : "нет",
                      },
                      { label: "Trust", value: String(s.trust_index) },
                      {
                        label: "Источники",
                        value: Array.isArray(s.sources) ? String(s.sources.length) : "0",
                      },
                    ]}
                  />
                </div>
              ))
            )}
          </section>
        </>
      )}
    </main>
  );
}
