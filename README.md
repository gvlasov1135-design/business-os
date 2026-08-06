# Business OS — FOUNDATION 1

Technical foundation: FastAPI API, Next.js status page, PostgreSQL, Redis, MinIO.

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

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |

## API endpoints

- `GET /health` — liveness
- `GET /api/v1/system/readiness` — checks PostgreSQL, Redis, MinIO

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
| `make logs` | Follow container logs |

## Foundation 1 scope

Included: Docker Compose stack, health/readiness endpoints, system status UI.

Not included: auth, RBAC, worker, audit, SQLAlchemy, Alembic, business entities.
