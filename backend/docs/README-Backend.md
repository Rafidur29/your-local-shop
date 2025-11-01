# Your Local Shop — Environment & Run / Test Guide

Place this file at `backend/docs/SETUP_AND_TESTING.md` (or copy into your repo README). It documents everything you need to start, seed, run, test and exercise the backend locally. It assumes you are working from the project `backend/` folder.

> Note: the repo paths in examples use `backend/` as the working folder. Adjust if your repo layout differs.

---

## Quick facts / prerequisites
- Tested environment: Windows (Git Bash / MINGW64), Python 3.10+ (you used 3.13), SQLite for local DB.
- Recommended shell on Windows for commands shown: **Git Bash (MINGW64)** or PowerShell (commands shown for both where different).
- Virtual environment: `.venv` in project root (under `backend/`).
- App entrypoint: `app.main:app` — run via `uvicorn`.
- OpenAPI (Swagger UI) available at: `http://127.0.0.1:8000/docs` when server running.

---

## File / folder quick reference
- `backend/` — working directory for all commands below
- `backend/.venv/` — virtual environment (created by `python -m venv .venv`)
- `backend/.env` — environment variables (FRONTEND_ORIGINS, DATABASE_URL, etc.)
- `backend/app/` — application packages (models, api, services)
- `backend/scripts/seed_products.py` — seed the catalogue
- `backend/tools/concurrency_reserve.py` — concurrency test tool (reserve & orders modes)
- `backend/tools/db_check.py` — quick DB query check (existing helpers)
- `backend/dev.db` or `backend/dev.sqlite` — default SQLite DB file (name per `DATABASE_URL`)
- `backend/requirements.txt` — project pinned deps

---

## 0) Clone & switch to backend folder (if not already)
```bash
# from your repo root (or wherever you keep project)
cd path/to/your-repo/backend
pwd  # should show .../your-repo/backend
```
## 1) Create & activate virtual environment
### Git Bash / MINGW64 (recommended on Windows)
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```
### PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
### macOS / Linux
```bash
python -m venv .venv
source .venv/bin/activate
```
## 2) Install dependencies
```bash
pip install -r requirements.txt
```
On Pydantic v2 warnings or BaseSettings moved error, ensure `pydantic-settings` installed:
```bash
pip install pydantic-settings
```
## 3) Set up environment variables (.env)
- Use single quotes around JSON-like env values to prevent shell parsing issues.
```text
DATABASE_URL=sqlite:///./dev.db
APP_HOST=127.0.0.1
APP_PORT=8000
FRONTEND_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]'
SECRET_KEY=change-this-secret
PAYMENT_MOCK_DELAY_MS=200
RESERVATION_TTL_SECONDS=900
```
- **Important**: By default, `init_db()` in `app/db/__init__.py` will drop all tables if the `RESET_DB` env var is set to `1`, `true` or `yes` (case insensitive). This is useful for development resets. Set this var as needed before running the server.
## 4) Initialise the database
### Initialise DB (create tables)
```bash
# inside backend/
python -c "from app.db import init_db; init_db()"
# You should see:
# Creating database tables...
# Database initialized.
```
On REBUILD the DB, use:
```bash
# Temporarily set the flag (Git Bash)
export RESET_DB=true
python -c "from app.db import init_db; init_db()"
# or for Powershell
$env:RESET_DB = "true"
python -c "from app.db import init_db; init_db()"
# Afterwards unset variable (optional)
unset RESET_DB   # Git Bash
Remove-Item Env:\RESET_DB  # PowerShell
```
### Seed initial product data
```bash
# inside backend/
python scripts/seed_products.py
# Output: Seeded 5 products into the catalogue.
```
Confirm seeding by checking products via API or DB check tool:
```bash
# quick sqlite query (if sqlite3 installed)
sqlite3 dev.db "SELECT sku, name, price_cents, stock FROM products;"
# OR use Python tool
python -c "from app.db import SessionLocal; db=SessionLocal(); print(db.execute('select sku,name from products').fetchall()); db.close()"
# Output: list of products
```
## 5) Run the backend server
### Dev server with auto-reload
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
"Terminal behaviour: leave running server in terminal; open new terminal tab/window for further commands."
### For concurrency tests or stable single-run
```bash 
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```
Leave this running in a terminal for the next steps.
## 6) Test the API
Open in  browser: `http://127.0.0.1:8000/docs` (or ctrl+click link in output).
Use Swagger UI to explore and test endpoints (e.g., list products, create orders).
## 7) Manual curl tests
### List products
```bash
curl -s "http://127.0.0.1:8000/api/products/" | jq .
```
### Single product
```bash
curl -s "http://127.0.0.1:8000/api/products/CHOC1234" | jq .
```
### Reserve stock
```bash
curl -X POST "http://127.0.0.1:8000/api/inventory/reserve" \
  -H "Content-Type: application/json" \
  -d '{"sku":"CHOC1234","qty":1,"ttl_seconds":60}'
```
### Commit reservation after PAYMENT_MOCK_DELAY_MS
```bash
curl -X POST "http://127.0.0.1:8000/api/inventory/commit" \
  -H "Content-Type: application/json" \
  -d '{"reservation_id":1,"order_id":101}'
```
### Create order with idempotency key
```bash
curl -s -X POST "http://127.0.0.1:8000/api/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-key-123" \
  -d '{
    "customer_id": null,
    "items": [{"sku":"CHOC1234","qty":1}],
    "payment_method": {"token":"tok-123"}
  }' | jq .
```
- Rerun same command with same `Idempotency-Key` to see idempotent response.
- Use `--header "Idempotency-Key: another-key-456"` to test a new order.
## 8) Run concurrency test tool
Use: `tools/concurrency_reserve.py` to simulate concurrent requests.
### Reserve mode
Open terminal A and run server as per step 5. Then in terminal B:
```bash
python tools/concurrency_reserve.py reserve --sku CHOC1234 --qty 1 --ttl 60 --workers 8
# Output: shows results of 8 concurrent reserve attempts
```
### Orders mode
```bash
python tools/concurrency_reserve.py orders --workers 6 --idempotency idempotency-final-test --sku CHOC1234 --qty 1
# Output: shows results of 6 concurrent order attempts with same idempotency key
```
- Always run concurrency tests against a running server (step 5).
- Concurrency script runs multiple threads to simulate concurrent requests. Check DB via `db_check.py` or API to confirm correct stock levels and idempotent order creation.
## 9) Additional DB checks
Use `tools/db_check.py` for quick DB queries.
```bash
# syntax: python tools/db_check.py <db-file> <idempotency-key> <sku>
python tools/db_check.py dev.db idempotency-final-test CHOC1234
# Output: shows orders with the given idempotency key and current stock for the SKU
```
## 10) Running tests (pytest)
All:
```bash
pytest -q
```
Specific test file:
```bash
pytest -q tests/test_orders.py
```
Capture output to log:
```bash
pytest -q | tee pytest_output.log
```
If tests need clean DB state, set `RESET_DB=true` in env before launching server and executing tests.
## 11) Useful development commands and tips
- Freeze current dependencies:
```bash
pip freeze > requirements.txt
```
- Recreate DB from scratch:
```bash
export RESET_DB=true     # Git Bash
python -c "from app.db import init_db; init_db()"
unset RESET_DB               # Git Bash
```
- Run server in background (Git Bash):
```bash
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 > server.log 2>&1 &
# not recommended for interactive dev, better to keep in terminal
```
- OpenAPI/Swagger UI: `http://127.0.0.1:8000/docs`
- Rebuild migrations skeleton (if using Alembic later)