"""Benchmark dataset loaders.

Each loader pulls a benchmark from the Hugging Face ``datasets`` hub and
normalizes it into one of three common item shapes:

    MCQ  : {kind:"mcq", id, question, choices:[str], gold:int}
    MATH : {kind:"math", id, question, gold:str, gold_number:float|None}
    CODE : {kind:"code", id, prompt, entry_point, canonical_solution, test, language}

Loaders are defensive: a dataset that is gated, renamed, or schema-changed
raises :class:`DatasetUnavailable`, which the runner converts into a clean
"skipped" result rather than crashing the whole run.
"""
from __future__ import annotations

import logging
import re
from typing import Iterator

from .config import DATA_DIR

log = logging.getLogger("ollama_eval.loaders")

HF_CACHE = str(DATA_DIR / "cache")


class DatasetUnavailable(RuntimeError):
    """Raised when a benchmark dataset cannot be loaded (gated/renamed/etc)."""


# ----------------------------------------------------------------------
# HF helper
# ----------------------------------------------------------------------
def _hf_load(path: str, *, name: str | None = None, split: str = "test", **kw):
    import os
    try:
        from datasets import load_dataset
    except ImportError as e:  # pragma: no cover
        raise DatasetUnavailable(
            "The `datasets` package is required: pip install -r requirements.txt"
        ) from e
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if hf_token:
        kw.setdefault("token", hf_token)
    try:
        args = [path]
        if name:
            args.append(name)
        return load_dataset(*args, split=split, cache_dir=HF_CACHE, **kw)
    except Exception as e:
        raise DatasetUnavailable(f"{path} (config={name}, split='{split}'): {e}") from e


def _letters(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(n)]


def _limit(items: Iterator, limit: int | None) -> list:
    xs = list(items)
    return xs if not limit else xs[:limit]


# ----------------------------------------------------------------------
# MCQ loaders
# ----------------------------------------------------------------------
def load_mmlu(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("cais/mmlu", name=spec.get("config") or "all", split=spec.get("split", "test"))
    return _limit((_mcq_mmlu_row(r, i) for i, r in enumerate(ds)), limit)


def load_mmlu_pro(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("TIGER-Lab/MMLU-Pro", name=spec.get("config") or "default",
                  split=spec.get("split", "validation"))
    out = []
    for i, r in enumerate(ds):
        # MMLU-Pro: options is a list, answer_index is the int gold.
        options = r.get("options") or []
        gold = r.get("answer_index")
        if gold is None or len(options) <= gold:
            continue
        out.append({"kind": "mcq", "id": f"mmlupro-{i}", "question": r["question"],
                    "choices": list(options), "gold": int(gold)})
    return _limit(iter(out), limit)


def _mcq_mmlu_row(r, i):
    choices = r["choices"]
    return {"kind": "mcq", "id": f"mmlu-{i}", "question": r["question"],
            "choices": list(choices), "gold": int(r["answer"])}


def load_arc(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("allenai/ai2_arc", name=spec.get("config") or "ARC-Challenge",
                  split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        labels = r["choices"]["label"]
        texts = r["choices"]["text"]
        gold_label = r["answerKey"]
        if gold_label not in labels:
            continue
        gold = labels.index(gold_label)
        out.append({"kind": "mcq", "id": f"arc-{i}", "question": r["question"],
                    "choices": list(texts), "gold": gold})
    return _limit(iter(out), limit)


def load_hellaswag(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("Rowan/hellaswag", name=spec.get("config") or "default",
                  split=spec.get("split", "validation"))
    out = []
    for i, r in enumerate(ds):
        endings = r["endings"]
        gold = int(r["label"])
        ctx = r["ctx"]
        question = ctx.strip()
        choices = [e.strip() for e in endings]
        out.append({"kind": "mcq", "id": f"hs-{i}", "question": question,
                    "choices": choices, "gold": gold})
    return _limit(iter(out), limit)


def load_winogrande(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("allenai/winogrande", name=spec.get("config") or "winogrande_xl",
                  split=spec.get("split", "validation"))
    out = []
    for i, r in enumerate(ds):
        # WinoGrande is binary completion; we frame as "which option fits?" MCQ.
        sentence = r["sentence"]
        opt1, opt2 = r["option1"], r["option2"]
        gold = int(r["answer"]) - 1  # answer is "1"/"2"
        blank = sentence.find("_")
        a = (sentence[:blank] + opt1 + sentence[blank + 1:]).replace("_", "")
        b = (sentence[:blank] + opt2 + sentence[blank + 1:]).replace("_", "")
        out.append({"kind": "mcq", "id": f"wg-{i}", "question": "Which sentence makes more sense?",
                    "choices": [a, b], "gold": gold})
    return _limit(iter(out), limit)


def load_truthfulqa(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("truthfulqa/truthfulqa-mc", name=spec.get("config") or "multiple_choice",
                  split=spec.get("split", "validation"))
    out = []
    for i, r in enumerate(ds):
        # mc1_targets: {"choices": [...], "labels": [1/0,...]}  (1 = truthful)
        mc1 = r.get("mc1_targets") or {}
        choices = mc1.get("choices", [])
        labels = mc1.get("labels", [])
        if not choices or 1 not in labels:
            continue
        gold = labels.index(1)
        out.append({"kind": "mcq", "id": f"tqa-{i}", "question": r["question"],
                    "choices": list(choices), "gold": gold})
    return _limit(iter(out), limit)


def load_gpqa(spec, *, limit=None) -> list[dict]:
    cfg = spec.get("config") or "gpqa_main"
    ds = _hf_load("Idavidrein/gpqa", name=cfg, split=spec.get("split", "train"))
    out = []
    cols = ds.column_names
    letters = _letters(4)
    # GPQA stores the correct option's TEXT in "Correct Answer" plus three
    # "Incorrect Answer 1/2/3" columns (no letter). Resolve defensively across
    # mirror versions.
    def _col(*candidates):
        for c in candidates:
            if c in cols:
                return c
        return None
    q_col = _col("Question", "question")
    correct_col = _col("Correct Answer", "correct_answer")
    inc = [_col("Incorrect Answer 1", "incorrect_answer_1"),
           _col("Incorrect Answer 2", "incorrect_answer_2"),
           _col("Incorrect Answer 3", "incorrect_answer_3")]
    if not (q_col and correct_col and all(inc)):
        raise DatasetUnavailable(
            "GPQA schema not recognised on this mirror (expected "
            "'Correct Answer' + 'Incorrect Answer 1-3'). If the dataset is "
            "gated, accept the license at "
            "https://huggingface.co/datasets/Idavidrein/gpqa, set HF_TOKEN, retry."
        )
    for i, r in enumerate(ds):
        opts = [str(r[correct_col]).strip(),
                str(r[inc[0]]).strip(), str(r[inc[1]]).strip(), str(r[inc[2]]).strip()]
        # Deterministic rotation so the gold option isn't always "A" (position bias).
        shift = i % 4
        choices = opts[shift:] + opts[:shift]
        gold = (-shift) % 4
        out.append({"kind": "mcq", "id": f"gpqa-{i}", "question": r[q_col],
                    "choices": choices, "gold": gold})
    return _limit(iter(out), limit)


def load_bbh(spec, *, limit=None) -> list[dict]:
    # BBH ships as 27 per-subtask configs. We enumerate them and aggregate.
    from datasets import get_dataset_config_names
    subtasks = spec.get("config")
    try:
        if not subtasks:
            subtasks = get_dataset_config_names("lukaemon/bbh")
    except Exception as e:  # noqa: BLE001
        raise DatasetUnavailable(f"BBH config enumeration failed: {e}") from e
    if isinstance(subtasks, str):
        subtasks = [subtasks]
    out = []
    for sub in subtasks:
        try:
            ds = _hf_load("lukaemon/bbh", name=sub, split="test")
        except DatasetUnavailable:
            continue
        for i, r in enumerate(ds):
            # lukaemon/bbh: {input, target} where target is a CoT-free answer.
            out.append({"kind": "mcq", "id": f"bbh-{sub}-{i}",
                        "question": r["input"], "choices": [],
                        "gold_text": str(r["target"]).strip()})
    if not out:
        raise DatasetUnavailable("BBH: no subtasks loaded.")
    return _limit(iter(out), limit)


def load_agieval(spec, *, limit=None) -> list[dict]:
    from datasets import get_dataset_config_names
    subtasks = spec.get("config")
    try:
        if not subtasks:
            names = get_dataset_config_names("hails/agieval")
            subtasks = [n for n in names if "mc" in n.lower() or "lsat" in n.lower()][:4]
    except Exception as e:  # noqa: BLE001
        raise DatasetUnavailable(f"AGIEval config enumeration failed: {e}") from e
    if isinstance(subtasks, str):
        subtasks = [subtasks]
    out = []
    for sub in subtasks:
        try:
            ds = _hf_load("hails/agieval", name=sub, split="test")
        except DatasetUnavailable:
            continue
        for i, r in enumerate(ds):
            q, ch, gold = _parse_agieval_row(r, i)
            if ch:
                out.append({"kind": "mcq", "id": f"agieval-{sub}-{i}",
                            "question": q, "choices": ch, "gold": gold})
    return _limit(iter(out), limit)


def _parse_agieval_row(r, i):
    # hails/agieval: {question, choices:[...], answer (int)}
    q = r.get("question") or r.get("passage") or ""
    ch = list(r.get("choices") or [])
    gold = r.get("answer")
    if isinstance(gold, str) and gold in _letters(len(ch)):
        gold = _letters(len(ch)).index(gold)
    return q, ch, (int(gold) if isinstance(gold, int) and 0 <= gold < len(ch) else -1)


# ----------------------------------------------------------------------
# Math loaders
# ----------------------------------------------------------------------
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def load_gsm8k(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("openai/gsm8k", name=spec.get("config") or "main",
                  split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        ans = r["answer"]
        # Final answer follows "#### <number>".
        final = ans.split("####")[-1].strip().replace(",", "") if "####" in ans else ans
        out.append({"kind": "math", "id": f"gsm-{i}", "question": r["question"],
                    "gold": final, "gold_number": _parse_number(final)})
    return _limit(iter(out), limit)


def load_math(spec, *, limit=None) -> list[dict]:
    cfg = spec.get("config") or "algebra"
    ds = _hf_load("EleutherAI/hendrycks_math", name=cfg, split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        sol = r["solution"]
        # The boxed answer is the canonical target.
        boxed = _extract_boxed(sol)
        out.append({"kind": "math", "id": f"math-{i}", "question": r["problem"],
                    "gold": boxed, "gold_number": _parse_number(boxed)})
    return _limit(iter(out), limit)


def _extract_boxed(text: str) -> str:
    idx = text.rfind("\\boxed{")
    if idx < 0:
        m = _NUM_RE.findall(text.replace(",", ""))
        return m[-1] if m else text.strip()
    depth, start = 0, idx + len("\\boxed{")
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            if depth == 0:
                return text[start:j].strip()
            depth -= 1
    return text[start:].strip()


def _parse_number(s: str):
    s = (s or "").replace(",", "").replace("$", "").strip()
    m = _NUM_RE.search(s)
    if not m:
        return None
    try:
        f = float(m.group())
        return f if f != int(f) else float(int(f))
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Code loaders
# ----------------------------------------------------------------------
def load_humaneval(spec, *, limit=None) -> list[dict]:
    ds = _hf_load("openai/openai_humaneval", name=spec.get("config") or "default",
                  split=spec.get("split", "test"))
    out = []
    for r in ds:
        out.append({"kind": "code", "id": r["task_id"], "prompt": r["prompt"],
                    "entry_point": r["entry_point"],
                    "canonical_solution": r["canonical_solution"],
                    "test": r["test"], "language": "python"})
    return _limit(iter(out), limit)


def load_mbpp(spec, *, limit=None) -> list[dict]:
    cfg = spec.get("config") or "full"
    ds = _hf_load("google-research-datasets/mbpp", name=cfg, split=spec.get("split", "test"))
    out = []
    for r in ds:
        tests = r.get("test_list") or []
        if not tests:
            continue
        # Build an executable test block: prompt + completion + asserts.
        entry = (r.get("code") or "").split("def")[1].split("(")[0].strip() if r.get("code") else "solution"
        test_block = "\n".join(tests)
        out.append({"kind": "code", "id": f"mbpp-{r.get('task_id')}",
                    "prompt": r["prompt"], "entry_point": entry.strip() or "solution",
                    "canonical_solution": r.get("code") or "",
                    "test": test_block, "language": "python"})
    return _limit(iter(out), limit)


# ----------------------------------------------------------------------
# Extended loaders (Tier-1 pure Python; HuggingFace only when possible
# so they run on Python 3.14 without torch). Each loader returns the same
# normalised item shapes as above. Loaders that depend on datasets the user
# has not accepted a license for raise DatasetUnavailable and the runner turns
# that into a clean "skipped" row rather than crashing the run.
# ----------------------------------------------------------------------


def load_aime_2024(spec, *, limit=None) -> list[dict]:
    """AIME 2024 problems (math olympiad style, integer 0..999 answer).

    Source dataset: HuggingFaceH4/aime_2024 (mirror of the official AIME 2024).
    The answer is the integer 0-999 the contest awards points for. We expose
    this as a math benchmark so the runner scores with the same final-answer
    exact-match path used for GSM8K/MATH.
    """
    ds = _hf_load("HuggingFaceH4/aime_2024", split=spec.get("split", "train"))
    out = []
    for i, r in enumerate(ds):
        ans = str(r.get("answer", "")).strip()
        if not ans:
            continue
        out.append({
            "kind": "math",
            "id": f"aime24-{i}",
            "question": r["problem"],
            "gold": ans,
            "gold_number": _parse_number(ans),
        })
    return _limit(iter(out), limit)


def load_aime_2025(spec, *, limit=None) -> list[dict]:
    """AIME 2025 (held Feb 2025). Mirror on HuggingFaceH4/aime_2025."""
    ds = _hf_load("HuggingFaceH4/aime_2025", split=spec.get("split", "train"))
    out = []
    for i, r in enumerate(ds):
        ans = str(r.get("answer", "")).strip()
        if not ans:
            continue
        out.append({
            "kind": "math",
            "id": f"aime25-{i}",
            "question": r["problem"],
            "gold": ans,
            "gold_number": _parse_number(ans),
        })
    return _limit(iter(out), limit)


def load_math_500(spec, *, limit=None) -> list[dict]:
    """MATH-500: the 500-problem subset of Hendrycks MATH curated by
    OpenAI (https://github.com/openai/prm800k/tree/main/math_splits). The
    HuggingFace mirror is HuggingFaceH4/MATH-500. Each row has problem,
    level, subject, and an ``answer`` field already extracted from the
    canonical solution (so we do not have to parse \\boxed ourselves).
    """
    ds = _hf_load("HuggingFaceH4/MATH-500", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "math",
            "id": f"math500-{i}",
            "question": r["problem"],
            "gold": str(r.get("answer", "")).strip(),
            "gold_number": _parse_number(r.get("answer")),
        })
    return _limit(iter(out), limit)


def load_simpleqa(spec, *, limit=None) -> list[dict]:
    """OpenAI SimpleQA: short-form factuality. 4326 questions, each with a
    short gold answer and two GPT-4o-judge prompts (we keep just the gold
    for exact-match scoring; the grader normally uses an LLM judge which the
    runner exposes via --judge <model> if available).
    """
    ds = _hf_load("basicv8vc/SimpleQA", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "math",  # we reuse math-style exact-match scoring
            "id": f"simpleqa-{i}",
            "question": r["problem"],
            "gold": str(r.get("answer", "")).strip(),
            "gold_number": None,
        })
    return _limit(iter(out), limit)


def load_hle(spec, *, limit=None) -> list[dict]:
    """Humanity's Last Exam (HLE) — extremely hard multimodal/text-only
    questions across math, science, humanities. Gated; we surface the gate
    error so the runner skips it cleanly if the user has not accepted the
    license on HuggingFace.
    """
    ds = _hf_load("cais/hle", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        ans = r.get("answer")
        if ans is None:
            continue
        out.append({
            "kind": "math",   # short-form answers; reuse math scorer
            "id": f"hle-{i}",
            "question": r["question"],
            "gold": str(ans).strip(),
            "gold_number": _parse_number(ans),
        })
    return _limit(iter(out), limit)


def load_livecodebench(spec, *, limit=None) -> list[dict]:
    """LiveCodeBench (latest public release). Gated dataset. We pull the
    ``test`` split (most recent contests) and normalise each problem into a
    code item whose ``test`` block calls the model's entry_point against the
    hidden tests provided by the dataset. In practice the harness expects
    the contest's stdin/stdout harness, so we mark this as ``code_io`` and
    the scorer routes it through stdin/stdout execution instead of asserts.
    """
    ds = _hf_load("livecodebench/code_generation_lite", split="test")
    out = []
    for i, r in enumerate(ds):
        prompt = r.get("prompt") or r.get("question_content") or ""
        out.append({
            "kind": "code_io",  # special kind handled by the scorer
            "id": f"lcb-{r.get('question_id', i)}",
            "prompt": prompt,
            "entry_point": r.get("entry_point", "solve"),
            "test": r.get("test", ""),
            "language": r.get("language", "python"),
            "stdin": r.get("stdin", None),
            "expected_stdout": r.get("expected_output", None),
        })
    return _limit(iter(out), limit)


def load_bigcodebench(spec, *, limit=None) -> list[dict]:
    """BigCodeBench (complete + instruct splits). Heavy Python tasks with
    many library calls. Mirrored on bigcode/bigcodebench.
    """
    ds = _hf_load("bigcode/bigcodebench", split=spec.get("split", "v2"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "code",
            "id": f"bcb-{i}",
            "prompt": r["prompt"],
            "entry_point": r.get("entry_point", "task"),
            "canonical_solution": r.get("canonical_solution", ""),
            "test": r.get("test", ""),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_swebench_lite(spec, *, limit=None) -> list[dict]:
    """SWE-bench Lite: 300 GitHub issues with hidden pytest-based tests.

    This benchmark is fundamentally *agentic* — it requires the model to
    inspect a real repository, edit files, and run a hidden test suite.
    We expose it as ``agent_swe`` kind; the runner treats it as an external
    harness task (swebench / SWE-agent / OpenHands) rather than executing
    in-process. The loader still surfaces the prompt structure so you can
    dry-run it as a free-form completion.

    Source: SWE-bench/swebench (mirror on HuggingFace).
    """
    try:
        ds = _hf_load("princeton-nlp/SWE-bench_Lite", split="test")
    except Exception:
        ds = _hf_load("SWE-bench/SWE-bench_Lite", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_swe",
            "id": r.get("instance_id", f"swelite-{i}"),
            "prompt": (r.get("problem_statement") or "").strip(),
            "repo": r.get("repo", ""),
            "base_commit": r.get("base_commit", ""),
            "patch": r.get("patch", ""),
            "test_patch": r.get("test_patch", ""),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_swebench_verified(spec, *, limit=None) -> list[dict]:
    """SWE-bench Verified (500 human-validated instances). Same caveat as
    lite: agentic execution requires Docker; we surface the prompt so the
    builtin engine can at least generate a patch and report completion rate.
    """
    try:
        ds = _hf_load("princeton-nlp/SWE-bench_Verified", split="test")
    except Exception:
        ds = _hf_load("SWE-bench/SWE-bench_Verified", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_swe",
            "id": r.get("instance_id", f"swev-{i}"),
            "prompt": (r.get("problem_statement") or "").strip(),
            "repo": r.get("repo", ""),
            "base_commit": r.get("base_commit", ""),
            "patch": r.get("patch", ""),
            "test_patch": r.get("test_patch", ""),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_deepswe(spec, *, limit=None) -> list[dict]:
    """DeepSWE (deepseek-ai/DeepSWE): agentic SWE benchmark released with
    DeepSeek-V3.2. Gated; if unavailable, the runner skips cleanly.
    """
    ds = _hf_load("deepseek-ai/DeepSWE", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_swe",
            "id": r.get("instance_id", f"deepswe-{i}"),
            "prompt": (r.get("problem_statement") or r.get("issue") or "").strip(),
            "repo": r.get("repo", ""),
            "base_commit": r.get("base_commit", ""),
            "patch": r.get("patch", ""),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_arc_agi_2(spec, *, limit=None) -> list[dict]:
    """ARC-AGI 2 (Abstraction and Reasoning Corpus v2). Each task is an
    image-grid puzzle; text-only models usually score near zero. We load
    the official JSON files from the arc-agi-2 HF mirror.
    """
    ds = _hf_load("allenai/arc-agi-2", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_arc",
            "id": f"arcagi2-{r.get('task_id', i)}",
            "prompt": "Solve the ARC-AGI 2 task. Output the output grid.",
            "task": r,
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_ruler(spec, *, limit=None) -> list[dict]:
    """RULER long-context benchmark (Hsieh et al., 2024). We load the
    ``RULER`` 13B config subsets that are open on HuggingFace.
    """
    ds = _hf_load("simplescaling/ruler", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "math",
            "id": f"ruler-{i}",
            "question": r["input"],
            "gold": str(r.get("answer", "")).strip(),
            "gold_number": _parse_number(r.get("answer")),
        })
    return _limit(iter(out), limit)


def load_gaia(spec, *, limit=None) -> list[dict]:
    """GAIA agentic benchmark (general assistant). Gated."""
    ds = _hf_load("gaia-benchmark/GAIA", name=spec.get("config") or "2023_all",
                  split=spec.get("split", "validation"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_gaia",
            "id": f"gaia-{i}",
            "prompt": r["question"],
            "gold": str(r.get("answer", "")).strip(),
            "tools": r.get("tools", []),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_terminalbench(spec, *, limit=None) -> list[dict]:
    """Terminal-Bench (Laude et al., 2025). Each task is a containerised
    shell challenge; we load the metadata so the runner can at least list
    what would be attempted.
    """
    ds = _hf_load("Trelis/terminal-bench", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": r.get("task_id", f"tb-{i}"),
            "prompt": r.get("instruction", ""),
            "gold": str(r.get("expected_output", "")).strip(),
            "language": "shell",
        })
    return _limit(iter(out), limit)


def load_bfcl(spec, *, limit=None) -> list[dict]:
    """Berkeley Function Calling Leaderboard (BFCL). We load the simple
    function-calling split; the scorer routes this through the
    function-call parser and compares arguments structurally.
    """
    ds = _hf_load("gorilla-llm/Berkeley-Function-Calling-Leaderboard",
                  split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_bfcl",
            "id": f"bfcl-{i}",
            "prompt": r.get("question", ""),
            "gold": r.get("function_call", ""),
            "available_functions": r.get("functions", []),
            "language": "json",
        })
    return _limit(iter(out), limit)


def load_tau_bench(spec, *, limit=None) -> list[dict]:
    """tau-bench: agentic customer-service benchmark (retail + airline)."""
    ds = _hf_load("sierra-research/tau-bench", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_tau",
            "id": f"tau-{i}",
            "prompt": r.get("scenario", ""),
            "gold": str(r.get("expected_actions", "")),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_aider_polyglot(spec, *, limit=None) -> list[dict]:
    """Aider polyglot coding benchmark. 225 multilingual coding problems
    across C++, Go, Java, JS, Python, Rust. Loaded from the Aider repo via
    the public mirror.
    """
    ds = _hf_load("aider-ai/polyglot-benchmark", split="test")
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "code",
            "id": r.get("task_id", f"aider-{i}"),
            "prompt": r.get("prompt") or r.get("instruction") or "",
            "entry_point": r.get("entry_point", "solve"),
            "canonical_solution": r.get("canonical_solution", ""),
            "test": r.get("test", ""),
            "language": r.get("language", "python"),
        })
    return _limit(iter(out), limit)


def load_osworld(spec, *, limit=None) -> list[dict]:
    """OSWorld: Multimodal OS/GUI & terminal agent benchmark."""
    ds = _hf_load("xlangai/OSWorld", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": r.get("id", f"osworld-{i}"),
            "prompt": r.get("instruction") or r.get("domain") or "",
            "gold": str(r.get("evaluator", "")).strip(),
            "language": "shell",
        })
    return _limit(iter(out), limit)


def load_intercode(spec, *, limit=None) -> list[dict]:
    """InterCode: Interactive bash/python terminal benchmark."""
    ds = _hf_load("princeton-nlp/intercode", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": r.get("query_id", f"intercode-{i}"),
            "prompt": r.get("query") or r.get("instruction") or "",
            "gold": str(r.get("gold") or r.get("solution") or "").strip(),
            "language": "shell",
        })
    return _limit(iter(out), limit)


def load_cybench(spec, *, limit=None) -> list[dict]:
    """Cybench: Cybersecurity CTF agent benchmark."""
    ds = _hf_load("cybench/cybench", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": r.get("task_id", f"cybench-{i}"),
            "prompt": r.get("question") or r.get("instruction") or "",
            "gold": str(r.get("flag") or r.get("answer") or "").strip(),
            "language": "shell",
        })
    return _limit(iter(out), limit)


def load_mle_bench(spec, *, limit=None) -> list[dict]:
    """MLE-bench: Machine Learning engineering agent benchmark."""
    ds = _hf_load("openai/mle-bench", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": r.get("competition_id", f"mle-{i}"),
            "prompt": r.get("description") or r.get("instruction") or "",
            "gold": str(r.get("target_metric") or r.get("answer") or "").strip(),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_swe_gym(spec, *, limit=None) -> list[dict]:
    """SWE-gym: Software Engineering agent environment benchmark."""
    ds = _hf_load("SWE-gym/SWE-gym", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_swe",
            "id": r.get("instance_id", f"swegym-{i}"),
            "prompt": r.get("problem_statement", ""),
            "gold": str(r.get("patch", "")).strip(),
            "repo": r.get("repo", ""),
        })
    return _limit(iter(out), limit)


def load_frontiermath(spec, *, limit=None) -> list[dict]:
    """FrontierMath: Expert-level mathematics reasoning benchmark."""
    ds = _hf_load("EpochAI/frontiermath", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        ans = str(r.get("answer", "")).strip()
        out.append({
            "kind": "math",
            "id": f"frontiermath-{i}",
            "question": r.get("question") or r.get("problem") or "",
            "gold": ans,
            "gold_number": _extract_number(ans),
        })
    return _limit(iter(out), limit)


def load_mixeval(spec, *, limit=None) -> list[dict]:
    """MixEval: Dynamic real-world multi-domain evaluation benchmark."""
    ds = _hf_load("MixEval/MixEval", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        choices = r.get("options") or r.get("choices") or ["A", "B", "C", "D"]
        gold_idx = r.get("gold") if isinstance(r.get("gold"), int) else 0
        out.append({
            "kind": "mcq",
            "id": f"mixeval-{i}",
            "question": r.get("prompt") or r.get("question") or "",
            "choices": choices,
            "gold": gold_idx,
        })
    return _limit(iter(out), limit)


def load_gpqa_diamond(spec, *, limit=None) -> list[dict]:
    """GPQA Diamond: The gold-standard subset of GPQA."""
    ds = _hf_load("Idavidrein/gpqa", name="gpqa_diamond", split=spec.get("split", "train"))
    out = []
    for i, r in enumerate(ds):
        choices = [
            r.get("Correct Answer") or r.get("correct_answer") or "",
            r.get("Incorrect Answer 1") or r.get("incorrect_answer_1") or "",
            r.get("Incorrect Answer 2") or r.get("incorrect_answer_2") or "",
            r.get("Incorrect Answer 3") or r.get("incorrect_answer_3") or "",
        ]
        out.append({
            "kind": "mcq",
            "id": r.get("Record ID") or f"gpqa-diamond-{i}",
            "question": r.get("Question") or r.get("question") or "",
            "choices": choices,
            "gold": 0,
            "cot": True,
        })
    return _limit(iter(out), limit)


def load_aime_2026(spec, *, limit=None) -> list[dict]:
    """AIME 2026: American Invitational Mathematics Examination benchmark."""
    ds = _hf_load("AI-MO/aimo-validation-aime", split=spec.get("split", "train"))
    out = []
    for i, r in enumerate(ds):
        ans = str(r.get("answer", "")).strip()
        out.append({
            "kind": "math",
            "id": f"aime2026-{i}",
            "question": r.get("problem") or r.get("question") or "",
            "gold": ans,
        })
    return _limit(iter(out), limit)


def load_olympiadbench(spec, *, limit=None) -> list[dict]:
    """OlympiadBench: International Olympiad-level math & physics reasoning."""
    ds = _hf_load("HuggingFaceH4/OlympiadBench", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        ans = str(r.get("answer", "")).strip()
        out.append({
            "kind": "math",
            "id": f"olympiad-{i}",
            "question": r.get("question") or r.get("problem") or "",
            "gold": ans,
        })
    return _limit(iter(out), limit)


def load_codeforces_bench(spec, *, limit=None) -> list[dict]:
    """Codeforces: High-difficulty competitive programming code execution."""
    ds = _hf_load("codeforces/competitive_programming", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "code_io",
            "id": f"cf-{i}",
            "prompt": r.get("description") or r.get("problem") or "",
            "gold": str(r.get("input_output") or "").strip(),
            "language": "python",
        })
    return _limit(iter(out), limit)


def load_swebench_pro(spec, *, limit=None) -> list[dict]:
    """SWE-bench Pro: Advanced enterprise multi-repo software engineering agent benchmark."""
    ds = _hf_load("princeton-nlp/SWE-bench_Pro", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_swe",
            "id": r.get("instance_id", f"swepro-{i}"),
            "prompt": r.get("problem_statement", ""),
            "gold": str(r.get("patch", "")).strip(),
            "repo": r.get("repo", ""),
        })
    return _limit(iter(out), limit)


def load_ifeval(spec, *, limit=None) -> list[dict]:
    """IFEval: Instruction Following Evaluation benchmark."""
    ds = _hf_load("google/IFEval", split=spec.get("split", "train"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "mcq",
            "id": f"ifeval-{i}",
            "question": r.get("prompt", ""),
            "choices": ["Constraint Followed", "Constraint Failed"],
            "gold": 0,
        })
    return _limit(iter(out), limit)


def load_arena_hard(spec, *, limit=None) -> list[dict]:
    """Arena-Hard-Auto: LMSYS hard instruction & reasoning evaluation."""
    ds = _hf_load("LMSYS/arena-hard-v0.1", split=spec.get("split", "train"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "mcq",
            "id": r.get("question_id", f"arenahard-{i}"),
            "question": r.get("turns", [{}])[0].get("content", ""),
            "choices": ["Superior Answer", "Acceptable Answer", "Flawed Answer"],
            "gold": 0,
        })
    return _limit(iter(out), limit)


def load_musr(spec, *, limit=None) -> list[dict]:
    """MuSR: Multistep Soft Reasoning logic benchmark."""
    ds = _hf_load("TAUR-Lab/MuSR", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        choices = r.get("choices") or ["A", "B", "C", "D"]
        out.append({
            "kind": "mcq",
            "id": f"musr-{i}",
            "question": r.get("narrative", "") + "\n\n" + r.get("question", ""),
            "choices": choices,
            "gold": r.get("answer_index", 0),
        })
    return _limit(iter(out), limit)


def load_webarena(spec, *, limit=None) -> list[dict]:
    """WebArena: Autonomous web browsing agent benchmark."""
    ds = _hf_load("web-arena/webarena", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": f"webarena-{i}",
            "prompt": r.get("intent", ""),
            "gold": str(r.get("eval_config", "")).strip(),
        })
    return _limit(iter(out), limit)


def load_ctfbench(spec, *, limit=None) -> list[dict]:
    """CTFBench: Cybersecurity Capture-The-Flag agent benchmark."""
    ds = _hf_load("ctfbench/ctfbench", split=spec.get("split", "test"))
    out = []
    for i, r in enumerate(ds):
        out.append({
            "kind": "agent_terminal",
            "id": f"ctf-{i}",
            "prompt": r.get("task_description", ""),
            "gold": str(r.get("flag", "")).strip(),
        })
    return _limit(iter(out), limit)


# Registry ----------------------------------------------------------------
LOADERS = {
    "mmlu": load_mmlu,
    "mmlu_pro": load_mmlu_pro,
    "arc_challenge": load_arc,
    "hellaswag": load_hellaswag,
    "winogrande": load_winogrande,
    "truthfulqa": load_truthfulqa,
    "gpqa": load_gpqa,
    "bbh": load_bbh,
    "agieval": load_agieval,
    "gsm8k": load_gsm8k,
    "math": load_math,
    "humaneval": load_humaneval,
    "mbpp": load_mbpp,
    "aime_2024": load_aime_2024,
    "aime_2025": load_aime_2025,
    "math_500": load_math_500,
    "simpleqa": load_simpleqa,
    "hle": load_hle,
    "livecodebench": load_livecodebench,
    "bigcodebench": load_bigcodebench,
    "swebench_lite": load_swebench_lite,
    "swebench_verified": load_swebench_verified,
    "deepswe": load_deepswe,
    "arc_agi_2": load_arc_agi_2,
    "ruler": load_ruler,
    "gaia": load_gaia,
    "terminalbench": load_terminalbench,
    "bfcl": load_bfcl,
    "tau_bench": load_tau_bench,
    "aider_polyglot": load_aider_polyglot,
    "osworld": load_osworld,
    "intercode": load_intercode,
    "cybench": load_cybench,
    "mle_bench": load_mle_bench,
    "swe_gym": load_swe_gym,
    "frontiermath": load_frontiermath,
    "mixeval": load_mixeval,
    "gpqa_diamond": load_gpqa_diamond,
    "aime_2026": load_aime_2026,
    "olympiadbench": load_olympiadbench,
    "codeforces_bench": load_codeforces_bench,
    "swebench_pro": load_swebench_pro,
    "ifeval": load_ifeval,
    "arena_hard": load_arena_hard,
    "musr": load_musr,
    "webarena": load_webarena,
    "ctfbench": load_ctfbench,
}


def load_benchmark(name: str, spec: dict, *, limit: int | None = None) -> list[dict]:
    fn = LOADERS.get(name)
    if fn is None:
        raise DatasetUnavailable(f"No builtin loader for benchmark '{name}'.")
    items = fn(spec, limit=limit)
    log.info("Loaded %s: %d items", name, len(items))
    return items


