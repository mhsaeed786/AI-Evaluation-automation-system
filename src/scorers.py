"""Scoring functions for the builtin engine.

Three families cover the bulk of public benchmarks:

  * ``score_mcq``  — multiple choice (MMLU, GPQA, ARC, HellaSwag, TruthfulQA,
    BBH, AGIEval). Scored by next-token logprob of the answer letter when the
    endpoint exposes ``top_logprobs`` (canonical loglikelihood path), with a
    generate-and-parse fallback. Chain-of-thought benchmarks force the generate
    path.
  * ``score_math`` — free-form math (GSM8K, MATH). Final answer is extracted
    (``\\boxed{}``, an ``Answer:`` line, or the last number) and compared to the
    gold number with numeric tolerance.
  * ``score_code`` — executable code (HumanEval, MBPP). The completion is
    appended to the prompt + hidden tests and run in a subprocess sandbox;
    pass@1 = exit 0.

The extended scorers below (LiveCodeBench stdin/stdout, SWE-bench/DeepSWE diff
parsing, ARC-AGI-2 grid JSON, BFCL function-calling, terminal-bench, GAIA) are
**baseline / parse-only** integrations — they check that the model emits a
well-formed artifact, not that it is genuinely correct against the full harness.
Treat their numbers as lower-bound sanity checks, not comparable pass rates.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

# Wall-clock cap for subprocess-executed model code / shell commands.
CODE_TIMEOUT = 20


# ======================================================================
# Shared helpers
# ======================================================================
def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if present, preserving indentation.

    HumanEval/MBPP prompts end mid-function, so the completion's leading
    indentation is semantically required — stripping it would turn a correct
    ``    return a + b`` into a top-level ``return`` and raise IndentationError
    on every item. We therefore strip only surrounding blank lines / trailing
    whitespace and the ``` markers, never the leading column of the code.
    """
    t = text or ""
    m = re.match(r"\s*```[a-zA-Z0-9]*\n?", t)          # optional leading fence line
    if m:
        t = t[m.end():]
        t = re.sub(r"\n?```\s*$", "", t)              # closing fence
    return t.lstrip("\n").rstrip()


def _letters(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(max(1, n))]


# ======================================================================
# MCQ
# ======================================================================
def _format_mcq(item: dict, answer_letter: str | None = None) -> str:
    letters = _letters(len(item["choices"]))
    lines = [f"Question: {item['question']}"]
    for L, choice in zip(letters, item["choices"]):
        lines.append(f"{L}) {choice}")
    if answer_letter:
        lines.append(f"Answer: {answer_letter}")
    else:
        lines.append("Answer with the letter of the best choice.")
    return "\n".join(lines)


def _parse_letter(text: str, letters: list[str]) -> str | None:
    """Extract an answer letter from a free-form (CoT) response."""
    t = text or ""
    # Pattern 1: "Answer: X" or "answer is X" (most explicit)
    m = re.search(r"answer(?:\s+is)?[:\s]*\(?([A-Za-z])\)?", t, re.IGNORECASE)
    if m and m.group(1).upper() in letters:
        return m.group(1).upper()
    # Pattern 2: "The answer is (X)" or "I choose X"
    m = re.search(r"(?:the answer is|i choose|option)\s*\(?([A-Za-z])\)?", t, re.IGNORECASE)
    if m and m.group(1).upper() in letters:
        return m.group(1).upper()
    # Pattern 3: last standalone letter in the text (CoT conclusion)
    found = re.findall(r"\b([A-Za-z])\b", t)
    for ch in reversed(found):
        if ch.upper() in letters:
            return ch.upper()
    return None


def _mcq_messages(item: dict, shots: list[dict]) -> list[dict]:
    parts = []
    for s in shots:
        sletters = _letters(len(s["choices"]))
        parts.append(_format_mcq(s, sletters[s["gold"]]))
    parts.append(_format_mcq(item))
    text = "\n\n".join(parts) + "\nAnswer:"
    return [{"role": "user", "content": text}]


def _mcq_generate_messages(item: dict, shots: list[dict]) -> list[dict]:
    """Messages for the generate-and-parse fallback path. Uses a system
    message to force a letter answer, which reasoning models need."""
    parts = []
    for s in shots:
        sletters = _letters(len(s["choices"]))
        parts.append(_format_mcq(s, sletters[s["gold"]]))
    parts.append(_format_mcq(item))
    text = "\n\n".join(parts)
    return [
        {"role": "system", "content": "Answer the multiple-choice question. "
         "Output ONLY the letter of the correct answer (e.g. A, B, C, or D). "
         "Do not explain."},
        {"role": "user", "content": text},
    ]


def score_mcq(client, model, item, *, shots, cot, temperature, max_tokens) -> dict:
    """Score one multiple-choice item. Returns {correct, predicted, method}."""
    letters = _letters(len(item["choices"]))
    gold = item.get("gold")
    gold_letter = letters[gold] if isinstance(gold, int) and 0 <= gold < len(letters) else None

    if cot:
        msgs = [
            {"role": "system", "content":
             "Answer the multiple-choice question. Think step by step, then end "
             "with 'Answer: <letter>'."},
            {"role": "user", "content": _format_mcq(item)},
        ]
        text = client.chat_text(model=model, messages=msgs,
                                temperature=temperature, max_tokens=max_tokens)
        pred = _parse_letter(text, letters)
        return {"correct": pred == gold_letter, "predicted": pred,
                "method": "generate", "raw": text}

    msgs = _mcq_messages(item, shots)
    scores = client.answer_letter_logprob(model=model, prompt_messages=msgs, letters=letters)
    if scores.present and scores.scores:
        pred = scores.argmax_letter()
        return {"correct": pred == gold_letter, "predicted": pred, "method": "logprob"}

    # Endpoint gave no usable top_logprobs — fall back to generate + parse.
    # Use a system message to force a letter answer (reasoning models need
    # explicit instruction), and give enough tokens for CoT if the model
    # insists on thinking before answering.
    gen_msgs = _mcq_generate_messages(item, shots)
    text = client.chat_text(model=model, messages=gen_msgs, temperature=temperature,
                            max_tokens=max(max_tokens, 256))
    pred = _parse_letter(text, letters)
    return {"correct": pred == gold_letter, "predicted": pred,
            "method": "generate_fallback", "raw": text[:200]}


# ======================================================================
# Math
# ======================================================================
def _last_boxed(text: str) -> str | None:
    """Return the contents of the last ``\\boxed{...}``, handling nested braces."""
    idx = text.rfind("\\boxed")
    if idx < 0:
        return None
    i = text.find("{", idx)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    return None


def _to_number(s) -> float | None:
    """Parse a number (int, decimal, fraction, with optional , $ %) from text."""
    t = str(s).strip().replace(",", "").replace("$", "").replace("%", "").replace(" ", "")
    if "/" in t:
        m = re.search(r"(-?\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", t)
        if m:
            try:
                denom = float(m.group(2))
                return float(m.group(1)) / denom if denom else None
            except (ValueError, ZeroDivisionError):
                return None
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", t)
    return float(m.group()) if m else None


def _extract_math_answer(text: str) -> float | None:
    if not text:
        return None
    boxed = _last_boxed(text)
    if boxed is not None:
        n = _to_number(boxed)
        if n is not None:
            return n
    m = re.search(r"answer[:\s]*\$?([^\n]+)", text, re.IGNORECASE)
    if m:
        n = _to_number(m.group(1))
        if n is not None:
            return n
    nums = re.findall(r"[-+]?\d*\.?\d+", text)
    if nums:
        return _to_number(nums[-1])
    return None


def _math_equal(a, b, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def _math_messages(item: dict, shots: list[dict]) -> list[dict]:
    sys_msg = {"role": "system", "content":
               "Solve the math problem step by step. Put your final numerical "
               "answer in \\boxed{}."}
    parts = []
    for s in shots:
        gold = s.get("gold_number", _to_number(s.get("gold")))
        parts.append(f"Problem: {s['question']}\nSolution: \\boxed{{{gold}}}")
    parts.append(f"Problem: {item['question']}")
    return [sys_msg, {"role": "user", "content": "\n\n".join(parts)}]


def score_math(client, model, item, *, shots, temperature, max_tokens) -> dict:
    """Score one math item by final-answer exact match (numeric tolerance)."""
    msgs = _math_messages(item, shots)
    text = client.chat_text(model=model, messages=msgs,
                            temperature=temperature, max_tokens=max_tokens)
    pred = _extract_math_answer(text)
    gold = item.get("gold_number")
    if gold is None:
        gold = _to_number(item.get("gold"))
    return {"correct": _math_equal(pred, gold), "predicted": pred, "gold": gold, "raw": text}


# ======================================================================
# Code (HumanEval / MBPP) — executed in a subprocess sandbox
# ======================================================================
def _run_python(src: str, timeout: int = CODE_TIMEOUT) -> tuple[bool, str]:
    try:
        proc = subprocess.run([sys.executable, "-c", src],
                              capture_output=True, text=True, timeout=timeout)
        return proc.returncode == 0, (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:  # noqa: BLE001 — keep the run alive
        return False, f"{type(e).__name__}: {e}"


def score_code(client, model, item, *, temperature, max_tokens) -> dict:
    """pass@1: append completion to prompt+tests, run, check exit 0."""
    completion = _strip_code_fences(client.chat_text(
        model=model,
        messages=[{"role": "user", "content": item["prompt"]}],
        temperature=temperature, max_tokens=max_tokens,
        stop=["\nclass ", "\nif __name__", "\ndef ", "\n\n\n"],
    ))
    src = item["prompt"] + "\n" + completion + "\n" + (item.get("test") or "")
    ok, err = _run_python(src)
    return {"passed": ok, "completion": completion[:600],
            "error": None if ok else (err or "")[:200]}


# ======================================================================
# Extended scorers (Tier-1 builtin engine)
# ======================================================================
def score_code_io(client, model, item, *, temperature, max_tokens):
    """LiveCodeBench-style stdin/stdout code execution."""
    completion = _code_completion(client, model, item, temperature, max_tokens)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", completion],
            input=(item.get("stdin") or ""),
            capture_output=True, text=True, timeout=CODE_TIMEOUT,
        )
        out = (proc.stdout or "").strip()
        expected = (item.get("expected_stdout") or "").strip()
        ok = proc.returncode == 0 and out == expected
        return {"passed": ok, "completion": completion[:600], "stdout": out[:200], "expected": expected[:200]}
    except subprocess.TimeoutExpired:
        return {"passed": False, "completion": completion[:600], "error": "timeout"}
    except Exception as e:  # noqa: BLE001
        return {"passed": False, "completion": completion[:600], "error": f"{type(e).__name__}: {e}"}


def _code_completion(client, model, item, temperature, max_tokens):
    completion = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content":
             "You write Python that reads from stdin and prints the answer to stdout. "
             "No markdown fences, no explanation, no extra prints."},
            {"role": "user", "content": item["prompt"]},
        ],
        temperature=temperature, max_tokens=max_tokens,
        stop=["\nclass ", "\nif __name__"],
    )
    return _strip_code_fences(completion)


def score_swe(client, model, item, *, temperature, max_tokens):
    """SWE-bench / DeepSWE: ask for a unified diff, parse it."""
    text = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content":
             "You are a senior software engineer. Output ONLY a unified diff "
             "(--- a/... +++ b/...) that fixes the issue. No markdown, no prose."},
            {"role": "user", "content": item["prompt"]},
        ],
        temperature=temperature, max_tokens=min(max_tokens, 2048),
    )
    patch = _strip_code_fences(text)
    parsed = bool(re.search(r"^---\s", patch, re.M) and re.search(r"^\+\+\+\s", patch, re.M))
    return {"passed": parsed, "completion": patch[:600]}


def score_arc_agi(client, model, item, *, temperature, max_tokens):
    """ARC-AGI-2: parse output grid JSON."""
    text = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content": "Solve the ARC task. Output ONLY the output grid as JSON."},
            {"role": "user", "content": item["prompt"]},
        ],
        temperature=temperature, max_tokens=max_tokens,
    )
    parsed = bool(re.search(r"\[\s*\d", text))
    return {"passed": parsed, "completion": text[:300]}


def score_function_call(client, model, item, *, temperature, max_tokens):
    """BFCL-style function-calling scorer."""
    import json
    text = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content":
             "You have access to these functions:\n" +
             json.dumps(item.get("available_functions", []), indent=2) +
             "\n\nCall exactly one function. Output a JSON object with keys \"name\" and \"arguments\"."},
            {"role": "user", "content": item["prompt"]},
        ],
        temperature=temperature, max_tokens=max_tokens,
    )
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"passed": False, "predicted": text[:200]}
    try:
        pred = json.loads(m.group())
        gold = json.loads(item["gold"]) if isinstance(item["gold"], str) else item["gold"]
        ok = pred.get("name") == gold.get("name") and pred.get("arguments") == gold.get("arguments")
        return {"passed": ok, "predicted": pred}
    except Exception as e:  # noqa: BLE001
        return {"passed": False, "predicted": text[:200], "error": str(e)}


def score_agent_terminal(client, model, item, *, temperature, max_tokens):
    """Terminal-bench baseline.

    SECURITY: this scorer executes model-generated shell commands locally.
    That is the whole point of terminal-bench, but it is genuinely dangerous
    — the model could emit anything. So execution is OFF by default and only
    runs when BOTH of these hold:

      1. The env var ``OLLAMA_EVAL_ALLOW_SHELL=1`` is explicitly set (opt-in),
         AND
      2. A POSIX shell (``bash`` or ``sh``) is discoverable on PATH via
         ``shutil.which`` — stock Windows has neither, so it stays fail-safe
         there even when opted in.

    When execution is disabled (the default), every item is recorded as
    not-passed with reason ``shell_exec_disabled``; terminal-bench then
    contributes nothing to the aggregate score until you consciously turn it
    on, and only on a disposable machine/container — never one holding real
    data or credentials.
    """
    if os.environ.get("OLLAMA_EVAL_ALLOW_SHELL") != "1":
        return {"passed": False, "skipped": True,
                "error": "shell_exec_disabled (set OLLAMA_EVAL_ALLOW_SHELL=1 to enable)"}

    text = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content":
             "Solve the shell task. Output ONLY the commands to run, no markdown."},
            {"role": "user", "content": item["prompt"]},
        ],
        temperature=temperature, max_tokens=max_tokens,
    )
    cmds = _strip_code_fences(text)
    shell = shutil.which("bash") or shutil.which("sh")
    if not shell:
        return {"passed": False, "skipped": True,
                "error": "no_shell_available (bash/sh not on PATH)"}
    try:
        proc = subprocess.run([shell, "-lc", cmds], capture_output=True, text=True,
                              timeout=CODE_TIMEOUT)
        out = (proc.stdout or "").strip()
        ok = out == (item.get("gold") or "").strip()
        return {"passed": ok, "stdout": out[:200]}
    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "timeout"}
    except Exception as e:  # noqa: BLE001
        return {"passed": False, "error": f"{type(e).__name__}: {e}"}


def score_gaia(client, model, item, *, temperature, max_tokens):
    """GAIA baseline: short-form answer exact-match."""
    text = client.chat_text(
        model=model,
        messages=[
            {"role": "system", "content":
             "Answer the question concisely. End with 'Answer: <text>'."},
            {"role": "user", "content": item["prompt"]},
        ],
        temperature=temperature, max_tokens=max_tokens,
    )
    m = re.search(r"answer[:\s]*(.+?)(?:\.|$)", text, re.I)
    pred = (m.group(1).strip() if m else text.strip()).lower()
    return {"passed": pred == (item.get("gold") or "").strip().lower(),
            "predicted": pred[:200]}
