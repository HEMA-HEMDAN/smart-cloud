# Backend

The backend is the research instrument behind Smart Cloud. It exposes a
FastAPI API, persists experiment data in PostgreSQL, stores document vectors
in Qdrant, and runs paired experiments comparing independent RAG with shared
document intelligence.

## Experiment flow

1. The documents API accepts PDF, text, and Markdown files, extracts their
   text, and stores versioned document records.
2. An experiment configuration selects a document, workload, chunking and
   retrieval settings, and an AI provider.
3. The experiment runner generates a deterministic consumer workload and
   executes both strategies. Independent RAG prepares a consumer-scoped
   collection; shared RAG prepares once on first demand and reuses eligible
   vectors for later consumers.
4. Each request still runs retrieval and answer generation. Preparation
   events and request measurements are recorded in PostgreSQL for later
   comparison.
5. The results API aggregates cost, latency, reuse, quality, and security
   measurements for the dashboard. The standalone `analysis/` package also
   computes summaries from experiment data.

The sharing boundary is document chunks and embeddings, not generated
answers. Read [`../docs/research/hypothesis.md`](../docs/research/hypothesis.md)
and [`../docs/research/experimental-design.md`](../docs/research/experimental-design.md)
for the research scope, strategies, and evaluation protocol.

## Run the API

Requirements: Python 3.12+, a running PostgreSQL database, and a running
Qdrant service. Create the database before applying migrations.

From the repository root, create and configure the environment:

```bash
cp server/.env.example server/.env
```

Set `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in `server/.env` to match your
database. By default, PostgreSQL and Qdrant are expected on `localhost`.
`GEMINI_API_KEY` is only needed for Gemini-backed work; mock providers are
available for offline experiments.

Install dependencies and apply migrations:

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
set -a
source .env
set +a
PYTHONPATH=. .venv/bin/alembic upgrade head
```

Start the development API from `server/`:

```bash
PYTHONPATH=. .venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- API reference: <http://localhost:8000/api/docs>
- Health check: <http://localhost:8000/api/v1/health>

## Code map

- `app/api/v1/` — document, experiment, result, and health endpoints.
- `app/documents/` — file extraction, versioning, and document storage.
- `app/experiments/` — workload generation and paired experiment execution.
- `app/rag/` — independent and shared retrieval strategies.
- `app/embeddings/` and `app/generation/` — mock and Gemini providers.
- `app/db/` — SQLAlchemy models, PostgreSQL sessions, and Qdrant lifecycle.
- `analysis/` — offline cost, latency, reuse, and evaluation summaries.
- `migrations/` — Alembic revisions for the PostgreSQL `research` schema.

## Tests and checks

Install development dependencies with `pip install -e ".[dev]"`, then run
from `server/`:

```bash
PYTHONPATH=. .venv/bin/pytest tests/unit/ -v
```

Integration tests require the backing services. See
[`../docs/development-setup.md`](../docs/development-setup.md) for the full
test, lint, type-check, and analysis commands.
