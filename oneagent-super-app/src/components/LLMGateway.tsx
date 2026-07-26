import React, { useState } from 'react';
import {
  Cpu,
  Zap,
  Shield,
  Layers,
  ArrowUp,
  ArrowDown,
  RefreshCw,
  CheckCircle2,
  Sliders,
  DollarSign,
  Search,
  Database
} from 'lucide-react';
import { ModelConfig, TaskRanking, CacheEntry, BudgetStats, TaskClass } from '../types';

interface LLMGatewayProps {
  models: ModelConfig[];
  taskRankings: TaskRanking[];
  cacheEntries: CacheEntry[];
  budgetStats: BudgetStats;
  onUpdateRankings: (newRankings: TaskRanking[]) => void;
  onUpdateBudgetCap: (newCap: number) => void;
}

export const LLMGateway: React.FC<LLMGatewayProps> = ({
  models,
  taskRankings,
  cacheEntries,
  budgetStats,
  onUpdateRankings,
  onUpdateBudgetCap,
}) => {
  const [selectedTaskClass, setSelectedTaskClass] = useState<TaskClass>('reason');
  const [activeTab, setActiveTab] = useState<'ranking' | 'cache' | 'providers'>('ranking');
  const [searchTerm, setSearchTerm] = useState('');

  const taskClasses: { id: TaskClass; label: string; desc: string }[] = [
    { id: 'classify', label: 'Classify & Triage', desc: 'Resource tagging, status triage' },
    { id: 'extract', label: 'JSON Extraction', desc: 'FHIR Schema, logs parsing' },
    { id: 'reason', label: 'Deep Reasoning', desc: 'Healthcare QA, LEAP analysis' },
    { id: 'code', label: 'Meta-Codegen', desc: 'Self-authoring python modules' },
    { id: 'long_context', label: 'Long Context', desc: 'Large FHIR bundles, ONC specs' },
    { id: 'vision', label: 'Vision & Multimodal', desc: 'Medical chart scans, OCR' },
  ];

  const currentRanking = taskRankings.find((r) => r.taskClass === selectedTaskClass) || taskRankings[0];

  const moveModelInRanking = (index: number, direction: 'up' | 'down') => {
    const updatedModelIds = [...currentRanking.rankedModelIds];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    if (targetIndex < 0 || targetIndex >= updatedModelIds.length) return;

    const temp = updatedModelIds[index];
    updatedModelIds[index] = updatedModelIds[targetIndex];
    updatedModelIds[targetIndex] = temp;

    const newRankings = taskRankings.map((tr) =>
      tr.taskClass === selectedTaskClass ? { ...tr, rankedModelIds: updatedModelIds } : tr
    );

    onUpdateRankings(newRankings);
  };

  const handleSetOverride = (modelId: string | undefined) => {
    const newRankings = taskRankings.map((tr) =>
      tr.taskClass === selectedTaskClass ? { ...tr, overrideModelId: modelId } : tr
    );
    onUpdateRankings(newRankings);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header Card */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-400" />
            Token-Disciplined LLM Gateway & Ranking Router
          </h2>
          <p className="text-xs text-slate-400 max-w-2xl">
            All AI queries route through one central gateway. Tasks are dispatched to the highest-ranked preference model for that task class, with automatic prompt hashing cache ($0 on hit) and daily budget caps.
          </p>
        </div>

        {/* Budget Setting Controls */}
        <div className="flex items-center space-x-3 bg-[#050505] p-3 rounded-lg border border-white/10 shrink-0">
          <DollarSign className="w-5 h-5 text-emerald-400" />
          <div>
            <label className="text-[10px] text-slate-400 block uppercase font-mono">Daily Budget Ceiling ($)</label>
            <div className="flex items-center space-x-2 mt-0.5">
              <input
                type="number"
                step="0.5"
                value={budgetStats.dailyCapUSD}
                onChange={(e) => onUpdateBudgetCap(parseFloat(e.target.value) || 1.0)}
                className="w-20 bg-[#0a0a0a] border border-white/10 text-slate-100 px-2 py-1 rounded text-xs font-mono focus:outline-none focus:border-blue-500"
              />
              <span className="text-xs text-slate-400 font-mono">USD / day</span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-white/10 space-x-6 text-sm">
        <button
          onClick={() => setActiveTab('ranking')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'ranking'
              ? 'text-blue-400 border-b-2 border-blue-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Task-Class Preference Rankings</span>
        </button>

        <button
          onClick={() => setActiveTab('cache')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'cache'
              ? 'text-blue-400 border-b-2 border-blue-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Prompt Cache Inspector ({cacheEntries.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('providers')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'providers'
              ? 'text-blue-400 border-b-2 border-blue-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Provider Adapters & Latency</span>
        </button>
      </div>

      {/* TAB 1: Task Class Rankings */}
      {activeTab === 'ranking' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Task Class Picker Column */}
          <div className="space-y-2">
            <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest font-mono px-1">
              Select Task Class
            </label>
            <div className="space-y-1">
              {taskClasses.map((tc) => (
                <button
                  key={tc.id}
                  onClick={() => setSelectedTaskClass(tc.id)}
                  className={`w-full text-left p-3 rounded-lg border text-xs transition cursor-pointer ${
                    selectedTaskClass === tc.id
                      ? 'bg-blue-600/15 border-blue-500/50 text-blue-300 shadow-sm'
                      : 'bg-[#0a0a0a] border-white/10 text-slate-400 hover:bg-white/5 hover:text-slate-200'
                  }`}
                >
                  <div className="font-semibold text-slate-200">{tc.label}</div>
                  <div className="text-[11px] text-slate-500 font-mono mt-0.5">{tc.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Ranking Reordering Column */}
          <div className="lg:col-span-3 bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/10">
              <div>
                <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-blue-600/20 text-blue-300 font-mono text-xs uppercase border border-blue-500/30">
                    {selectedTaskClass}
                  </span>
                  Preference Model Queue
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Top-ranked enabled model is automatically chosen unless overriden.
                </p>
              </div>

              {/* Override selector */}
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-slate-400 font-mono">Task Override:</span>
                <select
                  value={currentRanking.overrideModelId || ''}
                  onChange={(e) => handleSetOverride(e.target.value || undefined)}
                  className="bg-[#050505] border border-white/10 text-slate-200 px-2 py-1 rounded focus:outline-none focus:border-blue-500 font-mono"
                >
                  <option value="">Auto (Use Ranking Queue)</option>
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      Force: {m.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Models Ranked List */}
            <div className="space-y-2">
              {currentRanking.rankedModelIds.map((modelId, index) => {
                const model = models.find((m) => m.id === modelId);
                if (!model) return null;

                const isFirst = index === 0 && !currentRanking.overrideModelId;
                const isOverridden = currentRanking.overrideModelId === model.id;

                return (
                  <div
                    key={model.id}
                    className={`p-3 rounded-lg border flex items-center justify-between space-x-4 transition ${
                      isOverridden || isFirst
                        ? 'bg-blue-950/30 border-blue-500/40 text-slate-100'
                        : 'bg-[#050505] border-white/10 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-6 h-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center font-mono text-xs font-bold text-slate-300">
                        #{index + 1}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-slate-100">{model.name}</span>
                          {isFirst && (
                            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              ACTIVE PRIORITY
                            </span>
                          )}
                          {isOverridden && (
                            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              MANUAL OVERRIDE
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono space-x-3 mt-0.5">
                          <span>In: ${model.inputCostPer1K}/1K</span>
                          <span>Out: ${model.outputCostPer1K}/1K</span>
                          <span>Latency: {model.latencyMs}ms</span>
                          <span>Score: {model.qualityScore}/100</span>
                        </div>
                      </div>
                    </div>

                    {/* Move Controls */}
                    <div className="flex items-center space-x-1 shrink-0">
                      <button
                        onClick={() => moveModelInRanking(index, 'up')}
                        disabled={index === 0}
                        className="p-1 rounded bg-white/5 hover:bg-white/10 disabled:opacity-30 text-slate-300 transition cursor-pointer border border-white/10"
                        title="Move Up"
                      >
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => moveModelInRanking(index, 'down')}
                        disabled={index === currentRanking.rankedModelIds.length - 1}
                        className="p-1 rounded bg-white/5 hover:bg-white/10 disabled:opacity-30 text-slate-300 transition cursor-pointer border border-white/10"
                        title="Move Down"
                      >
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Prompt Cache Inspector */}
      {activeTab === 'cache' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                Response Cache Ledger (SQLite Hash Match)
              </h3>
              <p className="text-xs text-slate-400">
                Identical prompts skip LLM billing completely. Saved <strong>${budgetStats.savedCostUSDToday.toFixed(4)} USD</strong> today.
              </p>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search prompt hash..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-[#050505] border border-white/10 text-slate-200 text-xs pl-8 pr-3 py-1.5 rounded focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#050505] text-slate-400 uppercase text-[10px] border-b border-white/10">
                <tr>
                  <th className="p-3">Prompt Hash</th>
                  <th className="p-3">Prompt Snippet</th>
                  <th className="p-3">Task Class</th>
                  <th className="p-3">Model Used</th>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3 text-right">Saved ($)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {cacheEntries
                  .filter((c) => c.promptSnippet.toLowerCase().includes(searchTerm.toLowerCase()) || c.hash.includes(searchTerm))
                  .map((entry) => (
                    <tr key={entry.hash} className="hover:bg-white/5 transition">
                      <td className="p-3 font-semibold text-blue-400">#{entry.hash}</td>
                      <td className="p-3 text-slate-200 font-sans max-w-xs truncate">{entry.promptSnippet}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded bg-white/5 text-slate-300 border border-white/10">{entry.taskClass}</span>
                      </td>
                      <td className="p-3 text-slate-400">{entry.modelUsed}</td>
                      <td className="p-3 text-slate-500">{entry.timestamp}</td>
                      <td className="p-3 text-right text-emerald-400 font-bold">
                        +${entry.costSavedUSD.toFixed(5)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Providers Status */}
      {activeTab === 'providers' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m) => (
            <div key={m.id} className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-100">{m.name}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-600/20 text-blue-300 uppercase border border-blue-500/30">
                  {m.provider}
                </span>
              </div>
              <div className="space-y-1.5 text-xs font-mono text-slate-400">
                <div className="flex justify-between">
                  <span>Input / 1K tokens:</span>
                  <span className="text-slate-200">${m.inputCostPer1K}</span>
                </div>
                <div className="flex justify-between">
                  <span>Output / 1K tokens:</span>
                  <span className="text-slate-200">${m.outputCostPer1K}</span>
                </div>
                <div className="flex justify-between">
                  <span>Context Window:</span>
                  <span className="text-slate-200">{m.contextWindow.toLocaleString()} tokens</span>
                </div>
                <div className="flex justify-between">
                  <span>Avg Latency:</span>
                  <span className="text-slate-200">{m.latencyMs} ms</span>
                </div>
              </div>
              <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[11px]">
                <span className="text-emerald-400 flex items-center gap-1 font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Adapter Ready
                </span>
                <span className="text-slate-500 font-mono">Quality Score: {m.qualityScore}/100</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
