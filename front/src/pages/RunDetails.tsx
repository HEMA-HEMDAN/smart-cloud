import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchExperiment, fetchExperimentRuns } from '../api/client';
import { ArrowLeft, Clock, Calendar, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export const RunDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const { data: experiment, isLoading: loadingExp } = useQuery({
    queryKey: ['experiment', id],
    queryFn: () => fetchExperiment(id!),
    enabled: Boolean(id),
  });

  const { data: runs, isLoading: loadingRuns } = useQuery({
    queryKey: ['experiment-runs', id],
    queryFn: () => fetchExperimentRuns(id!),
    enabled: Boolean(id),
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

  return (
    <div className="space-y-6">
      {/* Header */}
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
          </div>
          {experiment.description && (
            <p className="text-sm text-gray-400 mt-1">{experiment.description}</p>
          )}
        </div>
      </div>

      {/* Meta Specs */}
      <div className="glass-panel p-5 rounded-xl border border-white/10 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div>
          <span className="text-gray-500 block">Repetitions Target:</span>
          <span className="text-white font-mono font-medium text-sm">{experiment.repetitions}</span>
        </div>
        <div>
          <span className="text-gray-500 block">Created On:</span>
          <span className="text-white font-mono font-medium text-sm">
            {new Date(experiment.created_at).toLocaleDateString()}
          </span>
        </div>
        <div>
          <span className="text-gray-500 block">Total Runs Executed:</span>
          <span className="text-white font-mono font-medium text-sm">{runs?.length ?? 0}</span>
        </div>
        <div>
          <span className="text-gray-500 block">Experiment ID:</span>
          <span className="text-gray-400 font-mono text-[11px] truncate block">{experiment.id}</span>
        </div>
      </div>

      {/* Runs List */}
      <div className="glass-panel p-6 rounded-xl border border-white/10">
        <h2 className="text-base font-semibold text-white mb-4">Run Executions</h2>

        {loadingRuns ? (
          <div className="py-8 text-center text-xs text-gray-400 font-mono">
            Fetching run status records...
          </div>
        ) : runs && runs.length > 0 ? (
          <div className="divide-y divide-white/5">
            {runs.map((run) => (
              <div key={run.id} className="py-4 flex items-center justify-between text-xs">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-white font-medium">Repetition #{run.repetition_index + 1}</span>
                    <span className="text-gray-500 font-mono text-[11px]">{run.id}</span>
                  </div>
                  <div className="flex items-center gap-4 text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {run.started_at ? new Date(run.started_at).toLocaleTimeString() : 'Not started'}
                    </span>
                    {run.finished_at && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        Finished: {new Date(run.finished_at).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {run.status === 'completed' ? (
                    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Completed
                    </span>
                  ) : run.status === 'failed' ? (
                    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                      <XCircle className="w-3.5 h-3.5" />
                      Failed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      <Clock className="w-3.5 h-3.5" />
                      {run.status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-gray-500 border border-dashed border-white/10 rounded-lg">
            <AlertCircle className="w-6 h-6 text-gray-600 mx-auto mb-2" />
            No runs recorded yet for this experiment configuration.
          </div>
        )}
      </div>
    </div>
  );
};
