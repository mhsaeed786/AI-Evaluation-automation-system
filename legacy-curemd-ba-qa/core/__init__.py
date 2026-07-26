"""
OneAgent Core Runtime — shared foundation for all modules.

Components:
  - llm:       Unified LLM gateway (router, cache, budget)
  - agents:    Generic agent loop + tool registry + memory
  - skills:    Skill pack system (prompt + tools bundles)
  - mcp:       MCP server host and client
  - rag:       RAG pipeline with ChromaDB
  - scheduler: Cron + event-triggered agent execution
  - meta:      Self-extension engine (module author, sandbox)
  - data:      Core database (SQLModel models)
  - auth:      Authentication layer
  - profile:   User profile and recurring-task ledger
"""

__version__ = "1.0.0"
