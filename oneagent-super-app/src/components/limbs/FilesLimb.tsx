import React from 'react';
import { FolderKanban, ShieldCheck, HardDrive, Trash2, Tag, CheckCircle2 } from 'lucide-react';

export const FilesLimb: React.FC = () => {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-300 text-xs font-mono mb-2 border border-violet-500/20">
          <FolderKanban className="w-3.5 h-3.5" />
          <span>Local AI File Organizer & Storage Guardian Merged</span>
        </div>
        <h2 className="text-base font-bold text-slate-100">Files & Storage Guardian Limb</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Scans workspace for duplicate FHIR bundles, categorizes clinical docs, and enforces storage quotas.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-violet-400 font-bold">
            <HardDrive className="w-4 h-4" />
            <span>Storage Guardian Quota</span>
          </div>
          <div className="text-xl text-slate-100 font-bold">12.4 GB / 50 GB</div>
          <p className="text-slate-400 font-sans">184 FHIR JSON files, 42 research PDFs, 12 pytest logs.</p>
        </div>

        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-emerald-400 font-bold">
            <Tag className="w-4 h-4" />
            <span>AI Auto-Tagger</span>
          </div>
          <div className="text-xl text-slate-100 font-bold">100% Tagged</div>
          <p className="text-slate-400 font-sans">Organized into /modules/fhir, /modules/leap, and /modules/research.</p>
        </div>

        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-sky-400 font-bold">
            <Trash2 className="w-4 h-4" />
            <span>Duplicate Purger</span>
          </div>
          <div className="text-xl text-slate-100 font-bold">28 Dead Artifacts Purged</div>
          <p className="text-slate-400 font-sans">Eliminated 28 stale .xlsx/.csv files from legacy app forks.</p>
        </div>
      </div>
    </div>
  );
};
