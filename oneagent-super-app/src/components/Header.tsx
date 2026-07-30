import React from 'react';
import { Cpu, Zap, Shield, Sparkles, Terminal, Activity } from 'lucide-react';
import { BudgetStats } from '../types';

interface HeaderProps {
  activeTab: string;
  budgetStats: BudgetStats;
  onOpenRunner: () => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, budgetStats, onOpenRunner }) => {
  const formatTabTitle = (tab: string) => {
    switch (tab) {
      case 'dashboard': return 'OneAgent Central Command';
      case 'llm_gateway': return 'LLM Gateway & Ranking Router';
      case 'agent_runner': return 'Agent Loop Execution Engine';
      case 'fhir': return 'FHIR BA/QA Suite (11-App Consolidated)';
      case 'leap': return 'LEAP Analytics & RWT Engine';
      case 'research': return 'Deep Researcher & SaaS Finder';
      case 'workops': return 'WorkOps, Outlook & DataSync';
      case 'content': return 'SEO & Tech Blog Pipeline';
      case 'files': return 'Files & Storage Guardian';
      case 'coding': return 'CLI Controller & Scaffolder';
      case 'skills_mcp': return 'Skills & MCP Connectors (Goose/Cherry/OpenClaw/Hermes)';
      case 'scheduler': return 'Cron Scheduler & Triggered Jobs';
      case 'meta': return 'Meta Engine (Self-Authoring Modules)';
      case 'settings': return 'System Settings & Telemetry';
      default: return 'OneAgent Platform';
    }
  };

  return (
    <header className="h-16 bg-[#0a0a0a] border-b border-white/10 px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-blue-600/20 rounded-lg border border-blue-500/30 text-blue-400">
          <Activity className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            {formatTabTitle(activeTab)}
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono tracking-wider uppercase">
              ONLINE
            </span>
          </h1>
          <p className="text-[11px] text-slate-500 font-mono">HealthOS BA/QA Automation Suite → OneAgent Unified</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Token Spend Badge */}
        <div className="hidden sm:flex items-center space-x-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10 text-xs">
          <Zap className="w-4 h-4 text-amber-400" />
          <span className="text-slate-400">Spent Today:</span>
          <span className="font-mono text-emerald-400 font-medium">
            ${budgetStats.currentSpendUSD.toFixed(3)}
          </span>
          <span className="text-slate-500 font-mono">/ ${budgetStats.dailyCapUSD.toFixed(2)}</span>
        </div>

        {/* Cache Savings Badge */}
        <div className="hidden lg:flex items-center space-x-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10 text-xs">
          <Shield className="w-4 h-4 text-blue-400" />
          <span className="text-slate-400">Cache Saved:</span>
          <span className="font-mono text-blue-300 font-medium">
            ${budgetStats.savedCostUSDToday.toFixed(3)} ({budgetStats.cachedHitsToday} hits)
          </span>
        </div>

        {/* Quick Launch Agent */}
        <button
          onClick={onOpenRunner}
          className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium transition shadow-sm shadow-blue-950 cursor-pointer"
        >
          <Terminal className="w-4 h-4" />
          <span>Run Agent Task</span>
        </button>
      </div>
    </header>
  );
};
