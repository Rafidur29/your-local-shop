#!/usr/bin/env bash
set -euo pipefail

# Usage: ./demo.sh   (assumes uvicorn run or use docker-compose up)
# This script will:
#  - run a set of curl smoke checks (idempotency, decline path, returns, cart)

APP_URL="http://127.0.0.1:8000"
echo "Ensure your app is running at $APP_URL (press Ctrl+C to stop demo at any time)"

# Quick health check
echo "Health check: GET /api/products"
curl -sS "$APP_URL/api/products" > /dev/null || { echo "Failed to reach app at $APP_URL"; exit 1; }
echo -e "\n"

echo "1) Create order (idempotency test)"
curl -i -H "Content-Type: application/json" -H "Idempotency-Key: idem-123" \
  -d '{"customer_id":null,"items":[{"sku":"T1","qty":2}],"payment_method":{"token":"test","force_decline":false}}' \
  "$APP_URL/api/orders"
echo -e "\n\nRepeat with same Idempotency-Key (should be same orderId)"
curl -i -H "Content-Type: application/json" -H "Idempotency-Key: idem-123" \
  -d '{"customer_id":null,"items":[{"sku":"T1","qty":2}],"payment_method":{"token":"test","force_decline":false}}' \
  "$APP_URL/api/orders"
echo -e "\n\n2) Payment decline path (expect 400)"
curl -i -H "Content-Type: application/json" -H "Idempotency-Key: idem-decline-1" \
  -d '{"customer_id":null,"items":[{"sku":"T2","qty":1}],"payment_method":{"token":"test","force_decline":true}}' \
  "$APP_URL/api/orders"
echo -e "\n\n3) Create return and receive it (idempotent)"
R=$(curl -sS -H "Content-Type: application/json" -d '{"order_id":1,"lines":[{"sku":"RET1","qty":1}]}' "$APP_URL/api/returns")
echo "create return response: $R"
RMA_ID=$(echo "$R" | python -c "import sys,json;print(json.load(sys.stdin).get('rma_id'))")
echo "RMA_ID=$RMA_ID"
curl -i -H "Idempotency-Key: rma-key-1" -X POST "$APP_URL/api/returns/${RMA_ID}/receive"
curl -i -H "Idempotency-Key: rma-key-1" -X POST "$APP_URL/api/returns/${RMA_ID}/receive"
echo -e "\n\n4) Cart add item smoke test"
curl -i -H "Content-Type: application/json" -d '{"sku":"TEST-001","qty":2}' "$APP_URL/api/cart/items"
echo -e "\n\nSmoke tests complete."
