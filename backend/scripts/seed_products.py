#!/usr/bin/env python3
"""
Seed products from a JSON file (frontend/mock/catalogue.json by default).
This script is robust to a few variations in the JSON structure and will
ensure a small set of test SKUs exist (so unit tests that expect TEST-001 etc pass).

Usage:
    python scripts/seed_products.py --file ../public/mock/catalogue.json
"""
import json
import argparse
import sys
import os
import inspect

# allow running from repo/scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.db import Base, engine, SessionLocal
from app.repositories.product_repo import ProductRepository

# ensure models imported so tables created (your repo probably does this elsewhere)
from app.models.product import Product  # noqa: F401

DEFAULT_SOURCE = os.path.join(os.path.dirname(__file__), "..", "public", "mock", "catalogue.json")

# A small list of test SKUs that tests expect; we will append these if not present in the source file.
TEST_SKUS_TO_ENSURE = [
    {"sku": "TEST-001", "name": "Seed Test 1", "price_cents": 199, "stock": 10, "description": "Seed SKU TEST-001"},
    {"sku": "TEST-002", "name": "Seed Test 2", "price_cents": 299, "stock": 10, "description": "Seed SKU TEST-002"},
    {"sku": "T1",      "name": "Tea 100g",     "price_cents": 300, "stock": 5,  "description": "Seed Tea"},
    {"sku": "T2",      "name": "Coffee 200g",  "price_cents": 600, "stock": 1,  "description": "Seed Coffee"},
    {"sku": "RES-1",   "name": "Reserve1",     "price_cents": 100, "stock": 5,  "description": "Reserve SKU 1"},
    {"sku": "RES-2",   "name": "Reserve2",     "price_cents": 200, "stock": 1,  "description": "Reserve SKU 2"},
    {"sku": "PKG1",    "name": "Test Package", "price_cents": 100, "stock": 1,  "description": "Package for tests"},
    {"sku": "RET1",    "name": "Returnable",   "price_cents": 500, "stock": 5,  "description": "Returnable item"},
]

def _normalize_entry(entry):
    """Return a normalized dict with keys: sku, name, price_cents, stock, description, image"""
    sku = entry.get("sku") or entry.get("id") or entry.get("productId")
    name = entry.get("name") or entry.get("title") or ""
    # price parsing: prefer price_cents; if not present, try price (string or numeric)
    price_cents = None
    if entry.get("price_cents") is not None:
        try:
            price_cents = int(entry.get("price_cents"))
        except Exception:
            # maybe string with decimals?
            try:
                price_cents = int(float(entry.get("price_cents")) * 100)
            except Exception:
                price_cents = 0
    else:
        raw_price = entry.get("price", entry.get("amount", 0))
        try:
            price_cents = int(float(raw_price) * 100)
        except Exception:
            price_cents = 0

    stock = None
    try:
        stock = int(entry.get("stock", entry.get("quantity", 0) or 0))
    except Exception:
        stock = 0

    description = entry.get("description") or ""
    image = entry.get("image")
    if not image:
        imgs = entry.get("images") or entry.get("image_urls") or []
        image = imgs[0] if isinstance(imgs, (list, tuple)) and len(imgs) > 0 else None

    return {
        "sku": sku,
        "name": name,
        "price_cents": price_cents,
        "stock": stock,
        "description": description,
        "image": image
    }

def seed_from_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # load input JSON
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse JSON from {path}: {e}")

    # normalize entries into list of dicts
    normalized = []
    if isinstance(data, dict):
        # if JSON is an object with an items list
        if "items" in data and isinstance(data["items"], list):
            source_list = data["items"]
        else:
            # treat dict values as entries
            source_list = list(data.values())
    elif isinstance(data, list):
        source_list = data
    else:
        source_list = []

    for entry in source_list:
        normalized.append(_normalize_entry(entry))

    # ensure test SKUs exist in normalized list (avoid duplicates)
    existing_skus = {e["sku"] for e in normalized if e.get("sku")}
    for must in TEST_SKUS_TO_ENSURE:
        if must["sku"] not in existing_skus:
            normalized.append({
                "sku": must["sku"],
                "name": must["name"],
                "price_cents": must["price_cents"],
                "stock": must["stock"],
                "description": must.get("description", ""),
                "image": must.get("image", None)
            })

    # Persist using repository
    db = SessionLocal()
    repo = ProductRepository(db)
    created = 0
    try:
        # detect whether repo.create_or_update accepts 'active' keyword
        sig = None
        try:
            sig = inspect.signature(repo.create_or_update)
            accepts_active = "active" in sig.parameters
        except Exception:
            accepts_active = False

        for entry in normalized:
            sku = entry.get("sku")
            if not sku:
                continue
            name = entry.get("name", "") or ""
            price = entry.get("price_cents", 0) or 0
            stock = entry.get("stock", 0) or 0
            description = entry.get("description", "") or ""
            image = entry.get("image", None)

            # call repository method, add active flag only if supported
            if accepts_active:
                repo.create_or_update(sku=sku, name=name, price_cents=int(price), stock=int(stock), description=description, image=image, active=True)
            else:
                repo.create_or_update(sku=sku, name=name, price_cents=int(price), stock=int(stock), description=description, image=image)
            created += 1

        db.commit()
        print("Seeded products:", created)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", default=DEFAULT_SOURCE, help="Path to product json (frontend mock) or a list of product entries")
    args = parser.parse_args()
    if not os.path.exists(args.file):
        print("File not found:", args.file)
        sys.exit(1)
    seed_from_file(args.file)
