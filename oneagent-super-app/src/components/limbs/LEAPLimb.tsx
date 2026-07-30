import React, { useState } from 'react';
import {
  BarChart3,
  Zap,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  AlertTriangle,
  Play,
  ShieldAlert,
  Ticket
} from 'lucide-react';
import { LEAPMetric } from '../../types';

interface LEAPLimbProps {
  metrics: LEAPMetric[];
  onTriggerCheck: () => Promise<void>;
}

export const LEAPLimb: React.FC<LEAPLimbProps> = ({ metrics, onTriggerCheck }) => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'rwt' | 'uds' | 'tickets'>('metrics');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleRunDiagnostics = async () => {
    setIsProcessing(true);
    await onTriggerCheck();
    setIsProcessing(false);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 text-xs font-mono mb-2 border border-amber-500/20">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>5 Legacy LEAP Modules Merged into 1 Limb</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">LEAP Analytics & RWT Diagnostics Suite</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real World Testing (RWT) telemetry, server throughput scaling, UDS compliance, and automated QA support tickets.
          </p>
        </div>

        <button
          onClick={handleRunDiagnostics}
          disabled={isProcessing}
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white font-medium rounded-lg text-xs transition flex items-center space-x-2 shadow-md shadow-amber-950 cursor-pointer"
        >
          <Play className="w-4 h-4 fill-white" />
          <span>{isProcessing ? 'Evaluating Telemetry...' : 'Run LEAP Diagnostics'}</span>
        </button>
      </div>

      {/* Sub Tabs */}
      <div className="flex border-b border-white/10 space-x-6 text-sm">
        <button
          onClick={() => setActiveTab('metrics')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'metrics'
              ? 'text-amber-400 border-b-2 border-amber-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Telemetry Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('rwt')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'rwt'
              ? 'text-amber-400 border-b-2 border-amber-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Zap className="w-4 h-4" />
          <span>RWT Scaling Specs</span>
        </button>

        <button
          onClick={() => setActiveTab('uds')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'uds'
              ? 'text-amber-400 border-b-2 border-amber-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>UDS eCQM Compliance</span>
        </button>

        <button
          onClick={() => setActiveTab('tickets')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeTab === 'tickets'
              ? 'text-amber-400 border-b-2 border-amber-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Ticket className="w-4 h-4" />
          <span>QA Support Triage</span>
        </button>
      </div>

      {/* TAB 1: Metrics */}
      {activeTab === 'metrics' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {metrics.map((m, idx) => (
            <div key={idx} className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>{m.title}</span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white/5 border border-white/10">{m.category}</span>
              </div>

              <div className="text-2xl font-bold font-mono text-slate-100">{m.value}</div>

              <div className="flex items-center justify-between text-xs font-mono">
                <span className={`flex items-center gap-1 ${m.trend === 'up' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {m.trend === 'up' ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {m.change}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                    m.status === 'optimal'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  }`}
                >
                  {m.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 2: RWT Scaling */}
      {activeTab === 'rwt' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 text-xs font-mono">
          <h3 className="text-sm font-semibold text-slate-100 font-sans">Real World Testing (RWT) High Throughput Log</h3>
          <p className="text-slate-400 font-sans">
            LEAP continuous traffic simulator verifying 5,000 requests/sec under ONC certified EHR load testing.
          </p>

          <div className="p-4 bg-[#050505] rounded-lg border border-white/10 space-y-2">
            <div className="flex justify-between text-slate-300">
              <span>Peak Simulated Concurrency:</span>
              <span className="text-emerald-400 font-bold">12,500 active threads</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Average P99 Response Latency:</span>
              <span className="text-emerald-400 font-bold">142 ms</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>HTTP 5xx Error Rate:</span>
              <span className="text-emerald-400 font-bold">0.0012% (Pass)</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: UDS Compliance */}
      {activeTab === 'uds' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 text-xs font-mono">
          <h3 className="text-sm font-semibold text-slate-100 font-sans">UDS eCQM Clinical Measure Thresholds</h3>
          <div className="space-y-3">
            <div className="p-3 bg-[#050505] rounded border border-white/10 space-y-1">
              <div className="flex justify-between text-slate-200 font-bold font-sans">
                <span>CMS122v11: Diabetes HbA1c Poor Control (&gt;9.0%)</span>
                <span className="text-emerald-400">Target: &lt;15% (Actual: 11.2%)</span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans">Status: Compliant with ONC UDS reporting requirements.</p>
            </div>

            <div className="p-3 bg-[#050505] rounded border border-white/10 space-y-1">
              <div className="flex justify-between text-slate-200 font-bold font-sans">
                <span>CMS165v11: Controlling High Blood Pressure</span>
                <span className="text-amber-400">Target: &gt;75% (Actual: 72.8%)</span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans">Status: Needs attention. 2.2% below optimal target threshold.</p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Support Triage */}
      {activeTab === 'tickets' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 text-xs font-mono">
          <h3 className="text-sm font-semibold text-slate-100 font-sans">HealthOS QA Support Ticket Triage Queue</h3>
          <div className="p-3 bg-[#050505] rounded border border-white/10 space-y-2">
            <div className="flex justify-between font-bold text-slate-200 font-sans">
              <span>Ticket #4912: LEAP RWT Telemetry Timeout during Bulk Export</span>
              <span className="text-amber-400">HIGH PRIORITY</span>
            </div>
            <p className="text-slate-400 font-sans">Auto-Triage Diagnosis: Agent identified memory spike in bulk export worker. Suggested fix: increase Redis queue timeout to 30s.</p>
          </div>
        </div>
      )}
    </div>
  );
};
