# Ollama Cloud Evaluation System

Benchmark **every** Ollama Cloud / Pro-plan model against the same suite the
original models are advertised on — then compare *measured* scores against the
vendors' *advertised* scores to see whether the hosted (often quantized)
versions really are "as smart" as claimed.

Drives Ollama Cloud through its **OpenAI-compatible endpoint** and scores a
wide suite spanning knowledge (MMLU, MMLU-Pro, ARC, HellaSwag, Winogrande,
TruthfulQA, BBH, AGIEval), reasoning (GPQA, AIME, HLE, SimpleQA, RULER),
math (GSM8K, MATH, MATH-500), code (HumanEval, MBPP, LiveCodeBench,
BigCodeBench, Aider polyglot), and agent/agentic tasks (SWE-bench Lite &
Verified, DeepSWE, ARC-AGI-2, BFCL, GAIA, terminal-bench). It then writes a
Markdown report with measured-vs-advertised deltas. See the **Benchmarks**
table below for which are full-fidelity vs baseline-only.

---

## Quick start (Windows)

```powershell
# from the project root
.\run.ps1 -SmokeOnly          # 1. install deps + verify your key & endpoint
.\run.ps1 -Quick              # 2. fast end-to-end run (~minutes, small samples)
.\run.ps1 -Quick -Benchmarks all
python -m src.report          # 3. render reports/comparison_*.md
```

Manual (any OS):

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # then paste your Ollama Cloud key into .env
python -m src.smoke_test        # pin the endpoint
python -m src.runner --models auto --benchmarks mmlu,gsm8k,humaneval --quick
python -m src.report
```

---

## 1. Install your key

1. Get a key at **https://ollama.com/cloud** (Pro plan).
2. Copy `.env.example` → `.env` and fill in:

   ```ini
   OLLAMA_API_KEY=oll_your_key_here
   OLLAMA_BASE_URL=https://api.ollama.com/v1   # see "Pinning the endpoint"
   OLLAMA_SEED=1234
   OLLAMA_TEMPERATURE=0.0
   OLLAMA_TIMEOUT=180
   ```

`.env` is git-ignored and never logged. The smoke test masks the key in its
output. **Do not commit `.env`.**

---

## 2. Pinning the endpoint

Ollama Cloud is OpenAI-compatible, but the exact base URL has shifted over time
and could not be live-verified when this project was built. The code defaults to

```
https://api.ollama.com/v1
```

and **confirms it at runtime** via `src/smoke_test.py`, which:

1. calls `GET /v1/models` and lists the models your key can see,
2. runs a tiny chat probe ("Reply with exactly: OK"),
3. probes whether `top_logprobs` is supported (decides MCQ scoring path).

If the smoke test fails with an auth/404/connection error, edit
`OLLAMA_BASE_URL` in `.env`. Candidate values if `https://api.ollama.com/v1`
doesn't resolve:

```
https://api.ollama.com/v1
https://cloud.ollama.com/v1
https://api.ollama.ai/v1
```

Re-run `python -m src.smoke_test` until it lists models. The model list it
returns is **canonical** — `--models auto` always uses the live list, not the
curated registry in `config/models.yaml`.

---

## 3. Run benchmarks

```bash
# Discover live models, run everything, full samples:
python -m src.runner --models auto --benchmarks all

# One model, the coding-focused benchmarks (profile from config/models.yaml):
python -m src.runner --models qwen3-coder --benchmarks coding

# Each model runs its own configured profile(s):
python -m src.runner --models auto --benchmarks per_profile

# Specific subset:
python -m src.runner --models deepseek-r1 --benchmarks mmlu,gpqa,gsm8k,math
```

**Profiles** (`general` / `coding` / `reasoning`) are defined in
`config/models.yaml` and map model → which benchmarks matter for it. Add models
or change profiles there.

Results are written one JSON per `(model, benchmark)` under `results/`. Each
record is self-describing (engine, seed, temperature, n_shot, base_url) so a
stale run is never confused with a fresh one. Re-running a benchmark overwrites
that model×benchmark's latest row.

### Engines

| Engine | Flag | What it is | Deps |
|---|---|---|---|
| **builtin** (default) | `--engine builtin` | Our own scorer — no torch, runs on Python 3.14. MCQ via answer-letter logprob (+generate fallback); math via boxed/regex exact-match; code via subprocess pass@1. | `requirements.txt` only |
| **lm-eval** | `--engine lm_eval` | EleutherAI lm-evaluation-harness, driven at the OpenAI endpoint. Loglikelihood-based — closest to how vendors report MCQ. | `requirements-harness.txt` (Python 3.11/12) |
| **evalplus** | `--engine evalplus` | EvalPlus (HumanEval+/MBPP+) — stricter pass@1 with augmented tests. | `requirements-harness.txt` |

```bash
.\run.ps1 -Engine lm_eval -InstallHarness        # Windows, installs Tier-2 deps too
```

The Tier-2 wrappers invoke the upstream harnesses as subprocesses (auth via
`OPENAI_API_KEY`/`OPENAI_BASE_URL` env) and fold their JSON output into the same
`ResultRecord` shape, so the comparison/report layer is identical across engines.

---

## 4. Read the report

```bash
python -m src.report
```

Writes `reports/comparison_<timestamp>.md` containing:

- a **measured matrix** (model × benchmark, %),
- a **delta table** (measured − advertised, sorted most-negative first),
- a **skipped/errored** section.

Vendor-advertised reference scores live in `config/published_scores.yaml` with a
source `verify:` link per model. **Treat them as best-effort** — vendors report
loglikelihood MCQ and pass@1 over larger samples than this tool; update the YAML
as you confirm numbers.

---

## Benchmarks

`--benchmarks all` runs the full registry below (~30 entries). They split into
two fidelity tiers — read the tier before comparing a number to a vendor's.

### Tier A — full-fidelity (scores are directly meaningful)

| Name | Kind | Measures | Scored by |
|---|---|---|---|
| `mmlu` | mcq | broad knowledge (57 subjects) | letter logprob |
| `mmlu_pro` | mcq | harder 10-option knowledge | letter logprob |
| `arc_challenge` | mcq | grade-school science reasoning | letter logprob (norm) |
| `hellaswag` | mcq | sentence completion / common sense | letter logprob (norm) |
| `winogrande` | mcq | coreference resolution | letter logprob |
| `truthfulqa` | mcq | resistance to common falsehoods | MC1 letter logprob |
| `gpqa` | mcq (CoT) | graduate-level science (gated) | generate + parse |
| `bbh` | free-text (CoT) | BIG-Bench Hard reasoning | text match |
| `agieval` | mcq | human-facing exams | letter logprob |
| `gsm8k` | math | grade-school math | final-answer exact-match |
| `math` | math | competition math | `\boxed{}` exact-match |
| `math_500` | math | MATH-500 subset | final-answer exact-match |
| `aime_2024` / `aime_2025` | math | AIME competition | final-answer exact-match |
| `simpleqa` | short-form QA | factual short answers | exact-match |
| `humaneval` | code | Python function correctness ⚡ | pass@1 (subprocess) |
| `mbpp` | code | mostly-basic Python programs ⚡ | pass@1 (subprocess) |
| `humaneval_plus` / `mbpp_plus` | code | EvalPlus-augmented tests ⚡ | pass@1 (evalplus engine) |

### Tier B — baseline / parse-only (lower-bound sanity checks, NOT pass rates)

These verify the model **emits a well-formed artifact**, not that it is
genuinely correct against the upstream harness. Treat their numbers as a
floor / sanity signal, not a comparable score. (The full SWE-bench, ARC-AGI-2,
BFCL, GAIA and terminal-bench harnesses each need their own runners / Docker;
the builtin integrations here are a fast first look.)

| Name | Kind | Checks | Executes model output? |
|---|---|---|---|
| `livecodebench` | code_io | stdin→stdout match ⚡ | yes (Python) |
| `bigcodebench` | code | subprocess pass ⚡ | yes (Python) |
| `aider_polyglot` | code | subprocess pass ⚡ | yes (Python) |
| `swebench_lite` / `swebench_verified` / `deepswe` | agent_swe | model emits a valid unified diff | no — parse only |
| `arc_agi_2` | agent_arc | model emits grid JSON | no — parse only |
| `bfcl` | agent_bfcl | function-call JSON matches gold | no — parse only |
| `gaia` | agent_gaia | short-form answer exact-match | no |
| `terminalbench` | agent_terminal | shell stdout matches gold ⚡⚠ | yes — **shell**, OFF by default (see Security) |
| `ruler` | math | long-context needle tasks | no |
| `hle` | short-form QA | Humanity's Last Exam | exact-match |
| `tau_bench` | agent_tau | *(not yet implemented)* | — skipped as `unknown_kind` |

⚡ = executes model output locally (see **Security note**).
⚠ = executes **shell** commands; opt-in only.

Use `config/benchmarks.yaml` to change `n_shot`, `limit`, `cot`, or the dataset
path. The `quick_limits:` table controls sample sizes for `--quick`.

---

## Methodology caveat (read before drawing conclusions)

A measured-vs-advertised **delta mixes model quality and methodology**, not a
pure quality verdict:

- **builtin vs vendor**: vendors score MCQ by *full loglikelihood* across all
  choices; this tool uses *next-token logprob of the answer letter* (or
  generate-and-parse). They correlate but are not identical.
- **quantization**: Ollama Cloud serves quantized models; the original
  advertised numbers are often full-precision FP16/BF16. Part of any gap is
  quantization, not the eval.
- **sample size**: `--quick` runs ~50 items per benchmark; full runs still use a
  subset for speed. Vendor numbers use the whole split.
- **prompting**: few-shot counts and CoT prompts differ slightly from each
  vendor's recipe.

For the closest-to-vendor numbers, use `--engine lm_eval` (loglikelihood) on the
full splits, and keep `temperature=0`, `seed=1234`.

---

## Security note

Several benchmarks **execute model-generated output locally**. There is no
OS-level sandbox — a wall-clock timeout (`CODE_TIMEOUT=20s`) is the only guard.
Review `src/scorers.py` before enabling any of these, and only run them on a
machine you're comfortable running untrusted code on (a disposable dev box or
container, never one holding real data or credentials):

| Scorer | Executes | Benchmarks | Default state |
|---|---|---|---|
| `score_code`, `score_code_io` | model-written **Python** (subprocess) | `humaneval`, `mbpp`, `bigcodebench`, `livecodebench`, evalplus | runs by default |
| `score_agent_terminal` | model-written **shell commands** (`bash -lc …`) | `terminalbench` | **OFF** — see below |
| `score_swe` | parse-only (checks the model emits a valid diff) | `swebench_*`, `deepswe` | safe — no execution |

**terminal-bench is OFF by default.** It runs arbitrary model-emitted shell
commands, which is the whole point of the benchmark but is genuinely dangerous.
`score_agent_terminal` only executes when **both** of these hold:

1. the env var `OLLAMA_EVAL_ALLOW_SHELL=1` is explicitly set, **and**
2. a POSIX shell (`bash`/`sh`) is found on PATH via `shutil.which` — stock
   Windows has neither, so it stays fail-safe there even if opted in.

When disabled (the default), every terminal-bench item is recorded as
not-passed with reason `shell_exec_disabled` and contributes nothing to the
aggregate score. To enable it, on a disposable Linux/container box:

```bash
export OLLAMA_EVAL_ALLOW_SHELL=1
python -m src.runner --benchmarks terminalbench
```

GPQA is a **gated** dataset: it requires accepting its license on HuggingFace
and setting `HF_TOKEN` in `.env` (added to `.env.example`). Without it, GPQA
loads are skipped gracefully with instructions — other benchmarks are
unaffected.

---

## Layout

```
config/            models.yaml (registry+profiles), benchmarks.yaml, published_scores.yaml
src/
  config.py        loads .env + YAMLs, exposes Config
  ollama_client.py OpenAI-SDK wrapper + retries + logprob helpers
  smoke_test.py    pins the endpoint / verifies the key
  loaders.py       HuggingFace dataset loaders per benchmark
  scorers.py       MCQ / math / code scoring
  engines/builtin.py  the default scorer loop
  runner.py        CLI: --models --benchmarks --engine --quick
  results.py       ResultRecord + JSON persistence
  compare.py       measured vs advertised
  report.py        Markdown report
harnesses/         Tier-2 wrappers (lm-eval, evalplus) — lazy-loaded
run.ps1            Windows bootstrap + launcher
```

---

## Troubleshooting

- **Smoke test: 401 / Unauthorized** → wrong `OLLAMA_API_KEY`. Re-check in `.env`.
- **Smoke test: connection refused / 404** → wrong `OLLAMA_BASE_URL`. Try the
  candidates in "Pinning the endpoint".
- **`top_logprobs not supported`** → the builtin engine falls back to
  generate-and-parse automatically; results still work, just slightly noisier on
  MCQ.
- **GPQA skipped** → set `HF_TOKEN` after accepting the GPQA license on HF.
- **`No wheel for Python 3.14`** → builtin engine has no such deps; this only
  happens with `--engine lm_eval`/`evalplus`. Use Python 3.11/3.12 for those
  (`.venv` per engine is fine).
- **Rate limits / timeouts** → raise `OLLAMA_TIMEOUT` in `.env`; the client
  already retries with exponential backoff (6 attempts).

---

_Reproducible given the same key, seed (1234), and temperature (0.0). Re-run any
benchmark to refresh its row; re-run `python -m src.report` to rebuild the table._
