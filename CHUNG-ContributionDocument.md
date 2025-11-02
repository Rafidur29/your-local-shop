# Backend Contribution & Implementation — Documentation (Markdown)

> Author: Chung
> Context: contribution documentation for the `backend/` repository and project-level infra (containerisation, CI, pre-commit, demo).
> This document records what you implemented, how to run it, troubleshooting notes, and a short checklist for reviewers/maintainers.

---

# Table of contents

- [Project summary](#project-summary)
- [What I implemented / changed (high level)](#what-i-implemented--changed-high-level)
- [Files & purpose (detailed)](#files--purpose-detailed)
- [How to run locally (dev) — commands](#how-to-run-locally-dev----commands)
- [How to run with Docker / Compose](#how-to-run-with-docker--compose)
- [Testing](#testing)
- [Pre-commit / formatting / linting](#pre-commit--formatting--linting)
- [CI (GitHub Actions) notes](#ci-github-actions-notes)
- [Demo script & smoke tests](#demo-script--smoke-tests)
- [Idempotency & concurrency notes](#idempotency--concurrency-notes)
- [Known issues & troubleshooting (what I saw)](#known-issues--troubleshooting-what-i-saw)
- [Merge / PR checklist for reviewers (Sith / Radifur / Chung)](#merge--pr-checklist-for-reviewers-sith--radifur--chung)
- [Evidence & submission checklist (Assignment 3 requirements)](#evidence--submission-checklist-assignment-3-requirements)
- [Next recommended actions](#next-recommended-actions)

---

# Project summary

This project is a small e-commerce backend (FastAPI + SQLAlchemy) and a frontend (React). My work focused on the backend and repository-level infrastructure: implementing core features, idempotency support, tests, containerisation, CI pipeline fix, pre-commit formatting, and a demo/test script to exercise flows (checkout, idempotency, returns, cart). I also coordinated changes so the frontend can call the backend (idempotency header, API shapes).

---

# What I implemented / changed (high level)

- Implemented **idempotency** support:
  - database model for idempotency records
  - `idempotency_repo` repository and usage from `order_service` and `return_service`
  - `idem_lock` utility (temporary lock helper) and logic to mark idempotency records `IN_PROGRESS` → `COMPLETED` or `FAILED`
- Implemented/adjusted **order flow**, checkout, payment mock adapter and SAGA-style compensations:
  - `order_service` logic including reservation, payment (mock), invoice creation, marking order status, and idempotency handling
- Implemented **return flow** and credit note/refund mock adapter
- Wrote/updated many tests under `backend/tests/` for catalogue, cart, inventory, fulfilment, order flow, returns, health
- Dockerised the app:
  - multi-stage `Dockerfile` (install deps in build stage, copy site-packages into runtime image)
  - `docker-compose.yml` to run Postgres + app with healthchecks
  - `Makefile` targets for build, up, down, test, demo
- Created **demo.sh** — a smoke script exercising key flows (idempotency, payment decline, create & receive return, cart add)
- Added `.github/workflows/ci.yml` — CI that:
  - runs tests (fixed `working-directory: ./backend`) so imports resolve
  - builds & (optionally) pushes docker image with secrets gating
- Added `.pre-commit-config.yaml` and ensured `black` / `isort` run on backend files
- Fixed many small issues in API routes and added better runtime logging (error printouts)
- Adjusted DB initialization / seeding for local dev and RESET_DB behaviour

---

# Files & purpose (detailed)

> Paths below are relative to repo root.

Core backend files you authored/modified (representative list and purpose):

- `backend/app/models/idempotency.py`
  Model `IdempotencyRecord` and `IdempotencyStatus` enum — stores idempotency key, operation, status, response payload, last error, timestamps.

- `backend/app/repositories/idempotency_repo.py`
  Repository to `begin`/`complete`/`fail` idempotent operations (insert record with `IN_PROGRESS`, mark `COMPLETED` with response, mark `FAILED` etc.). Uses SQLAlchemy sessions.

- `backend/app/services/order_service.py`
  Checkout business logic, integrates inventory reservation, payment adapter, invoice creation, idempotency coordinates, marks orders `COMPLETED`/`FAILED`.

- `backend/app/api/routes_order.py`
  FastAPI router for `POST /api/orders` (checkout). Accepts `Idempotency-Key` header (via FastAPI `Header` dependency). Wraps service exceptions, returns proper HTTP codes.

- `backend/app/models/order.py` (+ `order_lines`)
  Order persistence model and relationships to invoice/lines.

- `backend/app/services/return_service.py`
  Create return requests, process receiving returns, credit note/refund flow and idempotency.

- `backend/app/adapters/mock_payment.py` and `backend/app/adapters/mock_courier.py`
  Deterministic adapters for payment/courier for local testing; support `force_decline` flags to simulate failure scenarios.

- `backend/app/repositories/*_repo.py`
  Repos for products, cart, reservations etc.

- `backend/tests/*`
  Unit and integration tests covering the main flows (catalogue, cart, inventory, order_flow, returns, fulfilment, health). Running tests produced **13 passed** after fixes.

- `Dockerfile` (project root)
  Multi-stage image: installs dependencies, copies site-packages into runtime image, sets `PYTHONPATH=/app/backend`, CMD `uvicorn backend.app.main:app ...`. Fixed earlier `uvicorn` not in `$PATH` by copying site-packages and ensuring `PATH`.

- `docker-compose.yml` (project root)
  Postgres service + `app` service configured to depend on DB health; mounts repo for live reload.

- `Makefile`
  Targets: `venv`, `install`, `run`, `test`, `build`, `up`, `down`, `demo`.

- `demo.sh`
  Runs a set of curl requests to exercise idempotency, payment decline path, returns receive idempotency, cart add.

- `.github/workflows/ci.yml`
  CI workflow to run backend tests (note: fixed the `working-directory: ./backend` to avoid import path issues). Also contains steps for building/pushing docker image gated on registry secrets.

- `.pre-commit-config.yaml`
  Hooks for trailing whitespace, EOF fixer, `black`, `isort` — constrained to backend files.

- `README-Containerisation.md`
  Documented Docker/Docker Compose usage, how to run the app in container, demo instructions.

- `backend/app/utils/idem_lock.py`
  Temporary helper for locking idempotency flows — used as stop-gap to avoid duplicate concurrent processing when no DB-level locking is present.

---

# How to run locally (dev) — commands

Open a terminal at repo root. These commands assume you are on macOS/Linux; for Windows PowerShell adapt `export` to `setx` or create a `.env` and use `python-dotenv`.

1. Create virtualenv (optional but recommended)
```bash
python -m venv .venv
source .venv/bin/activate    # on Windows: .venv\Scripts\activate
pip install --upgrade pip
```
2. Install backend dependencies
```bash
pip install -r backend/requirements.txt
```
3. Set environment variables (optional, for local Postgres)
```bash
export RESET_DB=1
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
4. Open endpoints:
- `GET /api/products` — list products
- `POST /api/orders` — create order (checkout)
- `POST /api/returns` — create return request
- `POST /api/returns/{return_id}/receive` — receive return items
- `GET /docs` - OpenAPI UI

---
# How to run with Docker / Compose
1. Build image:
```bash
docker build -t yourlocalshop:dev .
```
2. Run with SQLite (recommended):
```bash
docker run --rm -e RESET_DB=1 -p 8000:8000 yourlocalshop:dev
# Logs will show "Uvicorn running on http://0.0.0.0:8000"
```
> Common troubleshooting: earlier the image failed with exec: "uvicorn": executable file not found. That was fixed by using a multi-stage Dockerfile and copying the site-packages from the build stage into runtime image so uvicorn and other installed binaries are present.
3. Or run with Postgres using docker-compose:
```bash
docker-compose up --build
```
4. Health check:
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/products
```
---
# Testing
1. Run tests:
```bash
export RESET_DB=1
pytest -q backend/tests
```
2. Expected output: `13 passed in X.XXs`
3. Single test with logging:
```bash
RESET_DB=1 pytest tests/test_order_flow.py::test_checkout_success_and_idempotency -q -s
```
---
# Pre-commit / formatting / linting
1. Install pre-commit hooks:
```bash
pre-commit install
pre-commit run --all-files
```
2. Hooks in `.pre-commit-config.yaml`:
- trailing-whitespace
- end-of-file-fixer
- black (configured for backend/)
- isort
- check-yaml
**Note**: Black and isort auto-fix files and may modify working tree; stage and commit the formatted files after hooks run.
---
# CI (GitHub Actions) notes
- Workflow file: `.github/workflows/ci.yml`
    - Install dependencies from `backend/requirements.txt`
    - Run tests from `./backend` working directory to ensure imports resolve
    - Build and (optionally) push Docker image to registry if secrets are set
- VSCode YAML linter sometimes flags `secrets` references as errors; these are valid in GitHub Actions context.
---
# Demo script & smoke tests
`demo.sh` runs a series of curl commands to exercise key flows:
1. `GET /api/products` — health check
2. Create order with idempotency key (twice) to test idempotency
3. Create order with payment decline to test failure handling
4. Create return request
5. Receive return items with idempotency key (twice) to test idempotency
6. Add item to cart
Run with:
```bash
./demo.sh
```
---
# Idempotency & concurrency notes
- Idempotency is implemented via `IdempotencyRecord` model and `idempotency_repo` repository.
- Operations (checkout, receive return) check for existing idempotency record by key and operation.
- If record exists and is `COMPLETED`, return stored response.
- If `IN_PROGRESS`, use `idem_lock` to prevent concurrent processing (temporary measure).
- If no record, insert with `IN_PROGRESS`, process operation, then mark `COMPLETED` or `FAILED`.
---
# Known issues & troubleshooting (what I saw)
1. Pytest import errors / missing tables
    - Symptoms: sqlite3.OperationalError: no such table: products, no such table: carts, no such table: idempotency_records
    - Cause: tests executed from wrong working directory (causes app startup/seeding not to run or database file mismatch) OR additional tests/ in repo root (not backend/tests/) use a different test config expecting migrations/seeds.
    - Fix applied: ensure CI and local test runs use working-directory: ./backend (or cd backend before pytest) so DB initialization/seeding works. Also coordinate with other teammates to ensure tests in repo root reference correct DB setup or are isolated.
2. Pre-commit auto-fixes modify files unexpectedly
    - Cause: black/isort run on staged files and modify them.
    - Fix: review changes after pre-commit runs, stage and commit the formatted files.
3. Docker initial failure: uvicorn executable not found
    - Cause: earlier Dockerfile did not copy installed site-packages into runtime image, so uvicorn binary was missing.
    - Fix: multi-stage Dockerfile that installs dependencies in build stage and copies site-packages into runtime image.
4. Frontend to backend API call failures
    - Cause: CORS issues or incorrect API URLs.
    - Fix: set `"proxy": "http://localhost:8000"` in frontend `package.json` to route API calls during development.
---
Author: Chung Hee Sii
Last updated: 2 Nov 2025
