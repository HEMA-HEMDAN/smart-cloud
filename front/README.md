# Smart Cloud Dashboard

The dashboard is the React and TypeScript interface for the Smart Cloud
research instrument. It lets researchers inspect uploaded document versions,
configure and launch paired experiments, follow run progress, and examine
results and diagnostics.

The experiment compares two backend strategies: independent RAG prepares a
separate document index per consumer, while shared RAG prepares document
chunks and embeddings on first demand and reuses them across consumers.
Questions are still retrieved and answered afresh in both strategies; answer
caching is not part of the comparison.

## Pages

- **Overview** — experiment and research summary.
- **Experiments** — browse experiment configurations and runs.
- **New experiment** — upload/select a document and configure a workload.
- **Run details** — inspect execution progress and per-run results.
- **Analysis** — compare cost, latency, reuse, and quality metrics.
- **Diagnostics** — check backend and dependency health.

## Run locally

Requirements: Node.js/npm and a running backend. The development server
forwards `/api` requests to `http://localhost:8000`.

```bash
npm install
npm run dev
```

Open <http://localhost:5173>. Start and configure the backend by following
[`../server/README.md`](../server/README.md).

## Build and lint

```bash
npm run build
npm run lint
```

The build runs TypeScript project checks followed by the Vite production
build.
