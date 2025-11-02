# Owner: Chung
# Merged from feature/backend
# Last Modified: 2 Nov 2025

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

# Copy dependency file from backend/
COPY backend/requirements.txt /app/backend/
# Install dependencies
RUN if [ -f backend/requirements.txt ]; then pip install --upgrade pip && pip install -r backend/requirements.txt; fi

# Copy all code. The backend folder is at /app/backend
COPY . /app

# Stage 2: runtime
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Determine the binary path for this Python version
ARG PYTHON_BIN_PATH=/usr/local/bin

# FIX: Add the Python binary path to PATH in the final stage
ENV PATH="${PYTHON_BIN_PATH}:${PATH}"

WORKDIR /app

# Copy essential runtime files from build stage
# Copy site-packages (libraries)
COPY --from=build /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
# FIX: Copy the Python executables (like uvicorn)
COPY --from=build ${PYTHON_BIN_PATH} ${PYTHON_BIN_PATH}
# Copy application code
COPY --from=build /app /app

# Set PYTHONPATH to allow imports like 'from app.api...' inside backend modules
# ENV PYTHONPATH=/app/backend

# environment defaults
ENV DATABASE_URL="sqlite:///./app.db" \
    HOST=0.0.0.0 \
    PORT=8000 \
    RESET_DB=0

EXPOSE 8000
# The CMD should reference the app relative to the PYTHONPATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
