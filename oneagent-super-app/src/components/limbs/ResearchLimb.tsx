import React, { useState } from 'react';
import { Search, Sparkles, ExternalLink, Lightbulb, Play, BookOpen, Layers } from 'lucide-react';
import { ResearchReport } from '../../types';

interface ResearchLimbProps {
  reports: ResearchReport[];
  onRunResearch: (topic: string) => Promise<ResearchReport>;
}

export const ResearchLimb: React.FC<ResearchLimbProps> = ({ reports, onRunResearch }) => {
  const [topic, setTopic] = useState('ONC HTI-2 Final Rule & FHIR Audit Requirements for 2026');
  const [isSearching, setIsSearching] = useState(false);
  const [activeReport, setActiveReport] = useState<ResearchReport | null>(reports[0] || null);

  const handleResearch = async () => {
    if (!topic.trim()) return;
    setIsSearching(true);
    try {
      const rep = await onRunResearch(topic);
      setActiveReport(rep);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-sky-500/10 text-sky-300 text-xs font-mono mb-2 border border-sky-500/20">
            <Search className="w-3.5 h-3.5" />
            <span>Deep Researcher & SaaS Finder Merged</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">Deep Research & Market Intelligence Limb</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Multi-turn web search, page scraping, citation indexing, and B2B SaaS software gap discovery.
          </p>
        </div>
      </div>

      {/* Input bar */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter research topic (e.g. ONC HTI-2 FHIR compliance)..."
            className="w-full bg-[#050505] border border-white/10 text-slate-100 text-xs pl-9 pr-4 py-2.5 rounded-lg focus:outline-none focus:border-sky-500"
          />
        </div>

        <button
          onClick={handleResearch}
          disabled={isSearching || !topic.trim()}
          className="w-full sm:w-auto px-5 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-medium rounded-lg text-xs transition flex items-center justify-center space-x-2 shadow-md shadow-sky-950 shrink-0 cursor-pointer"
        >
          <Sparkles className="w-4 h-4" />
          <span>{isSearching ? 'Synthesizing...' : 'Run Deep Research'}</span>
        </button>
      </div>

      {/* Results View */}
      {activeReport && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Report Column */}
          <div className="lg:col-span-2 bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-sky-400" />
                {activeReport.topic}
              </h3>
              <span className="text-[11px] font-mono text-slate-500">{activeReport.date}</span>
            </div>

            <div className="space-y-3 text-xs text-slate-300">
              <h4 className="font-semibold text-sky-300 uppercase font-mono text-[11px]">Executive Summary</h4>
              <p className="p-3 bg-[#050505] rounded-lg border border-white/10 text-slate-200 leading-relaxed">
                {activeReport.summary}
              </p>

              <h4 className="font-semibold text-sky-300 uppercase font-mono text-[11px]">Key Regulatory & Technical Insights</h4>
              <ul className="space-y-2">
                {activeReport.keyTakeaways.map((point, i) => (
                  <li key={i} className="flex items-start space-x-2 text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400 mt-1.5 shrink-0" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>

              <h4 className="font-semibold text-sky-300 uppercase font-mono text-[11px] pt-2">Cited Sources</h4>
              <div className="flex flex-wrap gap-2">
                {activeReport.sources.map((src, i) => (
                  <a
                    key={i}
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-[#050505] hover:bg-white/5 text-slate-300 text-[11px] rounded border border-white/10 transition"
                  >
                    <span>{src.title}</span>
                    <ExternalLink className="w-3 h-3 text-slate-500" />
                  </a>
                ))}
              </div>
            </div>
          </div>

          {/* SaaS Opportunities Column */}
          <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-400" />
              SaaS Opportunities Discovered
            </h3>

            <div className="space-y-3">
              {activeReport.saasOpportunities?.map((opp, idx) => (
                <div key={idx} className="p-3.5 bg-[#050505] rounded-lg border border-white/10 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-300">{opp.title}</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-300">
                      Difficulty: {opp.difficulty}
                    </span>
                  </div>
                  <p className="text-slate-400 text-[11px]">Target: {opp.targetAudience}</p>
                  <p className="text-slate-300 text-[11px] font-mono bg-[#0a0a0a] p-2 rounded border border-white/10">
                    Gap: {opp.marketGap}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
