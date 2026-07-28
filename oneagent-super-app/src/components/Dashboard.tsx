import React from 'react';
import {
  Activity,
  Zap,
  ShieldCheck,
  Clock,
  Sparkles,
  ArrowUpRight,
  Play,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  FileCode2,
  Terminal,
  Bot
} from 'lucide-react';
import { BudgetStats, LimbModuleManifest, CronJob, MCPConnector } from '../types';

interface DashboardProps {
  budgetStats: BudgetStats;
  limbs: LimbModuleManifest[];
  cronJobs: CronJob[];
  mcps: MCPConnector[];
  onNavigate: (tab: string) => void;
  onQuickRun: (task: string, module: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  budgetStats,
  limbs,
  cronJobs,
  mcps,
  onNavigate,
  onQuickRun,
}) => {
  const quickActions = [
    {
      title: 'FHIR US-Core Bundle Audit',
      module: 'fhir',
      prompt: 'Inspect active Patient & Encounter resources for US-Core missing NPIs and invalid dates.',
      icon: Activity,
      color: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
    },
    {
      title: 'LEAP RWT Scaling Diagnostics',
      module: 'leap',
      prompt: 'Check LEAP server throughput, RWT telemetry, and UDS eCQM compliance thresholds.',
      icon: Zap,
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    },
    {
      title: 'Deep Research: ONC HTI-2 Rule',
      module: 'research',
      prompt: 'Synthesize ONC HTI-2 final rule compliance obligations and spot SaaS opportunities.',
      icon: ShieldCheck,
      color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
    },
    {
      title: 'Generate Tech Blog & SEO Draft',
      module: 'content',
      prompt: 'Draft an engineering article on building US-Core FHIR auditors with token-optimized routers.',
      icon: FileCode2,
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    },
  ];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-[#0a0a0a] border border-white/10 p-6 shadow-2xl">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-blue-600/20 text-blue-300 text-xs font-mono mb-2 border border-blue-500/30">
              <Bot className="w-3.5 h-3.5" />
              <span>CureMD-BA-QA-Automation-suite Consolidation Active</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              OneAgent Personal Super-App Platform
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Consolidated 34 legacy forks behind a single runtime. Ranking-based LLM router, OpenClaude skill packs, Goose/Cherry/OpenClaw MCP connectors, cron scheduler, and self-authoring meta-engine.
            </p>
          </div>
          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => onNavigate('llm_gateway')}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 text-slate-200 text-xs font-medium rounded-lg border border-white/10 transition cursor-pointer"
            >
              Configure LLM Router
            </button>
            <button
              onClick={() => onNavigate('agent_runner')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg shadow-lg shadow-blue-950/50 transition cursor-pointer flex items-center space-x-1.5"
            >
              <Terminal className="w-4 h-4" />
              <span>Launch Execution</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0a0a0a] p-4 rounded-xl border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-mono text-[10px]">Daily LLM Budget</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 font-mono">
            ${budgetStats.currentSpendUSD.toFixed(3)}{' '}
            <span className="text-xs font-normal text-slate-500">/ ${budgetStats.dailyCapUSD.toFixed(2)}</span>
          </div>
          <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-amber-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (budgetStats.currentSpendUSD / budgetStats.dailyCapUSD) * 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-slate-400 flex justify-between font-mono">
            <span>{budgetStats.totalRequestsToday} LLM calls</span>
            <span className="text-emerald-400">{budgetStats.cachedHitsToday} cached ($0)</span>
          </p>
        </div>

        <div className="bg-[#0a0a0a] p-4 rounded-xl border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-mono text-[10px]">Consolidated Limbs</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 font-mono">
            7 Active Modules <span className="text-xs font-normal text-slate-500">(34 forks)</span>
          </div>
          <p className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> 100% Zero-Duplication Architecture
          </p>
        </div>

        <div className="bg-[#0a0a0a] p-4 rounded-xl border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-mono text-[10px]">MCP Connectors</span>
            <Cpu className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 font-mono">
            {mcps.filter((m) => m.status === 'connected').length} Connected
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Goose, Cherry, OpenClaw, Hermes
          </p>
        </div>

        <div className="bg-[#0a0a0a] p-4 rounded-xl border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase tracking-wider font-mono text-[10px]">Active Cron Jobs</span>
            <Clock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 font-mono">
            {cronJobs.filter((c) => c.status === 'active').length} Scheduled
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Nightly FHIR, Weekly LEAP
          </p>
        </div>
      </div>

      {/* Quick Launch Section */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest font-mono flex items-center gap-2">
          <Play className="w-4 h-4 text-blue-400" />
          Quick Automation Action Launcher
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, idx) => {
            const Icon = action.icon;
            return (
              <div
                key={idx}
                onClick={() => onQuickRun(action.prompt, action.module)}
                className="bg-[#0a0a0a] hover:bg-[#0f0f0f] p-4 rounded-xl border border-white/10 hover:border-blue-500/50 transition cursor-pointer group flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className={`p-2 rounded-lg ${action.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">
                      {action.module.toUpperCase()}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-slate-100 group-hover:text-blue-300 transition">
                    {action.title}
                  </h4>
                  <p className="text-[11px] text-slate-400 line-clamp-2">{action.prompt}</p>
                </div>

                <div className="flex items-center text-[11px] font-medium text-blue-400 group-hover:translate-x-1 transition">
                  <span>Execute Pipeline</span>
                  <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* System Architecture Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Consolidated Limbs Overview */}
        <div className="lg:col-span-2 bg-[#0a0a0a] rounded-xl border border-white/10 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest font-mono flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" />
              Consolidated Module Limbs Matrix
            </h3>
            <span className="text-xs font-mono text-slate-500">7 limbs active</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {limbs.map((limb) => (
              <div
                key={limb.id}
                onClick={() => onNavigate(limb.slug)}
                className="p-3 bg-[#050505] rounded-lg border border-white/10 hover:border-blue-500/30 hover:bg-white/5 transition cursor-pointer flex items-start justify-between space-x-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-slate-200">{limb.name}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-600/20 text-blue-300 border border-blue-500/30">
                      {limb.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2">{limb.description}</p>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-[10px] font-mono text-emerald-400 block">
                    {limb.toolCount} Tools
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 block">
                    {limb.mergedFromCount} merged
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* MCP & Scheduler Panel */}
        <div className="bg-[#0a0a0a] rounded-xl border border-white/10 p-5 space-y-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest font-mono flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            Agent Ecosystem Status
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-[#050505] rounded-lg border border-white/10 space-y-2">
              <div className="flex items-center justify-between font-mono text-slate-300">
                <span>MCP Protocol Status</span>
                <span className="text-emerald-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  Ready
                </span>
              </div>
              <div className="space-y-1 font-mono text-[11px] text-slate-400">
                <div className="flex justify-between">
                  <span>Goose CLI Connector:</span>
                  <span className="text-slate-200">Connected (14ms)</span>
                </div>
                <div className="flex justify-between">
                  <span>Cherry Studio Bridge:</span>
                  <span className="text-slate-200">Connected (22ms)</span>
                </div>
                <div className="flex justify-between">
                  <span>OpenClaw Agent MCP:</span>
                  <span className="text-slate-200">Connected (18ms)</span>
                </div>
                <div className="flex justify-between">
                  <span>Hermes Scheduler MCP:</span>
                  <span className="text-slate-200">Connected (12ms)</span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-[#050505] rounded-lg border border-white/10 space-y-2">
              <div className="flex items-center justify-between font-mono text-slate-300">
                <span>Next Scheduled Cron Job</span>
                <Clock className="w-3.5 h-3.5 text-blue-400" />
              </div>
              <p className="text-xs text-slate-200 font-semibold">{cronJobs[0]?.name}</p>
              <p className="text-[11px] text-slate-400 font-mono">{cronJobs[0]?.humanSchedule}</p>
              <button
                onClick={() => onNavigate('scheduler')}
                className="w-full mt-1 py-1.5 bg-white/5 hover:bg-white/10 text-slate-200 rounded text-[11px] font-medium transition cursor-pointer border border-white/10"
              >
                Manage Scheduler
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
