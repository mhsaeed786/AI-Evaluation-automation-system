# AI Evaluation Automation System

Benchmark **every** AI model from **every** provider against the same suite
of industry benchmarks (MMLU, GPQA, GSM8K, HumanEval, SWE-bench, AIME, and
25+ more) — then compare *measured* scores against *vendor-advertised* scores
to verify whether the metrics claimed by providers are actually correct, or
whether providers dial down metrics to improve cost, or fake model names to
save cost (e.g. serving glm-5-turbo behind a glm-5.2 tag).

## Repository structure

```
.
├── src/                     # Core evaluation engine (Python)
│   ├── config.py            #   Config loading + provider registry
│   ├── ollama_client.py     #   OpenAI-compatible chat client + retries
│   ├── provider_clients.py  #   Anthropic + Gemini native adapters
│   ├── loaders.py           #   HuggingFace dataset loaders (31 benchmarks)
│   ├── scorers.py           #   MCQ / math / code scoring functions
│   ├── scoring_types.py     #   Shared types (LetterScores)
│   ├── engines/
│   │   └── builtin.py       #   Default scoring engine
│   ├── runner.py            #   CLI runner (parallel providers)
│   ├── results.py           #   Result record + JSON persistence
│   ├── compare.py           #   Measured vs advertised comparison
│   ├── report.py            #   Markdown report generator
│   ├── dashboard.py         #   Web UI data layer
│   ├── server.py            #   Flask web app (threaded)
│   └── smoke_test.py        #   Endpoint/key connectivity test
├── harnesses/               # Tier-2 harness wrappers (lm-eval, EvalPlus)
├── config/                  # YAML configuration
│   ├── models.yaml          #   Model registry + profiles
│   ├── benchmarks.yaml      #   Benchmark registry (31 benchmarks)
│   ├── providers.yaml       #   Per-provider curated model lists
│   └── published_scores.yaml#   Vendor-advertised reference scores
├── templates/
│   └── index.html           #   Web dashboard SPA (8 tabs)
├── tests/
│   └── test_scoring.py      #   Offline scorer self-test (12 cases)
├── requirements.txt         #   Tier-1 deps (builtin engine, no torch)
├── requirements-harness.txt #   Tier-2 deps (lm-eval, EvalPlus)
├── run.ps1                  #   Windows bootstrap + launcher
├── .env.example             #   Environment template (all providers)
│
├── oneagent-super-app/      # [separate] OneAgent super-app (React/TS)
└── legacy-curemd-ba-qa/     # [separate] Legacy CureMD BA/QA suite
```

## Quick start

```powershell
# 1. Install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Add your API keys
Copy-Item .env.example .env
# Edit .env with your real keys

# 3. Verify connectivity
python -m src.smoke_test

# 4. Run benchmarks (all providers, all benchmarks, small samples)
python -m src.runner --provider all --models auto --benchmarks all --quick

# 5. Launch the web dashboard
python -m src.server
# Open http://127.0.0.1:5000
```

## Providers

| Provider | API type | Tier | Notes |
|---|---|---|---|
| Ollama Cloud | OpenAI-compat | **paid** | all models |
| Qwen Cloud | OpenAI-compat | **paid** | all models |
| GLM / Z.AI | OpenAI-compat | **paid** | all models |
| Gemini | OpenAI-compat | free | via /v1beta/openai endpoint |
| Groq | OpenAI-compat | free | |
| OpenRouter | OpenAI-compat | free | `:free` models only |
| Cerebras | OpenAI-compat | free | |
| HuggingFace | OpenAI-compat | free | router.huggingface.co |
| Cohere | OpenAI-compat | trial | |
| OpenAI | OpenAI-compat | paid | optional |
| Anthropic | Anthropic Messages | paid | optional (anthropic SDK) |
| Together / Mistral / etc. | OpenAI-compat | varies | optional |

Providers run **in parallel** via ThreadPoolExecutor (`--jobs`).

## Benchmarks (31)

Knowledge: MMLU, MMLU-Pro, ARC-Challenge, HellaSwag, WinoGrande, TruthfulQA,
GPQA, GPQA-Diamond, BBH, MixEval, IFEval, MuSR

Math: GSM8K, MATH, MATH-500, AIME 2024/2025/2026, SimpleQA, HLE

Code: HumanEval, MBPP, HumanEval+, MBPP+, LiveCodeBench, BigCodeBench

Agent: SWE-bench Lite/Verified, BFCL, GAIA, SWE-gym

## Web dashboard

8 tabs: Overview, Measured Matrix, Measured vs Advertised Deltas,
By Provider, Model Compare, Settings, Reports (CSV/JSON/MD download +
industry reference), Run trigger.

## Scoring

- **MCQ**: answer-letter logprob (canonical) → generate-and-parse fallback
  (system prompt forces letter answer for reasoning models)
- **Math**: final-answer extraction (\boxed{}, Answer:, last number) + exact match
- **Code**: subprocess pass@1 (HumanEval/MBPP) / stdin-stdout (LiveCodeBench)
- **Agent**: parse-only baseline (SWE-bench diff, BFCL JSON, GAIA exact-match)

## License

MIT
