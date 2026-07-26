"""
Scheduler — cron + event-triggered agent execution.

Two backends:
1. Celery + Redis (production) — durable, distributed
2. In-process (fallback) — for local/development use

Scheduled agents run at configured times or in response to events.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEDULES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "schedules"


class TriggerType(Enum):
    CRON = "cron"
    INTERVAL = "interval"
    EVENT = "event"


@dataclass
class ScheduledJob:
    id: str
    name: str
    trigger: TriggerType
    schedule: str  # cron expression, interval seconds, or event name
    agent_config: Dict[str, Any]  # AgentConfig as dict
    task_prompt: str
    module: str = ""
    enabled: bool = True
    last_run: Optional[float] = None
    last_result: Optional[str] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Scheduler:
    """Schedule and execute agent runs on cron, interval, or event triggers."""

    def __init__(self, schedules_dir: Optional[Path] = None):
        self._dir = schedules_dir or SCHEDULES_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, ScheduledJob] = {}
        self._celery_app = None
        self._event_handlers: Dict[str, List[str]] = {}  # event_name -> [job_ids]
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._load_jobs()

    def _load_jobs(self):
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                job = ScheduledJob(
                    id=data["id"],
                    name=data["name"],
                    trigger=TriggerType(data["trigger"]),
                    schedule=data["schedule"],
                    agent_config=data.get("agent_config", {}),
                    task_prompt=data["task_prompt"],
                    module=data.get("module", ""),
                    enabled=data.get("enabled", True),
                    metadata=data.get("metadata", {}),
                )
                self._jobs[job.id] = job
                if job.trigger == TriggerType.EVENT:
                    self._event_handlers.setdefault(job.schedule, []).append(job.id)
            except Exception as e:
                logger.error(f"Failed to load job {f}: {e}")

    def _save_job(self, job: ScheduledJob):
        path = self._dir / f"{job.id}.json"
        path.write_text(json.dumps({
            "id": job.id,
            "name": job.name,
            "trigger": job.trigger.value,
            "schedule": job.schedule,
            "agent_config": job.agent_config,
            "task_prompt": job.task_prompt,
            "module": job.module,
            "enabled": job.enabled,
            "last_run": job.last_run,
            "last_result": job.last_result,
            "run_count": job.run_count,
            "metadata": job.metadata,
        }, indent=2, default=str))

    def add_job(self, job: ScheduledJob):
        self._jobs[job.id] = job
        self._save_job(job)
        if job.trigger == TriggerType.EVENT:
            self._event_handlers.setdefault(job.schedule, []).append(job.id)

    def remove_job(self, job_id: str):
        job = self._jobs.pop(job_id, None)
        if job and job.trigger == TriggerType.EVENT:
            handlers = self._event_handlers.get(job.schedule, [])
            if job_id in handlers:
                handlers.remove(job_id)
        path = self._dir / f"{job_id}.json"
        if path.exists():
            path.unlink()

    def list_jobs(self) -> List[ScheduledJob]:
        return list(self._jobs.values())

    async def fire_event(self, event_name: str, payload: Optional[Dict] = None):
        """Trigger all jobs listening for this event."""
        job_ids = self._event_handlers.get(event_name, [])
        for jid in job_ids:
            job = self._jobs.get(jid)
            if job and job.enabled:
                prompt = job.task_prompt
                if payload:
                    prompt += f"\n\nEvent payload: {json.dumps(payload)}"
                await self._execute_job(job, prompt)

    async def _execute_job(self, job: ScheduledJob, prompt: str):
        """Execute a scheduled agent run."""
        logger.info(f"Executing scheduled job: {job.name} ({job.id})")
        try:
            from ..agents.loop import AgentLoop, AgentConfig
            config = AgentConfig(**job.agent_config) if job.agent_config else AgentConfig(name=job.name, module=job.module)
            agent = AgentLoop(config=config)
            result = await agent.run(prompt)
            job.last_run = time.time()
            job.last_result = result.output[:500] if result.success else f"Error: {result.error}"
            job.run_count += 1
            self._save_job(job)
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.last_run = time.time()
            job.last_result = f"Error: {e}"
            self._save_job(job)

    def start_background(self, interval: float = 60.0):
        """Start the in-process scheduler loop (for dev/local use)."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop_background(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self, interval: float):
        """Background loop that checks for due interval/cron jobs."""
        while self._running:
            now = time.time()
            for job in self._jobs.values():
                if not job.enabled or job.trigger == TriggerType.EVENT:
                    continue
                if job.trigger == TriggerType.INTERVAL:
                    interval_secs = float(job.schedule)
                    if job.last_run is None or (now - job.last_run) >= interval_secs:
                        asyncio.run(self._execute_job(job, job.task_prompt))
            time.sleep(interval)

    def get_celery_app(self):
        """Get or create Celery app for production use."""
        if self._celery_app is None:
            try:
                from celery import Celery
                import os
                broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
                self._celery_app = Celery("oneagent", broker=broker)
            except ImportError:
                logger.warning("Celery not installed. Using in-process scheduler.")
        return self._celery_app


_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
