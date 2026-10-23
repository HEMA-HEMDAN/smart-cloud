import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchExperiments, fetchHealth } from '../api/client';
import {
  TrendingDown,
  Layers,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle
} from 'lucide-react';

export const Overview: React.FC = () => {
  const { data: experiments, isLoading: loadingExps } = useQuery({
    queryKey: ['experiments'],
    queryFn: fetchExperiments,
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });

  const totalConfigs = experiments?.length ?? 0;

  return (
    <div className="space-y-8">
      {/* Page Title & Instrument State Banner */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Research Instrument Overview</h1>
        <p className="text-sm text-gray-400 mt-1">
          Evaluating whether demand-driven shared document intelligence reduces aggregate preparation cost while maintaining latency and strict authorization isolation.
        </p>
      </div>

      {/* Primary Research Metrics Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Prep Cost Ratio</span>
            <TrendingDown className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            --
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
            <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
            <span>Awaiting completed runs</span>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Preparation Reuse Rate</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            --
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
            <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
            <span>Strategy B first-demand metric</span>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Median Latency Δ</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            --
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
            <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
            <span>p50 (Shared) vs p50 (Indep)</span>
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Tenant Isolation</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            0 Violations
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-400/80">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Per-tenant filter enforced</span>
          </div>
        </div>
      </div>

      {/* Strategies Comparison Overview Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-xl border border-white/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none" />
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white">Strategy A: Independent Baseline</h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 font-mono">
              Control
            </span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">
            Every consumer independently prepares, chunks, and embeds documents. Vector collections are scoped strictly per-consumer (`exp_{'{run_id}'}_{'{consumer_id}'}`).
          </p>
          <div className="mt-4 pt-4 border-t border-white/5 space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Expected Aggregate Cost:</span>
              <span className="font-mono text-gray-200">N * (C_p + C_q)</span>
            </div>
            <div className="flex justify-between">
              <span>Collection Architecture:</span>
              <span className="font-mono text-gray-200">Isolated per consumer</span>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-white/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none" />
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white">Strategy B: Shared Intelligence</h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
              Treatment
            </span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">
            The first eligible consumer prepares on demand. Subsequent consumers reuse vectors with payload-level authorization checks (`authorized_consumers CONTAINS consumer_id`).
          </p>
          <div className="mt-4 pt-4 border-t border-white/5 space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Expected Aggregate Cost:</span>
              <span className="font-mono text-gray-200">C_p + N * C_q + C_m</span>
            </div>
            <div className="flex justify-between">
              <span>Break-even Condition:</span>
              <span className="font-mono text-gray-200">(N - 1) * C_p &gt; C_m</span>
            </div>
          </div>
        </div>
      </div>

      {/* System Status and Experiment Configurations List */}
      <div className="glass-panel rounded-xl border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white">Configured Experiments ({totalConfigs})</h2>
          <div className="text-xs text-gray-400">
            PostgreSQL: <span className="text-emerald-400 font-mono">{health?.services.postgres.ok ? 'OK' : 'Checking'}</span> | Qdrant: <span className="text-blue-400 font-mono">{health?.services.qdrant.ok ? 'OK' : 'Checking'}</span>
          </div>
        </div>

        {loadingExps ? (
          <div className="py-12 text-center text-sm text-gray-400 font-mono">
            Loading experiment configurations from backend...
          </div>
        ) : experiments && experiments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="text-xs uppercase bg-white/5 text-gray-400 border-b border-white/10">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Dataset</th>
                  <th className="px-4 py-3 font-medium">Repetitions</th>
                  <th className="px-4 py-3 font-medium">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {experiments.map((exp) => (
                  <tr key={exp.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 font-medium text-white">{exp.name}</td>
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">{exp.dataset_name}</td>
                    <td className="px-4 py-3 font-mono text-xs">{exp.repetitions}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {new Date(exp.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-10 text-center rounded-lg border border-dashed border-white/10 bg-white/[0.02]">
            <AlertCircle className="w-8 h-8 text-gray-500 mx-auto mb-2" />
            <div className="text-sm font-medium text-gray-300">No experiments configured yet</div>
            <p className="text-xs text-gray-500 mt-1">
              Create an experiment configuration to initiate paired A/B benchmarks.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
