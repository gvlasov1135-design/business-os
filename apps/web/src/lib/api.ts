import { authHeaders, clearAuthSession, setAuthSession, type AuthUser } from "./auth";
import type { HealthResponse, ReadinessResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(authHeaders(init?.headers));
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthSession();
    }
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { error?: { message?: string; code?: string } };
      if (body.error?.message) detail = body.error.message;
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  const response = await fetch(`${API_URL}/api/v1/system/readiness`, {
    cache: "no-store",
  });
  const data = (await response.json()) as ReadinessResponse;
  if (!response.ok && response.status !== 200 && response.status !== 503) {
    throw new Error(data.status ?? `Readiness failed: ${response.status}`);
  }
  return data;
}

export async function login(email: string, password: string, companyId?: string) {
  const data = await fetchJson<{ access_token: string; user: AuthUser }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      ...(companyId ? { company_id: companyId } : {}),
    }),
  });
  setAuthSession(data.access_token, data.user);
  return data;
}

export async function fetchMe() {
  return fetchJson<AuthUser>("/api/v1/auth/me");
}

export async function bootstrapIdentity() {
  return fetchJson<{
    company: { id: string; name: string };
    user: { id: string; email: string; full_name: string };
  }>("/api/v1/identity/bootstrap", { method: "POST", body: "{}" });
}

export async function runDemo(companyId?: string) {
  return fetchJson<Record<string, unknown>>("/api/v1/demo/run", {
    method: "POST",
    body: JSON.stringify(companyId ? { company_id: companyId } : {}),
  });
}

export async function uploadDocument(params: {
  companyId: string;
  title?: string;
  file: File;
}) {
  const form = new FormData();
  form.append("company_id", params.companyId);
  if (params.title) form.append("title", params.title);
  form.append("file", params.file);
  return fetchJson<{
    document: Record<string, unknown>;
    duplicate: boolean;
    existing_document_id?: string | null;
  }>("/api/v1/documents", {
    method: "POST",
    body: form,
  });
}

export async function recordDecisionResult(
  decisionId: string,
  payload: { actual_result: string; checked_at: string; comment?: string },
) {
  return fetchJson<Record<string, unknown>>(`/api/v1/decisions/${decisionId}/result`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function reviewDecisionResult(
  decisionId: string,
  payload: { review_notes: string; lesson_body?: string; lesson_category?: string },
) {
  return fetchJson<Record<string, unknown>>(`/api/v1/decisions/${decisionId}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createDecisionTask(
  decisionId: string,
  payload: { title: string; assignee_name: string; due_at?: string },
) {
  return fetchJson<Record<string, unknown>>(`/api/v1/decisions/${decisionId}/tasks`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDecisionTask(taskId: string, status: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/decisions/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function createSource(payload: {
  company_id: string;
  code: string;
  name: string;
  source_type: string;
  freshness_hours?: number;
}) {
  return fetchJson<Record<string, unknown>>("/api/v1/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function importRecord(sourceId: string, payload: Record<string, unknown>) {
  return fetchJson<{
    raw_record: Record<string, unknown>;
    fact: Record<string, unknown> | null;
    duplicate: boolean;
    blocked: boolean;
    issues: Record<string, unknown>[];
  }>("/api/v1/ingestion/import", {
    method: "POST",
    body: JSON.stringify({ source_id: sourceId, payload }),
  });
}

export async function fetchFact(factId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/facts/${factId}`);
}

export async function fetchRawRecord(rawRecordId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/raw-records/${rawRecordId}`);
}

export async function fetchAuditEvents(companyId?: string, limit = 50) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (companyId) query.set("company_id", companyId);
  return fetchJson<Record<string, unknown>[]>(`/api/v1/audit/events?${query.toString()}`);
}

export async function confirmStatement(statementId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/statements/${statementId}/confirm`, {
    method: "POST",
    body: "{}",
  });
}

export async function rejectStatement(statementId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/statements/${statementId}/reject`, {
    method: "POST",
    body: "{}",
  });
}

export async function confirmAlignmentIssue(issueId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/alignment/issues/${issueId}/confirm`, {
    method: "POST",
    body: "{}",
  });
}

export async function rejectAlignmentIssue(issueId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/alignment/issues/${issueId}/reject`, {
    method: "POST",
    body: "{}",
  });
}

export async function acceptAlignmentDeviation(issueId: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/alignment/issues/${issueId}/accept-deviation`,
    { method: "POST", body: "{}" },
  );
}

export async function requestAlignmentData(issueId: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/alignment/issues/${issueId}/request-data`,
    { method: "POST", body: "{}" },
  );
}

export async function applyAlignmentProposedChange(issueId: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/alignment/issues/${issueId}/apply-proposed-change`,
    { method: "POST", body: "{}" },
  );
}

export async function createAnalysis(companyId: string, question: string) {
  return fetchJson<Record<string, unknown>>("/api/v1/analyses", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId, question }),
  });
}

export async function createDecision(payload: {
  company_id: string;
  analysis_id?: string;
  recommendation_id?: string;
  status: string;
  rationale: string;
  owner_name: string;
  checkpoint_at?: string;
  expected_result: string;
}) {
  return fetchJson<Record<string, unknown>>("/api/v1/decisions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function extractDocument(documentId: string, versionId: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/documents/${documentId}/versions/${versionId}/extract`,
    { method: "POST", body: "{}" },
  );
}

export async function extractDocumentAsync(documentId: string, versionId: string) {
  return fetchJson<{ job_id: string; type: string }>(
    `/api/v1/documents/${documentId}/versions/${versionId}/extract-async`,
    { method: "POST", body: "{}" },
  );
}

export async function importCsv(sourceId: string, file: File) {
  const form = new FormData();
  form.append("source_id", sourceId);
  form.append("file", file);
  return fetchJson<Record<string, unknown>[]>("/api/v1/ingestion/import-csv", {
    method: "POST",
    body: form,
  });
}

export async function fetchDocument(documentId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/documents/${documentId}`);
}

export async function fetchStatements(documentId: string) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/documents/${documentId}/statements`);
}

export async function fetchAlignmentIssue(issueId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/alignment/issues/${issueId}`);
}

export async function fetchAlignmentIssues(companyId: string, status?: string) {
  const q = new URLSearchParams({ company_id: companyId });
  if (status) q.set("status", status);
  return fetchJson<Record<string, unknown>[]>(`/api/v1/alignment/issues?${q}`);
}

export async function fetchKnowledge(knowledgeId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/knowledge/${knowledgeId}`);
}

export async function fetchAnalysis(analysisId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/analyses/${analysisId}`);
}

export async function fetchDecision(decisionId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/decisions/${decisionId}`);
}

export async function fetchQualityIssues(companyId: string, status?: string) {
  const q = new URLSearchParams({ company_id: companyId });
  if (status) q.set("status", status);
  return fetchJson<Record<string, unknown>[]>(`/api/v1/data-quality/issues?${q}`);
}

export async function fetchQualityGate(companyId: string) {
  return fetchJson<{ blocked: boolean; reasons: string[] }>(
    `/api/v1/data-quality/gate?company_id=${companyId}`,
  );
}

export async function explainQualityIssue(issueId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/data-quality/issues/${issueId}/explain`, {
    method: "POST",
    body: "{}",
  });
}

export async function resolveQualityIssue(issueId: string, reason: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/data-quality/issues/${issueId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function searchKnowledge(companyId: string, query: string) {
  const params = new URLSearchParams({ company_id: companyId, q: query });
  return fetchJson<{ query: string; results: Record<string, unknown>[] }>(
    `/api/v1/knowledge/search?${params.toString()}`,
  );
}

export async function fetchKnowledgeList(companyId: string) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/knowledge?company_id=${companyId}`);
}

export async function fetchKnowledgeRelations(companyId: string, recordId?: string) {
  const q = new URLSearchParams({ company_id: companyId });
  if (recordId) q.set("record_id", recordId);
  return fetchJson<Record<string, unknown>[]>(`/api/v1/knowledge/relations?${q}`);
}

export async function fetchResolutionEntities(companyId: string) {
  return fetchJson<Record<string, unknown>[]>(
    `/api/v1/resolution/entities?company_id=${companyId}`,
  );
}

export async function fetchResolutionCandidates(companyId: string, status = "pending") {
  const params = new URLSearchParams({ company_id: companyId, status });
  return fetchJson<Record<string, unknown>[]>(
    `/api/v1/resolution/candidates?${params.toString()}`,
  );
}

export async function confirmResolutionCandidate(candidateId: string, note?: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/resolution/candidates/${candidateId}/confirm`,
    { method: "POST", body: JSON.stringify({ note: note ?? null }) },
  );
}

export async function rejectResolutionCandidate(candidateId: string, note?: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/resolution/candidates/${candidateId}/reject`,
    { method: "POST", body: JSON.stringify({ note: note ?? null }) },
  );
}

export async function fetchResolutionMemberships(entityId: string) {
  return fetchJson<Record<string, unknown>[]>(
    `/api/v1/resolution/entities/${entityId}/memberships`,
  );
}

export async function splitResolutionMembership(membershipId: string, note?: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/resolution/memberships/${membershipId}/split`,
    { method: "POST", body: JSON.stringify({ note: note ?? null }) },
  );
}

export async function fetchResolutionMerges(companyId: string) {
  return fetchJson<Record<string, unknown>[]>(
    `/api/v1/resolution/merges?company_id=${companyId}`,
  );
}

export async function fetchKpis(companyId: string) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/kpis?company_id=${companyId}`);
}

export async function fetchKpiVersions(kpiId: string) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/kpis/${kpiId}/versions`);
}

export async function fetchKpiSnapshots(kpiId: string) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/kpis/${kpiId}/snapshots`);
}

export async function recalculateKpi(
  kpiId: string,
  periodStart: string,
  periodEnd: string,
) {
  return fetchJson<Record<string, unknown>>(`/api/v1/kpis/${kpiId}/recalculate`, {
    method: "POST",
    body: JSON.stringify({ period_start: periodStart, period_end: periodEnd }),
  });
}

export async function createKpiVersion(
  kpiId: string,
  payload: {
    formula: Record<string, unknown>;
    source_mapping?: Record<string, unknown>;
    target_value?: number;
    change_reason?: string;
  },
) {
  return fetchJson<Record<string, unknown>>(`/api/v1/kpis/${kpiId}/versions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchExecutiveReadiness(companyId: string) {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/executive/readiness?company_id=${companyId}`,
  );
}

export async function fetchOutboxEvents(companyId: string, status = "pending") {
  const params = new URLSearchParams({ company_id: companyId, status });
  return fetchJson<Record<string, unknown>[]>(`/api/v1/outbox/events?${params.toString()}`);
}

export async function publishOutboxEvent(eventId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/outbox/events/${eventId}/publish`, {
    method: "POST",
    body: "{}",
  });
}

export async function fetchDecisions(companyId: string) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/decisions?company_id=${companyId}`);
}

export async function createCouncilSession(payload: {
  company_id: string;
  topic?: string;
  analysis_id?: string;
}) {
  return fetchJson<Record<string, unknown>>("/api/v1/council/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchCouncilSession(sessionId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/council/sessions/${sessionId}`);
}

export async function fetchCouncilSessions(companyId: string) {
  return fetchJson<Record<string, unknown>[]>(
    `/api/v1/council/sessions?company_id=${companyId}`,
  );
}

export async function postCouncilMessage(
  sessionId: string,
  payload: { channel: "table" | "private"; body: string; agent?: string },
) {
  return fetchJson<Record<string, unknown>[]>(`/api/v1/council/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function closeCouncilSession(sessionId: string) {
  return fetchJson<Record<string, unknown>>(`/api/v1/council/sessions/${sessionId}/close`, {
    method: "POST",
    body: "{}",
  });
}

export async function importWorkbook(companyId: string, file: File) {
  const form = new FormData();
  form.append("company_id", companyId);
  form.append("file", file);
  return fetchJson<Record<string, unknown>>("/api/v1/ingestion/import-workbook", {
    method: "POST",
    body: form,
  });
}

export async function runBistroPilot(payload: {
  file: File;
  companyId?: string;
  companyName?: string;
  question?: string;
}) {
  return runReportingUpload(payload);
}

export async function runReportingUpload(payload: {
  file: File;
  companyId?: string;
  companyName?: string;
  question?: string;
}) {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.companyId) form.append("company_id", payload.companyId);
  if (payload.companyName) form.append("company_name", payload.companyName);
  if (payload.question) form.append("question", payload.question);
  return fetchJson<Record<string, unknown>>("/api/v1/pilot/reports/run", {
    method: "POST",
    body: form,
  });
}

export function getApiUrl(): string {
  return API_URL;
}
