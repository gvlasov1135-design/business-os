#!/usr/bin/env bash
# Live stack smoke: health → readiness → bootstrap (idempotent) → login → demo run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/.env"
  set +a
fi

API_BASE="${API_BASE:-http://localhost:${API_PORT_HOST:-8000}}"
WEB_BASE="${WEB_BASE:-http://localhost:${WEB_PORT:-3000}}"
EMAIL="${SMOKE_EMAIL:-admin@example.com}"
PASSWORD="${SMOKE_PASSWORD:-${BOOTSTRAP_ADMIN_PASSWORD:-demo-admin}}"

echo "==> Smoke against API=$API_BASE WEB=$WEB_BASE"

echo "-- health"
curl -fsS -D - -o /tmp/bos-health.json "$API_BASE/health" | grep -qi 'x-request-id' \
  || { echo "missing X-Request-ID on /health"; exit 1; }
grep -q '"status":"ok"' /tmp/bos-health.json || grep -q '"status": "ok"' /tmp/bos-health.json

echo "-- readiness"
READY=$(curl -fsS "$API_BASE/api/v1/system/readiness")
echo "$READY" | grep -q '"status"'
STATUS=$(echo "$READY" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
if [[ "$STATUS" != "ready" ]]; then
  echo "readiness status=$STATUS (expected ready)"
  echo "$READY"
  exit 1
fi

echo "-- bootstrap (ok if already applied)"
BOOT_CODE=$(curl -sS -o /tmp/bos-boot.json -w "%{http_code}" -X POST "$API_BASE/api/v1/identity/bootstrap")
if [[ "$BOOT_CODE" != "201" && "$BOOT_CODE" != "409" ]]; then
  echo "bootstrap HTTP $BOOT_CODE"
  cat /tmp/bos-boot.json
  exit 1
fi

echo "-- login"
LOGIN=$(curl -fsS -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
COMPANY=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['user']['company_id'])")

echo "-- demo run"
curl -fsS -X POST "$API_BASE/api/v1/demo/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"company_id\":\"$COMPANY\"}" > /tmp/bos-demo.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/bos-demo.json"))
assert d.get("company_id") and d.get("analysis_id") and d.get("decision_id")
ex = d.get("extras") or {}
assert ex.get("silent_stage_skip_warned") is True
assert ex.get("justified_stage_skip_ok") is True
assert ex.get("needs_data_issue_id")
assert ex.get("applied_document_version_id")
assert (ex.get("knowledge_relation_ids") or []) 
assert (ex.get("rule_versions") or {}).get("prompt_executive")
print("demo extras ok")
company = d["company_id"]
analysis = d["analysis_id"]
open("/tmp/bos-demo-ids.env", "w").write(f"COMPANY={company}\nANALYSIS={analysis}\n")
PY

# shellcheck disable=SC1091
source /tmp/bos-demo-ids.env

echo "-- council session"
curl -fsS -X POST "$API_BASE/api/v1/council/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"company_id\":\"$COMPANY\",\"topic\":\"Smoke council\",\"analysis_id\":\"$ANALYSIS\"}" \
  > /tmp/bos-council.json
python3 - <<'PY'
import json
s = json.load(open("/tmp/bos-council.json"))
assert s.get("id") and s.get("status") == "open"
sid = s["id"]
open("/tmp/bos-council-id.txt", "w").write(sid)
print("council session", sid[:8])
PY
SID=$(cat /tmp/bos-council-id.txt)
curl -fsS -X POST "$API_BASE/api/v1/council/sessions/$SID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel":"table","body":"Краткий разбор SLA за столом"}' > /tmp/bos-council-msg.json
python3 - <<'PY'
import json
msgs = json.load(open("/tmp/bos-council-msg.json"))
assert len(msgs) == 4
assert {m["agent"] for m in msgs if m["role"] == "agent"} == {"executive", "sales", "critic"}
print("council table ok")
PY

echo "-- metrics"
curl -fsS "$API_BASE/metrics" | grep -q 'business_os_http_requests_total'

echo "-- web"
curl -fsS -o /dev/null -w "%{http_code}" "$WEB_BASE" | grep -Eq '200|307|308'

echo "OK: smoke passed"
