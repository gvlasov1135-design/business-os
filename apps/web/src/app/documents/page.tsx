"use client";

import { FormEvent, useEffect, useState } from "react";

import { EmptyDemoHint, FieldGrid, QuoteBlock, StatusPill } from "@/components/ui-bits";
import {
  confirmStatement,
  extractDocument,
  extractDocumentAsync,
  fetchDocument,
  fetchStatements,
  rejectStatement,
  uploadDocument,
} from "@/lib/api";
import { getAuthUser } from "@/lib/auth";

const STORAGE_KEY = "business-os-demo";

type Version = {
  id: string;
  version_number: number;
  original_filename: string;
  content_type: string;
  file?: { checksum_sha256?: string; size_bytes?: number };
};

type Statement = {
  id: string;
  statement_type: string;
  value_text: string;
  value_structured?: { amount?: number; unit?: string };
  confidence: number;
  status: string;
  source_anchor?: { quote?: string; page_number?: number; char_start?: number; char_end?: number };
};

export default function DocumentsPage() {
  const [document, setDocument] = useState<Record<string, unknown> | null>(null);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);
  const [companyId, setCompanyId] = useState("");
  const [title, setTitle] = useState("Загруженный регламент");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadNote, setUploadNote] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [appliedVersionId, setAppliedVersionId] = useState<string | null>(null);

  async function loadById(documentId: string) {
    setDocument(await fetchDocument(documentId));
    setStatements((await fetchStatements(documentId)) as Statement[]);
    setEmpty(false);
  }

  useEffect(() => {
    async function load() {
      const auth = getAuthUser();
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const demo = JSON.parse(raw) as {
          document_id?: string;
          company_id?: string;
          extras?: { applied_document_version_id?: string };
        };
        if (demo.company_id) setCompanyId(demo.company_id);
        if (demo.extras?.applied_document_version_id) {
          setAppliedVersionId(String(demo.extras.applied_document_version_id));
        }
        if (demo.document_id) {
          try {
            await loadById(demo.document_id);
            return;
          } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось загрузить документ");
            return;
          }
        }
      }
      if (auth?.company_id) setCompanyId(auth.company_id);
      setEmpty(true);
    }
    load();
  }, []);

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file || !companyId) {
      setError("Нужны ID компании и файл");
      return;
    }
    setUploading(true);
    setError(null);
    setUploadNote(null);
    try {
      const result = await uploadDocument({ companyId, title, file });
      const documentId = String(result.document.id);
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const demo = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ...demo, company_id: companyId, document_id: documentId }),
      );
      await loadById(documentId);
      setUploadNote(
        result.duplicate
          ? `Найден дубликат — показан документ ${result.existing_document_id}`
          : "Документ загружен",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setUploading(false);
    }
  }

  async function onExtract(versionId: string, asyncMode: boolean) {
    if (!document) return;
    setBusyId(versionId);
    setError(null);
    setUploadNote(null);
    try {
      if (asyncMode) {
        const job = await extractDocumentAsync(String(document.id), versionId);
        setUploadNote(`Извлечение в очереди: ${job.job_id}`);
      } else {
        await extractDocument(String(document.id), versionId);
        await loadById(String(document.id));
        setUploadNote("Извлечение завершено");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка извлечения");
    } finally {
      setBusyId(null);
    }
  }

  async function onStatementAction(statementId: string, action: "confirm" | "reject") {
    setBusyId(statementId);
    setError(null);
    try {
      if (action === "confirm") await confirmStatement(statementId);
      else await rejectStatement(statementId);
      if (document) await loadById(String(document.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обработать утверждение");
    } finally {
      setBusyId(null);
    }
  }

  const versions = ((document?.versions as Version[] | undefined) ?? []) as Version[];

  return (
    <main>
      <div className="page-head" style={{ marginBottom: 16 }}>
        <h1>Карточка документа</h1>
        <p>Загрузка, версии, извлечение и проверка утверждений.</p>
      </div>

      <section className="panel" style={{ marginBottom: 16 }}>
        <h2>Загрузка документа</h2>
        <form onSubmit={onUpload} className="stack-form">
          <label>
            ID компании
            <input value={companyId} onChange={(e) => setCompanyId(e.target.value)} required />
          </label>
          <label>
            Название
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Файл
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
          </label>
          <button className="btn btn-primary" type="submit" disabled={uploading}>
            {uploading ? "Загружаю…" : "Загрузить"}
          </button>
        </form>
        {uploadNote && <p className="ok-text">{uploadNote}</p>}
      </section>

      {error && <p className="error-text">{error}</p>}
      {empty && !document && <EmptyDemoHint />}

      {document && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h2>{String(document.title)}</h2>
          <FieldGrid
            items={[
              { label: "Статус", value: <StatusPill value={String(document.status)} /> },
              { label: "ID документа", value: String(document.id) },
              { label: "Версии", value: String(versions.length) },
              { label: "Последний файл", value: versions[0]?.original_filename ?? "—" },
            ]}
          />
        </section>
      )}

      {versions.map((version) => (
        <section className="panel" key={version.id} style={{ marginBottom: 16 }}>
          <h2>
            Версия {version.version_number}: {version.original_filename}
            {appliedVersionId === version.id ? " · из сверки (apply)" : ""}
          </h2>
          {appliedVersionId === version.id && (
            <p className="ok-text" style={{ marginBottom: 10 }}>
              Создана из предложения изменения документа на сверке Sales SLA.
            </p>
          )}
          <FieldGrid
            items={[
              { label: "Тип", value: version.content_type },
              {
                label: "Контрольная сумма",
                value: version.file?.checksum_sha256
                  ? `${version.file.checksum_sha256.slice(0, 16)}…`
                  : "—",
              },
              { label: "Размер", value: `${version.file?.size_bytes ?? 0} байт` },
              { label: "ID версии", value: version.id },
              {
                label: "Источник",
                value: appliedVersionId === version.id ? "alignment apply" : "загрузка / extract",
              },
            ]}
          />
          <div className="form-actions" style={{ marginTop: 12 }}>
            <button
              className="btn btn-primary"
              type="button"
              disabled={busyId === version.id}
              onClick={() => onExtract(version.id, false)}
            >
              Извлечь сейчас
            </button>
            <button
              className="btn"
              type="button"
              disabled={busyId === version.id}
              onClick={() => onExtract(version.id, true)}
            >
              В очередь
            </button>
          </div>
        </section>
      ))}

      {statements.map((statement) => (
        <section className="panel" key={statement.id} style={{ marginBottom: 16 }}>
          <h2>Утверждение · {statement.statement_type}</h2>
          <QuoteBlock text={statement.source_anchor?.quote || statement.value_text} />
          <div style={{ marginTop: 12 }}>
            <FieldGrid
              items={[
                { label: "Статус", value: <StatusPill value={statement.status} /> },
                {
                  label: "Значение",
                  value: statement.value_structured
                    ? `${statement.value_structured.amount ?? ""} ${statement.value_structured.unit ?? ""}`.trim() ||
                      statement.value_text
                    : statement.value_text,
                },
                { label: "Уверенность", value: `${Math.round(statement.confidence * 100)}%` },
                {
                  label: "Якорь",
                  value: `стр. ${statement.source_anchor?.page_number ?? "—"} · символы ${
                    statement.source_anchor?.char_start ?? "—"
                  }–${statement.source_anchor?.char_end ?? "—"}`,
                },
              ]}
            />
          </div>
          {statement.status === "proposed" && (
            <div className="form-actions" style={{ marginTop: 12 }}>
              <button
                className="btn btn-primary"
                type="button"
                disabled={busyId === statement.id}
                onClick={() => onStatementAction(statement.id, "confirm")}
              >
                Подтвердить
              </button>
              <button
                className="btn"
                type="button"
                disabled={busyId === statement.id}
                onClick={() => onStatementAction(statement.id, "reject")}
              >
                Отклонить
              </button>
            </div>
          )}
        </section>
      ))}
    </main>
  );
}
