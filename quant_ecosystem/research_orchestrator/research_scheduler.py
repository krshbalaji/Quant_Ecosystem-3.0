"""
research_scheduler.py
Priority-queue scheduler for research pipeline jobs.
Supports: interval-based, cron-style, event-triggered, and dependency-chained jobs.
Designed to orchestrate thousands of daily genome evaluations without blocking trading.
"""

from __future__ import annotations

import heapq
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Job definitions
# ---------------------------------------------------------------------------

@dataclass(order=True)
class ScheduledJob:
    next_run: float                             # epoch timestamp for next execution
    priority: int                               # lower = higher priority
    job_id: str = field(compare=False)
    name: str = field(compare=False)
    fn: Callable[[], Any] = field(compare=False)
    interval_seconds: Optional[float] = field(default=None, compare=False)
    max_runs: Optional[int] = field(default=None, compare=False)
    run_count: int = field(default=0, compare=False)
    last_run: Optional[float] = field(default=None, compare=False)
    last_duration_sec: float = field(default=0.0, compare=False)
    last_error: Optional[str] = field(default=None, compare=False)
    enabled: bool = field(default=True, compare=False)
    tags: Dict[str, str] = field(default_factory=dict, compare=False)
    dependencies: List[str] = field(default_factory=list, compare=False)
    timeout_sec: float = field(default=300.0, compare=False)

    def is_due(self, now: Optional[float] = None) -> bool:
        return self.enabled and (now or time.time()) >= self.next_run

    def reschedule(self) -> None:
        if self.interval_seconds:
            self.next_run = time.time() + self.interval_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "next_run": self.next_run,
            "priority": self.priority,
            "interval_seconds": self.interval_seconds,
            "run_count": self.run_count,
            "last_run": self.last_run,
            "last_duration_sec": self.last_duration_sec,
            "last_error": self.last_error,
            "enabled": self.enabled,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class ResearchScheduler:
    """
    Non-blocking research job scheduler.
    Runs in a background thread; trading loop is unaffected.

    Usage:
        scheduler = ResearchScheduler()
        scheduler.add_job("genome_evolution", fn=evolve_fn, interval_seconds=300, priority=10)
        scheduler.add_job("signal_ic_update", fn=ic_update_fn, interval_seconds=60, priority=5)
        scheduler.start()
        # ...
        scheduler.stop()

    Scaling to 1000s of strategies per day:
        - Set small intervals (60–300s) for high-value jobs
        - Use priority to protect critical jobs
        - Chain jobs via dependencies to manage resource usage
    """

    def __init__(self, max_concurrent: int = 4, poll_interval: float = 1.0) -> None:
        self._jobs: Dict[str, ScheduledJob] = {}
        self._heap: List[ScheduledJob] = []
        self._lock = threading.Lock()
        self._heap_dirty = False
        self._max_concurrent = int(max_concurrent)
        self._poll_interval = float(poll_interval)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._active_threads: Dict[str, threading.Thread] = {}
        self._completed_jobs: List[str] = []   # job_ids of finished jobs (for dependency tracking)

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_job(
        self,
        name: str,
        fn: Callable[[], Any],
        interval_seconds: Optional[float] = None,
        priority: int = 50,
        run_at: Optional[float] = None,
        max_runs: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None,
        dependencies: Optional[List[str]] = None,
        timeout_sec: float = 300.0,
        enabled: bool = True,
    ) -> str:
        job_id = f"job_{name}_{uuid.uuid4().hex[:8]}"
        next_run = run_at or time.time()
        job = ScheduledJob(
            next_run=next_run,
            priority=priority,
            job_id=job_id,
            name=name,
            fn=fn,
            interval_seconds=interval_seconds,
            max_runs=max_runs,
            tags=dict(tags or {}),
            dependencies=list(dependencies or []),
            timeout_sec=timeout_sec,
            enabled=enabled,
        )
        with self._lock:
            self._jobs[job_id] = job
            heapq.heappush(self._heap, job)
        return job_id

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
            self._heap_dirty = True

    def enable_job(self, job_id: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True

    def disable_job(self, job_id: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False

    def trigger_now(self, job_id: str) -> None:
        """Immediately trigger a job regardless of schedule."""
        if job_id in self._jobs:
            self._jobs[job_id].next_run = time.time()
            with self._lock:
                heapq.heappush(self._heap, self._jobs[job_id])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ResearchScheduler")
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Scheduling loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            self._cleanup_active()
            if self._heap_dirty:
                with self._lock:
                    heapq.heapify(self._heap)
                    self._heap_dirty = False

            while self._heap and len(self._active_threads) < self._max_concurrent:
                with self._lock:
                    if not self._heap:
                        break
                    job = self._heap[0]

                if not job.is_due(now):
                    break

                with self._lock:
                    heapq.heappop(self._heap)

                # Skip if removed or disabled
                if job.job_id not in self._jobs or not job.enabled:
                    continue

                # Check dependencies
                if not self._deps_satisfied(job):
                    # Re-queue for later
                    job.next_run = now + 10.0
                    with self._lock:
                        heapq.heappush(self._heap, job)
                    break

                # Check max_runs
                if job.max_runs is not None and job.run_count >= job.max_runs:
                    self.remove_job(job.job_id)
                    continue

                # Launch in thread
                t = threading.Thread(
                    target=self._execute, args=(job,), daemon=True, name=f"job_{job.name}"
                )
                self._active_threads[job.job_id] = t
                t.start()

            time.sleep(self._poll_interval)

    def _execute(self, job: ScheduledJob) -> None:
        start = time.time()
        try:
            job.fn()
            job.last_error = None
        except Exception as exc:
            job.last_error = str(exc)
        finally:
            job.last_run = start
            job.last_duration_sec = round(time.time() - start, 4)
            job.run_count += 1
            self._completed_jobs.append(job.job_id)
            if len(self._completed_jobs) > 10000:
                self._completed_jobs = self._completed_jobs[-5000:]
            # Reschedule if recurring
            if job.interval_seconds and job.job_id in self._jobs:
                if job.max_runs is None or job.run_count < job.max_runs:
                    job.reschedule()
                    with self._lock:
                        heapq.heappush(self._heap, job)

    def _cleanup_active(self) -> None:
        done = [jid for jid, t in self._active_threads.items() if not t.is_alive()]
        for jid in done:
            self._active_threads.pop(jid, None)

    def _deps_satisfied(self, job: ScheduledJob) -> bool:
        for dep_name in job.dependencies:
            if dep_name not in self._completed_jobs:
                # Check by job name in completed list
                satisfied = any(
                    j.name == dep_name
                    for jid in self._completed_jobs
                    for j in [self._jobs.get(jid)]
                    if j
                )
                if not satisfied:
                    return False
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_jobs": len(self._jobs),
            "active_jobs": len(self._active_threads),
            "heap_size": len(self._heap),
            "jobs": [j.to_dict() for j in sorted(self._jobs.values(), key=lambda j: j.next_run)],
        }

    def job_stats(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None

    def next_due(self) -> Optional[ScheduledJob]:
        if self._heap:
            return self._heap[0]
        return None
