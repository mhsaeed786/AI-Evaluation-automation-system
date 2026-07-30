"""
OneAgent Core — Queue & Steering System
Inspired by OpenClaw's queue/steering modes.

Features:
- Per-session run serialization (session lanes)
- Optional global lane for cross-session ordering
- Steering mode: inject messages mid-run (after tool calls, before next LLM call)
- Followup/collect mode: hold messages until current turn ends
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib


class QueueMode(Enum):
    STEER = "steer"        # Inject into current run (after tool calls, before next LLM)
    FOLLOWUP = "followup"  # Hold until current turn ends, then new turn
    COLLECT = "collect"    # Same as followup but batch all queued messages


@dataclass
class QueuedMessage:
    """A message in the steering/followup queue."""
    session_id: str
    content: str
    mode: QueueMode
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    role: str = "user"


class SessionQueue:
    """Per-session message queue with steering support."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._current_run: Optional[asyncio.Task] = None
        self._steer_queue: List[QueuedMessage] = []
        self._followup_queue: List[QueuedMessage] = []
        self._turn_complete = asyncio.Event()
        self._turn_complete.set()  # No turn running initially

    async def enqueue(self, message: QueuedMessage) -> str:
        """Add a message to the appropriate queue."""
        async with self._lock:
            if message.mode == QueueMode.STEER:
                self._steer_queue.append(message)
            else:
                self._followup_queue.append(message)
        return f"queued_{hashlib.sha256(message.timestamp.encode()).hexdigest()[:8]}"

    async def drain_steer_messages(self) -> List[QueuedMessage]:
        """Drain all steering messages (called after tool calls, before next LLM call)."""
        async with self._lock:
            messages = list(self._steer_queue)
            self._steer_queue.clear()
        return messages

    async def drain_followup_messages(self) -> List[QueuedMessage]:
        """Drain all followup/collect messages (called after turn ends)."""
        async with self._lock:
            messages = list(self._followup_queue)
            self._followup_queue.clear()
        return messages

    def has_pending(self) -> bool:
        """Check if there are pending messages."""
        return bool(self._steer_queue or self._followup_queue)

    async def mark_turn_start(self) -> None:
        """Mark that a new turn has started."""
        self._turn_complete.clear()

    async def mark_turn_end(self) -> None:
        """Mark that the current turn has ended."""
        self._turn_complete.set()

    async def wait_for_turn_end(self, timeout: float = None) -> bool:
        """Wait for the current turn to complete."""
        try:
            await asyncio.wait_for(self._turn_complete.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


class QueueManager:
    """Manages session queues with steering and serialization."""

    def __init__(self, use_global_lane: bool = False):
        self._session_queues: Dict[str, SessionQueue] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock() if use_global_lane else None
        self._use_global_lane = use_global_lane

    def get_queue(self, session_id: str) -> SessionQueue:
        """Get or create a session queue."""
        if session_id not in self._session_queues:
            self._session_queues[session_id] = SessionQueue()
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_queues[session_id]

    async def run_serialized(self, session_id: str, func: Callable, *args, **kwargs) -> Any:
        """Run a function within the session's serialization lane.

        Ensures only one operation runs per session at a time.
        If global lane is enabled, also serializes globally.
        """
        session_lock = self._session_locks[session_id]

        if self._use_global_lane and self._global_lock:
            async with self._global_lock:
                async with session_lock:
                    return await func(*args, **kwargs)
        else:
            async with session_lock:
                return await func(*args, **kwargs)

    async def steer(self, session_id: str, content: str) -> str:
        """Inject a steering message into the current run.

        The message will be delivered after current tool calls complete,
        before the next LLM call.
        """
        queue = self.get_queue(session_id)
        msg = QueuedMessage(
            session_id=session_id,
            content=content,
            mode=QueueMode.STEER,
        )
        return await queue.enqueue(msg)

    async def followup(self, session_id: str, content: str) -> str:
        """Queue a followup message for after the current turn ends."""
        queue = self.get_queue(session_id)
        msg = QueuedMessage(
            session_id=session_id,
            content=content,
            mode=QueueMode.FOLLOWUP,
        )
        return await queue.enqueue(msg)

    async def get_steer_messages(self, session_id: str) -> List[dict]:
        """Get and clear steering messages for a session."""
        queue = self.get_queue(session_id)
        messages = await queue.drain_steer_messages()
        return [{"content": m.content, "timestamp": m.timestamp} for m in messages]

    async def get_followup_messages(self, session_id: str) -> List[dict]:
        """Get and clear followup messages for a session."""
        queue = self.get_queue(session_id)
        messages = await queue.drain_followup_messages()
        return [{"content": m.content, "timestamp": m.timestamp} for m in messages]

    def has_pending_messages(self, session_id: str) -> bool:
        """Check if a session has pending messages."""
        queue = self._session_queues.get(session_id)
        if queue:
            return queue.has_pending()
        return False

    async def mark_turn_start(self, session_id: str) -> None:
        """Mark turn start for a session."""
        queue = self.get_queue(session_id)
        await queue.mark_turn_start()

    async def mark_turn_end(self, session_id: str) -> None:
        """Mark turn end for a session."""
        queue = self.get_queue(session_id)
        await queue.mark_turn_end()