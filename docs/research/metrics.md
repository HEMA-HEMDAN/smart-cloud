# Research Metrics, Operational Definitions & Economic Models

## 1. Economic Cost Models

To rigorously evaluate the economic viability of demand-driven shared intelligence, we establish two complementary models:
1. **Simplified Analytical Model:** An intuitive framework for theoretical break-even analysis under idealized conditions.
2. **General Event-Based Model:** A fine-grained accounting framework that captures arbitrary document counts, heterogeneous query volumes, document updates, and operational overhead.

---

### 1.1 Simplified Analytical Model

As an explanatory baseline, we represent aggregate workload costs as:

$$\text{Strategy A (Independent Baseline): } C_A = N \cdot (C_p + C_q)$$

$$\text{Strategy B (Shared Intelligence): } C_B = C_p + N \cdot C_q + C_m$$

Where:
- $N$: Number of independent consumers accessing the shared document ($N \ge 1$).
- $C_p$: Document preparation cost (parsing, chunking, embedding generation, vector indexing) per consumer.
- $C_q$: Query processing cost (query embedding, top-k retrieval, LLM answer generation).
- $C_m$: Maintenance, coordination, and storage overhead introduced by the shared layer.

#### Break-Even Condition
Shared preparation yields net economic savings ($C_B < C_A$) when:

$$(N - 1) \cdot C_p > C_m \implies N^* = \frac{C_m}{C_p} + 1$$

- When $C_m = 0$ (negligible shared overhead), $N^* = 1$, meaning any reuse ($N \ge 2$) provides immediate savings.
- If $C_m \ge C_p$, the threshold increases to $N^* \ge 2$, meaning at least two subsequent consumers must reuse the document to amortize the shared layer overhead.

#### Assumptions & Limitations of the Simplified Model
1. **Homogeneity Assumption:** Assumes $C_p$ is identical across all documents and consumers. In real workloads, document sizes, parsing complexities, and token counts vary substantially.
2. **Identical Query Workload:** Assumes query processing cost $C_q$ is identical between strategies. In practice, retrieval filtering in Strategy B may introduce minor latency differences, though token generation costs remain comparable.
3. **Static Corpus:** Does not explicitly account for document updates, re-preparations, or partial cache evictions.

---

### 1.2 General Event-Based Model

For empirical evaluation against realistic, dynamic workloads, we define an event-driven accounting model:

$$C_A = \sum_{d \in D} \sum_{c \in C} \text{cost}_{\text{prep}}(d, c) + \sum_{q \in Q_A} \text{cost}_{\text{query}}(q)$$

$$C_B = \sum_{d \in D} \text{cost}_{\text{prep}}^{\text{shared}}(d) + \text{cost}_{\text{maint}}(B) + \sum_{q \in Q_B} \text{cost}_{\text{query}}(q)$$

Where:
- $D$ is the set of requested document versions.
- $C$ is the set of simulated consumers.
- $Q_A, Q_B$ are the paired query sets issued under each strategy.
- $\text{cost}_{\text{maint}}(B)$ represents the total computational, storage, and synchronization overhead of the shared layer during the run.

---

### 1.3 Cost Categorization & Accounting Boundaries

To maintain accounting rigor and avoid double-counting, costs are segregated into four explicit categories:

| Category | Components Included | Measurement Source | Accounting Treatment |
|---|---|---|---|
| **1. Direct Provider Charges** | LLM generation tokens, embedding API tokens | API response usage metadata or token rate cards | Tracked as actual USD where billed, or estimated USD based on recorded rate cards. |
| **2. Local Compute & Resources** | CPU time (parsing, chunking, filtering), memory allocation, disk I/O | Process telemetry / OS timers | Measured in CPU milliseconds and MB storage. Valued in dollars only when running on cloud VMs. |
| **3. Shared-Layer Maintenance ($C_m$)** | Qdrant vector storage, payload index updates, invalidation bookkeeping | Database measurement logs | Tracked in database bytes, upsert calls, and invalidation latency. |
| **4. Total Workload Cost** | Sum of Categories 1, 2, and 3 | Aggregated run record | Standard comparison metric between Strategy A and Strategy B. |

> **Accounting Rule:** Estimated costs derived from published token rate cards must always be explicitly labeled as **Estimated USD** and must record the model pricing source and effective date. They must never be conflated with direct provider bills.

---

## 2. Operational Metrics & Formal Definitions

### 2.1 Preparation and Reuse Metrics

| Metric | Definition | Mathematical Formulation | Unit | Reporting Policy |
|---|---|---|---|---|
| **Preparation Attempts** | Total requests triggering document ingestion | $\text{Count}(\text{prep\_attempts})$ | Integer | Recorded per document version. |
| **Successful Preparations** | Ingestion pipelines completed without error | $\text{Count}(\text{prep\_success})$ | Integer | Must equal attempts minus failures. |
| **Failed Preparations** | Ingestions interrupted by timeouts or errors | $\text{Count}(\text{prep\_failure})$ | Integer | Errors logged; non-zero triggers investigation. |
| **Eligible Reuse Opportunities** | Consumer requests for a document that has already been prepared in the run | $\sum_{i > 1} \mathbb{I}(\text{doc}_i \in \text{PreparedDocs})$ | Integer | Evaluated at the moment of request. |
| **Reuse Hits** | Demands successfully served from existing intermediate vector artifacts | $\text{Count}(\text{is\_reuse} = \text{True})$ | Integer | Recorded in `preparation_events`. |
| **Preparation Reuse Rate** | Proportion of eligible opportunities satisfied by reuse | $\frac{\text{Reuse Hits}}{\text{Eligible Reuse Opportunities}}$ | $[0.0, 1.0]$ | **Undefined (N/A)** if denominator is 0 (never reported as 0.0). |
| **Avoided Preparations** | Count of duplicate parsing, chunking, and embedding runs eliminated | $\text{Reuse Hits}$ | Integer | Reported separately from Reuse Rate. |
| **Re-preparations** | Ingestion runs triggered by document revisions or cache invalidations | $\text{Count}(\text{re\_preparations})$ | Integer | Tracks freshness overhead. |

---

### 2.2 Cost Comparison Metrics

| Metric | Definition | Mathematical Formulation | Unit |
|---|---|---|---|
| **Total Prep Cost** | Aggregate expenditure spent preparing document vectors | $\sum \text{cost}_{\text{prep}}$ | USD ($) |
| **Total Query Cost** | Aggregate expenditure spent on query embedding & generation | $\sum \text{cost}_{\text{query}}$ | USD ($) |
| **Workload Cost Difference ($\Delta C$)** | Net monetary difference between strategies | $C_A - C_B$ | USD ($) |
| **Relative Cost Savings** | Percentage cost reduction achieved by Strategy B | $\frac{C_A - C_B}{C_A} \times 100\%$ | Percentage (%) |
| **Cost Per Answered Question** | Average workload cost per successfully generated answer | $\frac{C_{\text{strategy}}}{\text{Total Answers Generated}}$ | USD / Query |

---

### 2.3 Latency Metrics & Timing Boundaries

All timing measurements utilize monotonic microsecond clocks (`time.monotonic()`) with defined boundary intervals:

```
[Incoming Request]
       │  t_0 (Request arrival)
       ├── Preparation Phase (Strategy A or Strategy B first-demand)
       │       └── [Parsing] -> [Chunking] -> [Embedding API] -> [Vector Upsert]
       │  t_prep (Preparation complete)
       ├── Retrieval Phase
       │       └── [Query Embedding] -> [Qdrant Top-K Search] -> [Payload Auth Filter]
       │  t_retrieval (Retrieval complete)
       ├── Generation Phase
       │       └── [Prompt Assembly] -> [LLM Generate Content] -> [Response Parse]
       │  t_gen (Generation complete)
       ▼
   Total Latency = (t_gen - t_0)
```

| Metric | Measurement Boundary | Unit | Statistical Summary |
|---|---|---|---|
| **Preparation Latency** | $t_{\text{prep}} - t_0$ (duration of chunking, embedding, and indexing) | ms | Mean, Median (p50), p95 |
| **First-Demand Latency** | Total request latency on first document access (includes prep + query) | ms | Median, p95 |
| **Warm-Request Latency** | Total request latency when intermediate vectors already exist | ms | Median, p95 |
| **End-to-End Query Latency**| $t_{\text{gen}} - t_{\text{prep}}$ (retrieval + generation without preparation) | ms | Median (p50), p95, min, max |

> **Reporting Policy on Failures & Timeouts:** Timed-out or failed requests are flagged with an error status in `request_measurements`. They are **never silently excluded** from latency distributions; they are reported in timeout percentage tallies and counted in worst-case tail percentiles.

---

### 2.4 Retrieval and Answer Quality Metrics

To ensure that knowledge sharing does not degrade retrieval precision or answer veracity:

| Metric | Definition | Measurement Protocol | Unit / Range |
|---|---|---|---|
| **Retrieval Recall@k** | Fraction of relevant ground-truth chunks retrieved in top-k | $\frac{|\text{Retrieved Chunks} \cap \text{Ground Truth Chunks}|}{|\text{Ground Truth Chunks}|}$ | $[0.0, 1.0]$ |
| **Answer Factual Correctness**| Accuracy of the generated response against human-reviewed ground truth | Evaluated against verified reference answers using exact fact-alignment criteria | $[0.0, 1.0]$ |
| **Answer Faithfulness** | Proportion of generated claims directly supported by retrieved chunks | Fact extraction and entailment check against retrieved context | $[0.0, 1.0]$ |
| **Citation Accuracy** | Proportion of chunk citations pointing to verified evidence | Verification that cited `chunk_id` contains the claim | $[0.0, 1.0]$ |
| **Abstention Correctness** | Correctly stating "insufficient information" when context lacks answer | Binary check on unanswerable probe queries | $[0.0, 1.0]$ |

> **Critical Distinction:** **Semantic similarity is NOT factual correctness.** Two statements can have a cosine similarity of $0.92$ while asserting contradictory facts (e.g. "The drug was approved in 2021" vs "The drug was rejected in 2021"). Answer correctness must be measured against documented ground truth, not vector cosine distance.

---

### 2.5 Freshness & Document Update Metrics

| Metric | Definition | Requirement / Target |
|---|---|---|
| **Update Detection Latency** | Elapsed time between a source document update and system detection | Immediate (event-driven) |
| **Obsolete Artifact Invalidation**| Purging or tombstoning of Version $V_1$ chunks when $V_2$ is published | 100% invalidation rate |
| **Stale Answer Rate** | Proportion of post-update queries returning answers based on $V_1$ evidence | Strictly 0.0% |
| **Re-preparation Availability Delay**| Time from $V_2$ arrival until $V_2$ vectors become queryable | Bounded by preparation latency |

> **Update Invariant:** Obsolete document content must never be served as current evidence once an update is effective. During re-preparation, requests must either wait for the new version or explicitly report that the document is updating, depending on the configured consistency model.

---

### 2.6 Authorization Correctness Metrics

| Metric | Definition | Acceptable Threshold |
|---|---|---|
| **Unauthorized Retrieval Attempts** | Queries where consumer attempts retrieval without document authorization | Expected in adversarial tests |
| **Cross-Consumer Leakage Count** | Chunks returned to Consumer $C_i$ from a document authorized only to $C_j$ | **STRICTLY 0** |
| **Cross-Tenant Leakage Count** | Chunks returned across organizational tenant boundaries | **STRICTLY 0** |
| **Filter Failure Rate** | Instances where Qdrant retrieval filter failed to prune unauthorized IDs | **STRICTLY 0.0%** |

> **Zero-Tolerance Policy:** Any confirmed cross-consumer or cross-tenant leakage is a **fatal security failure**. Authorization correctness cannot be balanced as an engineering trade-off against cost or latency improvements.

---

## 3. Statistical Analysis & Reproducibility Guidelines

1. **Experimental Unit of Analysis:**  
   Statistical significance tests must treat the **entire paired workload run (or per-consumer aggregate)** as the unit of analysis ($N_{\text{runs}}$). Individual queries within a single run are autocorrelated and must not be treated as independent degrees of freedom.
2. **Paired Statistical Tests:**  
   - For normally distributed metrics (verified via Shapiro-Wilk test): **Paired Student's t-test**.
   - For skewed or heavy-tailed distributions (typical of latency and cost percentiles): **Wilcoxon signed-rank test**.
3. **Effect Size & Confidence Intervals:**  
   Report non-parametric effect sizes (Cliff's Delta or Cohen's $d$) alongside 95% bootstrap confidence intervals for cost and latency deltas.
4. **No Premature Significance Claims:**  
   Descriptive averages (e.g. "Strategy B was 24% cheaper on Run 1") must never be presented as proof of the general hypothesis without statistical significance testing across repeated randomized runs.
