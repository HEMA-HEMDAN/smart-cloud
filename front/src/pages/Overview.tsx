import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  fetchExperiments,
  fetchHealth,
  fetchExperimentRuns,
  fetchRunResults,
} from '../api/client';
import {
  TrendingDown,
  Layers,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  PlusCircle,
  ArrowRight,
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

  const latestExp = experiments?.[0];

  // Fetch runs for the latest experiment
  const { data: latestRuns } = useQuery({
    queryKey: ['experiment-runs', latestExp?.id],
    queryFn: () => fetchExperimentRuns(latestExp!.id),
    enabled: Boolean(latestExp?.id),
  });

  const completedRun = latestRuns?.find((r) => r.status === 'completed');

  // Fetch results if a completed run exists
  const { data: results } = useQuery({
    queryKey: ['run-results', completedRun?.id],
    queryFn: () => fetchRunResults(completedRun!.id),
    enabled: Boolean(completedRun?.id),
  });

  const totalConfigs = experiments?.length ?? 0;

  // Compute metrics from results
  const costA = results?.cost_summary?.per_strategy?.independent;
  const costB = results?.cost_summary?.per_strategy?.shared;
  const totalA = costA?.total_workload_usd || 0;
  const totalB = costB?.total_workload_usd || 0;
  const savingsPct = totalA > 0 ? (((totalA - totalB) / totalA) * 100).toFixed(1) : null;

  const reuseRate =
    results?.reuse_summary?.reuse_rate !== null && results?.reuse_summary?.reuse_rate !== undefined
      ? `${(results.reuse_summary.reuse_rate * 100).toFixed(1)}%`
      : null;

  const latA = results?.latency_summary?.per_strategy?.independent?.p50_ms;
  const latB = results?.latency_summary?.per_strategy?.shared?.p50_ms;
  const latencyDelta = latA && latB ? `${(latB - latA).toFixed(0)} ms` : null;

  return (
    <div className="space-y-8 pb-12">
      {/* Page Title & Instrument State Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Research Instrument Overview</h1>
          <p className="text-sm text-gray-400 mt-1">
            Evaluating whether demand-driven shared document intelligence reduces aggregate preparation cost while maintaining latency and strict authorization isolation.
          </p>
        </div>
        <Link
          to="/experiments/new"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-xs font-semibold transition shrink-0 shadow-lg shadow-blue-600/20"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Experiment</span>
        </Link>
      </div>

      {/* Primary Research Metrics Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Cost Savings</span>
            <TrendingDown className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {savingsPct !== null ? `${savingsPct}%` : '--'}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
            {savingsPct !== null ? (
              <span className="text-emerald-400 text-[11px] font-mono">Strategy B vs Baseline A</span>
            ) : (
              <>
                <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
                <span>Awaiting completed runs</span>
              </>
            )}
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Preparation Reuse Rate</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {reuseRate !== null ? reuseRate : '--'}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
            {reuseRate !== null ? (
              <span className="text-blue-400 text-[11px] font-mono">
                {results?.reuse_summary?.avoided_preparations || 0} avoided preps
              </span>
            ) : (
              <>
                <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
                <span>Strategy B reuse metric</span>
              </>
            )}
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Median Latency Δ</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {latencyDelta !== null ? latencyDelta : '--'}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
            {latB ? (
              <span className="text-purple-400 text-[11px] font-mono">p50: {latB.toFixed(0)}ms (Shared)</span>
            ) : (
              <>
                <HelpCircle className="w-3.5 h-3.5 text-gray-500" />
                <span>p50 (Shared) vs p50 (Indep)</span>
              </>
            )}
          </div>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Tenant Isolation</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {results ? `${results.security_violations} Violations` : '0 Violations'}
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
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
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
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/experiments/${exp.id}`}
                        className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium"
                      >
                        <span>View Runs</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
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
            <p className="text-xs text-gray-500 mt-1 mb-4">
              Create an experiment configuration to initiate paired A/B benchmarks.
            </p>
            <Link
              to="/experiments/new"
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-xs font-semibold transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Launch First Experiment</span>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};
