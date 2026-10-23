import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from '../api/client';
import { Server, Database, Cpu, Shield, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';

export const Diagnostics: React.FC = () => {
  const { data: health, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System Diagnostics & Environment</h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time status of backend infrastructure, database schemas, and AI model configurations.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white px-3.5 py-2 rounded-lg text-xs font-medium transition border border-white/10"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {isLoading ? (
        <div className="glass-panel p-12 text-center text-gray-400 rounded-xl font-mono text-sm">
          Querying backend health endpoint...
        </div>
      ) : error ? (
        <div className="glass-panel p-6 border-red-500/30 rounded-xl text-red-400 text-sm">
          Failed to load diagnostics: {(error as Error).message}
        </div>
      ) : health ? (
        <div className="space-y-6">
          {/* Services Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* PostgreSQL */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-sm">PostgreSQL Engine</h3>
                    <span className="text-xs text-gray-400 font-mono">
                      {health.config_summary.db_host}:{health.config_summary.db_port} / {health.config_summary.db_name}
                    </span>
                  </div>
                </div>
                {health.services.postgres.ok ? (
                  <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Connected
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20 font-medium">
                    <XCircle className="w-3.5 h-3.5" />
                    Disconnected
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-400 pt-2 border-t border-white/5 flex justify-between">
                <span>Roundtrip Latency:</span>
                <span className="font-mono text-white">
                  {health.services.postgres.latency_ms !== null ? `${health.services.postgres.latency_ms} ms` : 'N/A'}
                </span>
              </div>
              <div className="text-xs text-gray-400 flex justify-between">
                <span>Isolated Research Schema:</span>
                <span className="font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                  {health.config_summary.research_schema}
                </span>
              </div>
            </div>

            {/* Qdrant */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-sm">Qdrant Vector DB</h3>
                    <span className="text-xs text-gray-400 font-mono">
                      {health.config_summary.qdrant_host}:{health.config_summary.qdrant_port}
                    </span>
                  </div>
                </div>
                {health.services.qdrant.ok ? (
                  <span className="flex items-center gap-1 text-xs text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-500/20 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Connected
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20 font-medium">
                    <XCircle className="w-3.5 h-3.5" />
                    Disconnected
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-400 pt-2 border-t border-white/5 flex justify-between">
                <span>Vector Dimension:</span>
                <span className="font-mono text-white">
                  {health.config_summary.embedding_dimension} dimensions
                </span>
              </div>
              <div className="text-xs text-gray-400 flex justify-between">
                <span>Roundtrip Latency:</span>
                <span className="font-mono text-white">
                  {health.services.qdrant.latency_ms !== null ? `${health.services.qdrant.latency_ms} ms` : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Model & Non-sensitive Configuration Summary */}
          <div className="glass-panel p-6 rounded-xl border border-white/10 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-purple-400" />
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                  Provider & Runtime Specifications
                </h2>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <Shield className="w-3.5 h-3.5 text-emerald-400" />
                <span>Zero Secrets Exposed Contract</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3.5 rounded-lg bg-white/5 space-y-2">
                <div className="text-gray-400 font-semibold mb-1">Embedding Provider:</div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Model:</span>
                  <span className="text-white">{health.config_summary.gemini_embedding_model}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Dimension:</span>
                  <span className="text-white">{health.config_summary.embedding_dimension}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">API Key Configured:</span>
                  <span className={health.config_summary.gemini_configured ? "text-emerald-400" : "text-amber-400"}>
                    {health.config_summary.gemini_configured ? "Yes (Active)" : "No (Mock fallback available)"}
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-white/5 space-y-2">
                <div className="text-gray-400 font-semibold mb-1">Generation Provider:</div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Model:</span>
                  <span className="text-white">{health.config_summary.gemini_generation_model}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Environment:</span>
                  <span className="text-white">{health.environment}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">API Version:</span>
                  <span className="text-white">{health.version}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
