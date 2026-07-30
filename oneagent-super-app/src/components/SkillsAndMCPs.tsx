import React, { useState } from 'react';
import {
  Layers,
  Cpu,
  CheckCircle2,
  Plus,
  RefreshCw,
  Terminal,
  Zap,
  BookOpen,
  ArrowUpRight
} from 'lucide-react';
import { SkillPack, MCPConnector, Recipe } from '../types';

interface SkillsAndMCPsProps {
  skillPacks: SkillPack[];
  mcps: MCPConnector[];
  recipes: Recipe[];
  onToggleSkill: (id: string) => void;
  onPingMCP: (id: string) => Promise<void>;
}

export const SkillsAndMCPs: React.FC<SkillsAndMCPsProps> = ({
  skillPacks,
  mcps,
  recipes,
  onToggleSkill,
  onPingMCP,
}) => {
  const [activeTab, setActiveTab] = useState<'mcps' | 'skills' | 'recipes'>('mcps');
  const [pingingId, setPingingId] = useState<string | null>(null);

  const handlePing = async (id: string) => {
    setPingingId(id);
    await onPingMCP(id);
    setPingingId(null);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-300 text-xs font-mono mb-2 border border-blue-500/20">
            <Layers className="w-3.5 h-3.5" />
            <span>Multi-Model MCP Adapter Engine</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">Skills, MCP Connectors & Agent Recipes Hub</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Interoperable model context protocol (MCP) connectors for Goose CLI, Cherry Studio, OpenClaw, and Hermes, plus OpenClaude-style prompt packs.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/10 space-x-6 text-sm">
        <button
          onClick={() => setActiveTab('mcps')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'mcps'
              ? 'text-blue-400 border-b-2 border-blue-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>MCP Protocol Server Connectors ({mcps.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('skills')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'skills'
              ? 'text-blue-400 border-b-2 border-blue-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>OpenClaude Skill Packs ({skillPacks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('recipes')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'recipes'
              ? 'text-blue-400 border-b-2 border-blue-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Zap className="w-4 h-4" />
          <span>Agent Automation Recipes ({recipes.length})</span>
        </button>
      </div>

      {/* TAB 1: MCP Connectors */}
      {activeTab === 'mcps' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mcps.map((m) => (
            <div key={m.id} className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    {m.name}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 uppercase border border-blue-500/30">
                      {m.ecosystem}
                    </span>
                  </h3>
                  <p className="text-[11px] font-mono text-slate-400">{m.endpoint}</p>
                </div>

                <button
                  onClick={() => handlePing(m.id)}
                  disabled={pingingId === m.id}
                  className="px-2.5 py-1 bg-white/5 hover:bg-white/10 text-slate-200 rounded text-xs font-mono border border-white/10 transition flex items-center space-x-1 cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${pingingId === m.id ? 'animate-spin' : ''}`} />
                  <span>Ping</span>
                </button>
              </div>

              <div className="space-y-1.5 text-xs font-mono bg-[#050505] p-3 rounded-lg border border-white/10">
                <div className="text-slate-400 font-sans text-[11px]">Exposed MCP Tool Operations:</div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {m.toolsProvided.map((t, idx) => (
                    <span key={idx} className="text-[10px] px-2 py-0.5 rounded bg-[#0a0a0a] text-slate-300 border border-white/10">
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between text-xs font-mono pt-1">
                <span className="text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Status: Connected
                </span>
                <span className="text-slate-400">Latency: {m.lastPingMs} ms</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 2: Skill Packs */}
      {activeTab === 'skills' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skillPacks.map((s) => (
            <div key={s.id} className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-100">{s.name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-300 border border-white/10">
                    v{s.version}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{s.description}</p>
                <div className="text-[11px] font-mono text-slate-500">Author: {s.author}</div>
              </div>

              <div className="pt-2 border-t border-white/10 flex items-center justify-between">
                <span className="text-[11px] font-mono text-blue-400">{s.tools.length} Tools Included</span>
                <button
                  onClick={() => onToggleSkill(s.id)}
                  className={`px-3 py-1 rounded text-xs font-mono transition cursor-pointer ${
                    s.enabled
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-white/5 text-slate-400 border border-white/10'
                  }`}
                >
                  {s.enabled ? 'Enabled' : 'Disabled'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 3: Recipes */}
      {activeTab === 'recipes' && (
        <div className="space-y-3">
          {recipes.map((r) => (
            <div key={r.id} className="p-4 bg-[#0a0a0a] border border-white/10 rounded-xl flex items-center justify-between text-xs">
              <div className="space-y-1">
                <h4 className="font-bold text-slate-100">{r.title}</h4>
                <p className="text-slate-400">{r.description}</p>
                <div className="font-mono text-slate-500 text-[11px]">Trigger: {r.trigger} | Target: {r.targetLimb}</div>
              </div>
              <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded font-mono">
                Active
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
