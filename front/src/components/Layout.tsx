import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Activity,
  Layers,
  FlaskConical,
  BarChart3,
  Settings as SettingsIcon,
  PlusCircle,
  Database,
  Cpu
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navigation = [
    { name: 'Overview', href: '/', icon: Activity },
    { name: 'Experiments', href: '/experiments', icon: Layers },
    { name: 'New Experiment', href: '/experiments/new', icon: PlusCircle },
    { name: 'Analysis', href: '/analysis', icon: BarChart3 },
    { name: 'Diagnostics', href: '/diagnostics', icon: SettingsIcon },
  ];

  return (
    <div className="flex h-screen bg-[#0b0f19] text-gray-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/10 bg-[#0d1322] flex flex-col justify-between">
        <div>
          {/* Logo / Header */}
          <div className="h-16 flex items-center px-6 border-b border-white/10 gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <FlaskConical className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-sm tracking-wide text-white">Shared AI Intel</div>
              <div className="text-[11px] text-gray-400 font-mono tracking-tight">Research Instrument</div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* System Footer info */}
        <div className="p-4 border-t border-white/10 text-xs text-gray-500 space-y-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              PostgreSQL
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
              Active
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              Qdrant Vector
            </span>
            <span className="text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
              Active
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto flex flex-col">
        {/* Top bar */}
        <header className="h-16 border-b border-white/10 px-8 flex items-center justify-between bg-[#0d1322]/50 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <span className="text-xs px-2.5 py-1 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-mono">
              Hypothesis: Demand-Driven Shared Intelligence
            </span>
          </div>
          <div className="text-xs text-gray-400 font-mono">
            Mode: Strict Controlled A/B Evaluation
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8 max-w-7xl w-full mx-auto flex-1">
          {children}
        </div>
      </main>
    </div>
  );
};
