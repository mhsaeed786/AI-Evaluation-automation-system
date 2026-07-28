import React from 'react';
import {
  MessageSquare,
  LayoutDashboard,
  Cpu,
  Terminal,
  Activity,
  BarChart3,
  Search,
  Workflow,
  FileText,
  FolderKanban,
  Code,
  Layers,
  Clock,
  Sparkles,
  Settings,
  Bot,
  Brain,
  Globe,
  Smartphone,
  Zap
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingMetaCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, pendingMetaCount }) => {
  const coreNav = [
    { id: 'main_chat', label: 'Main Chat Workspace', icon: MessageSquare, badge: 'Interactive' },
    { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard },
    { id: 'llm_gateway', label: 'LLM Router & Budget', icon: Cpu },
    { id: 'agent_runner', label: 'Agent Loop Runner', icon: Terminal },
    { id: 'specialist_evolution', label: 'Specialist Evolution (RAG)', icon: Brain, badge: 'SQLite' },
    { id: 'agent_architecture', label: 'Agent Architecture', icon: Layers, badge: '12 Features' },
  { id: 'skill_runner', label: 'Skill Runner', icon: Zap, badge: 'Native' },
  { id: 'scraper', label: 'Web Scraper', icon: Globe, badge: 'Firecrawl-style' },
  { id: 'agent_harness', label: 'Coding Agent', icon: Code, badge: 'Aider-style' },
    { id: 'opensource_suite', label: 'Open Source AI Suite', icon: Sparkles, badge: '12 Tools' },
    { id: 'integrations_hub', label: 'Multi-Account Integrations', icon: Globe, badge: '11 Active' },
    { id: 'portable_targets', label: 'Portable Desktop & APK', icon: Smartphone, badge: 'Tauri' },
  ];

  const limbsNav = [
    { id: 'fhir', label: 'FHIR BA/QA Suite', icon: Activity, badge: '11 Merged' },
    { id: 'leap', label: 'LEAP Analytics', icon: BarChart3, badge: '5 Merged' },
    { id: 'research', label: 'Deep Research & SaaS', icon: Search },
    { id: 'workops', label: 'WorkOps & DataSync', icon: Workflow },
    { id: 'content', label: 'Content & SEO Blog', icon: FileText },
    { id: 'files', label: 'Files & Storage Guardian', icon: FolderKanban },
    { id: 'coding', label: 'CLI Controller & Code', icon: Code },
  ];

  const metaNav = [
    { id: 'skills_mcp', label: 'Skills & MCP Hub', icon: Layers, badge: 'Goose/OpenClaw' },
    { id: 'scheduler', label: 'Cron Scheduler', icon: Clock },
    { id: 'meta', label: 'Meta Engine (Codegen)', icon: Sparkles, badgeCount: pendingMetaCount },
    { id: 'settings', label: 'System Settings', icon: Settings },
  ];

  const renderNavItem = (item: { id: string; label: string; icon: any; badge?: string; badgeCount?: number }) => {
    const Icon = item.icon;
    const isActive = activeTab === item.id;

    return (
      <button
        key={item.id}
        onClick={() => setActiveTab(item.id)}
        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition cursor-pointer ${
          isActive
            ? 'bg-blue-600/15 text-blue-400 border-l-2 border-blue-500 shadow-sm'
            : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
        }`}
      >
        <div className="flex items-center space-x-2.5">
          <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
          <span>{item.label}</span>
        </div>

        {item.badge && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">
            {item.badge}
          </span>
        )}

        {item.badgeCount !== undefined && item.badgeCount > 0 && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
            {item.badgeCount} new
          </span>
        )}
      </button>
    );
  };

  return (
    <aside className="w-64 bg-[#080808] border-r border-white/10 flex flex-col h-screen shrink-0">
      {/* Brand logo */}
      <div className="p-4 border-b border-white/10 flex items-center space-x-3 bg-[#0a0a0a]">
        <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold shadow-md shadow-blue-950/40">
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-slate-100 tracking-tight">
            OneAgent <span className="text-blue-500 font-normal">SuperApp</span>
          </h2>
          <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">CureMD BA/QA Engine</p>
        </div>
      </div>

      {/* Nav List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-6">
        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-3 mb-2 font-mono">
            Core Operations
          </p>
          <div className="space-y-1">{coreNav.map(renderNavItem)}</div>
        </div>

        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-3 mb-2 font-mono">
            Consolidated Limbs
          </p>
          <div className="space-y-1">{limbsNav.map(renderNavItem)}</div>
        </div>

        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest px-3 mb-2 font-mono">
            Ecosystem & Meta
          </p>
          <div className="space-y-1">{metaNav.map(renderNavItem)}</div>
        </div>
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-white/10 bg-[#050505]">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            Gateway Online
          </span>
          <span className="font-mono text-slate-500">v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};
