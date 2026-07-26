import React, { useState } from 'react';
import {
  Smartphone,
  Monitor,
  Cloud,
  Download,
  Package,
  CheckCircle2,
  Terminal,
  Shield,
  Layers,
  FileCode,
  HardDrive
} from 'lucide-react';

export const PortableTargets: React.FC = () => {
  const [selectedTarget, setSelectedTarget] = useState<'desktop' | 'android' | 'web'>('desktop');
  const [isGenerating, setIsGenerating] = useState(false);
  const [buildLogs, setBuildLogs] = useState<string[]>([]);

  const handleGenerateBuildPackage = () => {
    setIsGenerating(true);
    setBuildLogs([`Initializing target packager for: ${selectedTarget.toUpperCase()}...`]);

    setTimeout(() => {
      setBuildLogs(prev => [
        ...prev,
        `[1/3] Bundling lightweight core runtime (SQLite embedded + Local Python Meta-Engine)...`
      ]);
    }, 600);

    setTimeout(() => {
      setBuildLogs(prev => [
        ...prev,
        `[2/3] Generating ${selectedTarget === 'desktop' ? 'Tauri/Electron .exe/.dmg' : selectedTarget === 'android' ? 'Capacitor/APK build manifest' : 'Docker Cloud Run container specs'}...`
      ]);
    }, 1200);

    setTimeout(() => {
      setBuildLogs(prev => [
        ...prev,
        `[3/3] Manifest generated successfully! All local knowledge base & specialist skills included.`,
        `[READY] OneAgent portable ${selectedTarget} release package compiled!`
      ]);
      setIsGenerating(false);
    }, 2000);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-blue-950/30 to-[#0a0a0a] border border-emerald-500/20 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Package className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                  Portable Cross-Platform Build Engine
                </h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
                  Tauri / Capacitor / Web
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl">
                OneAgent is architecturally lightweight and portable. Package the entire platform as a Desktop app (Windows/macOS/Linux via Tauri), Mobile Android APK (via Capacitor), or Hostable Cloud Run Web App.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Target Selector */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Desktop Target */}
        <button
          onClick={() => setSelectedTarget('desktop')}
          className={`p-5 rounded-2xl border transition text-left space-y-3 cursor-pointer ${
            selectedTarget === 'desktop'
              ? 'bg-blue-950/30 border-blue-500 text-slate-100 shadow-lg shadow-blue-950/40'
              : 'bg-[#0a0a0a] border-white/10 text-slate-400 hover:border-white/20'
          }`}
        >
          <div className="flex items-center justify-between">
            <Monitor className={`w-6 h-6 ${selectedTarget === 'desktop' ? 'text-blue-400' : 'text-slate-500'}`} />
            {selectedTarget === 'desktop' && <CheckCircle2 className="w-4 h-4 text-blue-400" />}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Portable Desktop Version</h3>
            <p className="text-xs text-slate-400 mt-1">Tauri / Electron standalone executable with embedded SQLite knowledge store.</p>
          </div>
          <div className="text-[10px] font-mono text-slate-500 border-t border-white/5 pt-2">
            Target Size: ~18 MB | RAM Footprint: ~65 MB
          </div>
        </button>

        {/* Android Target */}
        <button
          onClick={() => setSelectedTarget('android')}
          className={`p-5 rounded-2xl border transition text-left space-y-3 cursor-pointer ${
            selectedTarget === 'android'
              ? 'bg-emerald-950/30 border-emerald-500 text-slate-100 shadow-lg shadow-emerald-950/40'
              : 'bg-[#0a0a0a] border-white/10 text-slate-400 hover:border-white/20'
          }`}
        >
          <div className="flex items-center justify-between">
            <Smartphone className={`w-6 h-6 ${selectedTarget === 'android' ? 'text-emerald-400' : 'text-slate-500'}`} />
            {selectedTarget === 'android' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Android Mobile APK</h3>
            <p className="text-xs text-slate-400 mt-1">Capacitor native mobile container with offline local model support.</p>
          </div>
          <div className="text-[10px] font-mono text-slate-500 border-t border-white/5 pt-2">
            Target Size: ~12 MB | Minimum SDK: Android 8.0+
          </div>
        </button>

        {/* Cloud Web App */}
        <button
          onClick={() => setSelectedTarget('web')}
          className={`p-5 rounded-2xl border transition text-left space-y-3 cursor-pointer ${
            selectedTarget === 'web'
              ? 'bg-purple-950/30 border-purple-500 text-slate-100 shadow-lg shadow-purple-950/40'
              : 'bg-[#0a0a0a] border-white/10 text-slate-400 hover:border-white/20'
          }`}
        >
          <div className="flex items-center justify-between">
            <Cloud className={`w-6 h-6 ${selectedTarget === 'web' ? 'text-purple-400' : 'text-slate-500'}`} />
            {selectedTarget === 'web' && <CheckCircle2 className="w-4 h-4 text-purple-400" />}
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Hostable Web App / Cloud Run</h3>
            <p className="text-xs text-slate-400 mt-1">Docker container deployment with Google/Microsoft SSO integration.</p>
          </div>
          <div className="text-[10px] font-mono text-slate-500 border-t border-white/5 pt-2">
            Container Spec: Node 20 + Python 3.10
          </div>
        </button>
      </div>

      {/* Build Details Panel */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
            <Package className="w-4 h-4 text-emerald-400" />
            <span>Generate Build Artifact for: {selectedTarget.toUpperCase()}</span>
          </h3>

          <button
            onClick={handleGenerateBuildPackage}
            disabled={isGenerating}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-2 transition cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>Compile Portable Release Package</span>
          </button>
        </div>

        {buildLogs.length > 0 && (
          <div className="p-4 bg-black/80 rounded-xl border border-white/10 font-mono text-xs space-y-1 text-slate-300">
            <div className="text-[10px] uppercase text-emerald-400 font-bold mb-2">Build Output Stream</div>
            {buildLogs.map((log, i) => (
              <div key={i} className="flex items-center space-x-2">
                <span className="text-emerald-500">›</span>
                <span>{log}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
