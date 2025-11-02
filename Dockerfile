# Stage 1: build
FROM python:3.13-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app

# system deps for some packages (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/
RUN if [ -f /app/backend/requirements.txt ]; then pip install --upgrade pip && pip install -r /app/backend/requirements.txt; fi
# Copy all code, including the backend/ folder
COPY . /app
# ensure package imports resolve, specifically for the 'backend' structure
ENV PYTHONPATH=/app/backend

# Stage 2: runtime
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# ensure runtime has /usr/local/bin in PATH (default normally is fine)
ENV PATH="/usr/local/bin:$PATH"
# ensure python can import the backend package
ENV PYTHONPATH=/app/backend

# copy libs and source from build stage
COPY --from=build /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=build /app /app

# environment defaults (override via docker run)
ENV DATABASE_URL="sqlite:///./backend/app.db" \
    HOST=0.0.0.0 \
    PORT=8000 \
    RESET_DB=0

EXPOSE 8000

# Use python -m uvicorn to avoid depending on console scripts location
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
