import React, { useState } from 'react';
import { FileText, Sparkles, Copy, Check, Hash, Globe, FileCode } from 'lucide-react';

export const ContentLimb: React.FC = () => {
  const [topic, setTopic] = useState('How We Merged 34 AI-Generated Apps into One Agentic Runtime');
  const [generatedDraft, setGeneratedDraft] = useState('');
  const [isDrafting, setIsDrafting] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleDraft = () => {
    setIsDrafting(true);
    setTimeout(() => {
      setGeneratedDraft(`# ${topic}

*Published on OneAgent Tech Blog | Category: Software Architecture & AI Engineering*

## Introduction
Building multiple AI prototypes quickly leads to "app sprawl" — dozens of overlapping repositories, fragmented model providers, and skyrocketing API bills. In this article, we break down the architecture of **OneAgent**, a unified platform that consolidates 34 legacy forks behind a single, token-disciplined runtime.

## Key Architectural Principles
1. **Single LLM Gateway & Ranking Router**: Tasks are dynamically routed based on a preference-ranked queue (Gemini 3.6 Flash, Gemini 3.1 Pro, Claude Sonnet).
2. **Aggressive Prompt Caching**: Identical prompts match SQLite hashes for $0 cost on hits.
3. **OpenClaude Skills & MCP Connectors**: Standardized tool registries for Goose, Cherry, and OpenClaw.

## Conclusion
By unifying our runtime, we reduced token costs by 68% while enabling self-authoring meta-modules that safely grow the application on demand.
`);
      setIsDrafting(false);
    }, 600);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedDraft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 text-xs font-mono mb-2 border border-emerald-500/20">
            <FileText className="w-3.5 h-3.5" />
            <span>Automated Tech Blog & SEO Pipeline</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">Content & SEO Generator Limb</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Turns engineering notes, FHIR release logs, and research reports into Markdown blog posts and social snippets.
          </p>
        </div>
      </div>

      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="flex-1 w-full bg-[#050505] border border-white/10 text-slate-100 text-xs px-3 py-2.5 rounded-lg focus:outline-none focus:border-emerald-500 font-medium"
          />
          <button
            onClick={handleDraft}
            disabled={isDrafting}
            className="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-xs transition flex items-center justify-center space-x-2 shadow-md cursor-pointer shrink-0"
          >
            <Sparkles className="w-4 h-4" />
            <span>{isDrafting ? 'Drafting Article...' : 'Draft Article'}</span>
          </button>
        </div>

        {generatedDraft && (
          <div className="bg-[#050505] border border-white/10 rounded-xl p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <span className="text-emerald-400 font-bold flex items-center gap-2">
                <FileCode className="w-4 h-4" /> Markdown Output
              </span>
              <button
                onClick={handleCopy}
                className="flex items-center space-x-1 px-3 py-1 bg-white/5 hover:bg-white/10 text-slate-200 rounded text-[11px] border border-white/10 transition cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
              </button>
            </div>

            <pre className="text-slate-200 whitespace-pre-wrap font-sans leading-relaxed text-xs p-3 bg-[#0a0a0a] rounded border border-white/10">
              {generatedDraft}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
