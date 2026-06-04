#!/usr/bin/env bash
# Build, start, smoke-test, and tear down the Dockerized app.
# The container is always stopped on exit, even if a test fails.
#
# Usage:
#   ./scripts/test-docker.sh           # run all checks (incl. live AI call)
#   RUN_AI_TEST=0 ./scripts/test-docker.sh   # skip the AI connectivity check
set -euo pipefail

cd "$(dirname "$0")/.."

BASE_URL="http://127.0.0.1:8000"
RUN_AI_TEST="${RUN_AI_TEST:-1}"

cleanup() {
  echo "Stopping app..."
  docker compose down >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

echo "Building and starting app..."
docker compose up --build -d

echo "Waiting for server to be ready..."
for i in $(seq 1 60); do
  if curl -sf "$BASE_URL/api/health" >/dev/null 2>&1; then
    break
  fi
  [ "$i" -eq 60 ] && fail "server did not become healthy within 60s"
  sleep 1
done

echo "Checking /api/health..."
curl -sf "$BASE_URL/api/health" | grep -q '"status":"ok"' || fail "health check"

echo "Checking / (frontend)..."
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/")
[ "$code" = "200" ] || fail "frontend returned HTTP $code"

echo "Checking unauthenticated /api/board is rejected..."
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/board")
[ "$code" = "401" ] || fail "expected 401 for unauthenticated board, got HTTP $code"

echo "Logging in..."
TOKEN=$(curl -sf -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"password"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])") || fail "login"
[ -n "$TOKEN" ] || fail "login returned empty token"
AUTH="Authorization: Bearer $TOKEN"

echo "Checking /api/board..."
curl -sf -H "$AUTH" "$BASE_URL/api/board" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['version'] >= 1, 'version'
assert len(d['board']['columns']) == 5, 'expected 5 columns'
assert len(d['board']['cards']) == 10, 'expected 10 cards'
" || fail "board contents"

echo "Checking /api/auth/register (new account) and its token..."
REG_TOKEN=$(curl -sf -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"smoketest","password":"smoketestpw"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])") || fail "register"
[ -n "$REG_TOKEN" ] || fail "register returned empty token"
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $REG_TOKEN" "$BASE_URL/api/board")
[ "$code" = "200" ] || fail "registered token did not authorize board (HTTP $code)"

echo "Checking duplicate registration is rejected..."
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"smoketest","password":"smoketestpw"}')
[ "$code" = "409" ] || fail "expected 409 for duplicate username, got HTTP $code"

if [ "$RUN_AI_TEST" = "1" ]; then
  echo "Checking /api/ai/connectivity (live OpenAI call)..."
  resp=$(curl -s -X POST -H "$AUTH" "$BASE_URL/api/ai/connectivity")
  echo "$resp" | grep -q '"is_correct":true' || fail "AI connectivity: $resp"
fi

echo "All Docker smoke tests passed."
