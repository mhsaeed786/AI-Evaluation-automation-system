import { useState } from 'react';

export function AgentHarnessPanel() {
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState('gemini:gemini-2.5-flash');
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  async function runCodingAgent() {
    setLoading(true);
    setEvents([]);
    try {
      const res = await fetch('/api/coding/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, provider }),
      });
      const data = await res.json();
      setEvents(data.events || []);
    } catch (e) {
      setEvents([{ type: 'error', content: String(e) }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 p-4 text-slate-100">
      <h2 className="text-xl font-bold">Agent Harness (Coding Specialist)</h2>
      <input className="w-full p-2 rounded bg-slate-800 border border-slate-700" value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="Provider:Model" />
      <textarea className="w-full p-2 rounded bg-slate-800 border border-slate-700" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Describe the coding task..." rows={4} />
      <button onClick={runCodingAgent} disabled={loading} className="px-4 py-2 rounded bg-blue-600 disabled:bg-slate-600">{loading ? 'Running...' : 'Run Coding Agent'}</button>
      <div className="space-y-2">
        {events.map((ev, i) => (
          <div key={i} className="text-sm border-l-4 pl-2" style={{ borderColor: ev.type === 'tool_call' ? '#3b82f6' : ev.type === 'tool_result' ? '#22c55e' : '#a855f7' }}>
            <strong>{ev.type}</strong>{ev.tool && <span className="text-slate-500"> · {ev.tool}</span>}
            <p className="text-slate-300">{ev.content?.slice(0, 200)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
