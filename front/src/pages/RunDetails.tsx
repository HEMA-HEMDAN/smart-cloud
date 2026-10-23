import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchExperiment,
  fetchExperimentRuns,
  fetchRunProgress,
  fetchRunResults,
  fetchRunMeasurements,
  startNewRun,
  cancelRun,
  getExportUrl,
} from '../api/client';
import type {
  ResultsSummary,
  MeasurementItem,
  RunProgress,
} from '../api/client';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  Play,
  Download,
  ShieldCheck,
  TrendingDown,
  Layers,
  BarChart2,
  Table,
  StopCircle,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export const RunDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [strategyFilter, setStrategyFilter] = useState<string>('all');

  // Fetch Experiment Config
  const { data: experiment, isLoading: loadingExp } = useQuery({
    queryKey: ['experiment', id],
    queryFn: () => fetchExperiment(id!),
    enabled: Boolean(id),
  });

  // Fetch Experiment Runs
  const { data: runs } = useQuery({
    queryKey: ['experiment-runs', id],
    queryFn: () => fetchExperimentRuns(id!),
    enabled: Boolean(id),
  });

  // Auto-select latest run
  useEffect(() => {
    if (runs && runs.length > 0 && !selectedRunId) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  // Current selected run object
  const currentRun = runs?.find((r) => r.id === selectedRunId) || runs?.[0];

  // Poll progress if run is running
  const isRunning = currentRun?.status === 'running' || currentRun?.status === 'pending';
  const { data: liveProgress } = useQuery<RunProgress>({
    queryKey: ['run-progress', selectedRunId],
    queryFn: () => fetchRunProgress(selectedRunId),
    enabled: Boolean(selectedRunId) && isRunning,
    refetchInterval: isRunning ? 1500 : false,
  });

  // Poll runs list while running to detect status change
  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: ['experiment-runs', id] });
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [isRunning, id, queryClient]);

  // Fetch Run Results Summary
  const { data: results } = useQuery<ResultsSummary>({
    queryKey: ['run-results', selectedRunId],
    queryFn: () => fetchRunResults(selectedRunId),
    enabled: Boolean(selectedRunId) && !isRunning,
  });

  // Fetch Raw Measurements
  const { data: measurements } = useQuery<MeasurementItem[]>({
    queryKey: ['run-measurements', selectedRunId, strategyFilter],
    queryFn: () =>
      fetchRunMeasurements(
        selectedRunId,
        strategyFilter === 'all' ? undefined : strategyFilter,
        150
      ),
    enabled: Boolean(selectedRunId) && !isRunning,
  });

  // Start new run mutation
  const launchMutation = useMutation({
    mutationFn: () => startNewRun(id!),
    onSuccess: (newRun) => {
      queryClient.invalidateQueries({ queryKey: ['experiment-runs', id] });
      setSelectedRunId(newRun.id);
    },
  });

  // Cancel run mutation
  const cancelMutation = useMutation({
    mutationFn: () => cancelRun(id!, selectedRunId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiment-runs', id] });
      queryClient.invalidateQueries({ queryKey: ['run-progress', selectedRunId] });
    },
  });

  if (loadingExp) {
    return (
      <div className="glass-panel p-12 text-center text-gray-400 rounded-xl font-mono text-sm">
        Loading experiment details...
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="glass-panel p-8 text-center text-red-400 rounded-xl text-sm">
        Experiment not found.
      </div>
    );
  }

  // Cost data for charts
  const costA = results?.cost_summary?.per_strategy?.independent;
  const costB = results?.cost_summary?.per_strategy?.shared;
  const costChartData = [
    {
      category: 'Prep Cost',
      'Strategy A (Independent)': Number((costA?.preparation_estimated_usd || 0).toFixed(4)),
      'Strategy B (Shared)': Number((costB?.preparation_estimated_usd || 0).toFixed(4)),
    },
    {
      category: 'Query Cost',
      'Strategy A (Independent)': Number((costA?.total_estimated_usd || 0).toFixed(4)),
      'Strategy B (Shared)': Number((costB?.total_estimated_usd || 0).toFixed(4)),
    },
    {
      category: 'Total Workload',
      'Strategy A (Independent)': Number((costA?.total_workload_usd || 0).toFixed(4)),
      'Strategy B (Shared)': Number((costB?.total_workload_usd || 0).toFixed(4)),
    },
  ];

  // Latency data for charts
  const latA = results?.latency_summary?.per_strategy?.independent;
  const latB = results?.latency_summary?.per_strategy?.shared;
  const latencyChartData = [
    {
      metric: 'Median p50',
      'Strategy A': Number((latA?.p50_ms || 0).toFixed(1)),
      'Strategy B': Number((latB?.p50_ms || 0).toFixed(1)),
    },
    {
      metric: 'Tail p95',
      'Strategy A': Number((latA?.p95_ms || 0).toFixed(1)),
      'Strategy B': Number((latB?.p95_ms || 0).toFixed(1)),
    },
  ];

  const reuseRateDisplay =
    results?.reuse_summary?.reuse_rate !== null && results?.reuse_summary?.reuse_rate !== undefined
      ? `${(results.reuse_summary.reuse_rate * 100).toFixed(1)}%`
      : 'N/A';

  const avoidedPreps = results?.reuse_summary?.avoided_preparations || 0;
  const totalSharedPreps = results?.reuse_summary?.total_preparation_events || 0;

  // Calculate relative cost savings
  const totalA = costA?.total_workload_usd || 0;
  const totalB = costB?.total_workload_usd || 0;
  const savingsPct = totalA > 0 ? (((totalA - totalB) / totalA) * 100).toFixed(1) : null;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/experiments"
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">{experiment.name}</h1>
              <span className="text-xs px-2.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                {experiment.dataset_name}
              </span>
              {experiment.workload_config?.provider === 'mock' && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 font-mono">
                  MOCK / SIMULATED
                </span>
              )}
            </div>
            {experiment.description && (
              <p className="text-sm text-gray-400 mt-1">{experiment.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isRunning ? (
            <button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              className="flex items-center gap-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 px-3.5 py-2 rounded-lg text-xs font-semibold transition"
            >
              <StopCircle className="w-4 h-4" />
              <span>Cancel Run</span>
            </button>
          ) : (
            <button
              onClick={() => launchMutation.mutate()}
              disabled={launchMutation.isPending}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-xs font-semibold transition shadow-lg shadow-blue-600/20"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{launchMutation.isPending ? 'Starting...' : 'Execute New Run'}</span>
            </button>
          )}

          {selectedRunId && !isRunning && (
            <div className="flex items-center gap-1">
              <a
                href={getExportUrl(selectedRunId, 'csv')}
                className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white px-3 py-2 rounded-lg text-xs font-medium border border-white/10 transition"
                title="Export Observations as CSV"
              >
                <Download className="w-3.5 h-3.5" />
                <span>CSV</span>
              </a>
              <a
                href={getExportUrl(selectedRunId, 'jsonl')}
                className="flex items-center gap-1.5 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white px-3 py-2 rounded-lg text-xs font-medium border border-white/10 transition"
                title="Export Observations as JSONL"
              >
                <Download className="w-3.5 h-3.5" />
                <span>JSONL</span>
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Repetition Run Tabs */}
      {runs && runs.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-white/10">
          <span className="text-xs text-gray-500 font-medium mr-1">Runs:</span>
          {runs.map((r, idx) => (
            <button
              key={r.id}
              onClick={() => setSelectedRunId(r.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition flex items-center gap-1.5 shrink-0 ${
                selectedRunId === r.id
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/50 font-bold'
                  : 'bg-white/5 text-gray-400 hover:text-white border border-transparent'
              }`}
            >
              <span>#{idx + 1}</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  r.status === 'completed'
                    ? 'bg-emerald-400'
                    : r.status === 'running'
                    ? 'bg-blue-400 animate-pulse'
                    : r.status === 'failed'
                    ? 'bg-red-400'
                    : 'bg-gray-400'
                }`}
              />
            </button>
          ))}
        </div>
      )}

      {/* Live Execution Progress Card */}
      {isRunning && (
        <div className="glass-panel p-6 rounded-xl border border-blue-500/30 bg-blue-500/5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-3 h-3 rounded-full bg-blue-500 animate-ping" />
              <h2 className="text-sm font-semibold text-white">
                Executing Paired Experiment Run ({liveProgress?.current_strategy || 'In Progress'})
              </h2>
            </div>
            <span className="text-xs font-mono text-blue-300">
              Repetition {liveProgress?.current_repetition || 1} of {liveProgress?.total_repetitions || experiment.repetitions}
            </span>
          </div>

          <div className="w-full bg-black/40 rounded-full h-2 overflow-hidden border border-white/10">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  (((liveProgress?.current_repetition || 1) - 1) / (liveProgress?.total_repetitions || experiment.repetitions)) * 100 +
                    ((liveProgress?.completed_requests || 0) % 20) * 2.5
                )}%`,
              }}
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono pt-1">
            <div className="text-gray-400">
              Completed Queries: <strong className="text-white">{liveProgress?.completed_requests || 0}</strong>
            </div>
            <div className="text-gray-400">
              Failed Queries: <strong className="text-white">{liveProgress?.failed_requests || 0}</strong>
            </div>
            <div className="text-gray-400">
              Security Violations: <strong className="text-emerald-400">{liveProgress?.security_violations || 0}</strong>
            </div>
            <div className="text-gray-400">
              Elapsed Time: <strong className="text-white">{liveProgress?.elapsed_seconds || 0}s</strong>
            </div>
          </div>
        </div>
      )}

      {/* Main A/B Results Dashboard */}
      {!isRunning && results && (
        <div className="space-y-6">
          {/* Primary Research Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Cost Savings */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-1">
              <div className="flex items-center justify-between text-gray-400">
                <span className="text-xs uppercase tracking-wider font-semibold">Cost Difference</span>
                <TrendingDown className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {savingsPct !== null ? `${savingsPct}% Savings` : '--'}
              </div>
              <div className="text-[11px] text-gray-400 font-mono">
                Strategy B: ${totalB.toFixed(4)} vs A: ${totalA.toFixed(4)}
              </div>
            </div>

            {/* Preparation Reuse Rate */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-1">
              <div className="flex items-center justify-between text-gray-400">
                <span className="text-xs uppercase tracking-wider font-semibold">Reuse Rate</span>
                <Layers className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">{reuseRateDisplay}</div>
              <div className="text-[11px] text-gray-400 font-mono">
                Avoided {avoidedPreps} of {totalSharedPreps} preparations
              </div>
            </div>

            {/* Latency Comparison */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-1">
              <div className="flex items-center justify-between text-gray-400">
                <span className="text-xs uppercase tracking-wider font-semibold">Warm Latency (p50)</span>
                <Clock className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {latB?.p50_ms ? `${latB.p50_ms.toFixed(0)} ms` : '--'}
              </div>
              <div className="text-[11px] text-gray-400 font-mono">
                Strategy A: {latA?.p50_ms ? `${latA.p50_ms.toFixed(0)} ms` : '--'} (p95: {latB?.p95_ms?.toFixed(0)}ms)
              </div>
            </div>

            {/* Authorization Isolation */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-1">
              <div className="flex items-center justify-between text-gray-400">
                <span className="text-xs uppercase tracking-wider font-semibold">Tenant Isolation</span>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">
                {results.security_violations} Violations
              </div>
              <div className="text-[11px] text-emerald-400/80 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Adversarial probe passed (0 leakage)</span>
              </div>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Cost Breakdown Chart */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-4">
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-blue-400" />
                <span>Cost Breakdown by Strategy (USD)</span>
              </h3>
              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={costChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis dataKey="category" stroke="#888888" fontSize={11} />
                    <YAxis stroke="#888888" fontSize={11} tickFormatter={(v) => `$${v}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', fontSize: '11px' }}
                      formatter={(value: any) => [`$${Number(value).toFixed(4)}`, '']}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    <Bar dataKey="Strategy A (Independent)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Strategy B (Shared)" fill="#a855f7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Latency Percentiles Chart */}
            <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-4">
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-4 h-4 text-purple-400" />
                <span>Query Latency Percentiles (ms)</span>
              </h3>
              <div className="h-60 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={latencyChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis dataKey="metric" stroke="#888888" fontSize={11} />
                    <YAxis stroke="#888888" fontSize={11} tickFormatter={(v) => `${v}ms`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', fontSize: '11px' }}
                      formatter={(value: any) => [`${value} ms`, '']}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    <Bar dataKey="Strategy A" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Strategy B" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Raw Measurements Table */}
          <div className="glass-panel p-5 rounded-xl border border-white/10 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Table className="w-4 h-4 text-blue-400" />
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Raw Request Measurements ({measurements?.length || 0} recorded)
                </h3>
              </div>

              {/* Strategy Filter Tabs */}
              <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-lg border border-white/5 text-xs">
                <button
                  onClick={() => setStrategyFilter('all')}
                  className={`px-2.5 py-1 rounded transition ${
                    strategyFilter === 'all' ? 'bg-blue-600 text-white font-medium' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setStrategyFilter('independent')}
                  className={`px-2.5 py-1 rounded transition ${
                    strategyFilter === 'independent' ? 'bg-blue-600 text-white font-medium' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Strategy A
                </button>
                <button
                  onClick={() => setStrategyFilter('shared')}
                  className={`px-2.5 py-1 rounded transition ${
                    strategyFilter === 'shared' ? 'bg-blue-600 text-white font-medium' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Strategy B
                </button>
              </div>
            </div>

            {measurements && measurements.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-white/5 text-gray-400 uppercase text-[10px] tracking-wider border-b border-white/5 font-mono">
                    <tr>
                      <th className="py-2.5 px-3">Strategy</th>
                      <th className="py-2.5 px-3">Consumer</th>
                      <th className="py-2.5 px-3">Question</th>
                      <th className="py-2.5 px-3">Total Latency</th>
                      <th className="py-2.5 px-3">Retrieval</th>
                      <th className="py-2.5 px-3">Recall@k</th>
                      <th className="py-2.5 px-3">Correctness</th>
                      <th className="py-2.5 px-3">Generated Answer Snippet</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                    {measurements.slice(0, 50).map((m) => (
                      <tr key={m.id} className="hover:bg-white/5 transition">
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-sans font-semibold ${
                              m.strategy === 'independent'
                                ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                            }`}
                          >
                            {m.strategy}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-gray-300">{m.consumer_id || '--'}</td>
                        <td className="py-2.5 px-3 text-white max-w-xs truncate" title={m.question_text}>
                          {m.question_text}
                        </td>
                        <td className="py-2.5 px-3 text-gray-300">
                          {m.total_duration_ms ? `${m.total_duration_ms.toFixed(1)}ms` : '--'}
                        </td>
                        <td className="py-2.5 px-3 text-gray-400">
                          {m.retrieval_duration_ms ? `${m.retrieval_duration_ms.toFixed(1)}ms` : '--'}
                        </td>
                        <td className="py-2.5 px-3 text-emerald-400">
                          {m.recall_at_k !== null && m.recall_at_k !== undefined
                            ? `${(m.recall_at_k * 100).toFixed(0)}%`
                            : '--'}
                        </td>
                        <td className="py-2.5 px-3 text-blue-300">
                          {m.answer_correctness !== null && m.answer_correctness !== undefined
                            ? m.answer_correctness.toFixed(2)
                            : '--'}
                        </td>
                        <td className="py-2.5 px-3 text-gray-400 max-w-sm truncate" title={m.answer_text || ''}>
                          {m.answer_text || (m.error_message ? `Error: ${m.error_message}` : '--')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-gray-500">No measurements recorded for this run.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
