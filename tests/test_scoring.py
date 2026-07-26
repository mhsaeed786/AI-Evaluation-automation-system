"""Offline self-test for the builtin scoring layer.

Runs every scorer branch (MCQ logprob / generate / fallback, math
boxed / answer / last-number, code pass / fail) against a FAKE client
that returns canned responses — no network, no API key, no cost.

Usage:
    python tests\\test_scoring.py

Exits 0 if every assertion holds, 1 otherwise. Run this after editing
configs or scorers, and before trusting a paid benchmark run.
"""
from __future__ import annotations

import pathlib
import sys

# Make `src` importable when run directly as a script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.scoring_types import LetterScores  # noqa: E402
from src.scorers import score_code, score_math, score_mcq  # noqa: E402


class FakeClient:
    """Stand-in for OllamaCloudClient returning scripted answers.

    Only the methods the scorers call are implemented. Each instance is
    configured once with the canned responses for one test case.
    """

    base_url = "https://fake.test/v1"

    def __init__(self, *, logprob=None, generate=None, text=None):
        self._logprob = logprob            # LetterScores | None
        self._generate = generate          # str | None
        self._text = text                  # str | None

    def chat_text(self, *, model, messages, **kw):
        return self._text or ""

    def answer_letter_logprob(self, *, model, prompt_messages, letters, **kw):
        if self._logprob is not None:
            return self._logprob
        return LetterScores(scores={}, present=False)

    def answer_letter_generate(self, *, model, prompt_messages, letters, **kw):
        return self._generate


# ----------------------------------------------------------------------
# Test cases — each is (label, callable returning bool, expected).
# ----------------------------------------------------------------------
def _mcq_item(gold, choices=("alpha", "beta", "gamma", "delta"), q="Pick the best one."):
    return {"id": "x", "question": q, "choices": list(choices), "gold": gold}


def _math_item(gold_number, gold="?", question="What is 2+2?"):
    return {"id": "m", "question": question, "gold": gold, "gold_number": gold_number}


def _code_item(prompt, test, entry="f"):
    return {"id": "c", "prompt": prompt, "test": test, "entry_point": entry}


CASES = []


def case(label):
    def deco(fn):
        CASES.append((label, fn))
        return fn
    return deco


# --- MCQ: logprob path ------------------------------------------------
@case("mcq logprob correct (argmax == gold B)")
def _t1():
    ls = LetterScores(scores={"A": -2.3, "B": -0.1, "C": -3.0}, present=True)
    res = score_mcq(FakeClient(logprob=ls), "m", _mcq_item(1), shots=[], cot=False,
                    temperature=0.0, max_tokens=8)
    return res["correct"] is True and res["predicted"] == "B" and res["method"] == "logprob"


@case("mcq logprob incorrect (argmax B != gold A)")
def _t2():
    ls = LetterScores(scores={"A": -3.0, "B": -0.2}, present=True)
    res = score_mcq(FakeClient(logprob=ls), "m", _mcq_item(0), shots=[], cot=False,
                    temperature=0.0, max_tokens=8)
    return res["correct"] is False and res["predicted"] == "B"


@case("mcq logprob absent -> generate fallback correct")
def _t3():
    # present=False forces the fallback; canned generate returns "C".
    res = score_mcq(FakeClient(generate="C"), "m", _mcq_item(2), shots=[], cot=False,
                    temperature=0.0, max_tokens=8)
    return res["correct"] is True and res["method"] == "generate_fallback"


# --- MCQ: CoT generate path ------------------------------------------
@case("mcq cot parses 'Answer: C'")
def _t4():
    res = score_mcq(FakeClient(text="Let me think... it is C.\nAnswer: C"), "m",
                    _mcq_item(2), shots=[], cot=True, temperature=0.0, max_tokens=1024)
    return res["correct"] is True and res["method"] == "generate"


@case("mcq cot wrong letter marked incorrect")
def _t5():
    res = score_mcq(FakeClient(text="Answer: A"), "m", _mcq_item(2), shots=[],
                    cot=True, temperature=0.0, max_tokens=1024)
    return res["correct"] is False


# --- MATH -------------------------------------------------------------
@case("math boxed{42} matches gold 42")
def _t6():
    res = score_math(FakeClient(text="so we get $\\boxed{42}$"), "m",
                     _math_item(42.0), shots=[], temperature=0.0, max_tokens=1024)
    return res["correct"] is True


@case("math 'Answer: 7' matches gold 7")
def _t7():
    res = score_math(FakeClient(text="Step... \nAnswer: 7"), "m",
                     _math_item(7.0), shots=[], temperature=0.0, max_tokens=1024)
    return res["correct"] is True


@case("math last-number fallback (no boxed, no 'answer:')")
def _t8():
    res = score_math(FakeClient(text="The total is therefore 100."), "m",
                     _math_item(100.0), shots=[], temperature=0.0, max_tokens=1024)
    return res["correct"] is True


@case("math wrong answer marked incorrect")
def _t9():
    res = score_math(FakeClient(text="\\boxed{5}"), "m",
                     _math_item(9.0), shots=[], temperature=0.0, max_tokens=1024)
    return res["correct"] is False


# --- CODE (executed in a subprocess) ---------------------------------
_PROMPT = "def add(a, b):\n    \"\"\"Return the sum of a and b.\"\"\"\n"
_TEST = "assert add(1, 2) == 3\nassert add(0, 0) == 0\nprint('ok')\n"


@case("code correct completion passes tests")
def _t10():
    res = score_code(FakeClient(text="    return a + b"), "m",
                     _code_item(_PROMPT, _TEST, entry="add"),
                     temperature=0.0, max_tokens=1024)
    return res["passed"] is True


@case("code fenced completion is stripped and passes")
def _t11():
    res = score_code(FakeClient(text="```python\n    return a + b\n```"), "m",
                     _code_item(_PROMPT, _TEST, entry="add"),
                     temperature=0.0, max_tokens=1024)
    return res["passed"] is True


@case("code wrong completion fails tests")
def _t12():
    res = score_code(FakeClient(text="    return a - b"), "m",
                     _code_item(_PROMPT, _TEST, entry="add"),
                     temperature=0.0, max_tokens=1024)
    return res["passed"] is False


def main() -> int:
    fails = []
    for label, fn in CASES:
        err = ""
        try:
            ok = bool(fn())
        except Exception as exc:  # noqa: BLE001
            ok, err = False, f"{type(exc).__name__}: {exc}"
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}" + ("" if ok else f"  <- {err}"))
        if not ok:
            fails.append(label)
    print(f"\n{len(CASES) - len(fails)}/{len(CASES)} passed.")
    if fails:
        print("FAILED: " + ", ".join(fails))
        return 1
    print("All scoring branches verified offline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
