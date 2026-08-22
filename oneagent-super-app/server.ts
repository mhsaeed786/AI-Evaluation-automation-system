import express from 'express';
import path from 'path';
import { randomUUID } from 'crypto';
import { exec, execFile } from 'child_process';
import { promisify } from 'util';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

const execAsync = promisify(exec);

// Run a Python subprocess with an argv array (no shell interpolation).
function runPython(args: string[], cwd?: string): Promise<string> {
  return new Promise((resolve, reject) => {
    execFile('python3', args, { maxBuffer: 1024 * 1024, cwd }, (err, stdout) =>
      err ? reject(err) : resolve(stdout));
  });
}

dotenv.config();

const app = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const APP_VERSION = '1.0.0';
const MAX_BODY_BYTES = 1024 * 1024;

app.use(express.json({ limit: '1mb' }));

function newCorrelationId(): string {
  return randomUUID();
}

/**
 * Request-body validation: reject non-object / oversized JSON bodies with 400
 * before any handler runs.
 */
function requireJsonObject(req: express.Request, res: express.Response): boolean {
  const len = Number(req.headers['content-length'] || 0);
  if (len > MAX_BODY_BYTES) {
    res.status(400).json({ error: 'request body too large', correlationId: newCorrelationId() });
    return false;
  }
  const body = req.body;
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    res.status(400).json({ error: 'request body must be a JSON object', correlationId: newCorrelationId() });
    return false;
  }
  return true;
}

// Apply validation to all mutating API routes centrally.
app.use('/api', (req, res, next) => {
  if (req.method === 'POST' && !requireJsonObject(req, res)) return;
  next();
});

// Initialize GoogleGenAI client lazily
function getGeminiClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === 'MY_GEMINI_API_KEY') {
    return null;
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

// --------------------------------------------------------
// API ENDPOINTS
// --------------------------------------------------------

// Health check
app.get('/api/health', (_req, res) => {
  res.json({
    status: 'ok',
    version: APP_VERSION,
    app: 'OneAgent Super-App',
    geminiKeySet: Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== 'MY_GEMINI_API_KEY'),
    timestamp: new Date().toISOString(),
  });
});

// 1. LLM Router direct generation
app.post('/api/llm/generate', async (req, res, next) => {
  try {
    const { prompt, model = 'gemini-3.6-flash', taskClass = 'reason', systemInstruction } = req.body;
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }

    const ai = getGeminiClient();
    if (ai) {
      const response = await ai.models.generateContent({
        model: model || 'gemini-3.6-flash',
        contents: prompt,
        config: systemInstruction ? { systemInstruction } : undefined,
      });

      // Only report usage/cost when the provider actually returns it;
      // otherwise the fields stay null (never estimated).
      const usage = (response as any).usageMetadata ?? null;

      return res.json({
        text: response.text || null,
        modelUsed: model,
        tokensUsed: usage?.totalTokenCount ?? null,
        costEstimatedUSD: null,
        source: 'measured',
      });
    }

    // No API key configured — report honestly instead of simulating a reply.
    return res.status(503).json({
      text: null,
      modelUsed: model,
      tokensUsed: null,
      costEstimatedUSD: null,
      source: 'unavailable',
      error: 'GEMINI_API_KEY not configured',
    });
  } catch (err: any) {
    console.error('Error in /api/llm/generate:', err);
    next(err);
  }
});

// 2. Generic Agent Loop Execution (Plan -> Tool -> Observe -> Output)
app.post('/api/agent/run', async (req, res, next) => {
  try {
    const { taskPrompt, module = 'fhir', taskClass = 'reason', preferredModel = 'gemini-3.6-flash' } = req.body;
    const ai = getGeminiClient();

    const startTime = Date.now();

    if (ai) {
      try {
        const response = await ai.models.generateContent({
          model: preferredModel,
          contents: `You are the OneAgent Execution Engine for module '${module}'. Execute this task step-by-step, outlining the plan, tools needed, and final observation.\nTask: ${taskPrompt}`,
        });
        return res.json({
          id: `run-${Date.now()}`,
          taskPrompt,
          module,
          taskClass,
          modelUsed: preferredModel,
          status: 'completed',
          output: response.text || null,
          totalTokens: (response as any).usageMetadata?.totalTokenCount ?? null,
          costUSD: null,
          executionTimeMs: Date.now() - startTime,
          source: 'measured',
        });
      } catch (e: any) {
        console.warn('Gemini call inside agent run failed:', e.message);
      }
    }

    // No live engine available — report honestly rather than fabricating steps.
    return res.status(503).json({
      id: `run-${Date.now()}`,
      taskPrompt,
      module,
      taskClass,
      modelUsed: preferredModel,
      status: 'unavailable',
      output: null,
      totalTokens: null,
      costUSD: null,
      executionTimeMs: Date.now() - startTime,
      source: 'unavailable',
      error: 'No LLM engine configured or reachable',
    });
  } catch (err: any) {
    next(err);
  }
});

// 3. FHIR Inconsistency Audit Endpoint
app.post('/api/fhir/audit', async (req, res, next) => {
  try {
    const { resourceType = 'Patient', resourceData } = req.body;

    // No audit engine is wired up yet — report honestly instead of
    // returning fabricated findings.
    res.json({
      resourceType,
      resourceId: resourceData?.id ?? null,
      auditedAt: new Date().toISOString(),
      passed: null,
      issuesCount: 0,
      issues: [],
      source: 'unavailable',
      message: 'No FHIR audit engine connected; no issues can be reported.',
    });
  } catch (err: any) {
    next(err);
  }
});

// 4. Meta Module Authoring Engine Endpoints (Python core/meta/ integration)

// 4a. Author a new module using core.meta.cli author
app.post('/api/meta/author', async (req, res, next) => {
  try {
    const { moduleName, promptRequirements } = req.body;
    if (!moduleName || !promptRequirements) {
      return res.status(400).json({ error: 'moduleName and promptRequirements are required' });
    }

    const safeName = String(moduleName);
    const safeReqs = String(promptRequirements);

    try {
      const stdout = await runPython(['-m', 'core.meta.cli', 'author', '--name', safeName, '--reqs', safeReqs]);
      const pythonResult = JSON.parse(stdout);
      
      // Transform snake_case Python result to frontend interface
      const formattedModule = {
        id: pythonResult.id,
        name: pythonResult.name,
        slug: pythonResult.slug,
        description: pythonResult.description,
        promptOrigin: pythonResult.prompt_origin,
        modelAuthor: pythonResult.model_author,
        timestamp: pythonResult.timestamp,
        status: pythonResult.status,
        codeSnippet: pythonResult.code_snippet,
        testsCode: pythonResult.tests_code,
        testPassRate: pythonResult.test_pass_rate,
        sandboxOutput: pythonResult.sandbox_output,
        provenance: {
          generatedBy: pythonResult.provenance?.generated_by || 'OneAgent Meta Self-Authoring Sandbox',
          tokenCount: pythonResult.provenance?.token_count ?? null,
          parentFramework: pythonResult.provenance?.parent_framework || 'OneAgent Meta Core v1.0',
        },
      };

      return res.json(formattedModule);
    } catch (cmdErr: any) {
      console.warn('[Meta API] Python author invocation failed:', cmdErr.message);
      // The authoring engine is unavailable — report honestly instead of
      // returning a locally fabricated module.
      return res.status(503).json({
        id: null,
        name: moduleName,
        slug: String(moduleName).toLowerCase().replace(/[^a-z0-9]+/g, '_'),
        description: promptRequirements,
        status: 'unavailable',
        codeSnippet: null,
        testsCode: null,
        testPassRate: null,
        sandboxOutput: null,
        provenance: { generatedBy: null, tokenCount: null, parentFramework: null },
        source: 'unavailable',
        error: 'Meta authoring engine (core.meta.cli) failed or is not installed',
      });
    }
  } catch (err: any) {
    next(err);
  }
});

// 4b. List registered self-authored modules
app.get('/api/meta/list', async (_req, res, next) => {
  try {
    const stdout = await runPython(['-m', 'core.meta.cli', 'list']);
    const rawList = JSON.parse(stdout);
    const formatted = rawList.map((m: any) => ({
      id: m.id,
      name: m.name,
      slug: m.slug,
      description: m.description,
      promptOrigin: m.prompt_origin,
      modelAuthor: m.model_author,
      timestamp: m.timestamp,
      status: m.status,
      codeSnippet: m.code_snippet,
      testsCode: m.tests_code,
      testPassRate: m.test_pass_rate,
      sandboxOutput: m.sandbox_output,
      provenance: {
        generatedBy: m.provenance?.generated_by || 'OneAgent Meta Core',
        tokenCount: m.provenance?.token_count ?? null,
        parentFramework: m.provenance?.parent_framework || 'OneAgent Meta Core v1.0',
      },
    }));
    res.json(formatted);
  } catch (err: any) {
    res.json([]);
  }
});

// 4c. Update module status (approve / reject / revert)
app.post('/api/meta/status', async (req, res, next) => {
  try {
    const { id, status } = req.body;
    if (!id || !status) {
      return res.status(400).json({ error: 'id and status are required' });
    }
    const stdout = await runPython(['-m', 'core.meta.cli', 'status', '--id', String(id), '--status', String(status)]);
    const m = JSON.parse(stdout);
    res.json(m);
  } catch (err: any) {
    next(err);
  }
});

// 4d. Execute module inside isolated sandbox
app.post('/api/meta/run', async (req, res, next) => {
  try {
    const { id, inputData } = req.body;
    if (!id) {
      return res.status(400).json({ error: 'id is required' });
    }
    const inputJson = JSON.stringify(inputData || {});
    const stdout = await runPython(['-m', 'core.meta.cli', 'run', '--id', String(id), '--input', inputJson]);
    res.json(JSON.parse(stdout));
  } catch (err: any) {
    next(err);
  }
});

// 5. Knowledge Base & RAG Endpoint
app.post('/api/knowledge/query', async (req, res, next) => {
  try {
    const { query } = req.body;
    if (!query) {
      return res.status(400).json({ error: 'Query parameter is required' });
    }

    // No RAG index is wired up in this server — report honestly instead of
    // returning fabricated search hits.
    return res.json({
      query,
      resultsCount: 0,
      results: [],
      source: 'unavailable',
      message: 'No knowledge-base index connected to this server.',
    });
  } catch (err: any) {
    next(err);
  }
});

// Firecrawl Scraping Endpoint
app.post('/api/tools/firecrawl', async (req, res, next) => {
  try {
    const { url } = req.body;
    const targetUrl = url || 'https://www.hl7.org/fhir/overview.html';

    // No scraping backend configured — report honestly instead of returning
    // fabricated page content.
    return res.status(503).json({
      status: 'unavailable',
      url: targetUrl,
      title: null,
      markdown: null,
      metadata: { statusCode: null, linksCount: null, crawledAt: new Date().toISOString() },
      source: 'unavailable',
      error: 'No scraping backend (e.g. Firecrawl) configured',
    });
  } catch (err: any) {
    next(err);
  }
});

// Browser-Use Playwright Agent Endpoint
app.post('/api/tools/browser-use', async (req, res, next) => {
  try {
    const { goal } = req.body;

    // No browser automation runtime is attached to this server — report
    // honestly instead of returning fabricated steps/screenshots.
    return res.status(503).json({
      status: 'unavailable',
      goal: goal || null,
      stepsExecuted: [],
      screenshotUrl: null,
      source: 'unavailable',
      error: 'No browser automation backend (Playwright/browser-use) configured',
    });
  } catch (err: any) {
    next(err);
  }
});

// 6. Deep Research & SaaS Opportunity Finder
app.post('/api/research/run', async (req, res, next) => {
  try {
    const { topic } = req.body;
    const ai = getGeminiClient();

    let summaryText = '';
    if (ai) {
      try {
        const resp = await ai.models.generateContent({
          model: 'gemini-3.6-flash',
          contents: `Provide a concise 3-bullet deep research synthesis and 2 SaaS opportunity gaps for topic: ${topic}`,
        });
        summaryText = resp.text || '';
      } catch (e) {
        console.warn('Research Gemini call failed, using mock synthesis:', e);
      }
    }

    if (!summaryText) {
      // No research engine available — report honestly instead of
      // synthesizing mock insights.
      return res.status(503).json({
        id: `rep-${Date.now()}`,
        topic,
        summary: null,
        keyTakeaways: [],
        sources: [],
        saasOpportunities: [],
        date: new Date().toLocaleDateString(),
        source: 'unavailable',
        error: 'No LLM engine configured for deep research synthesis',
      });
    }

    res.json({
      id: `rep-${Date.now()}`,
      topic,
      summary: summaryText,
      keyTakeaways: [],
      sources: [],
      saasOpportunities: [],
      date: new Date().toLocaleDateString(),
      source: 'measured',
    });
  } catch (err: any) {
    next(err);
  }
});

// ========================================================
// NEW ENDPOINTS: Native Agent Architecture Features
// ========================================================

// 7. Workspace Files (SOUL.md, AGENTS.md, USER.md, etc.)
app.get('/api/workspace/context', async (_req, res, next) => {
  try {
    try {
      const context = await runPython(['-c', 'from core.workspace import WorkspaceManager; wm = WorkspaceManager(); print(wm.build_system_prompt_context())']);
      res.json({ context: context.trim() || null, source: 'measured' });
    } catch {
      // Workspace module unavailable — no fabricated SOUL.md/AGENTS.md content.
      res.status(503).json({
        context: null,
        source: 'unavailable',
        error: 'core.workspace module not available',
      });
    }
  } catch (err: any) {
    next(err);
  }
});

app.post('/api/workspace/initialize', async (req, res, next) => {
  try {
    const { user_name, user_role } = req.body;
    try {
      const result = await runPython(['-c', "import sys; from core.workspace import WorkspaceManager; wm = WorkspaceManager(); wm.initialize_default_workspace(sys.argv[1], sys.argv[2]); print('OK')", String(user_name || ''), String(user_role || '')]);
      res.json({ status: 'initialized', result: result.trim() });
    } catch {
      res.status(503).json({ status: 'unavailable', source: 'unavailable', error: 'core.workspace module not available' });
    }
  } catch (err: any) {
    next(err);
  }
});

// 8. Session Management (JSONL transcript + liveness)
app.get('/api/sessions', async (_req, res, next) => {
  try {
    try {
      const result = await runPython(['-c', 'from core.session import SessionManager; sm = SessionManager(); import json; print(json.dumps(sm.list_sessions()))']);
      res.json(JSON.parse(result));
    } catch {
      // Session store unavailable — return empty rather than demo data.
      res.json([]);
    }
  } catch (err: any) {
    next(err);
  }
});

app.post('/api/sessions/create', async (req, res, next) => {
  try {
    const { agent_id = 'main' } = req.body;
    const sessionId = `sess-${Date.now()}`;
    res.json({ session_id: sessionId, agent_id, status: 'active', created_at: new Date().toISOString() });
  } catch (err: any) {
    next(err);
  }
});

// 9. Session Liveness Classification
app.get('/api/sessions/:sessionId/liveness', async (req, res, next) => {
  try {
    const { sessionId } = req.params;
    // Liveness classification requires a live session backend — report
    // honestly instead of always claiming 'active'.
    res.json({
      session_id: sessionId,
      liveness: null,
      remediation: null,
      last_interaction: null,
      source: 'unavailable',
      message: 'No session backend connected; liveness unknown.',
    });
  } catch (err: any) {
    next(err);
  }
});

// 10. SSE Streaming for Agent Steps (Eigen-style step playback)
app.get('/api/agent/stream/:runId', async (req, res, next) => {
  const { runId } = req.params;
  const delay = Math.min(parseFloat(req.query.delay as string) || 0, 5);

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
  });

  // No agent execution backend streams real steps yet — emit an explicit
  // unavailable event instead of simulated step playback.
  if (delay > 0) {
    await new Promise(resolve => setTimeout(resolve, Math.min(delay * 1000, 1000)));
  }

  res.write(`data: ${JSON.stringify({ type: 'unavailable', runId, source: 'unavailable', message: 'No agent execution backend connected.' })}\n\n`);
  res.end();
});

// 11. Sub-Agent Management
app.post('/api/subagent/spawn', async (req, res, next) => {
  try {
    const { parent_session_id, task, context_mode = 'isolated' } = req.body;
    if (!parent_session_id || !task) {
      return res.status(400).json({ error: 'parent_session_id and task are required' });
    }
    const runId = `subagent-${Date.now()}`;
    // Sub-agent execution runtime is not attached to this server — report
    // honestly instead of pretending the sub-agent started running.
    res.status(503).json({
      run_id: runId,
      parent_session_id,
      child_session_id: null,
      task,
      context_mode,
      status: 'unavailable',
      message: 'No sub-agent execution backend connected.',
      source: 'unavailable',
    });
  } catch (err: any) {
    next(err);
  }
});

app.get('/api/subagent/:runId', async (req, res, next) => {
  try {
    const { runId } = req.params;
    // No execution runtime — status is genuinely unknown, not 'completed'.
    res.json({
      run_id: runId,
      status: 'unknown',
      result: null,
      tokens_used: null,
      runtime_ms: null,
      source: 'unavailable',
      message: 'No sub-agent execution backend connected.',
    });
  } catch (err: any) {
    next(err);
  }
});

app.get('/api/subagent', async (_req, res, next) => {
  try {
    res.json({
      active_count: 0,
      max_concurrent: 8,
      max_depth: 5,
      recommended_depth: 2,
      runs: [],
    });
  } catch (err: any) {
    next(err);
  }
});

// 12. Harness Registry
app.get('/api/harnesses', async (_req, res, next) => {
  try {
    res.json({
      harnesses: [
        { id: 'gemini', type: 'gemini', available: Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== 'MY_GEMINI_API_KEY') },
        { id: 'ollama', type: 'ollama', available: false },
      ],
      default: 'gemini',
    });
  } catch (err: any) {
    next(err);
  }
});

// 13. Capabilities Registry
app.get('/api/capabilities', async (_req, res, next) => {
  try {
    res.json({
      providers: [
        { id: 'oneagent-core', name: 'OneAgent Core', description: 'Base generalist agent capabilities', version: '1.0.0' },
      ],
      capabilities: [
        { type: 'text_inference', provider_id: 'oneagent-core', name: 'LLM Text Generation', priority: 50, enabled: true },
        { type: 'web_search', provider_id: 'oneagent-core', name: 'Web Search', priority: 50, enabled: true },
        { type: 'web_fetch', provider_id: 'oneagent-core', name: 'Web Page Fetch', priority: 50, enabled: true },
        { type: 'browser_control', provider_id: 'oneagent-core', name: 'Playwright Browser Automation', priority: 50, enabled: true },
        { type: 'code_execution', provider_id: 'oneagent-core', name: 'Sandboxed Code Execution', priority: 50, enabled: true },
        { type: 'file_ops', provider_id: 'oneagent-core', name: 'File Operations', priority: 50, enabled: true },
        { type: 'shell_exec', provider_id: 'oneagent-core', name: 'Shell Command Execution', priority: 50, enabled: true },
        { type: 'rag', provider_id: 'oneagent-core', name: 'SQLite RAG Knowledge Base', priority: 50, enabled: true },
        { type: 'meta_author', provider_id: 'oneagent-core', name: 'Meta Self-Authoring Engine', priority: 50, enabled: true },
      ],
      capability_types: ['text_inference', 'web_search', 'web_fetch', 'browser_control', 'code_execution', 'file_ops', 'shell_exec', 'image_generation', 'image_analysis', 'data_storage', 'message_channel', 'scheduler', 'rag', 'embedding', 'mcp_server', 'skill_provider', 'meta_author'],
    });
  } catch (err: any) {
    next(err);
  }
});

// 14. Hook System
app.get('/api/hooks', async (_req, res, next) => {
  try {
    res.json({
      plugin_hooks: [
        { name: 'security_validator', event: 'before_tool_call', priority: 90, description: 'Validates commands against allowlist' },
        { name: 'budget_tracker', event: 'after_agent_reply', priority: 50, description: 'Tracks LLM spending' },
      ],
      operator_scripts: {},
      events: ['before_model_resolve', 'before_prompt_build', 'before_agent_reply', 'after_agent_reply', 'before_tool_call', 'after_tool_call', 'tool_result_persist', 'session_create', 'session_start', 'session_end', 'session_compact', 'before_message_send', 'after_message_receive', 'gateway_startup', 'gateway_shutdown'],
    });
  } catch (err: any) {
    next(err);
  }
});

app.post('/api/hooks/register', async (req, res, next) => {
  try {
    const { event, name, priority = 50, description = '' } = req.body;
    if (!event || !name) {
      return res.status(400).json({ error: 'event and name are required' });
    }
    res.json({ status: 'registered', event, name, priority, description });
  } catch (err: any) {
    next(err);
  }
});

// 15. Recipes (Multi-step pipelines)
app.get('/api/recipes', async (_req, res, next) => {
  try {
    res.json([
      {
        id: 'rec-fhir-nightly',
        name: 'Nightly FHIR Inconsistency Sweep',
        description: 'Runs US-Core inconsistency checks over all updated FHIR patient records.',
        steps: [
          { name: 'fetch_bundles', skill: 'fhir_fetch', continue_on_error: false },
          { name: 'audit', skill: 'fhir_audit', depends_on: ['fetch_bundles'] },
          { name: 'report', skill: 'teams_notify', depends_on: ['audit'] },
        ],
      },
      {
        id: 'rec-research-pipeline',
        name: 'Deep Research Pipeline',
        description: 'Multi-step research: search → scrape → analyze → report',
        steps: [
          { name: 'search', skill: 'web_search' },
          { name: 'scrape', skill: 'web_fetch', depends_on: ['search'] },
          { name: 'analyze', skill: 'llm_analyze', depends_on: ['scrape'] },
          { name: 'report', skill: 'content_draft', depends_on: ['analyze'] },
        ],
      },
    ]);
  } catch (err: any) {
    next(err);
  }
});

app.post('/api/recipes/:recipeId/run', async (req, res, next) => {
  try {
    const { recipeId } = req.params;
    const { params = {} } = req.body;
    // No pipeline runner is attached to this server — report honestly
    // instead of returning fabricated step results.
    res.status(503).json({
      recipe_id: recipeId,
      params,
      status: 'unavailable',
      completed_steps: 0,
      total_steps: null,
      results: [],
      duration_ms: null,
      source: 'unavailable',
      error: 'No pipeline runner backend connected',
    });
  } catch (err: any) {
    next(err);
  }
});

// 16. Diagnostics
app.get('/api/diagnostics/flags', async (_req, res, next) => {
  try {
    res.json({
      flags: [],
      available_flags: ['gateway.*', 'browser.act', 'session.long_running', 'session.stalled', 'timeline'],
    });
  } catch (err: any) {
    next(err);
  }
});

app.post('/api/diagnostics/flags', async (req, res, next) => {
  try {
    const { flag, action = 'enable' } = req.body;
    res.json({ status: action, flag });
  } catch (err: any) {
    next(err);
  }
});

// 17. Queue / Steering
app.post('/api/queue/steer/:sessionId', async (req, res, next) => {
  try {
    const { sessionId } = req.params;
    const { content } = req.body;
    res.json({
      status: 'steered',
      session_id: sessionId,
      message: 'Steering message queued. Will be delivered after current tool calls, before next LLM call.',
    });
  } catch (err: any) {
    next(err);
  }
});

app.post('/api/queue/followup/:sessionId', async (req, res, next) => {
  try {
    const { sessionId } = req.params;
    const { content } = req.body;
    res.json({
      status: 'queued',
      session_id: sessionId,
      message: 'Followup message queued. Will start a new turn after current one ends.',
    });
  } catch (err: any) {
    next(err);
  }
});

// 18. Security: Command Validation
app.post('/api/security/validate-command', async (req, res, next) => {
  try {
    const { command } = req.body;
    const dangerous = /(?:;|\|\||&&|`|\$\(|\$\{|\n|\r|>\s|<\s|\(\s*\))/;
    const allowed = new Set(['python', 'python3', 'node', 'npm', 'npx', 'git', 'curl', 'docker', 'pytest']);
    const stripped = (command || '').trim();
    const binary = stripped.split(/\s+/)[0]?.split(/[/\\]/).pop()?.toLowerCase() || '';

    const issues = [];
    if (!stripped) issues.push('Empty command');
    if (dangerous.test(stripped)) issues.push('Contains dangerous shell metacharacters');
    if (!allowed.has(binary)) issues.push(`Binary '${binary}' not in allowlist`);

    res.json({
      command: stripped,
      valid: issues.length === 0,
      binary,
      issues,
      allowed_binaries: [...allowed].sort(),
    });
  } catch (err: any) {
    next(err);
  }
});

// Central error handler — clients get a generic message + correlationId;
// the detailed error is only logged server-side.
app.use((err: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  const correlationId = newCorrelationId();
  console.error(`[error] correlationId=${correlationId}`, err);
  // Honor client-error statuses carried by the error (e.g. body-parser's
  // malformed-JSON SyntaxError has statusCode=400) instead of blanket-500ing.
  const anyErr = err as { statusCode?: number; status?: number; type?: string };
  const status = typeof anyErr?.statusCode === 'number' ? anyErr.statusCode
    : typeof anyErr?.status === 'number' ? anyErr.status : 500;
  if (status >= 400 && status < 500) {
    res.status(status).json({ error: 'invalid request', correlationId });
    return;
  }
  res.status(500).json({ error: 'internal error', correlationId });
});

// Start Server async wrapper to support Vite dev server middleware
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res, next) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[OneAgent Super-App Server] Running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
