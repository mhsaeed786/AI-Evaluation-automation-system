import React, { useState } from 'react';
import { Workflow, Mail, MessageSquare, Download, Play, CheckCircle2 } from 'lucide-react';

export const WorkOpsLimb: React.FC = () => {
  const [synced, setSynced] = useState(false);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-300 text-xs font-mono mb-2 border border-blue-500/20">
            <Workflow className="w-3.5 h-3.5" />
            <span>4 WorkOps Apps Merged (Outlook, Teams, SharePoint, DataSync)</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">WorkOps & DataSync Orchestrator</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Auto-triage emails, monitor Teams channels, download SharePoint bundles, and run pytest harness for DataSync pipelines.
          </p>
        </div>

        <button
          onClick={() => setSynced(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition flex items-center space-x-2 shadow-md cursor-pointer"
        >
          <Play className="w-4 h-4 fill-white" />
          <span>Sync WorkOps Pipelines</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs font-mono">
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3">
          <div className="flex items-center space-x-2 text-blue-400 font-bold">
            <Mail className="w-4 h-4" />
            <span>Outlook Triage Engine</span>
          </div>
          <p className="text-slate-400 font-sans">Scans inbox for 'FHIR Error' & 'HAPI Server' threads and drafts automated QA replies.</p>
          <div className="p-2 bg-[#050505] rounded border border-white/10 text-[11px] text-emerald-400">
            Status: 14 Threads Analyzed, 0 Pending
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3">
          <div className="flex items-center space-x-2 text-blue-400 font-bold">
            <MessageSquare className="w-4 h-4" />
            <span>Teams Channel Bot</span>
          </div>
          <p className="text-slate-400 font-sans">Posts nightly FHIR inconsistency digests to #curemd-qa-alerts channel.</p>
          <div className="p-2 bg-[#050505] rounded border border-white/10 text-[11px] text-emerald-400">
            Status: Webhook Active
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3">
          <div className="flex items-center space-x-2 text-blue-400 font-bold">
            <Download className="w-4 h-4" />
            <span>DataSync & Pytest Harness</span>
          </div>
          <p className="text-slate-400 font-sans">Executes pytest test suites across DataSync pipelines and archives logs to SharePoint.</p>
          <div className="p-2 bg-[#050505] rounded border border-white/10 text-[11px] text-emerald-400">
            Pytest Pass Rate: 100% (24/24)
          </div>
        </div>
      </div>
    </div>
  );
};
