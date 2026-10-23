import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { fetchExperiments } from '../api/client';
import { PlusCircle, Layers, Calendar, Hash, ArrowRight } from 'lucide-react';

export const Experiments: React.FC = () => {
  const { data: experiments, isLoading, error } = useQuery({
    queryKey: ['experiments'],
    queryFn: fetchExperiments,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Experiment Configurations</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage experimental setups, dataset parameters, and view run executions.
          </p>
        </div>
        <Link
          to="/experiments/new"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-lg shadow-blue-600/20"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Experiment</span>
        </Link>
      </div>

      {isLoading ? (
        <div className="glass-panel p-12 text-center text-gray-400 rounded-xl font-mono text-sm">
          Loading experiments from research database...
        </div>
      ) : error ? (
        <div className="glass-panel p-6 border-red-500/30 rounded-xl text-red-400 text-sm">
          Error loading experiments: {(error as Error).message}
        </div>
      ) : experiments && experiments.length > 0 ? (
        <div className="grid grid-cols-1 gap-4">
          {experiments.map((exp) => (
            <div
              key={exp.id}
              className="glass-panel p-5 rounded-xl border border-white/10 hover:border-blue-500/30 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-white text-base">{exp.name}</h3>
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                    {exp.dataset_name}
                  </span>
                </div>
                {exp.description && (
                  <p className="text-xs text-gray-400">{exp.description}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-gray-500 pt-1">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(exp.created_at).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <Hash className="w-3.5 h-3.5" />
                    {exp.repetitions} repetitions
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <Link
                  to={`/experiments/${exp.id}`}
                  className="flex items-center gap-1.5 text-xs font-medium text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-3.5 py-2 rounded-lg border border-blue-500/30 transition"
                >
                  <span>View Runs</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-panel p-12 text-center rounded-xl border-dashed border border-white/15">
          <Layers className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-200">No experiment configurations found</h3>
          <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
            Get started by defining an experiment configuration with fixed dataset and chunking parameters.
          </p>
          <Link
            to="/experiments/new"
            className="inline-flex items-center gap-2 mt-4 bg-white/10 hover:bg-white/15 text-white text-xs font-medium px-4 py-2 rounded-lg transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Create First Configuration</span>
          </Link>
        </div>
      )}
    </div>
  );
};
