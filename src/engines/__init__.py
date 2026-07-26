"""Benchmark engines.

Two engines are available:

  * ``builtin`` — dependency-light, runs on Python 3.14, no torch. Default.
  * ``lm_eval`` / ``evalplus`` — thin wrappers over the gold-standard harnesses
    (Tier 2, optional heavy deps).

The runner selects the engine per benchmark from config/benchmarks.yaml.
"""
from .builtin import run_builtin  # noqa: F401
