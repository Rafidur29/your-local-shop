import json
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "dev.db"
KEY = sys.argv[2] if len(sys.argv) > 2 else None
SKU = sys.argv[3] if len(sys.argv) > 3 else None

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== Idempotency Records ===")
if KEY:
    cur.execute(
        "SELECT id, key, status, response_body, last_error, created_at, updated_at FROM idempotency_records WHERE key=?",
        (KEY,),
    )
else:
    cur.execute(
        "SELECT id, key, status, response_body, last_error, created_at, updated_at FROM idempotency_records ORDER BY created_at DESC LIMIT 20"
    )
rows = cur.fetchall()
for r in rows:
    rb = r[3] or "NULL"
    try:
        rb = json.loads(rb) if isinstance(rb, str) else rb
    except Exception:
        pass
    print(
        {
            "id": r[0],
            "key": r[1],
            "status": r[2],
            "response_body": rb,
            "last_error": r[4],
            "created_at": r[5],
            "updated_at": r[6],
        }
    )

print("\n=== Recent Orders ===")
cur.execute(
    "SELECT id, order_number, status, total_cents, created_at FROM orders ORDER BY created_at DESC LIMIT 20"
)
for r in cur.fetchall():
    print(r)

if SKU:
    print(f"\n=== Reservations for SKU={SKU} ===")
    cur.execute(
        "SELECT id, sku, quantity, status, reserved_at, reserved_until, order_id FROM inventory_reservations WHERE sku=? ORDER BY reserved_at DESC LIMIT 50",
        (SKU,),
    )
    for r in cur.fetchall():
        print(r)

conn.close()
