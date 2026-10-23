export interface ServiceStatus {
  ok: boolean;
  detail?: string | null;
  latency_ms?: number | null;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  services: {
    postgres: ServiceStatus;
    qdrant: ServiceStatus;
  };
  config_summary: {
    db_host: string;
    db_port: number;
    db_name: string;
    qdrant_host: string;
    qdrant_port: number;
    gemini_embedding_model: string;
    gemini_generation_model: string;
    embedding_dimension: number;
    research_schema: string;
    qdrant_collection_independent: string;
    qdrant_collection_shared: string;
    gemini_configured: boolean;
  };
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_hash: string;
  title: string | null;
  content_length_chars: number | null;
  created_at: string;
}

export interface DocumentChunk {
  chunk_id: string;
  chunk_index: number;
  start_char: number;
  end_char: number;
  text: string;
  token_estimate: number;
}

export interface DocumentPreview {
  id: string;
  document_id: string;
  version_hash: string;
  title: string | null;
  content_length_chars: number;
  text_preview: string;
  chunk_size: number;
  chunk_overlap: number;
  total_chunks: number;
  chunks: DocumentChunk[];
}

export interface BenchmarkQuestion {
  question_id: string;
  question_text: string;
  expected_answer?: string;
  expected_chunk_ids?: string[];
}

export interface ExperimentConfig {
  id: string;
  name: string;
  description: string | null;
  dataset_name: string;
  repetitions: number;
  created_at: string;
  chunking_config?: Record<string, unknown>;
  retrieval_config?: Record<string, unknown>;
  workload_config?: {
    document_version_id?: string;
    consumer_count?: number;
    type?: string;
    provider?: string;
    benchmark_questions?: BenchmarkQuestion[];
    [key: string]: unknown;
  };
}

export interface ExperimentRun {
  id: string;
  config_id: string;
  repetition_index: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface RunProgress {
  run_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'unknown';
  current_repetition?: number;
  total_repetitions?: number;
  current_strategy?: string;
  completed_requests?: number;
  failed_requests?: number;
  security_violations?: number;
  elapsed_seconds?: number;
  error?: string;
}

export interface MeasurementItem {
  id: string;
  run_id: string;
  strategy: string;
  consumer_id: string | null;
  question_id: string;
  question_text: string;
  retrieved_chunk_ids: string[] | null;
  retrieval_duration_ms: number | null;
  answer_text: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  generation_duration_ms: number | null;
  total_duration_ms: number | null;
  estimated_generation_cost_usd: number | null;
  ground_truth_answer: string | null;
  recall_at_k: number | null;
  answer_correctness: number | null;
  error_message: string | null;
}

export interface StrategyCostSummary {
  total_estimated_usd?: number | null;
  per_question_mean_usd?: number | null;
  preparation_estimated_usd?: number | null;
  total_workload_usd?: number | null;
  total_questions?: number;
}

export interface StrategyLatencySummary {
  p50_ms?: number | null;
  p95_ms?: number | null;
  mean_ms?: number | null;
  sample_size?: number;
}

export interface ResultsSummary {
  run_id: string;
  status: string;
  cost_summary: {
    per_strategy: Record<string, StrategyCostSummary>;
    note?: string;
  };
  latency_summary: {
    per_strategy: Record<string, StrategyLatencySummary>;
    note?: string;
  };
  reuse_summary: {
    total_preparation_events?: number;
    first_preparations?: number;
    reuses?: number;
    reuse_rate?: number | null;
    avoided_preparations?: number;
    note?: string;
  };
  quality_summary: {
    per_strategy: Record<
      string,
      {
        mean_recall_at_k?: number | null;
        mean_correctness?: number | null;
        evaluated_queries?: number;
      }
    >;
    note?: string;
  };
  security_violations: number;
  total_measurements: number;
  total_preparations: number;
  note?: string | null;
}

export interface CreateExperimentPayload {
  name: string;
  description?: string;
  provider_config_id: string;
  dataset_name: string;
  chunking_config: Record<string, unknown>;
  retrieval_config: Record<string, unknown>;
  workload_config: Record<string, unknown>;
  random_seed?: number;
  repetitions: number;
}

const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentVersion> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // fallback
    }
    throw new Error(errorDetail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentVersion[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) {
    throw new Error(`Failed to fetch documents: ${res.statusText}`);
  }
  return res.json();
}

export async function previewDocumentChunks(
  docId: string,
  chunkSize: number = 512,
  chunkOverlap: number = 64
): Promise<DocumentPreview> {
  const res = await fetch(
    `${API_BASE}/documents/${docId}/preview?chunk_size=${chunkSize}&chunk_overlap=${chunkOverlap}`
  );
  if (!res.ok) {
    throw new Error(`Failed to preview document chunks: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExperiments(): Promise<ExperimentConfig[]> {
  const res = await fetch(`${API_BASE}/experiments`);
  if (!res.ok) {
    throw new Error(`Failed to fetch experiments: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExperiment(id: string): Promise<ExperimentConfig> {
  const res = await fetch(`${API_BASE}/experiments/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch experiment ${id}: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExperimentRuns(id: string): Promise<ExperimentRun[]> {
  const res = await fetch(`${API_BASE}/experiments/${id}/runs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch runs for experiment ${id}: ${res.statusText}`);
  }
  return res.json();
}

export async function createExperiment(payload: CreateExperimentPayload): Promise<ExperimentConfig> {
  const res = await fetch(`${API_BASE}/experiments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // fallback
    }
    throw new Error(errorDetail || `Failed to create experiment (${res.status})`);
  }
  return res.json();
}

export async function startNewRun(experimentId: string): Promise<ExperimentRun> {
  const res = await fetch(`${API_BASE}/experiments/${experimentId}/start`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to start run: ${res.statusText}`);
  }
  return res.json();
}

export async function cancelRun(experimentId: string, runId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/experiments/${experimentId}/runs/${runId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to cancel run: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRunProgress(runId: string): Promise<RunProgress> {
  const res = await fetch(`${API_BASE}/results/progress/${runId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run progress: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRunResults(runId: string): Promise<ResultsSummary> {
  const res = await fetch(`${API_BASE}/results/${runId}/results`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run results: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRunMeasurements(
  runId: string,
  strategy?: string,
  limit: number = 100,
  offset: number = 0
): Promise<MeasurementItem[]> {
  const url = new URL(`${window.location.origin}${API_BASE}/results/${runId}/measurements`);
  if (strategy) url.searchParams.set('strategy', strategy);
  url.searchParams.set('limit', String(limit));
  url.searchParams.set('offset', String(offset));

  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Failed to fetch measurements: ${res.statusText}`);
  }
  return res.json();
}

export function getExportUrl(runId: string, format: 'csv' | 'jsonl' = 'csv'): string {
  return `${API_BASE}/results/${runId}/export?format=${format}`;
}
