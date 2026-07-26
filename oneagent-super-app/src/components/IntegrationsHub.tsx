import React, { useState } from 'react';
import {
  Workflow,
  Globe,
  Mail,
  MessageSquare,
  GitBranch,
  Radio,
  Key,
  Plus,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Shield,
  Layers,
  Bot,
  Zap,
  Trash2,
  RefreshCw,
  Sliders
} from 'lucide-react';

interface IntegrationInstance {
  id: string;
  category: 'm365' | 'slack' | 'azure_devops' | 'github' | 'chat_bots' | 'iot' | 'open_source_suite' | 'sso';
  name: string;
  accountLabel: string;
  endpointOrOrg: string;
  status: 'connected' | 'disconnected' | 'auth_required';
  lastSynced: string;
}

export const IntegrationsHub: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newIntegrationType, setNewIntegrationType] = useState('m365');
  const [newAccountLabel, setNewAccountLabel] = useState('');
  const [newEndpoint, setNewEndpoint] = useState('');

  const [instances, setInstances] = useState<IntegrationInstance[]>([
    {
      id: 'int-1',
      category: 'm365',
      name: 'Microsoft 365 & Graph API',
      accountLabel: 'Work Account (CureMD Corporate)',
      endpointOrOrg: 'graph.microsoft.com/v1.0 (Tenant: curemd.onmicrosoft.com)',
      status: 'connected',
      lastSynced: '2 mins ago'
    },
    {
      id: 'int-2',
      category: 'm365',
      name: 'Microsoft 365 & Graph API',
      accountLabel: 'Personal Outlook / Hotmail',
      endpointOrOrg: 'graph.microsoft.com/v1.0 (Personal)',
      status: 'connected',
      lastSynced: '15 mins ago'
    },
    {
      id: 'int-3',
      category: 'slack',
      name: 'Slack Workspace',
      accountLabel: 'CureMD Engineering Slack',
      endpointOrOrg: 'curemd-dev.slack.com',
      status: 'connected',
      lastSynced: '1 min ago'
    },
    {
      id: 'int-4',
      category: 'azure_devops',
      name: 'Azure DevOps On-Prem TFS',
      accountLabel: 'On-Prem Server instance',
      endpointOrOrg: 'tfs.internal.curemd.com/DefaultCollection',
      status: 'connected',
      lastSynced: '5 mins ago'
    },
    {
      id: 'int-5',
      category: 'azure_devops',
      name: 'Azure DevOps Online',
      accountLabel: 'Cloud ADO Account',
      endpointOrOrg: 'dev.azure.com/curemd-cloud',
      status: 'connected',
      lastSynced: '8 mins ago'
    },
    {
      id: 'int-6',
      category: 'github',
      name: 'GitHub Account',
      accountLabel: 'Org Account (@curemd-org)',
      endpointOrOrg: 'github.com/curemd-org',
      status: 'connected',
      lastSynced: '12 mins ago'
    },
    {
      id: 'int-7',
      category: 'chat_bots',
      name: 'Telegram Bot Gateway',
      accountLabel: 'OneAgent QA Alert Bot',
      endpointOrOrg: 'api.telegram.org/bot784192...',
      status: 'connected',
      lastSynced: 'Just now'
    },
    {
      id: 'int-8',
      category: 'iot',
      name: 'IoT MQTT Sensor Gateway',
      accountLabel: 'Lab Environment Sensors',
      endpointOrOrg: 'mqtt://iot-broker.internal.curemd.com:1883',
      status: 'connected',
      lastSynced: '30 secs ago'
    },
    {
      id: 'int-9',
      category: 'open_source_suite',
      name: 'Browser-Use Visual AI Navigator',
      accountLabel: 'Playwright Headless Cluster',
      endpointOrOrg: 'ws://localhost:9222/devtools/browser',
      status: 'connected',
      lastSynced: 'Active'
    },
    {
      id: 'int-10',
      category: 'open_source_suite',
      name: 'Firecrawl Deep Web Scraper',
      accountLabel: 'Local Firecrawl Docker Service',
      endpointOrOrg: 'http://localhost:3002/v1/scrape',
      status: 'connected',
      lastSynced: 'Active'
    },
    {
      id: 'int-11',
      category: 'sso',
      name: 'Google Workspace SSO',
      accountLabel: 'Enterprise Google Auth',
      endpointOrOrg: 'accounts.google.com/o/oauth2/v2/auth',
      status: 'connected',
      lastSynced: 'Active'
    }
  ]);

  const handleAddInstance = () => {
    if (!newAccountLabel.trim()) return;
    const newInst: IntegrationInstance = {
      id: `int-${Date.now()}`,
      category: newIntegrationType as any,
      name: getCategoryTitle(newIntegrationType),
      accountLabel: newAccountLabel,
      endpointOrOrg: newEndpoint || 'https://api.default.org',
      status: 'connected',
      lastSynced: 'Just added'
    };
    setInstances(prev => [newInst, ...prev]);
    setNewAccountLabel('');
    setNewEndpoint('');
    setShowAddModal(false);
  };

  const handleDeleteInstance = (id: string) => {
    setInstances(prev => prev.filter(i => i.id !== id));
  };

  const getCategoryTitle = (cat: string) => {
    switch (cat) {
      case 'm365': return 'Microsoft 365 & Graph API';
      case 'slack': return 'Slack Workspace';
      case 'azure_devops': return 'Azure DevOps / TFS';
      case 'github': return 'GitHub Account';
      case 'chat_bots': return 'Discord / Telegram Bot Gateway';
      case 'iot': return 'IoT MQTT / REST Gateway';
      case 'open_source_suite': return 'Open Source Tool Harness (Browser-Use, Firecrawl, OpenManus)';
      case 'sso': return 'SSO Gateway (Google / Microsoft)';
      default: return 'Integration Connector';
    }
  };

  const filteredInstances = activeTab === 'all'
    ? instances
    : instances.filter(i => i.category === activeTab);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-950/40 via-cyan-950/30 to-[#0a0a0a] border border-blue-500/20 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Workflow className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                  Unified Integrations & Multi-Account Hub
                </h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 font-mono">
                  Multi-Instance Auth
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl">
                Supports connecting multiple accounts and instances of M365/Graph API, Slack, Teams, Azure DevOps On-Prem/Online, GitHub, Telegram/Discord, IoT brokers, and open source agent frameworks (Browser-Use, Firecrawl, Perplexica).
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-2 shadow-lg shadow-blue-950/50 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Connect New Account / Instance</span>
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
        {[
          { id: 'all', label: 'All Connected Instances', icon: Layers },
          { id: 'm365', label: 'M365 & Graph API', icon: Mail },
          { id: 'slack', label: 'Slack & Teams', icon: MessageSquare },
          { id: 'azure_devops', label: 'Azure DevOps (On-Prem/Cloud)', icon: GitBranch },
          { id: 'github', label: 'GitHub Accounts', icon: GitBranch },
          { id: 'iot', label: 'IoT & Sensors', icon: Radio },
          { id: 'open_source_suite', label: 'OpenSource Harness (BrowserUse/Firecrawl)', icon: Zap },
          { id: 'sso', label: 'SSO Gateways', icon: Shield },
        ].map((tab) => {
          const Icon = tab.icon;
          const count = tab.id === 'all' ? instances.length : instances.filter(i => i.category === tab.id).length;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-medium transition cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:bg-white/5'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/10 text-slate-300">
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Instance Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredInstances.map((inst) => (
          <div
            key={inst.id}
            className="p-5 rounded-2xl bg-[#0a0a0a] border border-white/10 hover:border-white/20 transition space-y-4 relative group"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                  <Workflow className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-100">{inst.name}</h3>
                  <span className="text-[10px] text-blue-400 font-medium">{inst.accountLabel}</span>
                </div>
              </div>

              <span className="flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3 h-3" />
                <span>Connected</span>
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-black/60 border border-white/5 font-mono text-[11px] text-slate-300 truncate">
              {inst.endpointOrOrg}
            </div>

            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 border-t border-white/5 pt-3">
              <span>Last Synced: {inst.lastSynced}</span>
              <button
                onClick={() => handleDeleteInstance(inst.id)}
                className="text-rose-400 hover:text-rose-300 transition cursor-pointer opacity-0 group-hover:opacity-100"
                title="Disconnect instance"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal for adding integration instance */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e0e0e] border border-white/10 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl">
            <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <Plus className="w-4 h-4 text-blue-400" />
              <span>Connect New Account / Instance</span>
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 mb-1 block">Integration Category</label>
                <select
                  value={newIntegrationType}
                  onChange={(e) => setNewIntegrationType(e.target.value)}
                  className="w-full bg-black/80 border border-white/10 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="m365">Microsoft 365 / Outlook Graph API</option>
                  <option value="slack">Slack Workspace</option>
                  <option value="azure_devops">Azure DevOps (On-Prem TFS or Online)</option>
                  <option value="github">GitHub Account / Organization</option>
                  <option value="chat_bots">Telegram / Discord Bot</option>
                  <option value="iot">IoT MQTT / REST Sensor Broker</option>
                  <option value="open_source_suite">OpenSource Tool Harness (BrowserUse/Firecrawl)</option>
                  <option value="sso">Single Sign-On (Google / Keycloak)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 mb-1 block">Account Label / Identifier</label>
                <input
                  type="text"
                  placeholder="e.g. Work Account (Enterprise) or Org Account"
                  value={newAccountLabel}
                  onChange={(e) => setNewAccountLabel(e.target.value)}
                  className="w-full bg-black/80 border border-white/10 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-slate-400 mb-1 block">Endpoint URL / Tenant ID / Connection String</label>
                <input
                  type="text"
                  placeholder="e.g. tfs.company.com/DefaultCollection or graph.microsoft.com"
                  value={newEndpoint}
                  onChange={(e) => setNewEndpoint(e.target.value)}
                  className="w-full bg-black/80 border border-white/10 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:bg-white/5 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleAddInstance}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-medium transition cursor-pointer"
              >
                Save Instance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
