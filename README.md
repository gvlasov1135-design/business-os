# Business OS — Вертикальный срез

Документ → факт CRM → Сверка → Знание → AI-рекомендация → Решение.

Стек: FastAPI, Next.js, PostgreSQL, Redis, MinIO.

## Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local backend tests)
- Node.js 22+ (for local frontend lint/typecheck)

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Or with Make:

```bash
make up
```

## URLs

Default ports in `.env.example` are 3000/8000. Local `.env` may remap to **3010/8010** if host ports are busy.

| Service | URL |
|---------|-----|
| Web | http://localhost:3010 (or `:3000`) |
| API | http://localhost:8010 (or `:8000`) |
| API docs | http://localhost:8010/docs |
| MinIO console | http://localhost:9001 |

## Auth

With `AUTH_REQUIRED=true`:

1. `POST /api/v1/identity/bootstrap` → creates `admin@example.com` (password from `BOOTSTRAP_ADMIN_PASSWORD`, default `demo-admin`)
2. `POST /api/v1/auth/login` → bearer token
3. Send `Authorization: Bearer <token>` on write endpoints

Worker jobs use `X-Worker-Key: $WORKER_SECRET`.

## Pilot checklist (shared / local hardening)

Architecture is **frozen** for MVP pilot — see [`docs/active/MVP_FREEZE.md`](docs/active/MVP_FREEZE.md).

Before sharing the stack:

1. Copy `.env.example` → `.env` and set strong `AUTH_SECRET`, `WORKER_SECRET`, `BOOTSTRAP_ADMIN_PASSWORD`
2. Set `AUTH_REQUIRED=true`, `PILOT_MODE=true` (refuses default secrets), `RATE_LIMIT_PER_MINUTE=30`, `DOCS_ENABLED=false` if not needed
3. Set `CORS_ORIGINS` to your web origin(s) only (no `*`)
4. Optionally `BOOTSTRAP_ENABLED=false` after the first admin exists
5. `docker compose up --build -d` then `make smoke`

Smoke covers: `/health` (+ `X-Request-ID`), readiness, `/metrics`, bootstrap, login, demo run, web.

| Command | Description |
|---------|-------------|
| `make smoke` | Live compose smoke (`scripts/smoke.sh`) |
## API endpoints

- `GET /health` — liveness
- `GET /api/v1/system/readiness` — checks PostgreSQL, Redis, MinIO
- `POST /api/v1/auth/login` / `GET /api/v1/auth/me`
- `POST /api/v1/identity/bootstrap` — seed demo company/user/role/department
- `GET|POST /api/v1/companies`
- `GET|POST /api/v1/roles`
- `GET|POST /api/v1/departments`
- `GET|POST /api/v1/users`
- `GET /api/v1/audit/events` — audit trail
- `POST /api/v1/documents` — upload PDF/DOCX/XLSX (checksum + duplicate detection)
- `GET /api/v1/documents`
- `GET /api/v1/documents/{id}`
- `POST /api/v1/documents/{id}/versions`
- `GET /api/v1/documents/{id}/versions/{version_id}/file`
- `POST /api/v1/documents/{id}/versions/{version_id}/extract` — mock extraction
- `POST /api/v1/documents/{id}/versions/{version_id}/extract-async` — enqueue Redis job
- `GET /api/v1/documents/{id}/versions/{version_id}/fragments`
- `GET /api/v1/documents/{id}/statements`
- `POST /api/v1/documents/{id}/versions/{version_id}/statements` — manual statement
- `POST /api/v1/statements/{id}/confirm`
- `POST /api/v1/statements/{id}/reject`
- `POST /api/v1/sources` — register CRM/CSV/API source
- `GET /api/v1/sources`
- `POST /api/v1/ingestion/import` — import raw CRM payload → ObservedFact
- `POST /api/v1/ingestion/import-csv` — CSV file → rows → ObservedFact
- `GET /api/v1/raw-records/{id}`
- `GET /api/v1/facts`
- `GET /api/v1/facts/{id}`
- `GET /api/v1/data-quality/issues`
- `GET /api/v1/data-quality/gate` — analysis blocked if open DQ issues
- `POST /api/v1/alignment/checks` — compare confirmed deadline vs observed fact
- `GET /api/v1/alignment/issues/{id}`
- `GET /api/v1/alignment/issues?company_id=` — список проблем сверки
- `POST /api/v1/alignment/issues/{id}/confirm|reject|accept-deviation|request-data|apply-proposed-change`
- `GET /api/v1/knowledge` / `GET /api/v1/knowledge/{id}` — human-confirmed knowledge only
- `POST /api/v1/analyses` — mock AI analysis (blocked by DQ gate / missing data)
- `GET /api/v1/analyses/{id}`
- `POST /api/v1/decisions` / `GET /api/v1/decisions/{id}`
- `POST /api/v1/decisions/{id}/result` — record checkpoint outcome
- `POST /api/v1/demo/run` — full vertical-slice scenario for a company

## Database migrations

Alembic migrations `0001`–`0007` cover identity, documents, intelligence, ingestion/quality, alignment/knowledge/analysis/decisions, and user passwords.

Run manually:

```bash
make migrate
```

## Development commands

All commands use Docker (no local Python/Node required):

```bash
make test       # backend smoke tests
make lint       # frontend ESLint
make typecheck  # frontend TypeScript
make check      # test + lint + typecheck
```

### Local alternative (without Docker for tests)

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=src python -m pytest tests/ -v
```

On Windows PowerShell:

```powershell
cd apps/api
pip install -r requirements.txt
$env:PYTHONPATH="src"; python -m pytest tests/ -v
```

### Frontend lint and typecheck (local)

```bash
cd apps/web
npm install
npm run lint
npm run typecheck
```

### Make targets

| Command | Description |
|---------|-------------|
| `make up` | Build and start all services |
| `make down` | Stop services |
| `make test` | Run backend smoke tests (Docker) |
| `make lint` | Run frontend ESLint (Docker) |
| `make typecheck` | Run frontend TypeScript check (Docker) |
| `make check` | Run test + lint + typecheck |
| `make smoke` | Live stack smoke (health → login → demo) |
| `make logs` | Follow container logs |

## Foundation / vertical slice scope

Included:

- Docker Compose stack (Postgres, Redis, MinIO, API, Web, Worker stub)
- Identity (Company/User/Role/Department) + AuditEvent
- Documents (upload, versions, checksum, duplicates)
- Document Intelligence (fragments, extracted statements, confirm/reject)
- Ingestion (Source, RawRecord, ObservedFact) + Data Quality quarantine gate
- Reality Alignment + Knowledge (only after human confirm)
- Mock AI analysis with structured schema validation
- Decisions + result control
- `POST /api/v1/demo/run` end-to-end scenario
- Minimal UI screens for the slice
- CI workflow (API tests + web lint/typecheck)

Not included yet: real auth/SSO, real LLM providers, production connectors, full RBAC UI.
