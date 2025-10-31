import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import requests
import concurrent.futures
import json
from uuid import uuid4



BASE = "http://127.0.0.1:8000"
SKU = "CHOC1234"   # choose SKU with stock=1 or low stock
QTY = 1
WORKERS = 8

def try_reserve(i):
    payload = {"sku": SKU, "qty": QTY, "ttl_seconds": 60}
    try:
        r = requests.post(f"{BASE}/api/inventory/reserve", json=payload, timeout=5)
        return (i, r.status_code, r.text)
    except Exception as e:
        return (i, "ERR", str(e))

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(try_reserve, i) for i in range(WORKERS)]
        for f in concurrent.futures.as_completed(futures):
            print(f.result())
