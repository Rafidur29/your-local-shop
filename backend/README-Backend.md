Author: Chung Hee Sii
Last Modified: 2 Nov 2025
Description: ```
Instructions for containerising the backend and preparing for CI/CD.
This file also acts as the ownership of Chung Hee Sii for the backend component (specifically everything under backend/).
Any file outside of this directory is not owned by Chung Hee Sii unless explicitly commented in that file.
```

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
