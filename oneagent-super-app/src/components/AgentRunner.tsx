import React, { useState } from 'react';
import {
  Terminal,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  Zap,
  Cpu,
  Layers,
  Sparkles,
  Loader2,
  ListOrdered
} from 'lucide-react';
import { TaskClass, AgentRunLog, LimbModuleManifest } from '../types';

interface AgentRunnerProps {
  limbs: LimbModuleManifest[];
  initialTaskPrompt?: string;
  initialModule?: string;
  onExecuteAgent: (prompt: string, module: string, taskClass: TaskClass) => Promise<AgentRunLog>;
}

export const AgentRunner: React.FC<AgentRunnerProps> = ({
  limbs,
  initialTaskPrompt = '',
  initialModule = 'fhir',
  onExecuteAgent,
}) => {
  const [taskPrompt, setTaskPrompt] = useState(
    initialTaskPrompt || 'Audit active FHIR Patient resources for US-Core missing mandatory fields and validate NPIs.'
  );
  const [selectedModule, setSelectedModule] = useState(initialModule || 'fhir');
  const [selectedTaskClass, setSelectedTaskClass] = useState<TaskClass>('reason');
  const [isRunning, setIsRunning] = useState(false);
  const [runLog, setRunLog] = useState<AgentRunLog | null>(null);

  const handleRun = async () => {
    if (!taskPrompt.trim()) return;
    setIsRunning(true);
    setRunLog(null);

    try {
      const log = await onExecuteAgent(taskPrompt, selectedModule, selectedTaskClass);
      setRunLog(log);
    } catch (err) {
      console.error('Agent execution error:', err);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-blue-400" />
            Generic Agent Loop Runtime (`Plan → Tool → Observe → Repeat`)
          </h2>
          <p className="text-xs text-slate-400 max-w-2xl">
            Single shared agent loop implementation used across all consolidated limbs. Dispatches tool calls, records step observations, and caches memory vectors.
          </p>
        </div>

        <div className="flex items-center space-x-2 font-mono text-xs text-slate-400 bg-[#050505] p-2.5 rounded-lg border border-white/10">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Loop Memory: Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Column */}
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest font-mono flex items-center gap-2">
            <ListOrdered className="w-4 h-4 text-blue-400" />
            Task Parameters
          </h3>

          <div className="space-y-3 text-xs">
            {/* Limb Module Selector */}
            <div>
              <label className="text-slate-400 font-mono block mb-1">Target Limb Module</label>
              <select
                value={selectedModule}
                onChange={(e) => setSelectedModule(e.target.value)}
                className="w-full bg-[#050505] border border-white/10 text-slate-200 px-3 py-2 rounded-lg font-medium focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                {limbs.map((l) => (
                  <option key={l.slug} value={l.slug}>
                    {l.name} ({l.toolCount} tools)
                  </option>
                ))}
              </select>
            </div>

            {/* Task Class Selector */}
            <div>
              <label className="text-slate-400 font-mono block mb-1">Task Class Routing</label>
              <select
                value={selectedTaskClass}
                onChange={(e) => setSelectedTaskClass(e.target.value as TaskClass)}
                className="w-full bg-[#050505] border border-white/10 text-slate-200 px-3 py-2 rounded-lg font-medium focus:outline-none focus:border-blue-500 cursor-pointer font-mono"
              >
                <option value="classify">Classify & Triage</option>
                <option value="extract">JSON Schema Extract</option>
                <option value="reason">Deep Reasoning (Default)</option>
                <option value="code">Code & Meta Generator</option>
                <option value="long_context">Long Context Analysis</option>
                <option value="vision">Vision & Multimodal</option>
              </select>
            </div>

            {/* Task Prompt Area */}
            <div>
              <label className="text-slate-400 font-mono block mb-1">Task Execution Prompt</label>
              <textarea
                rows={5}
                value={taskPrompt}
                onChange={(e) => setTaskPrompt(e.target.value)}
                placeholder="Describe task to execute through agent loop..."
                className="w-full bg-[#050505] border border-white/10 text-slate-100 p-3 rounded-lg text-xs font-sans focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            <button
              onClick={handleRun}
              disabled={isRunning || !taskPrompt.trim()}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium rounded-lg text-xs shadow-md shadow-blue-950 transition flex items-center justify-center space-x-2 cursor-pointer"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  <span>Executing Loop...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Execute Agent Loop</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Output Console Column */}
        <div className="lg:col-span-2 bg-[#050505] border border-white/10 rounded-xl p-5 space-y-4 flex flex-col font-mono text-xs">
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1.5">
                <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
              </div>
              <span className="text-slate-400 text-[11px] ml-2">oneagent-terminal@core-loop</span>
            </div>

            {runLog && (
              <div className="flex items-center space-x-3 text-[11px] text-slate-400">
                <span>Model: <strong className="text-blue-400">{runLog.modelUsed}</strong></span>
                <span>Time: <strong className="text-slate-200">{runLog.executionTimeMs}ms</strong></span>
                <span>Tokens: <strong className="text-amber-400">{runLog.totalTokens}</strong></span>
              </div>
            )}
          </div>

          {/* Execution Log Stream */}
          <div className="flex-1 overflow-y-auto space-y-4 min-h-[360px] max-h-[500px]">
            {!runLog && !isRunning && (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-2 py-16">
                <Terminal className="w-8 h-8 opacity-40 text-slate-500" />
                <p className="text-xs">Agent loop idle. Enter prompt and click 'Execute Agent Loop'.</p>
              </div>
            )}

            {isRunning && (
              <div className="p-4 bg-blue-950/30 border border-blue-500/30 rounded-lg text-blue-300 space-y-2 animate-pulse">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span className="font-bold">Dispatching to LLM Router...</span>
                </div>
                <p className="text-[11px] text-slate-400">Selecting model via task class preference queue, inspecting prompt cache, building execution plan...</p>
              </div>
            )}

            {runLog && (
              <div className="space-y-4">
                {runLog.steps.map((step) => (
                  <div key={step.stepNumber} className="p-3 bg-[#0a0a0a] rounded-lg border border-white/10 space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 rounded-full bg-blue-600/30 text-blue-400 border border-blue-500/40 flex items-center justify-center font-bold text-[10px]">
                          #{step.stepNumber}
                        </span>
                        <span className="font-bold text-slate-200 uppercase">{step.phase}</span>
                        <span className="text-slate-400 font-sans">{step.title}</span>
                      </div>
                      <span className="text-slate-500">{step.timestamp}</span>
                    </div>

                    <p className="text-slate-300 text-xs font-sans pl-7">{step.details}</p>

                    {step.toolName && (
                      <div className="ml-7 p-2 bg-[#050505] rounded border border-white/10 text-[11px] text-amber-300">
                        Tool Called: <strong>{step.toolName}</strong> ({JSON.stringify(step.toolArgs)})
                      </div>
                    )}

                    {step.output && (
                      <div className="ml-7 p-2 bg-[#050505] rounded border border-white/10 text-[11px] text-emerald-400">
                        Output: {JSON.stringify(step.output)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
