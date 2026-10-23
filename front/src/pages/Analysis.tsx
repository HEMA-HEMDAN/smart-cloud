import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { Calculator, BarChart2, Info } from 'lucide-react';

export const Analysis: React.FC = () => {
  // Break-even economic model inputs:
  // C_p: Prep cost per document
  // C_q: Query processing cost
  // C_m: Shared maintenance overhead
  const [cp, setCp] = useState<number>(0.05); // $0.05 per doc prep
  const [cq, setCq] = useState<number>(0.005); // $0.005 per query
  const [cm, setCm] = useState<number>(0.02); // $0.02 shared overhead

  const breakevenN = useMemo(() => {
    if (cp <= 0) return 1;
    return (cm / cp) + 1;
  }, [cp, cm]);

  // Generate cost curve simulation over 1 to 15 consumers
  const chartData = useMemo(() => {
    const data = [];
    for (let n = 1; n <= 15; n++) {
      const costIndependent = n * (cp + cq);
      const costShared = cp + (n * cq) + cm;
      data.push({
        consumers: n,
        'Strategy A (Independent)': Number(costIndependent.toFixed(4)),
        'Strategy B (Shared)': Number(costShared.toFixed(4)),
      });
    }
    return data;
  }, [cp, cq, cm]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Research Analysis & Economic Model</h1>
        <p className="text-sm text-gray-400 mt-1">
          Explore theoretical break-even points and side-by-side cost trajectories based on empirical measurements.
        </p>
      </div>

      {/* Model Definition Card */}
      <div className="glass-panel p-6 rounded-xl border border-white/10 space-y-4">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
            Documented Economic Model
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300">
            <span className="text-gray-400 block mb-1">Strategy A (Independent):</span>
            C_independent = N * (C_p + C_q)
          </div>
          <div className="p-3.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300">
            <span className="text-gray-400 block mb-1">Strategy B (Shared):</span>
            C_shared = C_p + N * C_q + C_m
          </div>
        </div>
      </div>

      {/* Interactive Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="glass-panel p-6 rounded-xl border border-white/10 space-y-5">
          <div className="flex items-center gap-2 mb-2">
            <Calculator className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-white">Parameter Controls</h3>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-300">Prep Cost (C_p):</span>
              <span className="font-mono text-white">${cp.toFixed(3)}</span>
            </div>
            <input
              type="range"
              min="0.01"
              max="0.5"
              step="0.005"
              value={cp}
              onChange={(e) => setCp(parseFloat(e.target.value))}
              className="w-full accent-blue-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-300">Query Cost (C_q):</span>
              <span className="font-mono text-white">${cq.toFixed(4)}</span>
            </div>
            <input
              type="range"
              min="0.001"
              max="0.05"
              step="0.001"
              value={cq}
              onChange={(e) => setCq(parseFloat(e.target.value))}
              className="w-full accent-blue-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-300">Shared Overhead (C_m):</span>
              <span className="font-mono text-white">${cm.toFixed(3)}</span>
            </div>
            <input
              type="range"
              min="0.00"
              max="0.2"
              step="0.005"
              value={cm}
              onChange={(e) => setCm(parseFloat(e.target.value))}
              className="w-full accent-blue-500"
            />
          </div>

          <div className="p-4 rounded-lg bg-white/5 border border-white/10 text-center space-y-1">
            <span className="text-xs text-gray-400">Calculated Break-Even Point (N*):</span>
            <div className="text-2xl font-bold font-mono text-emerald-400">
              {breakevenN.toFixed(2)} consumers
            </div>
            <span className="text-[11px] text-gray-500 block">
              Shared strategy yields net savings when N &ge; {Math.ceil(breakevenN)}
            </span>
          </div>
        </div>

        {/* Dynamic Cost Projection Chart */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-xl border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Cost Trajectory vs Number of Consumers</h3>
            </div>
            <span className="text-xs text-gray-400 font-mono">1 to 15 Consumers</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="consumers" stroke="#6b7280" fontSize={12} tickLine={false} />
                <YAxis stroke="#6b7280" fontSize={12} tickFormatter={(v) => `$${v}`} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: 'rgba(255,255,255,0.1)', fontSize: 12, borderRadius: 8 }}
                  formatter={(val: any) => [`$${val}`, '']}
                />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                <Line
                  type="monotone"
                  dataKey="Strategy A (Independent)"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="Strategy B (Shared)"
                  stroke="#a855f7"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className="text-[11px] text-gray-400 mt-4 text-center">
            As consumers (N) scale, Strategy A preparation costs grow linearly with N, while Strategy B preparation occurs on first demand only.
          </p>
        </div>
      </div>
    </div>
  );
};
