# Authored-by: Chung Hee Sii
# Last Modified: 2 Nov 2025
# Merged from: feature/backend

# Define the application directory and image name
BACKEND_DIR = backend
IMAGE_NAME = yourlocalshop
TAG = $(IMAGE_NAME):dev

# Environment setup
VENV = .venv
PYTHON = $(VENV)/Scripts/python # Use Scripts for Windows compatibility

# --- Local Development Targets ---

.PHONY: venv
venv:
	@echo "Creating virtual environment..."
	python -m venv $(VENV)

.PHONY: install
install: venv
	@echo "Installing dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements.txt
	@echo "Local dependencies installed."

.PHONY: run
run: install
	@echo "Starting Uvicorn locally..."
	@export RESET_DB=1 && $(PYTHON) -m uvicorn $(BACKEND_DIR).app.main:app --host 0.0.0.0 --port 8000 --reload

# --- Test/Lint Targets ---

.PHONY: test
test: install
	@echo "Running tests..."
	@export RESET_DB=1 && cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q

.PHONY: lint
lint: install
	@echo "Running linting (flake8)..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install flake8
	@cd $(BACKEND_DIR) && $(PYTHON) -m flake8 .

# --- Docker Targets ---

.PHONY: build
build:
	@echo "Building Docker image $(TAG)..."
	docker build -t $(TAG) .

.PHONY: up
up: build
	@echo "Starting containers with docker-compose..."
	docker-compose up --build -d

.PHONY: down
down:
	@echo "Stopping containers..."
	docker-compose down

.PHONY: demo
demo:
	@echo "Running smoke tests..."
	./demo.sh
