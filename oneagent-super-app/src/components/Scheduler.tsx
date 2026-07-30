import React, { useState } from 'react';
import { Clock, Play, Pause, CheckCircle2, Plus, Calendar, AlertCircle } from 'lucide-react';
import { CronJob } from '../types';

interface SchedulerProps {
  cronJobs: CronJob[];
  onToggleJobStatus: (id: string) => void;
  onTriggerJobNow: (id: string) => Promise<void>;
}

export const Scheduler: React.FC<SchedulerProps> = ({
  cronJobs,
  onToggleJobStatus,
  onTriggerJobNow,
}) => {
  const [runningId, setRunningId] = useState<string | null>(null);

  const handleRunNow = async (id: string) => {
    setRunningId(id);
    await onTriggerJobNow(id);
    setRunningId(null);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 text-xs font-mono mb-2 border border-emerald-500/20">
            <Clock className="w-3.5 h-3.5" />
            <span>Celery & Redis Scheduler Background Daemon</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">Cron Scheduler & Scheduled Agents</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Automated recurring agent tasks: "Every Monday 8am LEAP digest", "Nightly FHIR Inconsistency Sweep", "SEO Blog Drafter".
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {cronJobs.map((job) => (
          <div
            key={job.id}
            className="p-5 bg-[#0a0a0a] border border-white/10 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs"
          >
            <div className="space-y-2 max-w-xl">
              <div className="flex items-center space-x-3">
                <span className="font-bold text-slate-100 text-sm">{job.name}</span>
                <span className="font-mono text-[10px] px-2 py-0.5 bg-white/5 text-slate-300 rounded border border-white/10">
                  {job.module}
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded border border-blue-500/30 font-bold">
                  Cron: {job.cronExpression}
                </span>
              </div>

              <p className="text-slate-300 font-sans">{job.taskPrompt}</p>

              <div className="flex items-center space-x-4 font-mono text-[11px] text-slate-400">
                <span>Schedule: <strong className="text-slate-200">{job.humanSchedule}</strong></span>
                <span>Next Run: <strong className="text-emerald-400">{job.nextRun}</strong></span>
              </div>
            </div>

            <div className="flex items-center space-x-3 shrink-0">
              <button
                onClick={() => handleRunNow(job.id)}
                disabled={runningId === job.id}
                className="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-xs transition flex items-center space-x-1.5 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>{runningId === job.id ? 'Running Task...' : 'Run Now'}</span>
              </button>

              <button
                onClick={() => onToggleJobStatus(job.id)}
                className={`px-3 py-2 rounded-lg text-xs font-mono transition cursor-pointer ${
                  job.status === 'active'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-white/5 text-slate-400 border border-white/10'
                }`}
              >
                {job.status === 'active' ? 'Pause Cron' : 'Resume Cron'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
