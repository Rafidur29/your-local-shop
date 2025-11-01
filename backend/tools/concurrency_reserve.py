import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import concurrent.futures
import time
import argparse
import json
from uuid import uuid4

BASE = os.environ.get("YLH_BASE", "http://127.0.0.1:8000")

def reserve_task(i, sku, qty, ttl):
    payload = {"sku": sku, "qty": qty, "ttl_seconds": ttl}
    try:
        r = requests.post(f"{BASE}/api/inventory/reserve", json=payload, timeout=10)
        return (i, "reserve", r.status_code, r.text)
    except Exception as e:
        return (i, "reserve", "ERR", str(e))

def order_task(i, idempotency_key, payload):
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key
    }
    try:
        r = requests.post(f"{BASE}/api/orders", json=payload, headers=headers, timeout=20)
        return (i, "order", r.status_code, r.text)
    except Exception as e:
        return (i, "order", "ERR", str(e))

def run_reserve_concurrent(workers, sku, qty, ttl):
    print(f"Running reserve test: workers={workers}, sku={sku}, qty={qty}, ttl={ttl}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(reserve_task, i, sku, qty, ttl) for i in range(workers)]
        results = [f.result() for f in futures]
        print(results)
        ids = [json.loads(r[3]).get("reservation_id") for r in results if r[2] == 200]
        print("Unique reservation ids:", set(ids))

def run_order_concurrent(workers, idempotency_key, payload):
    print(f"Running order test: workers={workers}, idempotency_key={idempotency_key}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(order_task, i, idempotency_key, payload) for i in range(workers)]
        results = [f.result() for f in futures]
        print("Results:")
        for r in results:
            print(r)
        ids = [json.loads(r[3]).get("reservation_id") for r in results if r[2] == 200]
        print("Unique reservation ids:", set(ids))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concurrency test tool (reserve or orders).")
    sub = parser.add_subparsers(dest="mode", required=True)

    r = sub.add_parser("reserve")
    r.add_argument("--sku", default="CHOC1234")
    r.add_argument("--qty", type=int, default=1)
    r.add_argument("--ttl", type=int, default=60)
    r.add_argument("--workers", type=int, default=8)

    o = sub.add_parser("orders")
    o.add_argument("--workers", type=int, default=8)
    o.add_argument("--idempotency", default="idem-test")
    o.add_argument("--sku", default="CHOC1234")
    o.add_argument("--qty", type=int, default=1)

    args = parser.parse_args()

    if args.mode == "reserve":
        run_reserve_concurrent(args.workers, args.sku, args.qty, args.ttl)
    elif args.mode == "orders":
        # Build simple order payload
        payload = {
            "customer_id": None,
            "items": [{"sku": args.sku, "qty": args.qty}],
            "payment_method": {"token": "tok-test"}
        }
        run_order_concurrent(args.workers, args.idempotency, payload)
