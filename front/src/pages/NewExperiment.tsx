import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { createExperiment } from '../api/client';
import { FlaskConical, AlertCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

const formSchema = z.object({
  name: z.string().min(3, 'Experiment name must be at least 3 characters'),
  description: z.string().optional(),
  dataset_name: z.string().min(2, 'Dataset name is required'),
  chunk_size: z.number().int().min(100).max(4000),
  chunk_overlap: z.number().int().min(0).max(1000),
  top_k: z.number().int().min(1).max(50),
  repetitions: z.number().int().min(1).max(20),
  random_seed: z.number().int().optional(),
  workload_type: z.enum(['high_reuse', 'moderate_reuse', 'cold_start']),
});

type FormValues = z.infer<typeof formSchema>;

export const NewExperiment: React.FC = () => {
  const navigate = useNavigate();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      description: '',
      dataset_name: 'scientific_corpus_v1',
      chunk_size: 512,
      chunk_overlap: 64,
      top_k: 5,
      repetitions: 3,
      random_seed: 42,
      workload_type: 'high_reuse',
    },
  });

  const onSubmit = async (values: FormValues) => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      // Create experiment with backend configuration structure
      await createExperiment({
        name: values.name,
        description: values.description || undefined,
        provider_config_id: '00000000-0000-0000-0000-000000000000', // Default provider
        dataset_name: values.dataset_name,
        chunking_config: {
          chunk_size: values.chunk_size,
          chunk_overlap: values.chunk_overlap,
        },
        retrieval_config: {
          top_k: values.top_k,
        },
        workload_config: {
          type: values.workload_type,
        },
        random_seed: values.random_seed,
        repetitions: values.repetitions,
      });
      navigate('/experiments');
    } catch (err) {
      setErrorMsg((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/experiments"
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">New Experiment Configuration</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Define parameters for paired Strategy A (independent) vs Strategy B (shared) execution.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="glass-panel p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="glass-panel p-6 rounded-xl border border-white/10 space-y-6">
        {/* Basic Info */}
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">Experiment Metadata</h2>
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Experiment Name</label>
            <input
              {...register('name')}
              type="text"
              placeholder="e.g. baseline-reuse-scale-test"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
            {errors.name && <p className="text-xs text-red-400 mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Description (Optional)</label>
            <textarea
              {...register('description')}
              rows={2}
              placeholder="Hypothesis note or specific condition evaluated..."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Dataset Name</label>
            <input
              {...register('dataset_name')}
              type="text"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-blue-500 font-mono"
            />
            {errors.dataset_name && <p className="text-xs text-red-400 mt-1">{errors.dataset_name.message}</p>}
          </div>
        </div>

        {/* Chunking & Retrieval */}
        <div className="space-y-4 pt-4 border-t border-white/10">
          <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">Chunking & Retrieval Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Chunk Size (chars)</label>
              <input
                {...register('chunk_size', { valueAsNumber: true })}
                type="number"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              />
              {errors.chunk_size && <p className="text-xs text-red-400 mt-1">{errors.chunk_size.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Chunk Overlap (chars)</label>
              <input
                {...register('chunk_overlap', { valueAsNumber: true })}
                type="number"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              />
              {errors.chunk_overlap && <p className="text-xs text-red-400 mt-1">{errors.chunk_overlap.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Retrieval Top K</label>
              <input
                {...register('top_k', { valueAsNumber: true })}
                type="number"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              />
              {errors.top_k && <p className="text-xs text-red-400 mt-1">{errors.top_k.message}</p>}
            </div>
          </div>
        </div>

        {/* Experimental Controls */}
        <div className="space-y-4 pt-4 border-t border-white/10">
          <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">Controls & Repetitions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Repetitions</label>
              <input
                {...register('repetitions', { valueAsNumber: true })}
                type="number"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              />
              {errors.repetitions && <p className="text-xs text-red-400 mt-1">{errors.repetitions.message}</p>}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Random Seed</label>
              <input
                {...register('random_seed', { valueAsNumber: true })}
                type="number"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1">Workload Profile</label>
              <select
                {...register('workload_type')}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3.5 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                <option value="high_reuse" className="bg-gray-900">High Reuse (80%)</option>
                <option value="moderate_reuse" className="bg-gray-900">Moderate Reuse (50%)</option>
                <option value="cold_start" className="bg-gray-900">Cold Start (Single Consumer)</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
          <Link
            to="/experiments"
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-sm font-medium transition shadow-lg shadow-blue-600/20"
          >
            <FlaskConical className="w-4 h-4" />
            <span>{isSubmitting ? 'Creating...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
