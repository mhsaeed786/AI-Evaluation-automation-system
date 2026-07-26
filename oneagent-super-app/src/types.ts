export type TaskClass = 'classify' | 'extract' | 'reason' | 'code' | 'long_context' | 'vision';

export type ProviderType = 'gemini' | 'anthropic' | 'openai' | 'ollama' | 'zai';

export interface ModelConfig {
  id: string;
  name: string;
  provider: ProviderType;
  inputCostPer1K: number;
  outputCostPer1K: number;
  latencyMs: number;
  contextWindow: number;
  qualityScore: number; // 0-100
  enabled: boolean;
}

export interface TaskRanking {
  taskClass: TaskClass;
  description: string;
  rankedModelIds: string[]; // Ordered by user preference
  overrideModelId?: string; // Optional manual override
}

export interface CacheEntry {
  hash: string;
  promptSnippet: string;
  taskClass: TaskClass;
  modelUsed: string;
  timestamp: string;
  tokensSaved: number;
  costSavedUSD: number;
}

export interface BudgetStats {
  dailyCapUSD: number;
  currentSpendUSD: number;
  totalTokensToday: number;
  totalRequestsToday: number;
  cachedHitsToday: number;
  savedCostUSDToday: number;
}

export interface AgentStep {
  stepNumber: number;
  phase: 'plan' | 'tool_call' | 'observe' | 'thought' | 'result';
  title: string;
  details: string;
  toolName?: string;
  toolArgs?: Record<string, any>;
  output?: any;
  timestamp: string;
}

export interface AgentRunLog {
  id: string;
  taskPrompt: string;
  module: string;
  taskClass: TaskClass;
  modelUsed: string;
  status: 'running' | 'completed' | 'failed';
  totalTokens: number;
  costUSD: number;
  executionTimeMs: number;
  steps: AgentStep[];
  startedAt: string;
}

export interface SkillPack {
  id: string;
  name: string;
  category: 'fhir' | 'leap' | 'research' | 'work_ops' | 'content' | 'coding' | 'general';
  description: string;
  author: string;
  version: string;
  promptTemplate: string;
  tools: string[];
  enabled: boolean;
}

export interface MCPConnector {
  id: string;
  name: string;
  ecosystem: 'goose' | 'cherry' | 'openclaw' | 'hermes' | 'standard_mcp';
  transport: 'stdio' | 'sse' | 'websocket';
  endpoint: string;
  status: 'connected' | 'disconnected' | 'syncing';
  toolsProvided: string[];
  lastPingMs: number;
}

export interface Recipe {
  id: string;
  title: string;
  description: string;
  trigger: string;
  stepsCount: number;
  targetLimb: string;
  active: boolean;
}

export interface CronJob {
  id: string;
  name: string;
  cronExpression: string; // e.g. "0 8 * * 1"
  humanSchedule: string; // "Every Monday at 8:00 AM"
  module: string;
  taskPrompt: string;
  status: 'active' | 'paused' | 'running';
  lastRun?: string;
  nextRun: string;
  lastRunStatus?: 'success' | 'failed';
}

export interface MetaModule {
  id: string;
  name: string;
  slug: string;
  description: string;
  promptOrigin: string;
  modelAuthor: string;
  timestamp: string;
  status: 'pending' | 'approved' | 'rejected' | 'reverted';
  codeSnippet: string;
  testsCode: string;
  testPassRate: number; // e.g. 100
  sandboxOutput: string;
  provenance: {
    generatedBy: string;
    tokenCount: number;
    parentFramework: string;
  };
}

// FHIR Limb Data Types
export interface FHIRInconsistency {
  id: string;
  resourceType: 'Patient' | 'Encounter' | 'Claim' | 'Provenance' | 'Observation';
  resourceId: string;
  field: string;
  issue: string;
  severity: 'critical' | 'warning' | 'info';
  suggestedFix: string;
}

export interface FHIRBundleItem {
  id: string;
  resourceType: string;
  status: string;
  lastUpdated: string;
  data: Record<string, any>;
}

// LEAP Analytics Types
export interface LEAPMetric {
  category: 'Scaling' | 'RWT' | 'UDS' | 'Support';
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  status: 'optimal' | 'attention' | 'critical';
}

// Research & SaaS Types
export interface ResearchReport {
  id: string;
  topic: string;
  summary: string;
  keyTakeaways: string[];
  sources: { title: string; url: string }[];
  saasOpportunities?: { title: string; targetAudience: string; difficulty: string; marketGap: string }[];
  date: string;
}

// System Module Limb manifest
export interface LimbModuleManifest {
  id: string;
  name: string;
  slug: string;
  iconName: string;
  category: string;
  description: string;
  toolCount: number;
  mergedFromCount: number;
  status: 'healthy' | 'updating' | 'draft';
  isSelfAuthored?: boolean;
}
