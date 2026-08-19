# MVP Architecture Freeze + Pilot Runbook

**Status:** Ordered backlog 1→2→3 done; follow-on pilot loop closed (2026-08-09):
provenance UI + DQ resolve/`needs_data` + knowledge relations.

## Opened (in order) — completed

1. **Pilot UX** — login/demo/alignment/executive/decisions path polish
2. **P1 AI** — versioned prompts + Decision DNA rules + Gateway redaction
3. **Sales deepen** — job description normative doc + DQ `silent_stage_skip`

## Follow-on (pilot loop) — completed

- UI: `rule_versions` on analysis; `silent_stage_skip` callouts on quality/alignment/demo
- DQ: `POST /data-quality/issues/{id}/resolve` with reason (non-blocking only)
- Demo: justified skip + `needs_data` issue; analysis soft-surfaces pending data requests
- Knowledge relations wired in demo + knowledge UI; documents mark applied version

## Opened: Sales SLA deepen

In scope for fork 3 (extend alignment / demo / extraction / UI — no new modules):

- Deadline severity from rule `severity_bands`
- Responsible check → **accept deviation** → KnowledgeRecord
- Process stages extract + alignment (skipped stages)
- KPI statement in policy + **share_within_target** % KPI
- Alignment UI: confirm / accept deviation / request data for all SLA issues
- Context Builder exposes `accepted_deviations` to Sales/Executive agents
- **Document-change proposal** on confirm (evidence.proposed_change)
- **Apply proposed change** → new document version (`POST …/apply-proposed-change`)
- Executive readiness: `sla_axes` + typed evidence

## Pilot path (UI)

1. http://localhost:3010/login — bootstrap + `demo-admin`
2. `/demo` — полный Sales SLA
3. `/alignment` — confirm / accept / apply правки + needs_data
4. `/quality` — silent skip resolve
5. `/executive` — готовность и решение
6. `/analysis` · `/documents` · `/knowledge` · `/decisions` · `/kpi`

## Opened forks (in order)

1. Pilot UX polish (this checklist)
2. P1 AI: versioned prompts / Decision DNA + Gateway redaction
3. Sales deepen: second normative doc + DQ silent-skip stages

```bash
cp .env.example .env   # or keep existing .env
# set AUTH_SECRET, WORKER_SECRET (non-default), AUTH_REQUIRED=true, PILOT_MODE=true
# RATE_LIMIT_PER_MINUTE=30, CORS_ORIGINS=http://localhost:3010
docker compose up --build -d
make smoke
```

URLs (this machine often remaps ports):

| Service | URL |
|---------|-----|
| Web | http://localhost:3010 |
| API | http://localhost:8010 |
| Readiness | http://localhost:8010/api/v1/system/readiness |
| Metrics | http://localhost:8010/metrics |
| Docs | http://localhost:8010/docs (disable with `DOCS_ENABLED=false`) |

Bootstrap login: `admin@example.com` / `$BOOTSTRAP_ADMIN_PASSWORD` (default `demo-admin`).

## Smoke

`make smoke` runs health (+ `X-Request-ID`) → readiness → bootstrap → login → demo → web.

CI also runs compose smoke on push/PR.

## After pilot

Re-open architecture only with an explicit choice of fork 2 or 3 (or a new scoped ticket).
