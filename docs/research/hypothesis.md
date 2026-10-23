# Research Hypothesis & Experimental Variables

## 1. Primary Hypothesis

**A demand-driven shared document-intelligence layer can reduce aggregate document-preparation and processing costs when documents are reused across multiple independent consumers, while maintaining acceptable answer quality, retrieval quality, freshness, latency, and strict authorization correctness.**

## 2. Experimental Strategies

### Strategy A: Independent RAG Baseline
- Each simulated consumer independently prepares and indexes its own documents.
- Document parsing, chunking, embedding, and vector indexing are strictly consumer-isolated.
- Vector collections are named per consumer: `exp_{run_id}_{consumer_id}`.
- No vectors, chunks, or cached answers are shared across consumers.

### Strategy B: Shared Intelligence RAG
- The first eligible consumer prepares a document on demand.
- Subsequent authorized consumers reuse existing vectors and chunk metadata without repeating embedding or preparation pipelines.
- Vectors reside in a shared run-scoped collection: `exp_{run_id}_shared`.
- Authorization filter is applied strictly on retrieval: `authorized_consumers CONTAINS consumer_id`.
- Unavoidable cross-tenant isolation violations are treated as critical security failures, not acceptable trade-offs.

## 3. Controlled Variables

Within every paired A/B comparison, the following variables must remain constant:
- **Corpus & Document Content:** Identical raw documents and version hashes.
- **Chunking Configuration:** Identical chunk sizes (e.g., 512 chars) and chunk overlap (e.g., 64 chars).
- **Embedding Model:** Identical model ID, provider, and embedding dimensions.
- **Generation Model:** Identical model ID, system prompts, temperature (0.0 for determinism), and max tokens.
- **Retrieval Parameters:** Identical `top_k` and similarity metrics.
- **Evaluation Benchmark:** Identical questions, ground-truth references, and sequence of requests.
