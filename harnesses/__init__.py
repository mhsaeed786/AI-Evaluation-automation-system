"""Tier-2 harness wrappers (optional, heavy deps).

These are lazy-imported by ``src/runner.py`` only when ``--engine`` selects
them. They invoke the upstream harnesses as subprocesses (pointed at Ollama
Cloud via environment variables) and convert their JSON output into the same
:class:`~src.results.ResultRecord` shape the builtin engine produces, so the
comparison/report layer is identical across engines.
"""
