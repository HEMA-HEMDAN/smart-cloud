# Metrics & Simplified Economic Model

## 1. Economic Cost Model

The experimental analysis utilizes the following simplified economic model:

$$C_{\text{independent}} = N \cdot (C_p + C_q)$$

$$C_{\text{shared}} = C_p + N \cdot C_q + C_m$$

Where:
- $N$: Number of independent consumers accessing the shared document.
- $C_p$: Cost of preparing (chunking, embedding, indexing) a document for one consumer.
- $C_q$: Cost of processing a query/question (retrieval + generation).
- $C_m$: Maintenance and coordination overhead of the shared document layer.

### Break-Even Condition

Shared preparation breaks even when:
$$(N - 1) \cdot C_p > C_m \implies N^* = \frac{C_m}{C_p} + 1$$

When $C_m = 0$ (negligible shared overhead), $N^* = 1$, meaning any reuse ($N \ge 2$) yields net savings.

## 2. Core Metrics

| Metric | Definition | Unit | Target / Goal |
|---|---|---|---|
| **Total Prep Cost** | Aggregate USD spent embedding/chunking documents | USD ($) | Lower in Shared |
| **Avoided Preparations** | Count of preparation calls skipped due to reuse | Count | Higher in Shared |
| **Preparation Reuse Rate** | $\frac{\text{Reuses}}{\text{Total Prep Events}}$ | $[0.0, 1.0]$ | Higher in Shared |
| **Median Latency** | 50th percentile of total request latency | ms | Strategy B comparable to A |
| **p95 Latency** | 95th percentile of request duration | ms | Strategy B bounded tail |
| **Retrieval Recall@k** | Overlap of retrieved chunks with ground truth chunks | $[0.0, 1.0]$ | No degradation ($\ge A$) |
| **Answer Correctness** | Semantic similarity / fact alignment with ground truth | $[0.0, 1.0]$ | No degradation ($\ge A$) |
| **Freshness** | Correct retrieval of updated versions after document revisions | Binary / % | 100% |
| **Cross-Tenant Leakage** | Unauthorized chunk retrieved across consumers | Count | Strictly 0 |

## 3. Analysis Rules

1. **Descriptive Rigor:** Analysis modules present empirical measurements without prematurely declaring the hypothesis "proven".
2. **Missing Data Handling:** Incomplete token usage from upstream providers is explicitly documented and never silently coerced to zero.
3. **Reproducibility:** Experiments specify random seeds and repetition counts to allow paired statistical testing (e.g. Wilcoxon signed-rank test or paired t-test).
