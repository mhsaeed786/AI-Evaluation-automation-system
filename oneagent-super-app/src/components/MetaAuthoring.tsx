import React, { useState } from 'react';
import {
  Sparkles,
  Code2,
  CheckCircle2,
  XCircle,
  Play,
  RotateCcw,
  FileCode,
  ShieldCheck,
  History,
  Terminal,
  Loader2
} from 'lucide-react';
import { MetaModule } from '../types';

interface MetaAuthoringProps {
  modules: MetaModule[];
  onGenerateModule: (name: string, requirements: string) => Promise<MetaModule>;
  onApproveModule: (id: string) => void;
  onRejectModule: (id: string) => void;
  onRevertModule: (id: string) => void;
}

export const MetaAuthoring: React.FC<MetaAuthoringProps> = ({
  modules,
  onGenerateModule,
  onApproveModule,
  onRejectModule,
  onRevertModule,
}) => {
  const [newModuleName, setNewModuleName] = useState('');
  const [newModuleReqs, setNewModuleReqs] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeModule, setActiveModule] = useState<MetaModule | null>(modules[0] || null);

  const handleGenerate = async () => {
    if (!newModuleName.trim() || !newModuleReqs.trim()) return;
    setIsGenerating(true);
    try {
      const generated = await onGenerateModule(newModuleName, newModuleReqs);
      setActiveModule(generated);
      setNewModuleName('');
      setNewModuleReqs('');
    } catch (e) {
      console.error(e);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-300 text-xs font-mono mb-2 border border-blue-500/20">
            <Sparkles className="w-3.5 h-3.5" />
            <span>OpenClaude Meta-Extension Engine</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">Meta-Engine: Self-Authoring Module Generator</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            When existing tools can't solve a recurring task, the meta-agent writes new Python limb modules under <code className="font-mono text-blue-300">modules/</code>, runs pytest in an isolated venv, and exposes them in the UI.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Authoring Form */}
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 text-xs">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Code2 className="w-4 h-4 text-blue-400" />
            Author New Limb Module
          </h3>

          <div className="space-y-3">
            <div>
              <label className="text-slate-400 font-mono block mb-1">Module Name</label>
              <input
                type="text"
                placeholder="e.g. Stock Analyzer, Clinical Chart Parser"
                value={newModuleName}
                onChange={(e) => setNewModuleName(e.target.value)}
                className="w-full bg-[#050505] border border-white/10 text-slate-100 p-2.5 rounded-lg focus:outline-none focus:border-blue-500 font-medium"
              />
            </div>

            <div>
              <label className="text-slate-400 font-mono block mb-1">Requirements & Logic Description</label>
              <textarea
                rows={4}
                placeholder="Describe recurring task, inputs, and output structure..."
                value={newModuleReqs}
                onChange={(e) => setNewModuleReqs(e.target.value)}
                className="w-full bg-[#050505] border border-white/10 text-slate-100 p-3 rounded-lg focus:outline-none focus:border-blue-500 font-sans resize-none"
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating || !newModuleName.trim() || !newModuleReqs.trim()}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium rounded-lg transition flex items-center justify-center space-x-2 shadow-md cursor-pointer"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>Generating Code & Tests...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Author & Test Module in Sandbox</span>
                </>
              )}
            </button>
          </div>

          <div className="pt-3 border-t border-white/10 space-y-2">
            <div className="text-slate-400 font-mono text-[11px] uppercase">Generated Modules History</div>
            <div className="space-y-1">
              {modules.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setActiveModule(m)}
                  className={`w-full text-left p-2.5 rounded border transition cursor-pointer flex items-center justify-between ${
                    activeModule?.id === m.id
                      ? 'bg-blue-600/20 border-blue-500/50 text-blue-300'
                      : 'bg-[#050505] border-white/10 text-slate-400 hover:bg-white/5'
                  }`}
                >
                  <span className="font-semibold text-slate-200 truncate">{m.name}</span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded uppercase ${
                      m.status === 'approved'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : m.status === 'pending'
                        ? 'bg-amber-500/20 text-amber-300'
                        : 'bg-rose-500/20 text-rose-300'
                    }`}
                  >
                    {m.status}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Code Review & Diff Inspector */}
        {activeModule && (
          <div className="lg:col-span-2 bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 font-mono text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/10">
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-blue-400" />
                  {activeModule.name}
                  <span className="text-[10px] text-slate-400 font-normal">({activeModule.slug}.py)</span>
                </h3>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">Author: {activeModule.modelAuthor}</p>
              </div>

              {/* Review Actions */}
              <div className="flex items-center space-x-2">
                {activeModule.status === 'pending' && (
                  <>
                    <button
                      onClick={() => onApproveModule(activeModule.id)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-medium transition cursor-pointer flex items-center space-x-1"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve & Mount</span>
                    </button>
                    <button
                      onClick={() => onRejectModule(activeModule.id)}
                      className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded font-medium transition cursor-pointer flex items-center space-x-1"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </>
                )}

                {activeModule.status === 'approved' && (
                  <button
                    onClick={() => onRevertModule(activeModule.id)}
                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-slate-200 rounded font-medium border border-white/10 transition cursor-pointer flex items-center space-x-1"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Revert Module</span>
                  </button>
                )}
              </div>
            </div>

            {/* Generated Python Snippet */}
            <div className="space-y-2">
              <span className="text-blue-400 font-bold block">Generated Code (modules/{activeModule.slug}.py)</span>
              <pre className="p-3 bg-[#050505] rounded-lg border border-white/10 text-slate-200 overflow-x-auto text-[11px]">
                {activeModule.codeSnippet}
              </pre>
            </div>

            {/* Sandbox Pytest Verification */}
            <div className="space-y-2">
              <span className="text-emerald-400 font-bold flex items-center gap-2">
                <Terminal className="w-4 h-4" />
                Isolated Sandbox Test Results ({activeModule.testPassRate}% Pass Rate)
              </span>
              <div className="p-3 bg-[#050505] rounded-lg border border-white/10 text-emerald-300 text-[11px] font-mono">
                {activeModule.sandboxOutput}
              </div>
            </div>

            {/* Provenance Metadata */}
            <div className="p-3 bg-[#050505] rounded-lg border border-white/10 text-[11px] space-y-1 text-slate-400 font-mono">
              <div className="text-slate-300 font-bold">Provenance & Audit Trail:</div>
              <div>Generated by: {activeModule.provenance.generatedBy}</div>
              <div>Tokens Consumed: {activeModule.provenance.tokenCount}</div>
              <div>Parent Framework: {activeModule.provenance.parentFramework}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
