import { useState } from 'react';

const SKILLS = [
  { id: 'research', label: 'Research' },
  { id: 'coding', label: 'Coding Agent' },
  { id: 'browser', label: 'Browser Scrape' },
];

export function SkillRunner() {
  const [skill, setSkill] = useState('research');
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState('gemini:gemini-2.5-flash');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function run() {
    setLoading(true);
    try {
      const res = await fetch(`/api/skills/${skill}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, provider }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 p-4 text-slate-100">
      <h2 className="text-xl font-bold">Native Skill Runner</h2>
      <div className="flex gap-2">
        {SKILLS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSkill(s.id)}
            className={`px-3 py-1 rounded text-sm ${skill === s.id ? 'bg-blue-600 text-white' : 'bg-slate-700'}`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <input className="w-full p-2 rounded bg-slate-800 border border-slate-700" value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="Provider:Model" />
      <textarea className="w-full p-2 rounded bg-slate-800 border border-slate-700" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Enter task or query..." rows={4} />
      <button onClick={run} disabled={loading} className="px-4 py-2 rounded bg-blue-600 disabled:bg-slate-600">{loading ? 'Running...' : 'Run Skill'}</button>
      {result && (
        <pre className="bg-slate-900 text-green-400 text-xs p-4 rounded overflow-auto max-h-96">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
