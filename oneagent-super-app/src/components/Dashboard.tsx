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
  Bot,
  Globe,
  Code
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
    { label: 'Research Skill', tab: 'skill_runner', icon: Zap, color: 'text-amber-400' },
    { label: 'Web Scraper', tab: 'scraper', icon: Globe, color: 'text-blue-400' },
    { label: 'Coding Agent', tab: 'agent_harness', icon: Code, color: 'text-emerald-400' },
    { label: 'Agent Architecture', tab: 'agent_architecture', icon: Layers, color: 'text-purple-400' },
    { label: 'LLM Router', tab: 'llm_gateway', icon: Cpu, color: 'text-cyan-400' },
    { label: 'Skills Hub', tab: 'skills_mcp', icon: Sparkles, color: 'text-pink-400' },
  ];

  return (
    <div className="space-y-6 p-6 text-slate-100">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bot className="w-7 h-7 text-blue-500" />
            OneAgent Command Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">Generalist agent with native specialists. Inspired by OpenManus, GPT Researcher, Goose, Gemini CLI, Cline, Firecrawl, Aider, smolagents, and more.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.tab}
              onClick={() => onNavigate(action.tab)}
              className="p-4 rounded-xl bg-slate-900/60 border border-white/10 hover:border-blue-500/40 hover:bg-slate-800/60 transition text-left group"
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className={`w-6 h-6 ${action.color}`} />
                <ArrowUpRight className="w-4 h-4 text-slate-500 opacity-0 group-hover:opacity-100 transition" />
              </div>
              <p className="text-xs font-medium text-slate-200">{action.label}</p>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-slate-900/40 border border-white/10 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h2 className="font-semibold">LLM Budget &amp; Usage</h2>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Total Calls</span>
              <span className="font-mono">{budgetStats.totalCalls.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Estimated Cost</span>
              <span className="font-mono">${budgetStats.totalCostUSD.toFixed(4)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Cache Hit Rate</span>
              <span className="font-mono text-emerald-400">{(budgetStats.cacheHitRate * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden mt-2">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                style={{ width: `${Math.min((budgetStats.totalCostUSD / 5) * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>

        <div className="bg-slate-900/40 border border-white/10 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-5 h-5 text-purple-400" />
            <h2 className="font-semibold">Active Limbs</h2>
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {limbs.length === 0 && <p className="text-sm text-slate-500">No limbs active yet.</p>}
            {limbs.map((limb) => (
              <div key={limb.id} className="flex items-center justify-between text-sm py-1 border-b border-white/5">
                <span className="flex items-center gap-2">
                  {limb.status === 'active' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-amber-400" />}
                  {limb.name}
                </span>
                <span className="text-xs text-slate-500">{limb.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900/40 border border-white/10 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-pink-400" />
            <h2 className="font-semibold">Scheduler Status</h2>
          </div>
          <div className="space-y-2">
            {cronJobs.slice(0, 5).map((job) => (
              <div key={job.id} className="flex items-center justify-between text-sm">
                <span className="text-slate-300">{job.name}</span>
                <span className={`text-xs ${job.enabled ? 'text-emerald-400' : 'text-slate-500'}`}>{job.enabled ? 'Active' : 'Paused'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
