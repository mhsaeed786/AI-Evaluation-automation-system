import React, { useState } from 'react';
import { Code, Terminal, Play, FolderPlus, GitBranch, CheckCircle2 } from 'lucide-react';

export const CodingLimb: React.FC = () => {
  const [cliCommand, setCliCommand] = useState('python -m oneagent.cli ask --task classify "is this an FHIR Patient resource?"');
  const [cliOutput, setCliOutput] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);

  const handleRunCommand = () => {
    setIsExecuting(true);
    setTimeout(() => {
      setCliOutput(`$ ${cliCommand}

[OneAgent CLI Controller - Version 1.0.0]
--------------------------------------------------
Task Class: CLASSIFY
Model Selected: gemini-3.6-flash (Ranked Priority #1)
Cache Check: Hash matched #8f92a11b0e ($0.00 spent)

Result:
Resource type confirmed: FHIR Patient (US-Core 6.1.0 profile)
Confidence: 99.8%
Execution Time: 12ms (Cached)
`);
      setIsExecuting(false);
    }, 400);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5">
        <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-300 text-xs font-mono mb-2 border border-blue-500/20">
          <Code className="w-3.5 h-3.5" />
          <span>CLI Controller & Repository Scaffolder</span>
        </div>
        <h2 className="text-base font-bold text-slate-100">CLI Controller & Code Limb</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Execute OneAgent CLI commands (`oneagent.cli ask`, `oneagent.cli run-agent`, `oneagent.cli budget`) and scaffold new limb plugins.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 font-mono text-xs">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Terminal className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={cliCommand}
              onChange={(e) => setCliCommand(e.target.value)}
              className="w-full bg-[#050505] border border-white/10 text-slate-100 text-xs pl-9 pr-4 py-2.5 rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            onClick={handleRunCommand}
            disabled={isExecuting}
            className="w-full sm:w-auto px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition flex items-center justify-center space-x-2 shadow-md cursor-pointer shrink-0"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>{isExecuting ? 'Executing...' : 'Run CLI Command'}</span>
          </button>
        </div>

        {cliOutput && (
          <pre className="p-4 bg-[#050505] border border-white/10 text-slate-200 rounded-xl leading-relaxed text-[11px] overflow-x-auto">
            {cliOutput}
          </pre>
        )}
      </div>
    </div>
  );
};
