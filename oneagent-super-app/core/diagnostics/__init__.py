"""
OneAgent Core — Diagnostic Flags + Timeline JSONL
Inspired by OpenClaw's diagnostics system.

Features:
- Subsystem-specific diagnostic flags (case-insensitive, wildcards)
- Structured timing events as JSONL for QA automation
- Session liveness classification (long_running, stalled, stuck)
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field


# Default diagnostic flags (can be overridden via ONEAGENT_DIAGNOSTICS env)
DEFAULT_DIAGNOSTICS = {
    # "gateway.*",
    # "browser.act",
    # "session.long_running",
    # "session.stalled",
    # "timeline",
}


@dataclass
class TimelineEvent:
    """A structured timing event for the timeline JSONL."""
    event_id: str
    event_type: str  # "startup", "runtime", "phase", "span"
    phase: str        # e.g., "init", "load_plugin", "model_call"
    span: str = ""    # Sub-span name
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: int = 0
    process_id: int = field(default_factory=os.getpid)
    plugin_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DiagnosticManager:
    """Manages diagnostic flags and structured timing events."""

    def __init__(self, diagnostics_dir: str = None):
        self._flags: Set[str] = self._parse_flags()
        self.diagnostics_dir = Path(diagnostics_dir or "./diagnostics")
        self._timeline_path = self.diagnostics_dir / f"timeline_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self._spans: Dict[str, float] = {}  # Open spans (name → start_time)

    def _parse_flags(self) -> Set[str]:
        """Parse diagnostic flags from env and defaults."""
        flags = set(DEFAULT_DIAGNOSTICS)
        env_flags = os.environ.get("ONEAGENT_DIAGNOSTICS", "")
        for flag in env_flags.split(","):
            flag = flag.strip().lower()
            if flag:
                flags.add(flag)
        return flags

    def is_enabled(self, flag: str) -> bool:
        """Check if a diagnostic flag is enabled (supports wildcards)."""
        flag = flag.lower()
        for f in self._flags:
            if f == flag:
                return True
            if f.endswith(".*"):
                prefix = f[:-2]
                if flag.startswith(prefix + ".") or flag == prefix:
                    return True
        return False

    def enable(self, flag: str) -> None:
        """Enable a diagnostic flag."""
        self._flags.add(flag.lower())

    def disable(self, flag: str) -> None:
        """Disable a diagnostic flag."""
        self._flags.discard(flag.lower())

    def list_flags(self) -> List[str]:
        """List all enabled flags."""
        return sorted(self._flags)

    def start_span(self, name: str, phase: str = "", plugin_id: str = "") -> str:
        """Start a timing span. Returns span ID."""
        span_id = f"{name}_{int(time.time() * 1000)}"
        self._spans[span_id] = time.time()

        if self.is_enabled("timeline"):
            self._write_event(TimelineEvent(
                event_id=span_id,
                event_type="span",
                phase=phase,
                span=name,
                plugin_id=plugin_id,
            ))

        return span_id

    def end_span(self, span_id: str, metadata: dict = None) -> int:
        """End a timing span. Returns duration in ms."""
        start = self._spans.pop(span_id, None)
        if start is None:
            return 0

        duration_ms = int((time.time() - start) * 1000)

        if self.is_enabled("timeline"):
            self._write_event(TimelineEvent(
                event_id=span_id,
                event_type="span_end",
                phase="",
                span=span_id.split("_")[0],
                duration_ms=duration_ms,
                metadata=metadata or {},
            ))

        return duration_ms

    def _write_event(self, event: TimelineEvent) -> None:
        """Write a timeline event to the JSONL file."""
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        with open(self._timeline_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "envelope": "oneagent.diagnostics.v1",
                "event_id": event.event_id,
                "event_type": event.event_type,
                "phase": event.phase,
                "span": event.span,
                "start_time": event.start_time,
                "duration_ms": event.duration_ms,
                "process_id": event.process_id,
                "plugin_id": event.plugin_id,
                "metadata": event.metadata,
            }) + "\n")

    def log_event(self, event_type: str, phase: str, metadata: dict = None) -> None:
        """Log a one-off event (not a span)."""
        if self.is_enabled("timeline"):
            self._write_event(TimelineEvent(
                event_id=f"evt_{int(time.time() * 1000)}",
                event_type=event_type,
                phase=phase,
                metadata=metadata or {},
            ))

    def classify_session_liveness(self, session_data: dict) -> str:
        """Classify a session's liveness.

        Returns: "active", "long_running", "stalled", or "stuck"

        - active: recently interacted, normal
        - long_running: active but slow (>5 min since last response)
        - stalled: active but no progress (>10 min)
        - stuck: stale bookkeeping, no active work
        """
        if not session_data.get("last_interaction_at"):
            return "stuck"

        try:
            last_interaction = datetime.fromisoformat(session_data["last_interaction_at"])
        except (ValueError, TypeError):
            return "stuck"

        now = datetime.now()
        since_interaction = now - last_interaction

        if since_interaction > timedelta(minutes=30):
            return "stuck"
        elif since_interaction > timedelta(minutes=10):
            return "stalled"
        elif since_interaction > timedelta(minutes=5):
            return "long_running"
        else:
            return "active"

    def get_session_remediation(self, liveness: str) -> str:
        """Get remediation action for a liveness classification."""
        actions = {
            "active": "No action needed.",
            "long_running": "Monitor. If no progress in 5 more minutes, consider intervention.",
            "stalled": "Abort-drain after grace period. Check for deadlocks or infinite loops.",
            "stuck": "Release session lane immediately. Clean up stale bookkeeping.",
        }
        return actions.get(liveness, "Unknown liveness classification.")