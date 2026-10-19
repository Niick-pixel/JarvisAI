"""Cron, and nothing more. The schedule lives in APScheduler; the jobs live in SQLite.

APScheduler's own job stores want SQLAlchemy, which is a dependency this project does not have and
does not need: `jobs` is already a table, so the scheduler is rebuilt from it at startup and after
every edit. That also means a job you disable stops firing immediately rather than at next boot.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from server.agents import loop
from server.db import repo
from server.models.agents import Job

log = logging.getLogger("jarvis.agents")


DOW_NAMES = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")


def trigger(expression: str) -> CronTrigger:
    """Cron as everyone else reads it.

    APScheduler numbers weekdays from Monday = 0; standard cron (and every form here) from
    Sunday = 0. Passed straight through, "1-5" - weekdays - fired Tuesday to Saturday. Numbers in
    the weekday field are turned into names first, which both read the same way.
    """
    fields = expression.split()
    if len(fields) == 5 and "/" not in fields[4]:
        fields[4] = re.sub(
            r"\d+",
            lambda m: DOW_NAMES[int(m.group()) % 7] if int(m.group()) <= 7 else m.group(),
            fields[4],
        )
    return CronTrigger.from_crontab(" ".join(fields))


def validate_cron(expression: str) -> str:
    """Returns an empty string when the expression is fine, else the reason it is not."""
    try:
        trigger(expression)
    except ValueError as exc:
        return str(exc)
    return ""


class JobScheduler:
    def __init__(self, runtime: loop.Runtime) -> None:
        self.runtime = runtime
        self._scheduler = AsyncIOScheduler(timezone=None)
        self._builtin: dict[str, tuple[str, Callable[[], Awaitable[object]]]] = {}
        """App-owned schedules (the morning briefing): not rows in `jobs`, kept across syncs."""

    def start(self) -> None:
        self._scheduler.start()
        self.sync()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def builtin(self, key: str, cron: str | None, fire: Callable[[], Awaitable[object]]) -> None:
        """Schedule (or with cron=None, unschedule) one of the app's own recurring tasks."""
        if cron is None:
            self._builtin.pop(key, None)
        else:
            self._builtin[key] = (cron, fire)
        self.sync()

    def sync(self) -> None:
        """Rebuild the schedule from the table. Called at startup and after any job edit."""
        self._scheduler.remove_all_jobs()
        for key, (cron, fire) in self._builtin.items():
            self._scheduler.add_job(fire, trigger(cron), id=f"builtin:{key}", replace_existing=True)
        with self.runtime.db.session() as conn:
            jobs = repo.agents.list_jobs(conn)
        for job in jobs:
            if not job.enabled:
                continue
            try:
                when = trigger(job.cron)
            except ValueError:
                # A job with an unparseable cron stays visible and simply never fires; the API
                # rejects bad expressions, so this only happens to rows edited by hand.
                log.warning("job %s has an invalid cron %r and will not run", job.id, job.cron)
                continue
            self._scheduler.add_job(
                self._fire, when, args=[job.id], id=job.id, replace_existing=True
            )

    def next_run_at(self, job_id: str) -> int | None:
        entry = self._scheduler.get_job(job_id)
        if entry is None or entry.next_run_time is None:
            return None
        return int(entry.next_run_time.timestamp() * 1000)

    def decorate(self, job: Job) -> Job:
        return job.model_copy(update={"next_run_at": self.next_run_at(job.id)})

    async def _fire(self, job_id: str) -> None:
        with self.runtime.db.session() as conn:
            job = repo.agents.get_job(conn, job_id)
        if job is None or not job.enabled:
            return
        log.info("job %s (%s) firing", job.id, job.name)
        await loop.start(self.runtime, job)
