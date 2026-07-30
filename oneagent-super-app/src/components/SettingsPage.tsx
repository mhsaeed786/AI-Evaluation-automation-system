import React from 'react';
import { Settings, Key, Shield, CheckCircle2, Cpu, Server, Database } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-300 text-xs font-mono mb-2 border border-blue-500/20">
          <Settings className="w-3.5 h-3.5" />
          <span>OneAgent Environment Configuration</span>
        </div>
        <h2 className="text-base font-bold text-slate-100">System Settings & Key Management</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Server-side API keys, model ranking parameters, and Keycloak authentication bridge.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono">
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 font-sans">
            <Key className="w-4 h-4 text-amber-400" />
            API Key Injections (.env.example)
          </h3>

          <div className="space-y-3">
            <div className="p-3 bg-[#050505] rounded border border-white/10 space-y-1">
              <div className="flex justify-between font-bold text-slate-200 font-sans">
                <span>GEMINI_API_KEY</span>
                <span className="text-emerald-400 font-mono">AUTO_INJECTED</span>
              </div>
              <p className="text-slate-400 font-sans text-[11px]">Server-side Google GenAI SDK key managed via AI Studio Secrets panel.</p>
            </div>

            <div className="p-3 bg-[#050505] rounded border border-white/10 space-y-1">
              <div className="flex justify-between font-bold text-slate-200 font-sans">
                <span>ANTHROPIC_API_KEY</span>
                <span className="text-slate-400 font-mono">OPTIONAL</span>
              </div>
              <p className="text-slate-400 font-sans text-[11px]">Claude 3.7 Sonnet adapter key.</p>
            </div>
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 font-sans">
            <Server className="w-4 h-4 text-sky-400" />
            Authentication & Persistence Architecture
          </h3>

          <div className="p-3 bg-[#050505] rounded border border-white/10 space-y-2 text-slate-300 font-sans">
            <div className="flex items-center space-x-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span className="font-bold font-mono text-xs">Single Runtime Engine Active</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Keycloak Single-Sign-On donated from FHIR developer portal. Single shared SQLite/SQLModel database backing all 7 limbs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
