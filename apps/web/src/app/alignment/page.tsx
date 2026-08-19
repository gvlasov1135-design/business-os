"use client";

import { useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, StatusPill } from "@/components/ui-bits";
import {
  acceptAlignmentDeviation,
  applyAlignmentProposedChange,
  confirmAlignmentIssue,
  fetchAlignmentIssue,
  fetchAlignmentIssues,
  fetchKnowledge,
  fetchQualityIssues,
  rejectAlignmentIssue,
  requestAlignmentData,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Issue = {
  id: string;
  status: string;
  severity: string;
  trust_index: number;
  normative_value?: {
    minutes?: number;
    role?: string;
    stages?: string[];
  };
  actual_value?: {
    minutes?: number;
    assigned_position?: string;
    actual_actor?: string;
    stages_completed?: string[];
    stages_skipped?: string[];
  };
  deviation_value?: {
    minutes?: number;
    mismatch?: boolean;
    label?: string;
    skipped_count?: number;
  };
  evidence?: Record<string, unknown>;
  proposed_change?: {
    title?: string;
    summary?: string;
    suggested_text?: string;
    status?: string;
    applied_version_id?: string;
  } | null;
};

type Knowledge = {
  id: string;
  title: string;
  body: string;
  status: string;
  trust_index: number;
  record_type: string;
};

function issueTitle(issue: Issue): string {
  const rule = String(issue.evidence?.rule_code || "");
  if (rule.includes("responsible") || issue.normative_value?.role) {
    return "Ответственный vs исполнитель";
  }
  if (rule.includes("process") || issue.normative_value?.stages) {
    return "Обязательные этапы процесса";
  }
  return "Срок первого контакта с лидом";
}

function IssueCard({
  issue,
  busy,
  onAction,
}: {
  issue: Issue;
  busy: boolean;
  onAction: (
    id: string,
    action: "confirm" | "reject" | "accept" | "request" | "apply",
  ) => void;
}) {
  const stagesNorm = (issue.normative_value?.stages || []).join(" → ");
  const normative =
    issue.normative_value?.minutes ??
    issue.normative_value?.role ??
    (stagesNorm || "—");
  const stagesFact = (issue.actual_value?.stages_skipped || []).join(", ");
  const actual =
    issue.actual_value?.minutes ??
    issue.actual_value?.actual_actor ??
    issue.actual_value?.assigned_position ??
    (stagesFact || "—");
  const deviation =
    issue.deviation_value?.minutes ??
    (issue.deviation_value?.mismatch ? "есть" : issue.deviation_value?.label) ??
    "—";

  return (
    <section className="panel" style={{ marginBottom: 16 }}>
      <h2>{issueTitle(issue)}</h2>
      <div className="compare-grid">
        <div className="compare-card">
          <div className="k">Норматив</div>
          <div className="v">{String(normative)}</div>
          <div className="s">по регламенту</div>
        </div>
        <div className="compare-card">
          <div className="k">Факт</div>
          <div className="v">{String(actual)}</div>
          <div className="s">по CRM</div>
        </div>
        <div className="compare-card">
          <div className="k">Отклонение</div>
          <div className="v">{String(deviation)}</div>
          <div className="s">severity: {issue.severity}</div>
        </div>
      </div>
      <div style={{ marginTop: 14 }}>
        <FieldGrid
          items={[
            { label: "Статус", value: <StatusPill value={issue.status} /> },
            { label: "Trust", value: String(issue.trust_index) },
            { label: "ID проблемы", value: issue.id },
            {
              label: "Правило",
              value: String(issue.evidence?.rule_code ?? "—"),
            },
          ]}
        />
      </div>
      {issue.status === "open" && (
        <div className="form-actions" style={{ marginTop: 12 }}>
          <button
            className="btn btn-primary"
            type="button"
            disabled={busy}
            onClick={() => onAction(issue.id, "confirm")}
          >
            Подтвердить
          </button>
          <button
            className="btn"
            type="button"
            disabled={busy}
            onClick={() => onAction(issue.id, "accept")}
          >
            Принять отклонение
          </button>
          <button
            className="btn"
            type="button"
            disabled={busy}
            onClick={() => onAction(issue.id, "request")}
          >
            Запросить данные
          </button>
          <button
            className="btn"
            type="button"
            disabled={busy}
            onClick={() => onAction(issue.id, "reject")}
          >
            Отклонить
          </button>
        </div>
      )}
      {issue.proposed_change && (
        <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
          <strong>Предложение изменения документа</strong>
          <p style={{ marginTop: 6 }}>{String(issue.proposed_change.summary || "")}</p>
          {issue.proposed_change.suggested_text ? (
            <p className="muted-note" style={{ marginTop: 6 }}>
              Черновик: {String(issue.proposed_change.suggested_text)}
            </p>
          ) : null}
          <p className="muted-note" style={{ marginTop: 6 }}>
            Статус правки: {String(issue.proposed_change.status || "proposed")}
            {issue.proposed_change.applied_version_id
              ? ` · version ${issue.proposed_change.applied_version_id}`
              : ""}
          </p>
          {issue.status === "confirmed" && issue.proposed_change.status !== "applied" && (
            <div className="form-actions" style={{ marginTop: 10 }}>
              <button
                className="btn btn-primary"
                type="button"
                disabled={busy}
                onClick={() => onAction(issue.id, "apply")}
              >
                Создать версию документа
              </button>
            </div>
          )}
        </div>
      )}
      {issue.status === "needs_data" && issue.evidence?.data_request ? (
        <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
          <strong>Запрос данных</strong>
          <p style={{ marginTop: 6 }}>
            {String(
              (issue.evidence.data_request as { message?: string }).message ||
                "Нужны дополнительные данные",
            )}
          </p>
        </div>
      ) : null}
    </section>
  );
}

export default function AlignmentPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [knowledgeItems, setKnowledgeItems] = useState<Knowledge[]>([]);
  const [dq, setDq] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [companyId, setCompanyId] = useState<string | null>(null);

  async function reloadAll(issueIds: string[], knowledgeIds: string[]) {
    const loaded = await Promise.all(issueIds.map((id) => fetchAlignmentIssue(id)));
    setIssues(loaded as Issue[]);
    const knowledge = await Promise.all(
      knowledgeIds.filter(Boolean).map((id) => fetchKnowledge(id)),
    );
    setKnowledgeItems(knowledge as Knowledge[]);
    if (companyId) {
      setDq(await fetchQualityIssues(companyId, "open"));
    }
  }

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw
        ? (JSON.parse(raw) as {
            issue_id?: string;
            knowledge_id?: string;
            company_id?: string;
            extras?: Record<string, unknown>;
          })
        : {};
      const cid = demo.company_id || auth?.company_id || "";
      setCompanyId(cid || null);
      if (!cid && !demo.issue_id) {
        setEmpty(true);
        return;
      }
      const extras = demo.extras || {};
      const knowledgeIds = [
        demo.knowledge_id,
        extras.responsible_knowledge_id,
        extras.stage_knowledge_id,
      ]
        .filter(Boolean)
        .map(String);
      try {
        if (cid) {
          const listed = (await fetchAlignmentIssues(cid)) as Issue[];
          if (listed.length) {
            setIssues(listed);
            setDq(await fetchQualityIssues(cid, "open"));
            if (knowledgeIds.length) {
              const knowledge = await Promise.all(knowledgeIds.map((id) => fetchKnowledge(id)));
              setKnowledgeItems(knowledge as Knowledge[]);
            }
            return;
          }
        }
        const issueIds = [
          demo.issue_id,
          extras.responsible_issue_id,
          extras.stage_issue_id,
          extras.needs_data_issue_id,
        ]
          .filter(Boolean)
          .map(String);
        if (!issueIds.length) {
          setEmpty(true);
          return;
        }
        await reloadAll(issueIds, knowledgeIds);
        if (cid) setDq(await fetchQualityIssues(cid, "open"));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить сверку");
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onAction(
    issueId: string,
    action: "confirm" | "reject" | "accept" | "request" | "apply",
  ) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      if (action === "confirm") await confirmAlignmentIssue(issueId);
      else if (action === "reject") await rejectAlignmentIssue(issueId);
      else if (action === "accept") await acceptAlignmentDeviation(issueId);
      else if (action === "apply") await applyAlignmentProposedChange(issueId);
      else await requestAlignmentData(issueId);
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      const extras = (demo.extras as Record<string, unknown>) || {};
      const issueIds = [
        demo.issue_id,
        extras.responsible_issue_id,
        extras.stage_issue_id,
      ]
        .filter(Boolean)
        .map(String);
      const knowledgeIds = [
        demo.knowledge_id,
        extras.responsible_knowledge_id,
        extras.stage_knowledge_id,
      ]
        .filter(Boolean)
        .map(String);
      await reloadAll(issueIds, knowledgeIds);
      const labels = {
        confirm: "Расхождение подтверждено",
        reject: "Расхождение отклонено",
        accept: "Отклонение принято (Sales exception)",
        request: "Запрошены дополнительные данные",
        apply: "Создана новая версия документа по предложению",
      } as const;
      setNote(labels[action]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить действие сверки");
    } finally {
      setBusy(false);
    }
  }

  if (empty) {
    return (
      <main>
        <div className="page-head" style={{ marginBottom: 16 }}>
          <h1>Проблема сверки</h1>
          <p>Sales SLA: срок, ответственный, этапы процесса.</p>
        </div>
        <EmptyDemoHint />
      </main>
    );
  }

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Сверка Sales SLA</h1>
        <p>Срок · ответственный · этапы. Подтверждение, accept deviation, запрос данных.</p>
      </div>
      {error && <p className="error-text">{error}</p>}
      {note && <p className="ok-text">{note}</p>}

      {issues.map((issue) => (
        <IssueCard key={issue.id} issue={issue} busy={busy} onAction={onAction} />
      ))}

      {knowledgeItems.map((knowledge) => (
        <section className="panel" style={{ marginBottom: 16 }} key={knowledge.id}>
          <h2>Запись знаний</h2>
          <p style={{ marginBottom: 12 }}>{knowledge.body}</p>
          <FieldGrid
            items={[
              { label: "Название", value: knowledge.title },
              { label: "Тип", value: knowledge.record_type },
              { label: "Статус", value: <StatusPill value={knowledge.status} /> },
              { label: "Trust", value: String(knowledge.trust_index) },
            ]}
          />
        </section>
      ))}

      <section className="panel">
        <h2>Проблемы качества данных</h2>
        {dq.length === 0 ? (
          <p>Открытых проблем нет</p>
        ) : (
          <div className="list-stack" style={{ marginTop: 10 }}>
            {dq.map((item) => (
              <div className="row" key={String(item.id)}>
                <strong>
                  {String(item.code)} · {String(item.severity)}
                  {item.code === "silent_stage_skip" ? " · silent skip" : ""}
                </strong>
                <span>{String(item.message)}</span>
                {item.code === "silent_stage_skip" ? (
                  <p className="muted-note" style={{ marginTop: 6 }}>
                    Не блокирует анализ. Закройте с причиной на{" "}
                    <a href="/quality">странице качества</a>.
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
