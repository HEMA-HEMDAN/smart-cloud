# Experimental Design & Protocol Specification

## 1. Overview and Design Principles

The experimental instrument is designed to provide an **unbiased, repeatable, paired comparative evaluation** between two retrieval-augmented generation paradigms:
1. **Strategy A (Control):** Independent RAG baseline with consumer-isolated preparation.
2. **Strategy B (Treatment):** Demand-driven Shared Intelligence RAG with intermediate artifact reuse and server-side authorization enforcement.

To eliminate external confounders, both strategies are evaluated under identical workloads, corpora, document revision schedules, and model parameters.

---

## 2. Experimental Strategy Specifications

### 2.1 Strategy A: Independent RAG Baseline (Control)

In Strategy A, every simulated consumer operates in complete isolation:

- **Isolated Ingestion Pipeline:** Document parsing, text chunking, embedding generation, and vector indexing are executed independently for each consumer requesting a document.
- **Strict Physical Vector Isolation:** Vector collections are strictly scoped by run and consumer ID:
  $$\text{Collection Name} = \text{exp\_}\{\text{run\_id}\}\_\{\text{consumer\_id}\}$$
- **Zero Artifact Sharing:** Chunks, embeddings, metadata, and responses are never shared across consumer collections.
- **Explicit Redundancy Accounting:** When Consumer 2 requests the same document already processed by Consumer 1, Consumer 2 repeats the entire parsing, chunking, and embedding pipeline. The duplicate tokens, processing time, and storage are measured and recorded explicitly.
- **Infrastructure Baseline Purity:** To prevent contamination, Strategy A must not benefit from shared vector stores, in-memory caches, or local artifact reuse. Any provider-side caching or connection pooling must be documented to distinguish experimental variables from underlying cloud infrastructure behavior.

### 2.2 Strategy B: Shared Intelligence RAG (Treatment)

In Strategy B, document preparation is demand-driven and shared across authorized consumers:

- **First-Demand Preparation:** When a document is first requested by an authorized consumer, the system executes the parsing, chunking, embedding, and indexing pipeline once.
- **Run-Scoped Shared Index:** Intermediate artifacts are stored in a single run-scoped collection:
  $$\text{Collection Name} = \text{exp\_}\{\text{run\_id}\}\_\text{shared}$$
- **Intermediate Artifact Reuse:** Subsequent requests by any authorized consumer reuse the existing chunks and vector embeddings directly from the shared index, bypassing duplicate parsing and embedding generation.
- **Full Query Processing:** Every query performs a fresh query embedding, executes top-k retrieval, and invokes the generation model. **Answer caching and semantic query memoization are explicitly excluded** from the baseline comparison.
- **Event Lifecycle Tracking:** Every lifecycle phase is explicitly emitted as an auditable database event:
  - `preparation_attempt`, `preparation_success`, `preparation_failure`
  - `reuse_hit`, `reuse_miss`
  - `invalidation_event`, `document_update`, `re_preparation`
- **Artifact Eligibility Verification:** Before an artifact is reused, the engine verifies that the cached vectors match the exact document version and configuration tuple (see Section 4).
- **Decoupled Access Control:** Reusing an indexed artifact does not automatically grant access to the consumer; document authorization is evaluated independently on every retrieval call.

---

## 3. Controlled Variables & Experimental Invariants

Within every paired A/B comparison run, the following variables must remain strictly identical:

| Variable | Control Specification | Verification Method |
|---|---|---|
| **Raw Corpus** | Identical raw text/PDF/markdown documents | SHA-256 content hashes |
| **Document Versions** | Identical sequence of initial and revised document states | Version IDs in `document_versions` |
| **Chunking Parameters** | Identical chunking algorithm, `chunk_size` (chars/tokens), and `chunk_overlap` | Serialized JSON in `chunking_config` |
| **Embedding Provider & Model** | Identical provider (e.g. Gemini), model ID, and dimension (e.g., 768 or 3072) | Provider config snapshot per run |
| **Generation Provider & Model**| Identical provider, model ID, and system prompts | Provider config snapshot per run |
| **Generation Hyperparameters** | Temperature fixed to $0.0$ for deterministic output; identical `max_tokens` | Model invocation logs |
| **Retrieval Hyperparameters** | Identical similarity metric (Cosine), identical `top_k` | Retrieval config in `experiment_configs` |
| **Evaluation Questions** | Identical question set, ordering, and ground-truth references | Benchmark question dataset |
| **Workload Schedule** | Identical sequence of consumer requests and timing | Deterministic workload seed |

### Cross-Provider Evaluation as an Orthogonal Factor
Alternative embedding and generation providers (e.g. Google Gemini, open-source local embeddings) must be treated as a separate experimental factor. Within any given provider configuration, Strategy A and Strategy B must use equivalent models and parameters.

---

## 4. Authorization & Artifact Identity Architecture

Vector sharing introduces critical multi-tenant and multi-consumer security considerations that do not exist in isolated architectures.

### 4.1 Server-Side Authorization Invariant
- **Untrusted Client Inputs:** Consumer identities and access privileges are determined exclusively by trusted backend logic (e.g., validated JWT claims, organizational session state), never accepted directly from client-supplied HTTP headers or query parameters.
- **Per-Retrieval Authorization Filter:** In Strategy B, retrieval is constrained by a payload filter on the vector database:
  $$\text{Filter: } \text{authorized\_consumers CONTAINS } \text{consumer\_id}$$
  This filter is one component of defense-in-depth, accompanied by application-level validation.
- **Zero-Tolerance Disclosure Rule:** Any instance of a consumer retrieving a chunk from a document they are not authorized to view is classified as a **critical security failure**, resulting in immediate rejection of the configuration. Access control correctness is non-negotiable and cannot be traded off against cost or latency improvements.

### 4.2 Artifact Eligibility Tuple
To prevent stale, incorrect, or corrupted vector retrievals, a shared artifact is eligible for reuse if and only if all elements of the following 5-tuple match the incoming request:

$$\text{Artifact Eligibility} = \langle \text{doc\_id}, \text{version\_hash}, \text{chunk\_config\_hash}, \text{embedding\_model\_id}, \text{dim} \rangle$$

- **Version Matching:** An artifact prepared for Version 1 cannot satisfy a request requiring Version 2.
- **Model Incompatibility Guard:** Vectors generated by different models or dimensionalities (e.g. 768 vs. 3072) must never be mixed in the same collection.

---

## 5. Experimental Workloads & Workload Profiles

The experiment evaluates both strategies across distinct, configurable workload profiles:

```
[Workload Generator]
        │
        ├── 1. Single Consumer Cold Start (N=1, baseline overhead)
        ├── 2. High Reuse Distribution (80% reuse, skewed access)
        ├── 3. Moderate Reuse Distribution (50% reuse)
        ├── 4. Low Reuse / Tail Access (20% reuse, broad corpus)
        └── 5. Document Revision / Freshness Update
```

### 5.1 Profile Definitions
1. **Single-Consumer Cold Start:**  
   $N = 1$ consumer, unprimed cache. Evaluates the pure overhead of the shared layer ($C_m$) when no reuse opportunities exist.
2. **High Reuse (Concentrated Head):**  
   $N \ge 5$ consumers accessing a core set of 20% of documents representing 80% of total query volume (Pareto skew).
3. **Moderate Reuse:**  
   $N \ge 5$ consumers with uniformly distributed document access across a medium corpus.
4. **Low Reuse (Long Tail):**  
   Large document corpus where most documents are queried only once or twice across consumers.
5. **Document Update & Invalidation:**  
   A document is modified mid-run (e.g., at request $T_{50}$). The workload evaluates update detection, artifact invalidation, latency spikes during re-preparation, and stale answer avoidance.

### 5.2 Workload Configuration Schema
Every workload run specifies:
- `num_consumers`: Count of distinct simulated consumer personas.
- `num_documents`: Total available documents in the benchmark corpus.
- `document_versions`: Revision mapping per document over time.
- `total_queries`: Aggregate count of queries issued.
- `skew_factor`: Distribution parameter (e.g. Zipfian $\alpha$) controlling head vs. tail document popularity.
- `random_seed`: Deterministic seed driving query sequences and consumer selection.

---

## 6. Execution Protocol & Contamination Prevention

To ensure experimental integrity across repeated runs:

1. **Pre-flight Cleaning:** Before each repetition, the experiment engine purges temporary collections, drops test vector collections, and verifies database connectivity.
2. **Paired A/B Order:** For each repetition index $r \in \{1 \dots R\}$:
   - Run Strategy A with Seed $S_r$, capturing full event logs.
   - Run Strategy B with identical Seed $S_r$, capturing full event logs.
   - Alternating run order ($A \to B$ vs. $B \to A$) is permitted to control for transient provider-side latency drift.
3. **Cross-Run State Isolation:** Runs must never share collections or cached state from previous runs. Strategy B collections are scoped strictly to `run_id`.
4. **Offline Re-computability:** All raw LLM responses, chunk payloads, token measurements, and timing breakdowns are persisted to the database. Analysis scripts can be executed offline without re-invoking external model APIs.

---

## 7. Threats to Validity & Mitigation Strategies

| Threat Category | Potential Threat | Mitigation Protocol |
|---|---|---|
| **Internal Validity** | Provider API throttling and variable network latency | Record fine-grained timestamps separating local processing from external API calls; use retries with exponential backoff; flag timeout events. |
| **Internal Validity** | Non-deterministic LLM generations | Set temperature to $0.0$; pin model versions (avoid floating `-latest` aliases where possible). |
| **Construct Validity** | Equating semantic similarity with factual correctness | Benchmark against human-reviewed ground truth with strict string and fact-alignment criteria, rather than cosine similarity alone. |
| **Construct Validity** | Unaccounted shared maintenance costs | Instrument local database queries, vector upserts, and authorization filtering explicitly in the $C_m$ cost category. |
| **External Validity** | Synthetic document homogeneity | Use standard, diverse scientific and technical benchmark corpora with variable document lengths and table structures. |
| **Statistical Validity** | Treating intra-run queries as independent repetitions | Treat the entire workload run (or consumer aggregate) as the primary experimental unit for paired hypothesis testing. |
