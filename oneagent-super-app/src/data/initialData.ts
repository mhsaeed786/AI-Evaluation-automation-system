import {
  ModelConfig,
  TaskRanking,
  CacheEntry,
  BudgetStats,
  SkillPack,
  MCPConnector,
  Recipe,
  CronJob,
  MetaModule,
  FHIRInconsistency,
  FHIRBundleItem,
  LEAPMetric,
  ResearchReport,
  LimbModuleManifest
} from '../types';

export const INITIAL_MODELS: ModelConfig[] = [
  {
    id: 'gemini-3.6-flash',
    name: 'Gemini 3.6 Flash',
    provider: 'gemini',
    inputCostPer1K: 0.0001,
    outputCostPer1K: 0.0004,
    latencyMs: 180,
    contextWindow: 1000000,
    qualityScore: 92,
    enabled: true
  },
  {
    id: 'gemini-3.1-pro-preview',
    name: 'Gemini 3.1 Pro',
    provider: 'gemini',
    inputCostPer1K: 0.00125,
    outputCostPer1K: 0.005,
    latencyMs: 420,
    contextWindow: 2000000,
    qualityScore: 98,
    enabled: true
  },
  {
    id: 'claude-3-7-sonnet',
    name: 'Claude 3.7 Sonnet',
    provider: 'anthropic',
    inputCostPer1K: 0.003,
    outputCostPer1K: 0.015,
    latencyMs: 380,
    contextWindow: 200000,
    qualityScore: 97,
    enabled: true
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    inputCostPer1K: 0.00015,
    outputCostPer1K: 0.0006,
    latencyMs: 210,
    contextWindow: 128000,
    qualityScore: 89,
    enabled: true
  },
  {
    id: 'ollama-deepseek-r1',
    name: 'DeepSeek R1 (Ollama Local)',
    provider: 'ollama',
    inputCostPer1K: 0.0,
    outputCostPer1K: 0.0,
    latencyMs: 650,
    contextWindow: 64000,
    qualityScore: 91,
    enabled: true
  }
];

export const INITIAL_TASK_RANKINGS: TaskRanking[] = [
  {
    taskClass: 'classify',
    description: 'Resource tagging, FHIR status triage, sentiment & classification',
    rankedModelIds: ['gemini-3.6-flash', 'gpt-4o-mini', 'ollama-deepseek-r1', 'gemini-3.1-pro-preview', 'claude-3-7-sonnet']
  },
  {
    taskClass: 'extract',
    description: 'JSON schema extraction, FHIR Bundle parsing, log telemetry parsing',
    rankedModelIds: ['gemini-3.6-flash', 'gemini-3.1-pro-preview', 'claude-3-7-sonnet', 'gpt-4o-mini', 'ollama-deepseek-r1']
  },
  {
    taskClass: 'reason',
    description: 'Complex healthcare QA logic, LEAP anomaly investigation, research synthesis',
    rankedModelIds: ['gemini-3.1-pro-preview', 'claude-3-7-sonnet', 'gemini-3.6-flash', 'ollama-deepseek-r1', 'gpt-4o-mini']
  },
  {
    taskClass: 'code',
    description: 'Meta-agent module generation, unit tests writing, refactoring & CLI scripts',
    rankedModelIds: ['gemini-3.1-pro-preview', 'claude-3-7-sonnet', 'gemini-3.6-flash', 'gpt-4o-mini', 'ollama-deepseek-r1']
  },
  {
    taskClass: 'long_context',
    description: 'Large FHIR bundles, 100+ page ONC HTI-2 specs, repository scanning',
    rankedModelIds: ['gemini-3.1-pro-preview', 'gemini-3.6-flash', 'claude-3-7-sonnet', 'gpt-4o-mini', 'ollama-deepseek-r1']
  },
  {
    taskClass: 'vision',
    description: 'Document image extraction, clinical chart scans, architecture diagrams',
    rankedModelIds: ['gemini-3.6-flash', 'gemini-3.1-pro-preview', 'claude-3-7-sonnet', 'gpt-4o-mini', 'ollama-deepseek-r1']
  }
];

export const INITIAL_CACHE_ENTRIES: CacheEntry[] = [
  {
    hash: '8f92a11b0e',
    promptSnippet: 'Validate Patient resource FHIR compliance for field identifier.system',
    taskClass: 'extract',
    modelUsed: 'gemini-3.6-flash',
    timestamp: '2026-07-24 02:15:00',
    tokensSaved: 1420,
    costSavedUSD: 0.00057
  },
  {
    hash: '3c4e9d721a',
    promptSnippet: 'Summarize LEAP RWT scaling report for Q2 compliance checklist',
    taskClass: 'reason',
    modelUsed: 'gemini-3.1-pro-preview',
    timestamp: '2026-07-24 01:40:12',
    tokensSaved: 4850,
    costSavedUSD: 0.02425
  },
  {
    hash: '11a90c23ef',
    promptSnippet: 'Generate pytest script for FHIR inconsistency query mapping',
    taskClass: 'code',
    modelUsed: 'gemini-3.1-pro-preview',
    timestamp: '2026-07-23 23:10:44',
    tokensSaved: 3200,
    costSavedUSD: 0.01600
  }
];

export const INITIAL_BUDGET_STATS: BudgetStats = {
  dailyCapUSD: 5.00,
  currentSpendUSD: 0.428,
  totalTokensToday: 184500,
  totalRequestsToday: 64,
  cachedHitsToday: 21,
  savedCostUSDToday: 0.185
};

export const INITIAL_SKILL_PACKS: SkillPack[] = [
  {
    id: 'skill-fhir-auditor',
    name: 'FHIR US-Core & HTI-2 Auditor',
    category: 'fhir',
    description: 'Audits FHIR bundles against US-Core 3.1.1/6.1.0 profiles, detects provenance gaps and invalid NPI references.',
    author: 'CureMD BA/QA Team',
    version: '2.4.0',
    promptTemplate: 'You are an expert FHIR BA/QA auditor. Inspect the input resource bundle against US-Core specifications...',
    tools: ['fhir_inconsistency_check', 'hapi_explorer', 'npi_validator', 'provenance_mapper'],
    enabled: true
  },
  {
    id: 'skill-leap-scaling',
    name: 'LEAP RWT & Analytics Diagnostics',
    category: 'leap',
    description: 'Diagnoses Real World Testing (RWT) telemetry, UDS compliance metrics, and high-throughput scaling bottlenecks.',
    author: 'LEAP Ops Team',
    version: '1.8.2',
    promptTemplate: 'Analyze LEAP performance metrics and check UDS electronic clinical quality measure thresholds...',
    tools: ['leap_rwt_fetcher', 'uds_compliance_eval', 'scaling_threshold_check'],
    enabled: true
  },
  {
    id: 'skill-deep-researcher',
    name: 'Multi-Source Deep Researcher',
    category: 'research',
    description: 'Performs multi-turn web search, page scraping, citation indexing, and SaaS opportunity scoring.',
    author: 'OneAgent Meta Core',
    version: '3.1.0',
    promptTemplate: 'Conduct deep research into the target topic, fetch primary documentation, cross-reference sources...',
    tools: ['web_search', 'web_scraper', 'citation_builder', 'saas_gap_analyzer'],
    enabled: true
  },
  {
    id: 'skill-content-seo',
    name: 'SEO & Tech Blog Pipeline',
    category: 'content',
    description: 'Generates SEO-optimized articles, social media summaries, and developer newsletter digests from tech notes.',
    author: 'OneAgent Media',
    version: '1.2.0',
    promptTemplate: 'Transform engineering notes and FHIR release notes into engaging blog posts formatted in Markdown...',
    tools: ['markdown_formatter', 'keyword_density_check', 'social_snippet_gen'],
    enabled: true
  },
  {
    id: 'skill-workops-automation',
    name: 'Outlook, Teams & DataSync Ops',
    category: 'work_ops',
    description: 'Monitors incoming healthcare support emails, triages Teams threads, and triggers DataSync pipelines.',
    author: 'WorkOps Engine',
    version: '2.0.1',
    promptTemplate: 'Extract action items from communication logs and map to DataSync jobs...',
    tools: ['outlook_triage', 'teams_channel_post', 'datasync_trigger'],
    enabled: true
  }
];

export const INITIAL_MCP_CONNECTORS: MCPConnector[] = [
  {
    id: 'mcp-goose',
    name: 'Goose CLI Agent Connector',
    ecosystem: 'goose',
    transport: 'stdio',
    endpoint: 'goose-mcp-server --port 8081',
    status: 'connected',
    toolsProvided: ['goose.execute_recipe', 'goose.shell_exec', 'goose.system_inspect'],
    lastPingMs: 14
  },
  {
    id: 'mcp-cherry',
    name: 'Cherry Studio MCP Bridge',
    ecosystem: 'cherry',
    transport: 'sse',
    endpoint: 'http://localhost:8082/mcp/sse',
    status: 'connected',
    toolsProvided: ['cherry.chat_sync', 'cherry.prompt_library', 'cherry.memory_dump'],
    lastPingMs: 22
  },
  {
    id: 'mcp-openclaw',
    name: 'OpenClaw Autonomous Runner',
    ecosystem: 'openclaw',
    transport: 'websocket',
    endpoint: 'ws://localhost:8083/openclaw',
    status: 'connected',
    toolsProvided: ['openclaw.browser_agent', 'openclaw.dom_click', 'openclaw.extract_dom'],
    lastPingMs: 18
  },
  {
    id: 'mcp-hermes',
    name: 'Hermes Workflow Scheduler MCP',
    ecosystem: 'hermes',
    transport: 'stdio',
    endpoint: 'hermes-mcp-server',
    status: 'connected',
    toolsProvided: ['hermes.dispatch_job', 'hermes.query_queue', 'hermes.retry_failed'],
    lastPingMs: 12
  }
];

export const INITIAL_RECIPES: Recipe[] = [
  {
    id: 'rec-fhir-nightly',
    title: 'Nightly FHIR Inconsistency Sweep & Alert',
    description: 'Runs US-Core inconsistency checks over all updated FHIR patient records and posts discrepancies to Teams.',
    trigger: 'Cron: Every night at 02:00 AM',
    stepsCount: 4,
    targetLimb: 'FHIR Suite',
    active: true
  },
  {
    id: 'rec-leap-weekly',
    title: 'LEAP RWT Compliance Weekly Digest',
    description: 'Aggregates RWT telemetry and generates an executive summary report for QA leads.',
    trigger: 'Cron: Every Monday at 08:00 AM',
    stepsCount: 3,
    targetLimb: 'LEAP Analytics',
    active: true
  },
  {
    id: 'rec-saas-finder',
    title: 'Automated Healthcare SaaS Opportunity Finder',
    description: 'Scrapes ONC regulatory changes and identifies high-margin B2B SaaS software gaps.',
    trigger: 'Manual / Event-Driven',
    stepsCount: 5,
    targetLimb: 'Deep Research',
    active: true
  }
];

export const INITIAL_CRON_JOBS: CronJob[] = [
  {
    id: 'cron-1',
    name: 'Weekly LEAP RWT Scaling Summary',
    cronExpression: '0 8 * * 1',
    humanSchedule: 'Every Monday at 08:00 AM',
    module: 'LEAP Analytics',
    taskPrompt: 'Generate weekly LEAP scaling and UDS compliance report with bottleneck recommendations.',
    status: 'active',
    lastRun: '2026-07-20 08:00:00',
    nextRun: '2026-07-27 08:00:00',
    lastRunStatus: 'success'
  },
  {
    id: 'cron-2',
    name: 'Daily FHIR Inconsistency Scanner',
    cronExpression: '0 2 * * *',
    humanSchedule: 'Daily at 02:00 AM',
    module: 'FHIR Suite',
    taskPrompt: 'Scan FHIR server bundles for missing NPIs, missing extensions, and invalid date formats.',
    status: 'active',
    lastRun: '2026-07-24 02:00:00',
    nextRun: '2026-07-25 02:00:00',
    lastRunStatus: 'success'
  },
  {
    id: 'cron-3',
    name: 'SEO Blog Post Auto-Drafter',
    cronExpression: '0 10 * * 3',
    humanSchedule: 'Every Wednesday at 10:00 AM',
    module: 'Content & SEO',
    taskPrompt: 'Draft an article on latest ONC HTI-2 FHIR compliance standards for the tech blog.',
    status: 'paused',
    lastRun: '2026-07-16 10:00:00',
    nextRun: '2026-07-29 10:00:00',
    lastRunStatus: 'success'
  }
];

export const INITIAL_META_MODULES: MetaModule[] = [
  {
    id: 'meta-mod-1',
    name: 'FHIR Bundle Cost Analyzer',
    slug: 'fhir_cost_analysis',
    description: 'Calculates API bandwidth, storage costs, and transaction load per FHIR patient bundle.',
    promptOrigin: 'Build a tool that estimates bandwidth and dollar cost for processing 100k FHIR bundles per day.',
    modelAuthor: 'gemini-3.1-pro-preview',
    timestamp: '2026-07-23 18:30:12',
    status: 'approved',
    codeSnippet: `def analyze_bundle_cost(bundle_json: dict) -> dict:\n    entries = bundle_json.get("entry", [])\n    size_kb = len(str(bundle_json)) / 1024\n    estimated_cost = len(entries) * 0.000012 + (size_kb * 0.000005)\n    return {\n        "total_resources": len(entries),\n        "size_kb": round(size_kb, 2),\n        "estimated_cost_usd": round(estimated_cost, 6)\n    }`,
    testsCode: `def test_analyze_bundle_cost():\n    sample = {"entry": [{"resource": {"resourceType": "Patient"}}] }\n    res = analyze_bundle_cost(sample)\n    assert "estimated_cost_usd" in res\n    assert res["total_resources"] == 1`,
    testPassRate: 100,
    sandboxOutput: 'pytest sandbox/test_fhir_cost.py: 3 passed in 0.12s. All assertions successful.',
    provenance: {
      generatedBy: 'OneAgent Meta-Authoring Engine',
      tokenCount: 1450,
      parentFramework: 'OneAgent Core v1.0'
    }
  },
  {
    id: 'meta-mod-2',
    name: 'Outlook Ticket Triage & Response Auto-Draft',
    slug: 'outlook_teams_triage',
    description: 'Auto-categorizes CureMD support emails and drafts quick responses for QA engineers.',
    promptOrigin: 'Create a module that parses incoming support emails, checks FHIR error codes, and drafts replies.',
    modelAuthor: 'gemini-3.1-pro-preview',
    timestamp: '2026-07-24 01:10:00',
    status: 'approved',
    codeSnippet: `def triage_email(subject: str, body: str) -> dict:\n    is_fhir_bug = "FHIR" in subject or "HAPI" in body\n    priority = "HIGH" if "production" in body.lower() else "MEDIUM"\n    return {\n        "category": "FHIR_API_ISSUE" if is_fhir_bug else "GENERAL",\n        "priority": priority,\n        "draft_reply": f"Hello, thank you for reaching out regarding '{subject}'. Our QA team is investigating."\n    }`,
    testsCode: `def test_triage_email():\n    res = triage_email("FHIR 500 Error in Production", "HAPI server returned 500")\n    assert res["priority"] == "HIGH"\n    assert res["category"] == "FHIR_API_ISSUE"`,
    testPassRate: 100,
    sandboxOutput: 'pytest sandbox/test_triage.py: 2 passed in 0.08s. All assertions successful.',
    provenance: {
      generatedBy: 'OneAgent Meta-Authoring Engine',
      tokenCount: 1120,
      parentFramework: 'OneAgent Core v1.0'
    }
  }
];

export const INITIAL_FHIR_INCONSISTENCIES: FHIRInconsistency[] = [
  {
    id: 'inc-101',
    resourceType: 'Patient',
    resourceId: 'pat-882910',
    field: 'identifier.system',
    issue: 'Missing mandatory US-Core MRN system URI (expected http://hospital.smarthealthit.org)',
    severity: 'critical',
    suggestedFix: 'Inject system string "http://hospital.smarthealthit.org" into identifier array.'
  },
  {
    id: 'inc-102',
    resourceType: 'Encounter',
    resourceId: 'enc-449122',
    field: 'period.end',
    issue: 'Encounter end timestamp occurs before period.start (negative duration detected)',
    severity: 'critical',
    suggestedFix: 'Fix timestamp ordering: start 2026-07-23T10:00:00Z, end 2026-07-23T10:45:00Z.'
  },
  {
    id: 'inc-103',
    resourceType: 'Provenance',
    resourceId: 'prov-10928',
    field: 'agent.who',
    issue: 'Provenance agent reference lacks required Practitioner NPI profile extension',
    severity: 'warning',
    suggestedFix: 'Add Practitioner reference with valid 10-digit NPI identifier extension.'
  },
  {
    id: 'inc-104',
    resourceType: 'Claim',
    resourceId: 'clm-338102',
    field: 'diagnosis.sequence',
    issue: 'Non-sequential diagnosis ranking index (found 1, 3, missing sequence 2)',
    severity: 'info',
    suggestedFix: 'Re-index claim diagnosis elements sequentially 1, 2, 3.'
  }
];

export const INITIAL_FHIR_BUNDLE: FHIRBundleItem[] = [
  {
    id: 'pat-882910',
    resourceType: 'Patient',
    status: 'active',
    lastUpdated: '2026-07-24 01:22:10',
    data: {
      name: [{ family: 'Smith', given: ['John', 'A.'] }],
      gender: 'male',
      birthDate: '1984-05-12',
      telecom: [{ system: 'phone', value: '555-0192' }],
      address: [{ city: 'New York', state: 'NY', postalCode: '10001' }]
    }
  },
  {
    id: 'enc-449122',
    resourceType: 'Encounter',
    status: 'finished',
    lastUpdated: '2026-07-24 01:25:00',
    data: {
      class: { code: 'AMB', display: 'ambulatory' },
      type: [{ text: 'Annual Physical Examination' }],
      subject: { reference: 'Patient/pat-882910' }
    }
  },
  {
    id: 'obs-991204',
    resourceType: 'Observation',
    status: 'final',
    lastUpdated: '2026-07-24 01:30:15',
    data: {
      code: { coding: [{ system: 'http://loinc.org', code: '883-9', display: 'ABO group' }] },
      valueString: 'A positive',
      subject: { reference: 'Patient/pat-882910' }
    }
  }
];

export const INITIAL_LEAP_METRICS: LEAPMetric[] = [
  {
    category: 'Scaling',
    title: 'Server Throughput (RPS)',
    value: '4,850 rps',
    change: '+14.2%',
    trend: 'up',
    status: 'optimal'
  },
  {
    category: 'RWT',
    title: 'Real World Testing Validation',
    value: '99.84%',
    change: '+0.12%',
    trend: 'up',
    status: 'optimal'
  },
  {
    category: 'UDS',
    title: 'UDS eCQM Compliance Rate',
    value: '94.2%',
    change: '-1.5%',
    trend: 'down',
    status: 'attention'
  },
  {
    category: 'Support',
    title: 'CureMD QA Support Tickets',
    value: '12 Open',
    change: '-5 tickets',
    trend: 'up',
    status: 'optimal'
  }
];

export const INITIAL_RESEARCH_REPORTS: ResearchReport[] = [
  {
    id: 'rep-001',
    topic: 'ONC HTI-2 Final Rule & FHIR Audit Requirements for 2026',
    summary: 'ONC HTI-2 mandates automated patient-facing API validation, multi-factor EHR auditing, and strict Provenance telemetry for electronic health information exchanges.',
    keyTakeaways: [
      'HTI-2 enforces mandatory US-Core v6.1.0 compliance across all certified EHR modules.',
      'FHIR Bulk Data export must support automated rate limiting and client token rotation.',
      'API access logging requires cryptographic timestamping in Provenance resources.'
    ],
    sources: [
      { title: 'ONC Official HTI-2 Implementation Manual', url: 'https://www.healthit.gov/hti-2' },
      { title: 'HL7 US-Core Implementation Guide v6.1.0', url: 'https://hl7.org/fhir/us/core' }
    ],
    saasOpportunities: [
      {
        title: 'Auto-FHIR Provenance Validator',
        targetAudience: 'EHR Vendors & QA Teams',
        difficulty: 'Medium',
        marketGap: 'Most EHRs lack real-time US-Core extension syntax checking before sending claims.'
      },
      {
        title: 'ONC HTI-2 Continuous Audit Engine',
        targetAudience: 'Healthcare Compliance Officers',
        difficulty: 'Low',
        marketGap: 'High demand for background cron auditors that output executive pass/fail dashboards.'
      }
    ],
    date: '2026-07-22'
  }
];

export const INITIAL_LIMB_MANIFESTS: LimbModuleManifest[] = [
  {
    id: 'limb-fhir',
    name: 'FHIR BA/QA Suite',
    slug: 'fhir',
    iconName: 'Activity',
    category: 'Healthcare & Specs',
    description: 'Consolidated from 11 FHIR apps: inconsistency queries, HAPI explorer, cost analysis, and provider mapping.',
    toolCount: 14,
    mergedFromCount: 11,
    status: 'healthy'
  },
  {
    id: 'limb-leap',
    name: 'LEAP Analytics',
    slug: 'leap',
    iconName: 'BarChart3',
    category: 'Telemetry & Testing',
    description: 'Consolidated from LEAP scaling, RWT, analytics, support triage, and UDS reporting.',
    toolCount: 9,
    mergedFromCount: 5,
    status: 'healthy'
  },
  {
    id: 'limb-research',
    name: 'Deep Research & SaaS',
    slug: 'research',
    iconName: 'Search',
    category: 'Market Intelligence',
    description: 'Consolidated from deep researcher and SaaS opportunity finder.',
    toolCount: 8,
    mergedFromCount: 3,
    status: 'healthy'
  },
  {
    id: 'limb-workops',
    name: 'WorkOps & DataSync',
    slug: 'workops',
    iconName: 'Workflow',
    category: 'Workflow Automation',
    description: 'Consolidated from Outlook, Teams, SharePoint downloader, and DataSync runner.',
    toolCount: 11,
    mergedFromCount: 4,
    status: 'healthy'
  },
  {
    id: 'limb-content',
    name: 'Content & SEO Pipeline',
    slug: 'content',
    iconName: 'FileText',
    category: 'Publishing',
    description: 'Automated blog, SEO keyword optimizer, social posts, and release note summaries.',
    toolCount: 6,
    mergedFromCount: 2,
    status: 'healthy'
  },
  {
    id: 'limb-files',
    name: 'Files & Storage Guardian',
    slug: 'files',
    iconName: 'FolderKanban',
    category: 'Data Management',
    description: 'Local AI file organizer, storage guardian, duplicate remover, and metadata tagger.',
    toolCount: 7,
    mergedFromCount: 3,
    status: 'healthy'
  },
  {
    id: 'limb-coding',
    name: 'CLI Controller & Code Scaffolder',
    slug: 'coding',
    iconName: 'Code',
    category: 'Developer Tools',
    description: 'Repo scaffolder, CLI controller, diff viewer, and automated test harness.',
    toolCount: 10,
    mergedFromCount: 4,
    status: 'healthy'
  }
];
