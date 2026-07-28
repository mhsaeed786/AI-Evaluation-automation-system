from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List
import asyncio
import uuid

@dataclass
class ScheduledTask:
    id: str
    name: str
    cron: str
    fn: Callable
    enabled: bool = True
    last_run: datetime = None
    next_run: datetime = None

class TaskScheduler:
    """Simple async scheduler; cron parsing deferred to croniter if available."""
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}

    def add(self, name: str, cron: str, fn: Callable) -> str:
        tid = str(uuid.uuid4())
        self.tasks[tid] = ScheduledTask(id=tid, name=name, cron=cron, fn=fn)
        return tid

    def remove(self, tid: str):
        self.tasks.pop(tid, None)

    def list(self) -> List[dict]:
        return [{"id": t.id, "name": t.name, "cron": t.cron, "enabled": t.enabled} for t in self.tasks.values()]

    async def run_manual(self, tid: str):
        t = self.tasks.get(tid)
        if t:
            t.last_run = datetime.utcnow()
            return await t.fn()

    async def loop(self, interval: int = 60):
        while True:
            await asyncio.sleep(interval)
