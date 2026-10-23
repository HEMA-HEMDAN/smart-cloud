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

export interface ExperimentConfig {
  id: string;
  name: string;
  description: string | null;
  dataset_name: string;
  repetitions: number;
  created_at: string;
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
    throw new Error(`Failed to create experiment: ${res.statusText}`);
  }
  return res.json();
}
