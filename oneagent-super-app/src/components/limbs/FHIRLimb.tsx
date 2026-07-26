import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FileCode,
  DollarSign,
  Search,
  Filter,
  Play,
  Database,
  ArrowRight
} from 'lucide-react';
import { FHIRInconsistency, FHIRBundleItem } from '../../types';

interface FHIRLimbProps {
  inconsistencies: FHIRInconsistency[];
  bundleItems: FHIRBundleItem[];
  onRunAudit: (resourceType: string) => Promise<void>;
}

export const FHIRLimb: React.FC<FHIRLimbProps> = ({
  inconsistencies,
  bundleItems,
  onRunAudit,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'inconsistencies' | 'explorer' | 'cost' | 'mapping'>('inconsistencies');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedResource, setSelectedResource] = useState<FHIRBundleItem>(bundleItems[0]);
  const [isAuditing, setIsAuditing] = useState(false);

  // Cost calculator state
  const [bundleCount, setBundleCount] = useState<number>(100000);
  const [avgSizeKb, setAvgSizeKb] = useState<number>(45);

  const calculateCost = () => {
    const totalMb = (bundleCount * avgSizeKb) / 1024;
    const bandwidthCost = totalMb * 0.00008;
    const storageCost = totalMb * 0.00002;
    const processingCost = bundleCount * 0.000005;
    return {
      totalMb: totalMb.toFixed(2),
      totalUSD: (bandwidthCost + storageCost + processingCost).toFixed(2),
    };
  };

  const handleAuditClick = async () => {
    setIsAuditing(true);
    await onRunAudit('Patient');
    setIsAuditing(false);
  };

  const filteredInconsistencies = inconsistencies.filter(
    (inc) => selectedSeverity === 'all' || inc.severity === selectedSeverity
  );

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-300 text-xs font-mono mb-2 border border-rose-500/20">
            <Activity className="w-3.5 h-3.5" />
            <span>11 Legacy FHIR Apps Consolidated into 1 Module</span>
          </div>
          <h2 className="text-base font-bold text-slate-100">FHIR BA/QA Automation Suite</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            US-Core compliance auditing, HAPI FHIR Explorer, Bundle cost modeler, and Provider NPI provenance mapping.
          </p>
        </div>

        <button
          onClick={handleAuditClick}
          disabled={isAuditing}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-medium rounded-lg text-xs transition flex items-center space-x-2 shadow-md shadow-rose-950 cursor-pointer"
        >
          <Play className="w-4 h-4 fill-white" />
          <span>{isAuditing ? 'Auditing US-Core...' : 'Run US-Core Audit'}</span>
        </button>
      </div>

      {/* Sub Tabs */}
      <div className="flex border-b border-white/10 space-x-6 text-sm">
        <button
          onClick={() => setActiveSubTab('inconsistencies')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeSubTab === 'inconsistencies'
              ? 'text-rose-400 border-b-2 border-rose-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Inconsistency Scanner ({inconsistencies.length})</span>
        </button>

        <button
          onClick={() => setActiveSubTab('explorer')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeSubTab === 'explorer'
              ? 'text-rose-400 border-b-2 border-rose-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>HAPI FHIR Explorer</span>
        </button>

        <button
          onClick={() => setActiveSubTab('cost')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeSubTab === 'cost'
              ? 'text-rose-400 border-b-2 border-rose-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <DollarSign className="w-4 h-4" />
          <span>Bundle Cost Analysis</span>
        </button>

        <button
          onClick={() => setActiveSubTab('mapping')}
          className={`pb-3 font-medium transition cursor-pointer flex items-center space-x-2 ${
            activeSubTab === 'mapping'
              ? 'text-rose-400 border-b-2 border-rose-500 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileCode className="w-4 h-4" />
          <span>Provider & Provenance Remap</span>
        </button>
      </div>

      {/* SUBTAB 1: Inconsistencies */}
      {activeSubTab === 'inconsistencies' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100">US-Core Inconsistencies & Validation Flags</h3>
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-400 font-mono">Severity Filter:</span>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="bg-[#050505] border border-white/10 text-slate-200 px-2 py-1 rounded font-mono"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical Only</option>
                <option value="warning">Warning Only</option>
                <option value="info">Info Only</option>
              </select>
            </div>
          </div>

          <div className="space-y-3">
            {filteredInconsistencies.map((inc) => (
              <div
                key={inc.id}
                className="p-4 bg-[#050505] rounded-lg border border-white/10 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2 py-0.5 rounded font-mono uppercase text-[10px] font-bold ${
                        inc.severity === 'critical'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : inc.severity === 'warning'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <span className="font-bold text-slate-200 font-mono">
                      {inc.resourceType} / {inc.resourceId}
                    </span>
                    <span className="text-slate-500 font-mono font-normal">→ {inc.field}</span>
                  </div>
                  <span className="text-slate-500 font-mono text-[10px]">#{inc.id}</span>
                </div>

                <p className="text-slate-300 font-sans">{inc.issue}</p>

                <div className="p-2 bg-[#0a0a0a] rounded border border-white/10 text-emerald-400 font-mono text-[11px] flex items-center space-x-2">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>Fix: {inc.suggestedFix}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUBTAB 2: HAPI Explorer */}
      {activeSubTab === 'explorer' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-100">Bundle Resources</h3>
            <div className="space-y-2">
              {bundleItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedResource(item)}
                  className={`w-full text-left p-3 rounded-lg border text-xs transition cursor-pointer ${
                    selectedResource.id === item.id
                      ? 'bg-rose-600/20 border-rose-500/50 text-rose-200'
                      : 'bg-[#050505] border-white/10 text-slate-400 hover:bg-white/5'
                  }`}
                >
                  <div className="font-bold text-slate-200">{item.resourceType} ({item.id})</div>
                  <div className="text-[11px] text-slate-500 font-mono mt-0.5">Updated: {item.lastUpdated}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 bg-[#050505] border border-white/10 rounded-xl p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <span className="font-bold text-rose-400">
                JSON Document: {selectedResource.resourceType} / {selectedResource.id}
              </span>
              <span className="text-emerald-400">Status: {selectedResource.status}</span>
            </div>
            <pre className="text-slate-300 overflow-x-auto p-3 bg-[#0a0a0a] rounded border border-white/10 text-[11px] max-h-96">
              {JSON.stringify(selectedResource.data, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* SUBTAB 3: Cost Calculator */}
      {activeSubTab === 'cost' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-100">FHIR Bulk Transmission Cost Modeler</h3>
          <p className="text-xs text-slate-400">
            Estimates bandwidth and storage expenditure for enterprise bulk FHIR operations.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div className="space-y-4 bg-[#050505] p-4 rounded-lg border border-white/10 text-xs">
              <div>
                <label className="text-slate-400 block font-mono mb-1">Total Bundles / Day</label>
                <input
                  type="number"
                  value={bundleCount}
                  onChange={(e) => setBundleCount(parseInt(e.target.value) || 0)}
                  className="w-full bg-[#0a0a0a] border border-white/10 text-slate-100 p-2 rounded font-mono"
                />
              </div>

              <div>
                <label className="text-slate-400 block font-mono mb-1">Average Bundle Size (KB)</label>
                <input
                  type="number"
                  value={avgSizeKb}
                  onChange={(e) => setAvgSizeKb(parseInt(e.target.value) || 0)}
                  className="w-full bg-[#0a0a0a] border border-white/10 text-slate-100 p-2 rounded font-mono"
                />
              </div>
            </div>

            <div className="bg-[#050505] p-4 rounded-lg border border-white/10 space-y-3 text-xs font-mono flex flex-col justify-center">
              <div className="text-slate-400">Calculated Bandwidth Volume:</div>
              <div className="text-2xl font-bold text-slate-100">{calculateCost().totalMb} MB</div>
              <div className="text-slate-400 mt-2">Estimated Daily Infrastructure Cost:</div>
              <div className="text-3xl font-bold text-emerald-400">${calculateCost().totalUSD} USD</div>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 4: Provider Mapping */}
      {activeSubTab === 'mapping' && (
        <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-5 space-y-4 text-xs font-mono">
          <h3 className="text-sm font-semibold text-slate-100 font-sans">Provider NPI & Provenance Remapper</h3>
          <p className="text-slate-400 font-sans">
            Automatically transforms non-standard practitioner refs into US-Core standard NPI extension syntax.
          </p>

          <div className="p-4 bg-[#050505] rounded-lg border border-white/10 space-y-3">
            <div className="text-amber-300 font-bold">Input Non-Standard Ref:</div>
            <div className="text-slate-300">Practitioner/legacy-dr-smith-9021</div>
            <div className="flex items-center text-slate-500 py-1">
              <ArrowRight className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-emerald-400 font-bold">Mapped US-Core Provenance Reference:</div>
            <pre className="p-3 bg-[#0a0a0a] rounded border border-white/10 text-[11px] text-slate-200">
{`{
  "reference": "Practitioner/npi-1928301928",
  "extension": [{
    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-npi",
    "valueIdentifier": {
      "system": "http://hl7.org/fhir/sid/us-npi",
      "value": "1928301928"
    }
  }]
}`}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
