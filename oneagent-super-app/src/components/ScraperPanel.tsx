import { useState } from 'react';

export function ScraperPanel() {
  const [url, setUrl] = useState('');
  const [javascript, setJavascript] = useState(true);
  const [screenshot, setScreenshot] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function scrape() {
    setLoading(true);
    try {
      const res = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, javascript, screenshot }),
      });
      setResult(await res.json());
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 p-4 text-slate-100">
      <h2 className="text-xl font-bold">Firecrawl-Style Scraper</h2>
      <input className="w-full p-2 rounded bg-slate-800 border border-slate-700" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com" />
      <div className="flex gap-4">
        <label className="flex items-center gap-2"><input type="checkbox" checked={javascript} onChange={(e) => setJavascript(e.target.checked)} /> JavaScript</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={screenshot} onChange={(e) => setScreenshot(e.target.checked)} /> Screenshot</label>
      </div>
      <button onClick={scrape} disabled={loading} className="px-4 py-2 rounded bg-blue-600 disabled:bg-slate-600">{loading ? 'Scraping...' : 'Scrape'}</button>
      {result && (
        <div className="bg-slate-900 text-green-400 text-xs p-4 rounded overflow-auto max-h-96">
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
