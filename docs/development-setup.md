# Development Setup & Local Workflow Guide

This document provides exact, reproducible commands to develop, lint, test, and run the **Organization-Aware, Demand-Driven Shared AI Intelligence** research environment.

---

## 1. Prerequisites & Infrastructure Services

Ensure PostgreSQL and Qdrant are running locally before starting the backend:

- **PostgreSQL**: Running on `localhost:5432` with database `smart-cloud`.
  - Schema Isolation: All research tables live in the `research` schema, strictly isolated from other database objects.
- **Qdrant**: Running on `localhost:6333` (REST) and `localhost:6334` (gRPC).
  ```bash
  docker run -d -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
  ```

---

## 2. Backend Setup (`server/`)

The backend is built with FastAPI, SQLAlchemy 2 (asyncpg / psycopg2), Alembic, and Pydantic v2.

### Virtual Environment & Dependencies

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ".[dev]"
```

### Environment Configuration

Copy the template configuration:
```bash
cp .env.example .env
```
Ensure `.env` matches your local credentials:
```ini
DB_NAME=smart-cloud
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=localhost
DB_PORT=5432
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
GEMINI_API_KEY=  # Optional for synthetic/mock execution
ENVIRONMENT=development
LOG_LEVEL=info
```

### Database Migrations

Generate migration revisions (online inspection targeting `research` schema):
```bash
PYTHONPATH=. .venv/bin/alembic revision --autogenerate -m "migration_name"
```

Apply migrations safely to PostgreSQL:
```bash
PYTHONPATH=. .venv/bin/alembic upgrade head
```

### Running the Backend Development Server

```bash
cd server
PYTHONPATH=. .venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
- API Docs: `http://localhost:8000/api/docs`
- Health Endpoint: `http://localhost:8000/api/v1/health`

### Code Quality & Testing

```bash
cd server

# 1. Run full test suite (unit + integration)
PYTHONPATH=. .venv/bin/pytest -v

# 2. Run unit tests only (no external services needed)
PYTHONPATH=. .venv/bin/pytest tests/unit/ -v

# 3. Linting and formatting with Ruff
.venv/bin/ruff check .
.venv/bin/ruff format --check .

# 4. Strict type checking with Mypy
.venv/bin/mypy app analysis tests
```

---

## 3. Independent Analysis Layer (`server/analysis/`)

The analysis package can be run independently of FastAPI using read-only database connections or exported CSV/JSONL measurements:

```bash
cd server
PYTHONPATH=. .venv/bin/python -c "
import pandas as pd
from analysis import compute_cost_summary, compute_latency_summary, compute_reuse_summary

# Analysis can load exported data or run directly
print('Analysis layer loaded successfully')
"
```

---

## 4. Frontend Dashboard (`front/`)

The research dashboard is built with React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, and Recharts.

### Dependencies & Setup

```bash
cd front
npm install
```

### Running the Frontend Dev Server

```bash
cd front
npm run dev
```
Access the dashboard at `http://localhost:5173`. API requests to `/api/*` are automatically proxied to the backend on `http://localhost:8000`.

### Type Checking & Production Build

```bash
cd front
npm run build
```
This runs `tsc -b` in strict mode followed by `vite build`.
