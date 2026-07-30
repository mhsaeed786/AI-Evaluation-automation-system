import React, { useState, useEffect } from 'react';
import {
  Brain, Cpu, Shield, GitBranch, Zap, Activity, Layers,
  Server, Terminal, RefreshCw, CheckCircle2, AlertCircle,
  PlayCircle, FileCode, Lock, Network, Clock
} from 'lucide-react';

interface HarnessInfo { id: string; type: string; available: boolean; }
interface CapabilityInfo { type: string; provider_id: string; name: string; priority: number; enabled: boolean; }
interface HookInfo { name: string; event: string; priority: number; description: string; }
interface SessionInfo { session_id: string; agent_id: string; status: string; turn_count: number; token_count: number; updated_at: string; }
interface RecipeInfo { id: string; name: string; description: string; steps: any[]; }

export const AgentArchitecture: React.FC = () => {
  const [activeSection, setActiveSection] = useState('overview');
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityInfo[]>([]);
  const [hooks, setHooks] = useState<HookInfo[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [recipes, setRecipes] = useState<RecipeInfo[]>([]);
  const [loading, setLoading] = useState({});

  const sections = [
    { id: 'overview', label: 'Architecture Overview', icon: Layers },
    { id: 'harnesses', label: 'Agent Harnesses', icon: Cpu },
    { id: 'capabilities', label: 'Capability Registry', icon: Network },
    { id: 'hooks', label: 'Hook System', icon: Zap },
    { id: 'sessions', label: 'Session Manager', icon: Server },
    { id: 'recipes', label: 'Recipe Runner', icon: GitBranch },
    { id: 'security', label: 'Security Layer', icon: Shield },
    { id: 'diagnostics', label: 'Diagnostics', icon: Activity },
  ];

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading({ all: true });
    try {
      const [h, c, hk, s, r] = await Promise.all([
        fetch('/api/harnesses').then(r => r.json()).catch(() => ({ harnesses: [] })),
        fetch('/api/capabilities').then(r => r.json()).catch(() => ({ capabilities: [] })),
        fetch('/api/hooks').then(r => r.json()).catch(() => ({ plugin_hooks: [] })),
        fetch('/api/sessions').then(r => r.json()).catch(() => []),
        fetch('/api/recipes').then(r => r.json()).catch(() => []),
      ]);
      setHarnesses(h.harnesses || []);
      setCapabilities(c.capabilities || []);
      setHooks(hk.plugin_hooks || []);
      setSessions(s);
      setRecipes(r);
    } catch (e) {
      console.error('Failed to load architecture data:', e);
    } finally {
      setLoading({});
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-950/30 via-purple-950/20 to-[#0a0a0a] border border-blue-500/20">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">Agent Architecture</h1>
            <p className="text-xs text-slate-400 mt-1">
              Native features inspired by OpenClaw, Eigent, and Super-App orchestrator.
              Harness abstraction, capability registration, dual hooks, session management, recipe runner, security layer.
            </p>
          </div>
        </div>
      </div>

      {/* Section Tabs */}
      <div className="flex flex-wrap gap-2">
        {sections.map(s => {
          const Icon = s.icon;
          return (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition cursor-pointer ${
                activeSection === s.id
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:bg-white/5'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{s.label}</span>
            </button>
          );
        })}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { icon: Cpu, title: 'Harness Abstraction', desc: 'Pluggable model loop executors (Gemini, Ollama, custom)', source: 'OpenClaw', color: 'blue' },
            { icon: Network, title: 'Capability Registration', desc: 'Explicit capability types: TextInference, WebSearch, BrowserControl, etc.', source: 'OpenClaw', color: 'purple' },
            { icon: Server, title: 'Session Manager', desc: 'JSONL transcripts, session-lane serialization, auto-compaction', source: 'OpenClaw', color: 'emerald' },
            { icon: Zap, title: 'Dual Hook System', desc: 'Plugin hooks (programmatic) + operator scripts (lifecycle)', source: 'OpenClaw', color: 'amber' },
            { icon: GitBranch, title: 'Recipe Runner', desc: 'Ordered skill chains with DAG dependencies, parallel execution', source: 'Super-App', color: 'rose' },
            { icon: Shield, title: 'Security Layer', desc: 'Command allowlist, metacharacter rejection, SSRF protection', source: 'Super-App', color: 'red' },
            { icon: Brain, title: 'Sub-Agent System', desc: 'Push-based completion, isolated/fork context, depth policy', source: 'OpenClaw', color: 'cyan' },
            { icon: Activity, title: 'Diagnostics', desc: 'Subsystem flags, timeline JSONL, session liveness', source: 'OpenClaw', color: 'orange' },
            { icon: Clock, title: 'Queue & Steering', desc: 'Inject mid-run (steer) or hold for next turn (followup)', source: 'OpenClaw', color: 'indigo' },
            { icon: FileCode, title: 'Workspace Files', desc: 'SOUL.md, AGENTS.md, USER.md, BOOTSTRAP.md persona system', source: 'OpenClaw', color: 'pink' },
            { icon: PlayCircle, title: 'SSE Step Playback', desc: 'Replay agent execution with adjustable speed', source: 'Eigent', color: 'teal' },
            { icon: Terminal, title: 'Command Validation', desc: 'Allowlist of permitted binaries + injection prevention', source: 'Super-App', color: 'yellow' },
          ].map((f, i) => {
            const Icon = f.icon;
            return (
              <div key={i} className="p-4 rounded-xl bg-[#0a0a0a] border border-white/10 space-y-3">
                <div className="flex items-center space-x-2">
                  <Icon className={`w-5 h-5 text-${f.color}-400`} />
                  <h3 className="text-sm font-bold text-slate-200">{f.title}</h3>
                </div>
                <p className="text-xs text-slate-400">{f.desc}</p>
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className={`px-2 py-0.5 rounded bg-${f.color}-500/10 text-${f.color}-300 border border-${f.color}-500/20`}>
                    Source: {f.source}
                  </span>
                  <span className="text-emerald-400 flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3" /> Native
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Harnesses */}
      {activeSection === 'harnesses' && (
        <div className="space-y-4">
          <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6">
            <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Registered Agent Harnesses</span>
            </h3>
            <div className="space-y-3">
              {harnesses.length === 0 ? (
                <p className="text-xs text-slate-500">No harnesses loaded. Click refresh to load.</p>
              ) : (
                harnesses.map(h => (
                  <div key={h.id} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/10">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${h.available ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                      <span className="text-sm font-mono text-slate-300">{h.id}</span>
                      <span className="text-xs text-slate-500">({h.type})</span>
                    </div>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded ${h.available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-500'}`}>
                      {h.available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                ))
              )}
            </div>
            <button onClick={loadAll} className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs flex items-center space-x-2 cursor-pointer">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      )}

      {/* Capabilities */}
      {activeSection === 'capabilities' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center space-x-2">
            <Network className="w-4 h-4 text-purple-400" />
            <span>Capability Registry ({capabilities.length})</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {capabilities.map((cap, i) => (
              <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/10">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-mono text-purple-300">{cap.type}</span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${cap.enabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                    {cap.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{cap.name}</p>
                <p className="text-[10px] font-mono text-slate-500 mt-1">Provider: {cap.provider_id} | Priority: {cap.priority}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hooks */}
      {activeSection === 'hooks' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center space-x-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <span>Dual Hook System</span>
          </h3>
          <div className="space-y-3">
            {hooks.map((h, i) => (
              <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/10">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-mono text-amber-300">{h.name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400">
                    Priority: {h.priority}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  <span className="font-mono text-amber-500">{h.event}</span> — {h.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sessions */}
      {activeSection === 'sessions' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center space-x-2">
            <Server className="w-4 h-4 text-emerald-400" />
            <span>Session Manager ({sessions.length} sessions)</span>
          </h3>
          <div className="space-y-2">
            {sessions.map((s, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/10">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                  <span className="text-xs font-mono text-slate-300">{s.session_id}</span>
                  <span className="text-[10px] text-slate-500">{s.turn_count} turns | {s.token_count} tokens</span>
                </div>
                <div className="flex items-center space-x-2 text-[10px]">
                  <span className={`px-2 py-0.5 rounded ${s.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                    {s.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recipes */}
      {activeSection === 'recipes' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center space-x-2">
            <GitBranch className="w-4 h-4 text-rose-400" />
            <span>Recipe Runner ({recipes.length} recipes)</span>
          </h3>
          <div className="space-y-4">
            {recipes.map((r, i) => (
              <div key={i} className="p-4 rounded-lg bg-white/[0.02] border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-rose-300">{r.name}</span>
                  <button
                    onClick={async () => {
                      await fetch(`/api/recipes/${r.id}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
                    }}
                    className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs cursor-pointer flex items-center space-x-1"
                  >
                    <PlayCircle className="w-3 h-3" /> Run
                  </button>
                </div>
                <p className="text-xs text-slate-400 mb-2">{r.description}</p>
                <div className="flex flex-wrap gap-2">
                  {r.steps?.map((step: any, si: number) => (
                    <span key={si} className="text-[10px] font-mono px-2 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                      {step.name} → {step.skill}
                      {step.depends_on?.length ? ` (after: ${step.depends_on.join(', ')})` : ''}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security */}
      {activeSection === 'security' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <Shield className="w-4 h-4 text-red-400" />
            <span>Security Layer</span>
          </h3>
          <div className="space-y-3">
            {[
              { icon: Lock, title: 'Command Allowlist', desc: 'Only permitted binaries can execute. Blocks unknown executables by default.' },
              { icon: AlertCircle, title: 'Metacharacter Rejection', desc: 'Blocks ;, ||, &&, `, $(), ${}, >, <, () to prevent shell injection.' },
              { icon: Network, title: 'SSRF Protection', desc: 'Blocks private network ranges (127.x, 10.x, 172.16-31.x, 192.168.x, localhost).' },
              { icon: FileCode, title: 'Path Sandboxing', desc: 'File operations must resolve within the workspace directory.' },
            ].map((s, i) => {
              const Icon = s.icon;
              return (
                <div key={i} className="flex items-start space-x-3 p-3 rounded-lg bg-white/[0.02] border border-white/10">
                  <Icon className="w-4 h-4 text-red-400 mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-slate-200">{s.title}</p>
                    <p className="text-xs text-slate-400">{s.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Diagnostics */}
      {activeSection === 'diagnostics' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <Activity className="w-4 h-4 text-orange-400" />
            <span>Diagnostics</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-white/[0.02] border border-white/10">
              <h4 className="text-xs font-bold text-orange-300 mb-2">Session Liveness</h4>
              <div className="space-y-2 text-xs">
                <div className="flex items-center space-x-2"><div className="w-2 h-2 rounded-full bg-emerald-400" /> <span className="text-slate-300">active</span> — Recently interacted, normal</div>
                <div className="flex items-center space-x-2"><div className="w-2 h-2 rounded-full bg-yellow-400" /> <span className="text-slate-300">long_running</span> — Active but slow (&gt;5min)</div>
                <div className="flex items-center space-x-2"><div className="w-2 h-2 rounded-full bg-orange-400" /> <span className="text-slate-300">stalled</span> — No progress (&gt;10min)</div>
                <div className="flex items-center space-x-2"><div className="w-2 h-2 rounded-full bg-red-400" /> <span className="text-slate-300">stuck</span> — Stale, release lane</div>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-white/[0.02] border border-white/10">
              <h4 className="text-xs font-bold text-orange-300 mb-2">Timeline JSONL</h4>
              <p className="text-xs text-slate-400">
                Structured timing events written as JSONL for QA automation.
                Each event: envelope, event_id, phase, span, duration_ms, process_id, plugin_id.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};