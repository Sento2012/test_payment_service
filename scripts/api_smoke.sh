#!/usr/bin/env bash
# Смоук-тест API: позитив (создание → идемпотентность → ожидание обработки) и
# негатив (auth, обязательные заголовки, валидация, 404). Требует запущенный сервис.
#
# Использование:
#   ./scripts/api_smoke.sh
#   BASE_URL=http://api.payments.localhost:8088 API_KEY=secret-api-key ./scripts/api_smoke.sh
#   WEBHOOK_URL=https://webhook.site/<uuid> ./scripts/api_smoke.sh   # чтобы реально получить хук
set -uo pipefail

BASE_URL="${BASE_URL:-http://api.payments.localhost:8088}"
API_KEY="${API_KEY:-secret-api-key}"
WEBHOOK_URL="${WEBHOOK_URL:-https://example.com/hook}"
PAYMENTS="$BASE_URL/api/v1/payments"

pass=0; fail=0
ok()  { echo "  ✓ $1"; pass=$((pass + 1)); }
bad() { echo "  ✗ $1"; fail=$((fail + 1)); }
field() { python3 -c "import sys,json;print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "API: $BASE_URL"

# 1. создание платежа → 202
key="smoke-$(date +%s)"
created=$(curl -s -X POST "$PAYMENTS" \
  -H "X-API-Key: $API_KEY" -H "Idempotency-Key: $key" -H "Content-Type: application/json" \
  -d "{\"amount\":\"100.00\",\"currency\":\"USD\",\"metadata\":{\"smoke\":true},\"webhook_url\":\"$WEBHOOK_URL\"}")
pid=$(printf '%s' "$created" | field payment_id)
if [ -n "$pid" ]; then ok "создание платежа → 202 (payment_id=$pid)"; else bad "создание не удалось: $created"; fi

# 2. идемпотентность: тот же Idempotency-Key → тот же платёж
if [ -n "$pid" ]; then
  pid2=$(curl -s -X POST "$PAYMENTS" \
    -H "X-API-Key: $API_KEY" -H "Idempotency-Key: $key" -H "Content-Type: application/json" \
    -d "{\"amount\":\"100.00\",\"currency\":\"USD\",\"webhook_url\":\"$WEBHOOK_URL\"}" | field payment_id)
  [ "$pid" = "$pid2" ] && ok "идемпотентность: тот же payment_id" || bad "идемпотентность: $pid ≠ $pid2"
fi

# 3. ожидание обработки (2–5с): статус становится succeeded/failed
if [ -n "$pid" ]; then
  final=""
  for _ in $(seq 1 15); do
    st=$(curl -s "$PAYMENTS/$pid" -H "X-API-Key: $API_KEY" | field status)
    if [ "$st" = "succeeded" ] || [ "$st" = "failed" ]; then final="$st"; break; fi
    sleep 2
  done
  [ -n "$final" ] && ok "обработка завершена → status=$final" || bad "статус не финализировался (всё ещё pending)"
fi

# 4. без X-API-Key → 401
c=$(code -X POST "$PAYMENTS" -H "Idempotency-Key: k" -H "Content-Type: application/json" -d '{"amount":"1.00","currency":"USD"}')
[ "$c" = "401" ] && ok "без X-API-Key → 401" || bad "без X-API-Key → $c (ждали 401)"

# 5. без Idempotency-Key → 422
c=$(code -X POST "$PAYMENTS" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"amount":"1.00","currency":"USD"}')
[ "$c" = "422" ] && ok "без Idempotency-Key → 422" || bad "без Idempotency-Key → $c (ждали 422)"

# 6. невалидная сумма → 422
c=$(code -X POST "$PAYMENTS" -H "X-API-Key: $API_KEY" -H "Idempotency-Key: bad-$(date +%s)" -H "Content-Type: application/json" -d '{"amount":"0","currency":"USD"}')
[ "$c" = "422" ] && ok "amount=0 → 422" || bad "amount=0 → $c (ждали 422)"

# 7. неизвестный платёж → 404
c=$(code "$PAYMENTS/00000000-0000-0000-0000-000000000000" -H "X-API-Key: $API_KEY")
[ "$c" = "404" ] && ok "неизвестный платёж → 404" || bad "неизвестный платёж → $c (ждали 404)"

echo
echo "итог: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
