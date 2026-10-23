import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchDocuments,
  uploadDocument,
  previewDocumentChunks,
  createExperiment,
  startNewRun,
} from '../api/client';
import type { DocumentPreview, BenchmarkQuestion } from '../api/client';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  Plus,
  Trash2,
  Sparkles,
  PlayCircle,
  ShieldCheck,
} from 'lucide-react';

export const NewExperiment: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Form states
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [consumerCount, setConsumerCount] = useState<number>(10);
  const [repetitions, setRepetitions] = useState<number>(10);
  const [randomSeed, setRandomSeed] = useState<number>(42);
  const [chunkSize, setChunkSize] = useState<number>(512);
  const [chunkOverlap, setChunkOverlap] = useState<number>(64);
  const [topK, setTopK] = useState<number>(5);
  const [workloadType, setWorkloadType] = useState<'high_reuse' | 'moderate_reuse' | 'cold_start'>('high_reuse');
  const [providerMode, setProviderMode] = useState<'mock' | 'gemini'>('mock');

  // Document states
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Benchmark questions
  const [questions, setQuestions] = useState<BenchmarkQuestion[]>([
    {
      question_id: 'q1',
      question_text: 'What is the main finding or proposition in this document?',
      expected_answer: '',
      expected_chunk_ids: [],
    },
  ]);

  const [activeQuestionIdx, setActiveQuestionIdx] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch registered documents
  const { data: documents, refetch: refetchDocs } = useQuery({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
  });

  // Automatically select the first document if available and none selected
  useEffect(() => {
    if (documents && documents.length > 0 && !selectedDocId) {
      setSelectedDocId(documents[0].id);
    }
  }, [documents, selectedDocId]);

  // Fetch document preview when document or chunking parameters change
  const { data: docPreview } = useQuery<DocumentPreview>({
    queryKey: ['doc-preview', selectedDocId, chunkSize, chunkOverlap],
    queryFn: () => previewDocumentChunks(selectedDocId, chunkSize, chunkOverlap),
    enabled: Boolean(selectedDocId),
  });

  // Handle file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    try {
      const doc = await uploadDocument(file);
      await refetchDocs();
      setSelectedDocId(doc.id);
      if (!name) {
        setName(`eval_${doc.document_id.toLowerCase()}_N${consumerCount}_R${repetitions}`);
      }
    } catch (err) {
      setUploadError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  // Add question
  const handleAddQuestion = () => {
    const nextIdx = questions.length + 1;
    setQuestions([
      ...questions,
      {
        question_id: `q${nextIdx}`,
        question_text: '',
        expected_answer: '',
        expected_chunk_ids: [],
      },
    ]);
    setActiveQuestionIdx(questions.length);
  };

  // Remove question
  const handleRemoveQuestion = (idx: number) => {
    if (questions.length <= 1) return;
    const next = questions.filter((_, i) => i !== idx);
    setQuestions(next);
    setActiveQuestionIdx(Math.max(0, idx - 1));
  };

  // Toggle chunk evidence for the active question
  const handleToggleEvidenceChunk = (chunkId: string) => {
    if (!questions[activeQuestionIdx]) return;
    const current = questions[activeQuestionIdx].expected_chunk_ids || [];
    const exists = current.includes(chunkId);
    const updated = exists ? current.filter((id) => id !== chunkId) : [...current, chunkId];

    const nextQuestions = [...questions];
    nextQuestions[activeQuestionIdx] = {
      ...nextQuestions[activeQuestionIdx],
      expected_chunk_ids: updated,
    };
    setQuestions(nextQuestions);
  };

  // Submit and launch
  const handleLaunchExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDocId) {
      setErrorMsg('Please select or upload a source document.');
      return;
    }
    const finalName = name.trim() || `eval_${Date.now()}`;
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const config = await createExperiment({
        name: finalName,
        description: description || undefined,
        provider_config_id: '00000000-0000-0000-0000-000000000000',
        dataset_name: docPreview?.title || 'uploaded_corpus',
        chunking_config: {
          chunk_size: chunkSize,
          chunk_overlap: chunkOverlap,
        },
        retrieval_config: {
          top_k: topK,
        },
        workload_config: {
          document_version_id: selectedDocId,
          consumer_count: consumerCount,
          type: workloadType,
          provider: providerMode,
          benchmark_questions: questions,
        },
        random_seed: randomSeed,
        repetitions: repetitions,
      });

      // Launch first run immediately
      await startNewRun(config.id);
      await queryClient.invalidateQueries({ queryKey: ['experiments'] });
      navigate(`/experiments/${config.id}`);
    } catch (err) {
      setErrorMsg((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-8 pb-12">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/experiments"
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Configure New Experiment Lab</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Upload a document, set benchmark ground-truth, configure paired A/B parameters, and run.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="glass-panel p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleLaunchExperiment} className="space-y-8">
        {/* Step 1: Document Upload & Extraction */}
        <div className="glass-panel p-6 rounded-xl border border-white/10 space-y-5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold">1</span>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Source Document & Content Extraction</h2>
            </div>
            {docPreview && (
              <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Text Extracted & Ready</span>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Upload Dropzone */}
            <div className="space-y-3">
              <label className="text-xs font-medium text-gray-300 block">Upload New Document (.pdf, .txt, .md)</label>
              <div className="border-2 border-dashed border-white/15 hover:border-blue-500/50 rounded-xl p-5 text-center transition-colors relative cursor-pointer bg-white/5">
                <input
                  type="file"
                  accept=".pdf,.txt,.md,.markdown"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                />
                <Upload className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                <p className="text-xs text-gray-300 font-medium">Click or drag a file to extract text</p>
                <p className="text-[11px] text-gray-500 mt-1">PDF (searchable), TXT, or Markdown up to 10MB</p>
                {uploading && <p className="text-xs text-blue-400 font-mono mt-2 animate-pulse">Extracting text & hashing...</p>}
              </div>
              {uploadError && <p className="text-xs text-red-400 mt-1">{uploadError}</p>}
            </div>

            {/* Select Existing Document */}
            <div className="space-y-3">
              <label className="text-xs font-medium text-gray-300 block">Or Select Registered Document</label>
              {documents && documents.length > 0 ? (
                <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => setSelectedDocId(doc.id)}
                      className={`p-3 rounded-lg border text-xs cursor-pointer transition flex items-center justify-between ${
                        selectedDocId === doc.id
                          ? 'bg-blue-600/20 border-blue-500/50 text-white'
                          : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <FileText className="w-4 h-4 shrink-0 text-blue-400" />
                        <span className="truncate font-medium">{doc.title || doc.document_id}</span>
                      </div>
                      <span className="font-mono text-[10px] text-gray-500 shrink-0">
                        {doc.content_length_chars?.toLocaleString()} chars
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500 italic p-3 bg-white/5 rounded-lg">No documents uploaded yet.</p>
              )}
            </div>
          </div>

          {/* Extracted Preview Accordion */}
          {docPreview && (
            <div className="pt-3 border-t border-white/5 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">
                  Version SHA-256: <code className="text-blue-300 font-mono text-[11px]">{docPreview.version_hash.slice(0, 16)}...</code>
                </span>
                <span className="text-gray-400 font-mono">
                  {docPreview.total_chunks} chunks generated ({docPreview.content_length_chars.toLocaleString()} chars)
                </span>
              </div>

              {/* Chunk browser */}
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-300">Chunk Preview & Evidence Selector:</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 max-h-36 overflow-y-auto p-1 bg-black/20 rounded-lg border border-white/5">
                  {docPreview.chunks.slice(0, 20).map((chk) => {
                    const isSelected = questions[activeQuestionIdx]?.expected_chunk_ids?.includes(chk.chunk_id);
                    return (
                      <div
                        key={chk.chunk_id}
                        onClick={() => handleToggleEvidenceChunk(chk.chunk_id)}
                        className={`p-2 rounded border text-[11px] cursor-pointer transition ${
                          isSelected
                            ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300 font-medium'
                            : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono font-bold">{chk.chunk_id}</span>
                          <span className="text-[10px] text-gray-500 font-mono">~{chk.token_estimate} tok</span>
                        </div>
                        <p className="line-clamp-2 text-[10px] leading-tight text-gray-300">{chk.text}</p>
                      </div>
                    );
                  })}
                </div>
                <p className="text-[11px] text-gray-500 italic">
                  Tip: Click on chunks above to attach them as expected ground-truth evidence for Question #{activeQuestionIdx + 1}.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Step 2: Benchmark Questions & Expected Evidence */}
        <div className="glass-panel p-6 rounded-xl border border-white/10 space-y-5">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold">2</span>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Benchmark Questions & Ground Truth</h2>
            </div>
            <button
              type="button"
              onClick={handleAddQuestion}
              className="flex items-center gap-1.5 text-xs bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 px-3 py-1.5 rounded-lg border border-blue-500/30 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Question</span>
            </button>
          </div>

          {/* Question tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {questions.map((q, idx) => (
              <button
                key={q.question_id}
                type="button"
                onClick={() => setActiveQuestionIdx(idx)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition shrink-0 ${
                  activeQuestionIdx === idx
                    ? 'bg-blue-600 text-white'
                    : 'bg-white/5 text-gray-400 hover:text-white'
                }`}
              >
                Question #{idx + 1} {q.expected_chunk_ids && q.expected_chunk_ids.length > 0 ? `(${q.expected_chunk_ids.length} ev)` : ''}
              </button>
            ))}
          </div>

          {/* Active Question Fields */}
          {questions[activeQuestionIdx] && (
            <div className="space-y-4 bg-white/5 p-4 rounded-xl border border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-white">Question #{activeQuestionIdx + 1} Definition</span>
                {questions.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveQuestion(activeQuestionIdx)}
                    className="text-red-400 hover:text-red-300 text-xs flex items-center gap-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </button>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-gray-300 block mb-1">Question Text</label>
                <input
                  type="text"
                  value={questions[activeQuestionIdx].question_text}
                  onChange={(e) => {
                    const next = [...questions];
                    next[activeQuestionIdx].question_text = e.target.value;
                    setQuestions(next);
                  }}
                  placeholder="e.g. What is the break-even threshold for shared intelligence?"
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-300 block mb-1">
                    Expected Ground-Truth Answer <span className="text-gray-500">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={questions[activeQuestionIdx].expected_answer || ''}
                    onChange={(e) => {
                      const next = [...questions];
                      next[activeQuestionIdx].expected_answer = e.target.value;
                      setQuestions(next);
                    }}
                    placeholder="Reference answer used to evaluate correctness"
                    className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-300 block mb-1">
                    Expected Evidence Chunks <span className="text-gray-500">(Recall@k Ground Truth)</span>
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1.5 rounded-lg">
                      {questions[activeQuestionIdx].expected_chunk_ids?.length || 0} chunks tagged
                    </span>
                    <span className="text-[11px] text-gray-400 truncate">
                      {questions[activeQuestionIdx].expected_chunk_ids?.join(', ') || 'Select from Step 1 preview'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Step 3: Workload & Strategy Parameters */}
        <div className="glass-panel p-6 rounded-xl border border-white/10 space-y-5">
          <div className="flex items-center gap-2 border-b border-white/5 pb-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold">3</span>
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Experiment Configuration & Workload</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div>
              <label className="text-xs font-medium text-gray-300 block mb-1">Experiment Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. lab_eval_run_01"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-300 block mb-1">Optional Notes</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Evaluating 10 consumers against v1"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-300 block mb-1">Provider Execution Mode</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setProviderMode('mock')}
                  className={`py-2 px-3 rounded-lg border text-xs font-medium transition flex items-center justify-center gap-2 ${
                    providerMode === 'mock'
                      ? 'bg-blue-600/30 border-blue-500 text-blue-300'
                      : 'bg-white/5 border-white/10 text-gray-400'
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>MOCK</span>
                </button>
                <button
                  type="button"
                  onClick={() => setProviderMode('gemini')}
                  className={`py-2 px-3 rounded-lg border text-xs font-medium transition flex items-center justify-center gap-2 ${
                    providerMode === 'gemini'
                      ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300'
                      : 'bg-white/5 border-white/10 text-gray-400'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Gemini (Live)</span>
                </button>
              </div>
            </div>
          </div>

          {/* Sliders for Consumers and Repetitions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300 font-medium">Simulated Consumers (N):</span>
                <span className="font-mono text-blue-400 font-bold">{consumerCount} consumers</span>
              </div>
              <input
                type="range"
                min="2"
                max="30"
                value={consumerCount}
                onChange={(e) => setConsumerCount(parseInt(e.target.value))}
                className="w-full accent-blue-500"
              />
              <p className="text-[11px] text-gray-500">
                Independent consumers demanding the document. Default: 10 consumers.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300 font-medium">Repetitions (Paired A/B Runs):</span>
                <span className="font-mono text-purple-400 font-bold">{repetitions} repetitions</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                value={repetitions}
                onChange={(e) => setRepetitions(parseInt(e.target.value))}
                className="w-full accent-purple-500"
              />
              <p className="text-[11px] text-gray-500">
                Number of repeated paired comparisons for statistical analysis. Default: 10 repetitions.
              </p>
            </div>
          </div>

          {/* Hyperparameters */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">Workload Profile</label>
              <select
                value={workloadType}
                onChange={(e) => setWorkloadType(e.target.value as any)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none"
              >
                <option value="high_reuse">High Reuse (Sequential)</option>
                <option value="moderate_reuse">Moderate Reuse (Permuted)</option>
                <option value="cold_start">Cold Start (Independent)</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">Random Seed</label>
              <input
                type="number"
                value={randomSeed}
                onChange={(e) => setRandomSeed(parseInt(e.target.value) || 0)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">Chunk Size (chars)</label>
              <input
                type="number"
                value={chunkSize}
                onChange={(e) => setChunkSize(parseInt(e.target.value) || 512)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">Chunk Overlap (chars)</label>
              <input
                type="number"
                value={chunkOverlap}
                onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 64)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">Retrieval Top-K</label>
              <input
                type="number"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none"
              />
            </div>
          </div>

          {/* Workload Summary Callout */}
          <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 space-y-1">
            <span className="font-semibold block text-white">Calculated Workload Expectations:</span>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
              <div>Strategy A Preps: <strong>{consumerCount * repetitions}</strong></div>
              <div>Strategy B Initial: <strong>{repetitions}</strong></div>
              <div>Strategy B Reuses: <strong>{(consumerCount - 1) * repetitions}</strong></div>
              <div>Total Queries (A+B): <strong>{2 * consumerCount * repetitions * questions.length}</strong></div>
            </div>
          </div>
        </div>

        {/* Submit Action */}
        <div className="flex items-center justify-between">
          <Link
            to="/experiments"
            className="text-xs text-gray-400 hover:text-white transition"
          >
            Cancel and Return
          </Link>
          <button
            type="submit"
            disabled={isSubmitting || !selectedDocId}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-6 py-2.5 rounded-xl text-sm font-semibold transition shadow-lg shadow-blue-600/30 disabled:opacity-50"
          >
            <PlayCircle className="w-4 h-4" />
            <span>{isSubmitting ? 'Initializing Run...' : 'Launch Paired Experiment Lab'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
