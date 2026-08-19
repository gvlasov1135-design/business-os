"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { EmptyDemoHint, StatusPill } from "@/components/ui-bits";
import {
  closeCouncilSession,
  createCouncilSession,
  fetchCouncilSession,
  fetchCouncilSessions,
  postCouncilMessage,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type ChannelKey = "table" | "executive" | "sales" | "critic" | "data_doctor";

type Message = {
  id: string;
  channel: "table" | "private";
  role: "user" | "agent" | "system";
  agent?: string | null;
  body: string;
  created_at: string;
};

type Session = {
  id: string;
  company_id: string;
  analysis_id?: string | null;
  topic: string;
  status: string;
  messages: Message[];
};

const CHANNELS: { key: ChannelKey; label: string; hint: string }[] = [
  { key: "table", label: "Общий стол", hint: "Executive · Sales · Critic" },
  { key: "executive", label: "Executive", hint: "Личный чат" },
  { key: "sales", label: "Sales", hint: "Личный чат" },
  { key: "critic", label: "Critic", hint: "Личный чат" },
  { key: "data_doctor", label: "Data Doctor", hint: "Качество данных" },
];

function filterMessages(messages: Message[], channel: ChannelKey): Message[] {
  if (channel === "table") {
    return messages.filter((m) => m.channel === "table");
  }
  return messages.filter(
    (m) => m.channel === "private" && (m.agent === channel || (m.role === "user" && m.agent === channel)),
  );
}

export default function CouncilPage() {
  const [companyId, setCompanyId] = useState("");
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [channel, setChannel] = useState<ChannelKey>("table");
  const [draft, setDraft] = useState("");
  const [topic, setTopic] = useState("Заседание по Sales SLA");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [past, setPast] = useState<{ id: string; topic: string; status: string }[]>([]);

  useEffect(() => {
    const auth = getAuthUser();
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const demo = raw
      ? (JSON.parse(raw) as {
          company_id?: string;
          analysis_id?: string;
          council_session_id?: string;
        })
      : {};
    const cid = demo.company_id || auth?.company_id || "";
    setCompanyId(cid);
    if (demo.analysis_id) setAnalysisId(demo.analysis_id);

    async function boot() {
      if (!cid) return;
      try {
        const listed = (await fetchCouncilSessions(cid)) as {
          id: string;
          topic: string;
          status: string;
        }[];
        setPast(listed.slice(0, 8));
        const prefer = demo.council_session_id || listed.find((s) => s.status === "open")?.id;
        if (prefer) {
          const loaded = (await fetchCouncilSession(String(prefer))) as Session;
          setSession(loaded);
        }
      } catch {
        /* empty company ok */
      }
    }
    boot();
  }, []);

  const visible = useMemo(
    () => filterMessages(session?.messages ?? [], channel),
    [session, channel],
  );

  function persistSessionId(id: string) {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...demo, company_id: companyId, council_session_id: id }),
    );
  }

  async function onOpen(event?: FormEvent) {
    event?.preventDefault();
    if (!companyId) {
      setError("Нужен ID компании — войдите или запустите демо");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = (await createCouncilSession({
        company_id: companyId,
        topic: topic.trim() || undefined,
        analysis_id: analysisId || undefined,
      })) as Session;
      setSession(created);
      persistSessionId(created.id);
      setChannel("table");
      const listed = (await fetchCouncilSessions(companyId)) as {
        id: string;
        topic: string;
        status: string;
      }[];
      setPast(listed.slice(0, 8));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось открыть заседание");
    } finally {
      setBusy(false);
    }
  }

  async function onSend(event: FormEvent) {
    event.preventDefault();
    if (!session || !draft.trim()) return;
    if (session.status !== "open") {
      setError("Заседание закрыто");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload =
        channel === "table"
          ? { channel: "table" as const, body: draft.trim() }
          : {
              channel: "private" as const,
              agent: channel,
              body: draft.trim(),
            };
      await postCouncilMessage(session.id, payload);
      const refreshed = (await fetchCouncilSession(session.id)) as Session;
      setSession(refreshed);
      setDraft("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить");
    } finally {
      setBusy(false);
    }
  }

  async function onClose() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const closed = (await closeCouncilSession(session.id)) as Session;
      setSession(closed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось закрыть");
    } finally {
      setBusy(false);
    }
  }

  async function onLoadPast(id: string) {
    setBusy(true);
    setError(null);
    try {
      const loaded = (await fetchCouncilSession(id)) as Session;
      setSession(loaded);
      persistSessionId(loaded.id);
      setChannel("table");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Заседание ИИ-агентов</h1>
        <p>
          Общий стол — спор Executive, Sales и Critic. Личные чаты — с каждым агентом и Data
          Doctor. Решение принимает человек.
        </p>
      </div>

      {!companyId && <EmptyDemoHint />}
      {error && <p className="error-text">{error}</p>}

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Открыть заседание</h2>
        <form onSubmit={onOpen} className="stack-form">
          <label>
            ID компании
            <input value={companyId} onChange={(e) => setCompanyId(e.target.value)} required />
          </label>
          <label>
            Повестка
            <input value={topic} onChange={(e) => setTopic(e.target.value)} />
          </label>
          {analysisId ? (
            <p className="muted-note">Привязка к анализу: {analysisId.slice(0, 8)}…</p>
          ) : (
            <p className="muted-note">
              Можно сначала запустить <Link href="/analysis">разовый анализ</Link> и продолжить за
              столом.
            </p>
          )}
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={busy || !companyId}>
              {busy ? "Открываю…" : "Открыть заседание"}
            </button>
            {session?.status === "open" && (
              <button className="btn" type="button" disabled={busy} onClick={onClose}>
                Закрыть заседание
              </button>
            )}
            <Link href="/decisions" className="btn">
              К решениям
            </Link>
          </div>
        </form>
      </section>

      {past.length > 0 && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>Недавние заседания</h2>
          <div className="list-stack" style={{ marginTop: 10 }}>
            {past.map((item) => (
              <div className="row" key={item.id}>
                <strong>{item.topic}</strong>
                <span>
                  <StatusPill value={item.status} /> · {item.id.slice(0, 8)}…
                </span>
                <button
                  className="btn"
                  type="button"
                  style={{ marginTop: 8 }}
                  disabled={busy}
                  onClick={() => onLoadPast(item.id)}
                >
                  Открыть
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {session && (
        <section className="council-shell panel">
          <div className="council-meta">
            <div>
              <strong>{session.topic}</strong>
              <div className="muted-note" style={{ marginTop: 4 }}>
                <StatusPill value={session.status} /> · session {session.id.slice(0, 8)}…
                {session.analysis_id ? ` · analysis ${String(session.analysis_id).slice(0, 8)}…` : ""}
              </div>
            </div>
          </div>

          <div className="council-layout">
            <aside className="council-channels">
              <div className="nav-group-title" style={{ color: "var(--muted)" }}>
                Каналы
              </div>
              {CHANNELS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={
                    channel === item.key ? "council-channel active" : "council-channel"
                  }
                  onClick={() => setChannel(item.key)}
                >
                  <span className="nav-label">{item.label}</span>
                  <span className="nav-hint">{item.hint}</span>
                </button>
              ))}
            </aside>

            <div className="council-chat">
              <div className="council-thread">
                {visible.length === 0 ? (
                  <p className="muted-note">Пока пусто — напишите сообщение.</p>
                ) : (
                  visible.map((msg) => (
                    <div
                      key={msg.id}
                      className={`council-bubble council-${msg.role}${
                        msg.agent ? ` agent-${msg.agent}` : ""
                      }`}
                    >
                      <div className="council-bubble-meta">
                        {msg.role === "user"
                          ? "Вы"
                          : msg.role === "system"
                            ? "Система"
                            : msg.agent || "Агент"}
                      </div>
                      <div className="council-bubble-body">{msg.body}</div>
                    </div>
                  ))
                )}
              </div>

              {session.status === "open" && (
                <form onSubmit={onSend} className="council-compose">
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={3}
                    placeholder={
                      channel === "table"
                        ? "Сказать всем за столом…"
                        : `Личное сообщение для ${channel}…`
                    }
                    required
                  />
                  <button className="btn btn-primary" type="submit" disabled={busy}>
                    {channel === "table" ? "Спросить всех" : "Отправить"}
                  </button>
                </form>
              )}
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
