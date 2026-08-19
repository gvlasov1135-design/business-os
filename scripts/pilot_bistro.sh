#!/usr/bin/env bash
# Import Бистро workbook and run first analysis against live API.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT/.env"
  set +a
fi

API_BASE="${API_BASE:-http://localhost:${API_PORT_HOST:-8010}}"
EMAIL="${SMOKE_EMAIL:-admin@example.com}"
PASSWORD="${SMOKE_PASSWORD:-${BOOTSTRAP_ADMIN_PASSWORD:-demo-admin}}"
FILE="${1:-$ROOT/data/pilot/bistro_2026.xlsx}"

if [[ ! -f "$FILE" ]]; then
  echo "Workbook not found: $FILE"
  echo "Copy «Бистро 2026.xlsx» to data/pilot/bistro_2026.xlsx"
  exit 1
fi

echo "==> Pilot bistro against $API_BASE"
echo "    file: $FILE"

curl -fsS -X POST "$API_BASE/api/v1/identity/bootstrap" -o /tmp/bos-boot.json || true

LOGIN=$(curl -fsS -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -fsS -X POST "$API_BASE/api/v1/pilot/reports/run" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@${FILE};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  > /tmp/bos-bistro-pilot.json

python3 - <<'PY'
import json
d = json.load(open("/tmp/bos-bistro-pilot.json"))
assert d.get("company_id") and d.get("analysis_id")
imp = d.get("import") or {}
conc = d.get("conclusions") or {}
print("company:", d["company_id"])
print("analysis:", d["analysis_id"], "blocked=", d.get("analysis_blocked"))
print("facts:", imp.get("fact_count"), "by_origin:", imp.get("by_origin"))
print("summary:", (conc.get("summary") or "")[:160])
print("meanings:", len(conc.get("meanings") or []), "risks:", len(conc.get("risks") or []))
print("OK: open http://localhost:3010/reports")
PY
