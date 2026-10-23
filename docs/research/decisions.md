# Research Architecture & Methodological Decisions

This document records the foundational methodological, architectural, and design decisions governing the **Organization-Aware, Demand-Driven Shared AI Intelligence** research instrument.

---

## 1. Confirmed Design Decisions

### Decision 1: Two-Strategy Paired A/B Experimental Formulation
- **Status:** Confirmed
- **Context:** The core hypothesis evaluates whether sharing document intelligence reduces aggregate preparation costs without degrading performance, quality, or security compared to independent processing.
- **Decision:** The experiment compares two strictly controlled strategies:
  - **Strategy A (Control):** Independent RAG baseline where every simulated consumer independently chunks, embeds, and indexes its own documents in consumer-scoped collections (`exp_{run_id}_{consumer_id}`).
  - **Strategy B (Treatment):** Shared Intelligence RAG where the first eligible consumer prepares chunks and vectors on demand into a run-scoped collection (`exp_{run_id}_shared`), and subsequent consumers reuse those vectors with per-retrieval authorization filtering.
- **Rationale:** Paired A/B execution under identical random seeds and workloads isolates the effect of shared preparation from background variability in model latency or network conditions.
- **Consequences:** Strategy A requires more total vector collections and API embedding calls, providing a true measure of redundant preparation.

---

### Decision 2: Intermediate Artifact Reuse Boundary (Chunks & Vectors Only)
- **Status:** Confirmed
- **Context:** Knowledge reuse can occur at multiple levels: raw document text, parsed chunks, vector embeddings, prompt attention contexts, or final generated answers.
- **Decision:** The initial research comparison restricts reuse strictly to **parsed text chunks and dense vector embeddings**. Generated answers, semantic query caches, and LLM attention-state caches (e.g. prompt caching) are explicitly excluded. Every incoming query performs a fresh query embedding, retrieves top-k chunks, and invokes the generation model.
- **Rationale:** Conflating answer caching with document-preparation reuse would obscure whether cost reductions stem from avoiding ingestion or simply bypassing the language model. Furthermore, answer caching risks serving outdated answers to dynamic questions.
- **Consequences:** Generation API costs will scale with total queries in both strategies, allowing the analysis to isolate preparation savings specifically.

---

### Decision 3: Database Schema Isolation (`research` schema)
- **Status:** Confirmed
- **Context:** The host database (`smart-cloud`) may support existing or future operational application tables in PostgreSQL.
- **Decision:** All research experiment entities (`experiment_configs`, `experiment_runs`, `preparation_events`, `request_measurements`, `document_versions`, `provider_configs`, `pricing_assumptions`) and Alembic migration tracking are restricted strictly to a dedicated PostgreSQL schema: `research`.
- **Rationale:** Completely eliminates the risk of conflicting table names, destructive drops, or migration interference with application data in `public`.
- **Consequences:** All SQLAlchemy models declare `__table_args__ = {"schema": "research"}`, and Alembic migration scripts specify `version_table_schema="research"`.

---

### Decision 4: Server-Side Authorization Invariant & Zero-Tolerance Leakage
- **Status:** Confirmed
- **Context:** In a shared vector store, documents with differing access restrictions reside in the same physical collection.
- **Decision:** Consumer identity and document access permissions must be resolved exclusively by trusted server-side logic (never accepted blindly from client headers). Retrieval is constrained by a vector payload filter (`authorized_consumers CONTAINS consumer_id`). Any instance of unauthorized chunk retrieval is classified as a **critical security failure**, not an acceptable engineering trade-off.
- **Rationale:** Multi-tenant and organizational knowledge systems cannot compromise data governance for cost savings.
- **Consequences:** Synthetic adversarial probe queries must be included in benchmark workloads to verify that unauthorized consumers are blocked from retrieving protected chunks.

---

### Decision 5: Deterministic Evaluation Protocol ($T = 0.0$)
- **Status:** Confirmed
- **Context:** LLM generation temperature introduces sampling variance that can obscure subtle differences between retrieval strategies.
- **Decision:** All experimental generation calls fix temperature to $0.0$ and pin model configurations. Workload request ordering and consumer arrivals are driven by explicit deterministic random seeds.
- **Rationale:** Maximizes reproducibility and ensures that observed differences in answer quality or latency stem from retrieval context variations rather than generation sampling randomness.
- **Consequences:** True stochastic variability is characterized across repeated runs with different fixed seeds rather than intra-run sampling temperature.

---

### Decision 6: Decoupled Offline Analysis Layer
- **Status:** Confirmed
- **Context:** Running analytical queries and statistical tests during real-time serving could degrade experiment performance.
- **Decision:** The analysis package (`server/analysis/`) is decoupled from FastAPI. It operates in read-only mode, executing either directly against PostgreSQL or against exported CSV/JSONL run logs.
- **Rationale:** Enables statistical significance calculations (paired t-tests, Wilcoxon tests, bootstrap confidence intervals) to be repeated, peer-reviewed, and audited without running web services or repeating paid API calls.

---

## 2. Proposed Implementation Requirements

These requirements specify the technical contract for the upcoming experiment execution engine:

1. **Transaction & Run Isolation:** Each execution of an experiment configuration must receive a unique UUID `run_id`. All vector collections and database measurement rows must be tagged with this `run_id`.
2. **Fine-Grained Latency Instrumentation:** Latency measurements must use monotonic clocks and record separate timestamps for:
   - Request receipt ($t_0$)
   - Document preparation start & end ($t_{\text{prep\_start}}, t_{\text{prep\_end}}$)
   - Retrieval search start & end ($t_{\text{ret\_start}}, t_{\text{ret\_end}}$)
   - LLM generation call start & end ($t_{\text{gen\_start}}, t_{\text{gen\_end}}$)
3. **Token Usage Auditability:** When the provider API returns token usage counts (`prompt_tokens`, `completion_tokens`, `embedding_tokens`), the system records `tokens_available = True` and exact integers. If unavailable, `tokens_available = False` is recorded, and estimation methods are documented.
4. **Document Revision Protocol:** The engine must support injecting document revisions mid-workload, triggering event logs for `invalidation` and `re_preparation`.

---

## 3. Assumptions Requiring Empirical Validation

The following assumptions underpin the research design and must be explicitly evaluated during testing:

- **Assumption A1 (Overhead Boundedness):** The maintenance and coordination overhead of the shared layer ($C_m$, including Qdrant payload filtering and metadata tracking) is small relative to embedding preparation cost ($C_m \ll C_p$).
- **Assumption A2 (Latency Parity on Warm Requests):** Warm-request latency under Strategy B (retrieval with payload filtering) is statistically indistinguishable from warm-request latency under Strategy A.
- **Assumption A3 (Zero Quality Degradation):** Sharing intermediate vectors does not reduce Retrieval Recall@k or answer correctness relative to independent preparation of the same document version.
- **Assumption A4 (Scalability of Authorization Filtering):** Payload-level authorization checks scale effectively without causing retrieval latency degradation as consumer ID arrays grow.

---

## 4. Future Extensions (Post-Baseline Scope)

The following capabilities are recognized as valuable extensions but are explicitly deferred until the primary A/B comparison is completed:

- **Concurrency & High QPS Workloads:** Multi-threaded or asynchronous concurrent load testing to stress vector database read/write locks during simultaneous first-demand preparation.
- **Semantic Answer Caching:** Introducing response caching on top of Strategy B to evaluate whether caching final answers offers additive savings without stale-data risks.
- **Partial Chunk Invalidation:** Re-indexing only modified sections of updated documents rather than full-document re-preparation.
- **Cross-Tenant Hierarchical Boundaries:** Extending authorization models from flat consumer IDs to hierarchical institutional role-based access control (RBAC).

---

## 5. Open Research Questions

1. **Cache Retention & Eviction Policies:** What is the optimal eviction policy (e.g., Least Recently Used, Least Frequently Used, Cost-Weighted Eviction) for shared vector collections when storage budgets are constrained?
2. **Cold-Start Latency Impact on User Experience:** How does the first-demand preparation latency penalty affect interactive user perception, and can background predictive pre-warming mitigate it without becoming upfront pre-computation?
3. **Threshold for Dynamic Invalidation vs. Version Stacking:** In fast-updating corpora, is it more economical to purge obsolete vectors immediately or retain them with valid time-range metadata?
