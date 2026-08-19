"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import {
  confirmResolutionCandidate,
  fetchResolutionCandidates,
  fetchResolutionEntities,
  fetchResolutionMemberships,
  fetchResolutionMerges,
  rejectResolutionCandidate,
  splitResolutionMembership,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Candidate = {
  id: string;
  match_method: string;
  match_key: string;
  match_value: string;
  confidence: number;
  status: string;
  blocks_analysis: boolean;
  evidence?: Record<string, unknown>;
};

type Entity = {
  id: string;
  display_name: string;
  entity_type: string;
  trust_index: number;
};

export default function ResolutionPage() {
  const [companyId, setCompanyId] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [merges, setMerges] = useState<Record<string, unknown>[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [memberships, setMemberships] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async (cid: string) => {
    setCandidates((await fetchResolutionCandidates(cid, "pending")) as Candidate[]);
    setEntities((await fetchResolutionEntities(cid)) as Entity[]);
    setMerges(await fetchResolutionMerges(cid));
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
        setError(err instanceof Error ? err.message : "Не удалось загрузить Entity Resolution");
      }
    }
    load();
  }, [reload]);

  async function onConfirm(id: string) {
    setBusy(true);
    setError(null);
    try {
      await confirmResolutionCandidate(id, "Подтверждено в UI");
      if (companyId) await reload(companyId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка подтверждения");
    } finally {
      setBusy(false);
    }
  }

  async function onReject(id: string) {
    setBusy(true);
    setError(null);
    try {
      await rejectResolutionCandidate(id, "Отклонено в UI");
      if (companyId) await reload(companyId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка отклонения");
    } finally {
      setBusy(false);
    }
  }

  async function onSelectEntity(entityId: string) {
    setSelectedEntity(entityId);
    setError(null);
    try {
      setMemberships(await fetchResolutionMemberships(entityId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить связи");
    }
  }

  async function onSplit(membershipId: string) {
    setBusy(true);
    setError(null);
    try {
      await splitResolutionMembership(membershipId, "Разделение в UI");
      if (companyId) await reload(companyId);
      if (selectedEntity) setMemberships(await fetchResolutionMemberships(selectedEntity));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка split");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Entity Resolution</h1>
        <p>
          Связыва записей источников с канонической сущностью. Exact — автоматически; deterministic
          и кандидаты — только после подтверждения. Исходные записи сохраняются.
        </p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Кандидаты на объединение</h2>
        {candidates.length === 0 ? (
          <p>Открытых кандидатов нет</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {candidates.map((c) => (
              <div className="row" key={c.id}>
                <strong>
                  {c.match_method} · {c.match_key}={c.match_value}
                </strong>
                <FieldGrid
                  items={[
                    { label: "Уверенность", value: String(c.confidence) },
                    {
                      label: "Блокирует анализ",
                      value: c.blocks_analysis ? "да" : "нет",
                    },
                    {
                      label: "Доказательства",
                      value: c.evidence
                        ? `${c.evidence.left_external_id} ↔ ${c.evidence.right_external_id}`
                        : "—",
                    },
                  ]}
                />
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button className="btn btn-primary" type="button" disabled={busy} onClick={() => onConfirm(c.id)}>
                    Подтвердить
                  </button>
                  <button className="btn" type="button" disabled={busy} onClick={() => onReject(c.id)}>
                    Отклонить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Канонические сущности</h2>
        {entities.length === 0 ? (
          <p>Пока нет</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {entities.map((e) => (
              <div className="row" key={e.id}>
                <button className="btn" type="button" onClick={() => onSelectEntity(e.id)}>
                  {e.display_name}
                </button>
                <span>
                  {e.entity_type} · Trust {e.trust_index}
                </span>
              </div>
            ))}
          </div>
        )}
        {selectedEntity && (
          <div style={{ marginTop: 12 }}>
            <h3>Связи сущности</h3>
            {memberships.map((m) => (
              <div className="row" key={String(m.id)} style={{ marginTop: 8 }}>
                <span>
                  {String(m.external_id)} · {String(m.match_method)} ·{" "}
                  <StatusPill value={String(m.status)} />
                </span>
                {m.status === "active" && (
                  <button
                    className="btn"
                    type="button"
                    disabled={busy}
                    style={{ marginTop: 6 }}
                    onClick={() => onSplit(String(m.id))}
                  >
                    Split
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <h2>История merge / split</h2>
        {merges.length === 0 ? (
          <p>Событий нет</p>
        ) : (
          <pre style={{ marginTop: 8, overflow: "auto" }}>
            {JSON.stringify(merges.slice(0, 12), null, 2)}
          </pre>
        )}
      </section>
    </main>
  );
}
