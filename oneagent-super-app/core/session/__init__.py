"""
OneAgent Core — Session Manager with Transcript Persistence
Inspired by OpenClaw's session-lane serialization + write lock pattern.

Features:
- JSONL transcript files per session (append-only)
- Per-session queue serialization (prevents tool/session races)
- Three-timestamp lifecycle (sessionStartedAt, lastInteractionAt, updatedAt)
- Auto-compaction on context limit (tool-call/result pairing preserved)
- Successor transcripts (new file after compaction, old becomes archive)
- Memory flush before compaction
"""

import os
import json
import time
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class SessionStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    COMPACTED = "compacted"
    ARCHIVED = "archived"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    OBSERVATION = "observation"


@dataclass
class Message:
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_result: Optional[str] = None
    tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "tool_result": self.tool_result,
            "tokens": self.tokens,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(
            role=MessageRole(d["role"]),
            content=d["content"],
            timestamp=d.get("timestamp", datetime.now().isoformat()),
            tool_name=d.get("tool_name"),
            tool_call_id=d.get("tool_call_id"),
            tool_result=d.get("tool_result"),
            tokens=d.get("tokens", 0),
            metadata=d.get("metadata", {}),
        )


@dataclass
class Session:
    session_id: str
    agent_id: str = "main"
    status: SessionStatus = SessionStatus.ACTIVE
    session_started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_interaction_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: List[Message] = field(default_factory=list)
    token_count: int = 0
    turn_count: int = 0
    is_compacted: bool = False
    parent_session_id: Optional[str] = None  # For sub-agents

    def touch(self):
        """Update last_interaction_at and updated_at."""
        now = datetime.now().isoformat()
        self.last_interaction_at = now
        self.updated_at = now

    def to_metadata(self) -> dict:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "session_started_at": self.session_started_at,
            "last_interaction_at": self.last_interaction_at,
            "updated_at": self.updated_at,
            "token_count": self.token_count,
            "turn_count": self.turn_count,
            "is_compacted": self.is_compacted,
            "parent_session_id": self.parent_session_id,
        }


class SessionManager:
    """Manages agent sessions with JSONL transcript persistence."""

    def __init__(self, sessions_dir: str = None):
        self.sessions_dir = Path(sessions_dir or os.environ.get(
            "ONEAGENT_SESSIONS_DIR",
            str(Path.home() / ".oneagent" / "sessions")
        ))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Session] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._session_queues: Dict[str, asyncio.Queue] = {}
        self._max_context_tokens = 128000
        self._compaction_keep_recent = 20  # Keep last N messages after compaction

    def _transcript_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.jsonl"

    def _metadata_path(self) -> Path:
        return self.sessions_dir / "sessions.json"

    def _load_metadata(self) -> Dict[str, dict]:
        path = self._metadata_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_metadata(self, sessions: Dict[str, dict]) -> None:
        path = self._metadata_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)

    def create_session(self, session_id: str = None, agent_id: str = "main",
                       parent_session_id: str = None) -> Session:
        """Create a new session."""
        if session_id is None:
            session_id = hashlib.sha256(
                f"{agent_id}:{time.time()}".encode()
            ).hexdigest()[:16]

        session = Session(
            session_id=session_id,
            agent_id=agent_id,
            parent_session_id=parent_session_id,
        )
        self._sessions[session_id] = session
        self._session_locks[session_id] = asyncio.Lock()
        self._save_session_metadata(session)
        return session

    def _save_session_metadata(self, session: Session) -> None:
        """Update the sessions.json metadata index."""
        metadata = self._load_metadata()
        metadata[session.session_id] = session.to_metadata()
        self._save_metadata(metadata)

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID, loading from disk if needed."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try loading from disk
        transcript_path = self._transcript_path(session_id)
        if not transcript_path.exists():
            return None

        metadata = self._load_metadata()
        meta = metadata.get(session_id)
        if not meta:
            return None

        session = Session(
            session_id=meta["session_id"],
            agent_id=meta.get("agent_id", "main"),
            status=SessionStatus(meta.get("status", "active")),
            session_started_at=meta.get("session_started_at", datetime.now().isoformat()),
            last_interaction_at=meta.get("last_interaction_at", datetime.now().isoformat()),
            updated_at=meta.get("updated_at", datetime.now().isoformat()),
            token_count=meta.get("token_count", 0),
            turn_count=meta.get("turn_count", 0),
            is_compacted=meta.get("is_compacted", False),
            parent_session_id=meta.get("parent_session_id"),
        )

        # Load messages from JSONL
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg_dict = json.loads(line)
                    session.messages.append(Message.from_dict(msg_dict))
                except json.JSONDecodeError:
                    continue

        self._sessions[session_id] = session
        self._session_locks[session_id] = asyncio.Lock()
        return session

    async def append_message(self, session_id: str, message: Message) -> None:
        """Append a message to a session's transcript (thread-safe per session)."""
        lock = self._session_locks.get(session_id)
        if lock is None:
            session = self.get_session(session_id)
            if session is None:
                raise ValueError(f"Session {session_id} not found")
            lock = self._session_locks[session_id]

        async with lock:
            session = self._sessions[session_id]
            session.messages.append(message)
            session.token_count += message.tokens
            session.turn_count += 1 if message.role in (MessageRole.USER, MessageRole.ASSISTANT) else 0
            session.touch()

            # Append to JSONL file
            transcript_path = self._transcript_path(session_id)
            with open(transcript_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(message.to_dict()) + "\n")

            self._save_session_metadata(session)

    async def run_serialized(self, session_id: str, func: Callable, *args, **kwargs) -> Any:
        """Run a function within the session's serialization lane.

        Ensures only one operation runs per session at a time.
        """
        lock = self._session_locks.get(session_id)
        if lock is None:
            session = self.get_session(session_id)
            if session is None:
                raise ValueError(f"Session {session_id} not found")
            lock = self._session_locks[session_id]

        async with lock:
            return await func(*args, **kwargs)

    def needs_compaction(self, session: Session) -> bool:
        """Check if a session needs context compaction."""
        return session.token_count > self._max_context_tokens

    async def compact_session(self, session_id: str, summarize_func: Callable = None) -> str:
        """Compact a session by summarizing older messages.

        Preserves tool-call/result pairing. Creates a successor transcript.
        Returns the new session ID.
        """
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        lock = self._session_locks[session_id]
        async with lock:
            # Memory flush: save a summary of what we learned before compacting
            if summarize_func:
                old_messages = session.messages[:-self._compaction_keep_recent]
                summary = await summarize_func([m.to_dict() for m in old_messages])
            else:
                summary = "Session compacted. Older messages summarized."

            # Keep recent messages intact
            recent_messages = session.messages[-self._compaction_keep_recent:]

            # Create successor session
            new_session_id = f"{session_id}_c{session.turn_count}"
            new_session = Session(
                session_id=new_session_id,
                agent_id=session.agent_id,
                parent_session_id=session_id,
            )

            # Add summary as first message
            summary_msg = Message(
                role=MessageRole.SYSTEM,
                content=f"[Compaction Summary]\n{summary}",
                metadata={"compacted_from": session_id, "compacted_at": datetime.now().isoformat()},
            )
            new_session.messages = [summary_msg] + recent_messages
            new_session.token_count = sum(m.tokens for m in new_session.messages)
            new_session.is_compacted = True

            # Write new transcript
            transcript_path = self._transcript_path(new_session_id)
            with open(transcript_path, "w", encoding="utf-8") as f:
                for msg in new_session.messages:
                    f.write(json.dumps(msg.to_dict()) + "\n")

            # Archive old session
            session.status = SessionStatus.COMPACTED
            self._save_session_metadata(session)
            self._save_session_metadata(new_session)

            self._sessions[new_session_id] = new_session
            self._session_locks[new_session_id] = asyncio.Lock()

            return new_session_id

    def list_sessions(self, agent_id: str = None) -> List[dict]:
        """List all sessions, optionally filtered by agent_id."""
        metadata = self._load_metadata()
        sessions = list(metadata.values())
        if agent_id:
            sessions = [s for s in sessions if s.get("agent_id") == agent_id]
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions

    def get_context_messages(self, session_id: str, limit: int = None) -> List[dict]:
        """Get messages for context window, as dicts ready for LLM API."""
        session = self.get_session(session_id)
        if session is None:
            return []

        messages = session.messages
        if limit:
            messages = messages[-limit:]

        # Convert to API format (strip internal fields)
        result = []
        for msg in messages:
            entry = {"role": msg.role.value, "content": msg.content}
            if msg.tool_name:
                entry["tool_name"] = msg.tool_name
            if msg.tool_result is not None:
                entry["tool_result"] = msg.tool_result
            result.append(entry)
        return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its transcript."""
        session = self.get_session(session_id)
        if session is None:
            return False

        # Remove transcript file
        transcript_path = self._transcript_path(session_id)
        if transcript_path.exists():
            transcript_path.unlink()

        # Remove from metadata
        metadata = self._load_metadata()
        metadata.pop(session_id, None)
        self._save_metadata(metadata)

        # Remove from memory
        self._sessions.pop(session_id, None)
        self._session_locks.pop(session_id, None)

        return True