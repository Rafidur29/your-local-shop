# Containerization and CI/CD Preparation

### A Prepare Repository Locally

1.  **Copy Environment File:** Copy the example file to create your local `.env`.
    ```bash
    cp .env.example .env
    # Edit .env to set DATABASE_URL if you want Postgres in docker-compose
    ```

2.  **Setup Virtual Environment (Local Run):** If you are running tests or uvicorn directly (not in Docker), set up your virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # or Windows: .venv\Scripts\Activate.ps1
    pip install -U pip
    pip install -r backend/requirements.txt
    ```

3.  **Run Tests (Verification):** Ensure all tests pass before containerizing. Run from the repository root:
    ```bash
    RESET_DB=1 pytest -q ./backend
    ```

### B Local Containerized Run (docker-compose)

1.  **Build & Run with Postgres (Recommended Dev Stack):**
    ```bash
    docker-compose up --build
    ```
    This command builds the `app` image, starts the `db` (Postgres) service, and runs the app with live reload enabled. The app will be accessible at `http://localhost:8000`.

2.  **Plain Docker Run (SQLite only):** If you only want to use SQLite and skip Postgres:
    ```bash
    docker build -t yourlocalshop:latest .
    docker run -e RESET_DB=1 -p 8000:8000 yourlocalshop:latest
    ```

### C Run Demo Smoke Checks

If the application is running locally (uvicorn or in a container via `docker-compose up`), run the demo script to verify basic functionality:
```bash
./demo.sh
```

### D CI/CD with GitHub Actions

1. **Commit CI File**: Commit the newly created .github/workflows/ci.yml file.
2. **Trigger Workflow**: Push your branch and/or open a Pull Request (PR) to trigger the CI workflow.
3. **Confirm**: Verify in the GitHub Actions tab that the pytest -q step passes on both Python versions.

### E Optional: Deployment Preparation
- **Render/Heroku**: set build command to `pip install -r backend/requirements.txt` and start command to `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- **Docker Hub**: push your Docker image to Docker Hub for easy deployment.
- **Google Cloud Run/AWS ECS**: deploy your Docker image directly to these services.
- **Kubernetes**: create deployment and service YAML files to run your containerized app in a Kubernetes cluster.


Phase-by-phase plan
Phase 0 — Repo & environment bootstrap (do this first; 0.5–1 day)

Goal: Create repository skeleton, local dev environment and CI pipeline; app boots and shows health.

Why now: Without DB or Sith, you can create runnable skeleton, API surface, docs and tests.

Deliverables: repo skeleton, working uvicorn run, /api/health, OpenAPI page.

Commands (exact):

# from project root
git init
mkdir -p yourlocalshop-backend/{app,tests,diagrams,scripts}
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy alembic pydantic[dotenv] pytest httpx python-dotenv
pip freeze > requirements.txt


Files to create (minimum):

/yourlocalshop-backend
  README.md
  requirements.txt
  .env.example
  run.sh            # start script
  app/__init__.py
  app/main.py       # FastAPI instantiation + health route
  app/config.py     # load env (pydantic BaseSettings)
  app/api/health.py
  app/adapters/mock_payment.py
  app/adapters/mock_courier.py
  app/db/__init__.py  # SQLAlchemy session factory
  tests/test_health.py
  .github/workflows/ci.yml  # basic CI skeleton (pytest)


Start the app locally:

# set env
cp .env.example .env
# run
uvicorn app.main:app --reload --port 8000
# or use run.sh


Verification:

GET http://localhost:8000/api/health returns JSON with status: ok and db: connected|notconnected (for SQLite it will be connected).

OpenAPI UI at http://localhost:8000/docs.

Acceptance criteria (Phase 0):

App starts in <10s locally

/api/health returns valid JSON

CI pipeline runs pytest (even if minimal tests)

Phase 1 — Catalogue read API + cache skeleton (2–3 days)

Goal: Implement public product listing and product detail endpoints so frontend shows catalogue pages.

Why now: Frontend depends on these endpoints first. They’re read-only and don’t require complex DB logic.

Deliverables:

GET /api/products with pagination & basic filters

GET /api/products/{sku}

Local seed script to load sample products

Simple in-process cache (LRU or in-memory) and cache warmup script (top-500 configurable stub)

Files to create/modify:

app/models/product.py         # SQLAlchemy model (simple)
app/repositories/product_repo.py
app/services/catalogue_service.py
app/api/routes_catalogue.py   # routers
scripts/seed_products.py
app/cache.py                  # simple in-memory cache & warmup function


Commands:

# run seed
python scripts/seed_products.py --file sample_products.json
# start server
uvicorn app.main:app --reload


Verification:

Frontend product list displays items (use browser or curl).

TTFB measurement: use curl -w "%{time_starttransfer}\n" -sS http://localhost:8000/api/products — ensure <0.3s local dev (real target: 300ms @95th in staging).

Acceptance criteria (Phase 1):

Product listing + product detail return JSON with price, SKU, stockHint (no authoritative stock).

Cache warmup runs on bootstrap (even as async background task).

OpenAPI shows models & endpoints.

Phase 2 — Cart endpoints & guest cart persistence (2–3 days)

Goal: Implement cart model, add/remove/update items, guest cart via UUID cookie and cart merge for registered users.

Why now: Core user flow; can be implemented with SQLite and without deep inventory logic.

Deliverables:

POST /api/cart/items — add item

PATCH /api/cart/items/{id} — update qty

GET /api/cart

DELETE /api/cart/items/{id}

Guest cart cookie strategy and POST /api/cart/merge endpoint

Server-side validation hooks for price snapshot via Catalogue service

Files:

app/models/cart.py
app/models/cart_item.py
app/schemas/cart_schema.py
app/services/cart_service.py
app/api/routes_cart.py


Verification:

Use frontend or httpx tests to add items, update qty, confirm totals.

Test guest cart cookie flow: create cookie, add items, simulate login and POST /api/cart/merge

Acceptance criteria (Phase 2):

Cart operations perform server-side validation and return price snapshots.

Cart persistence survives server restart (SQLite file-based).

Phase 3 — Inventory skeleton & reservation (reserve TTL 900s) (2–4 days)

Goal: Add an InventoryService and a persisted reservation table so checkout can be tested. Reservation TTL default = 900 seconds (15 minutes) per assignment design.

Why now: Inventory is required for checkout correctness. Implementing a simple reservation model lets you test order flows without full concurrency logic.

Deliverables:

inventory_reservations table + SQLAlchemy model

InventoryService.reserve(sku, qty, reservation_id, ttl=900) + InventoryService.release(reservation_id) + InventoryService.commit(reservation_id)

Background job to expire reservations (simple apscheduler or a scheduled pytest-run script)

InventoryService uses pessimistic reservation when stock ≤ 5 (configurable).

Files:

app/models/inventory_reservation.py
app/services/inventory_service.py
app/tasks/expire_reservations.py


Verification tests:

Unit test: reserve item reduces available stock (in reservation sense).

Integration test: reserve -> commit -> stock decremented on commit.

TTL verification: create reservation with small TTL (e.g., 2s) and assert auto-expiry.

Acceptance criteria (Phase 3):

Reservations persist to DB and respect TTL (900s default).

Release and commit behave deterministically.

Phase 4 — Order creation orchestration + Mock Payment (4–6 days) (critical)

Goal: Implement synchronous checkout orchestration (OrderService/Orchestrator) that performs: cart validation → inventory reservation check/confirm → payment via MockPaymentAdapter → commit inventory → generate invoice → enqueue fulfilment event.

Why now: This is the core workflow for the assignment and the first thing that demonstrates end-to-end capabilities.

Deliverables:

POST /api/orders (checkout) must accept Idempotency-Key header

OrderService.create_order(payload, idempotency_key) orchestration with clear steps and error handling

Mock Payment Adapter implementing idempotency storage and deterministic responses (success/fail scenarios)

API returns 201 with {orderId, status, invoiceId} on success

Files:

app/models/order.py
app/models/order_line.py
app/models/invoice.py
app/services/order_service.py
app/adapters/mock_payment.py
app/repositories/idempotency_repo.py
app/api/routes_order.py


Important behaviour (implement in code):

Idempotency: record idempotency key → response payload. Repeated requests with the same key return the same response and do not duplicate charges/orders.

Compensation: on payment success but inventory commit failure → trigger refund via mock adapter and mark order as FAILED/REFUNDED.

Timeouts & retries: payment adapter retry up to 2 times with exponential backoff on transient errors.

Commands to run tests:

pytest tests/unit/test_order_service.py::test_checkout_success
pytest tests/integration/test_checkout_flow.py


Verification:

Re-run identical checkout request with same Idempotency-Key and confirm single order created and no duplicate invoices.

Simulate payment decline and confirm reservation release and correct error code returned.

Measure checkout latency for payment part (should be within mocked expectations).

Acceptance criteria (Phase 4):

Checkout endpoint creates order, returns 201, and invoice persisted.

Idempotency is tested & verified (unit test).

Compensation path tested: payment success + DB failure triggers refund dance (mocked).

Phase 5 — Fulfilment & packing admin endpoints (2–3 days)

Goal: Implement creation of PackingTask after order paid, admin endpoints to list pending packing tasks and mark pack-complete causing courier booking webhook to fire.

Why now: Closes end-to-end: order placed → packing tasks → shipment.

Deliverables:

POST /api/admin/packing-tasks/{id}/packed — mark packed

PackingTask model & FulfilmentBatch creation

Mock Courier Adapter that returns tracking number

Shipment model created after booking

Files:

app/models/packing_task.py
app/models/shipment.py
app/services/fulfilment_service.py
app/adapters/mock_courier.py
app/api/routes_admin.py


Verification:

Create order → check packing task appears in admin list

Mark packed → booking occurs → shipment record with tracking number created

Acceptance criteria (Phase 5):

Packing tasks created within 10s of order paid (in tests simulate background).

Shipment created and contains tracking id.

Phase 6 — Returns (RMA) & Invoices (2–3 days)

Goal: Implement ReturnRequest RMA flow as per Assignment 2 design: create RMA → courier receive → inventory update → refund via mock payment adapter.

Deliverables:

POST /api/returns — create RMA

Update Inventory on receive & Invoice.credit_note

Tests for refund flow and RMA lifecycle

Verification & acceptance: as in the design doc (refund within expected time, notification generated).

Phase 7 — Tests, CI, docs, OpenAPI & evidence collection (2–3 days)

Goal: Produce robust automated tests, CI pipeline, OpenAPI export, Postman collection, and evidence items (screenshots, CI logs) required by the assignment.

Deliverables:

Unit tests (services)

Integration tests leveraging SQLite in-memory or a test DB file

ci.yml GitHub Actions to run tests + flake/black checks

docs/openapi.json or docs/swagger.html

scripts/seed_products.py and test scenario scripts (checkout success, idempotency, concurrent checkout script)

Verification:

CI run passes on PR

Documented screenshot evidence of passing tests, example pytest --maxfail=1 -q output saved.

Acceptance criteria:

Test coverage for core services (catalogue, cart, order, inventory) with passing CI.

Provide screenshot/video or logs to show scenarios run (for submission).

Phase 8 — Hardening & hand-off to Sith (DB & deployment) (Sith tasks)

Goal: Hand-off tasks that require Sith (DB tuning, migrations to Postgres, deployment pipeline, performance tuning).

What you do before Sith begins (skeletons you prepare):

Alembic skeleton in alembic/ with initial migration files (empty or basic schema).

Repository interfaces (abstract base classes) so Sith just needs to implement DB specifics.

Dockerfile & docker-compose.yml templates that include Postgres service (commented lines) so Sith can enable.

Migration checklist telling Sith what to fill: exact CREATE TABLE DDL for each model and constraints.

Sith’s likely tasks (detailed):

Replace SQLite with Postgres connection string in app/config.py

Run Alembic migrations to create persistent schema

Add connection pool tuning & production settings

Set up system for secrets (vault/ENV) per bootstrap requirements

Deploy to chosen infra and run staging bootstrap smoke tests

Skeletons you deliver to Sith (so he can start):

alembic/env.py wired to app.db session factory

migrations/versions/ with placeholder migration scripts

docker-compose.yml with postgres service but commented volumes/credentials to be set by Sith

docs/deployment.md with start commands and runtime env keys to set

Phase 9 — Load test & perf checks (optional but recommended)

Goal: Run a simple load script to confirm behaviour under short bursts; check checkout throughput & reservation correctness.

Tools: locust or a simple python script using concurrent.futures.ThreadPoolExecutor + httpx.

Targets (from design):

20 orders/minute initial acceptance

TTFB for catalogue <= 300ms (95th)

Checkout completion <= 5s (95th)

Acceptance criteria: pass smoke load tests or show graceful degradation.

Environment setup (complete commands) — reproducible dev environment
# 1. clone & venv
git clone <repo-url> yourlocalshop-backend
cd yourlocalshop-backend
python3 -m venv .venv
. .venv/bin/activate

# 2. install (pin versions)
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy alembic pydantic python-dotenv pytest httpx alembic apscheduler
pip freeze > requirements.txt

# 3. initialize db (SQLite for dev)
export DATABASE_URL=sqlite:///./dev.db
python -c "from app.db import init_db; init_db()"

# 4. seed products
python scripts/seed_products.py --file sample_products.json

# 5. run dev server
uvicorn app.main:app --reload --port 8000

# 6. run tests
pytest -q
