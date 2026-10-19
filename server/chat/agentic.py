"""Agent mode in chat: the model may use tools while it answers you.

A chat turn with tools on is an agent run attached to that chat: the same gate, the same
approvals, the same audit log, the same rows that let a run parked at "approve?" survive a
restart. What differs from a scheduled job: the conversation is yours (the user turn is your
message, not a job prompt), each generation streams live into the chat, and the last answer
stays in the chat instead of going to the Inbox.

Runs belong to one hidden job, `job_chat`, so the existing tables need nothing new.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from server.agents import loop
from server.chat import run as runner
from server.chat.execute import execute as generate
from server.connections.store import Accounts
from server.db import repo
from server.models.agents import Job, JobRunStatus
from server.models.params import SamplingParams
from server.models.stream import ChatRequest
from server.tools import gate

log = logging.getLogger("jarvis.chat.agent")

CHAT_JOB_ID = repo.agents.CHAT_JOB_ID
DEFAULT_TOOLS = [
    "list_dir",
    "read_file",
    "write_file",
    "run_shell",
    "http_get",
    "forecast",
    "home_devices",
    "home_control",
    "email_search",
    "email_read",
    "email_draft",
    "github_notifications",
    "github_search",
    "github_read",
    "github_comment",
]


@dataclass
class Turn:
    tools: list[str]
    model_id: str | None = None
    params: SamplingParams = field(default_factory=SamplingParams)
    live_run_id: str = ""
    """The generation streaming right now, for the chat to attach to."""
    cancelled: bool = False
    project: str = ""
    """Code mode's project folder: the workspace for this turn instead of the chat's own."""


class ChatAgents:
    def __init__(self, rt: loop.Runtime) -> None:
        self.rt = rt
        self.turns: dict[str, Turn] = {}

    def _job(self, tools: list[str], project: str = "") -> Job:
        with self.rt.db.session() as conn:
            repo.agents.ensure_chat_job(conn, DEFAULT_TOOLS)
            job = repo.agents.get_job(conn, CHAT_JOB_ID)
        assert job is not None
        workspace = project or str(self.rt.settings.agents.workspace / "chat")
        return job.model_copy(update={"tools": tools, "workspace": workspace})

    async def start(
        self,
        conversation_id: str,
        content: str,
        tools: list[str] | None,
        model_id: str | None,
        params: SamplingParams,
        project: str | None = None,
    ) -> str:
        folder = ""
        if project:
            path = Path(project).expanduser()
            if not path.is_absolute() or not path.is_dir():
                raise ValueError(f"{project} is not a folder on this PC.")
            folder = str(path.resolve())
        # Account tools only once the account is connected: otherwise they are noise in the prompt.
        accounts = Accounts(self.rt.settings.paths.data_dir)
        prefixes = {"email_": "gmail", "github_": "github"}
        chosen = [
            t
            for t in (tools or DEFAULT_TOOLS)
            if t in DEFAULT_TOOLS
            and all(not t.startswith(p) or accounts.get(n) for p, n in prefixes.items())
        ]
        self._job(chosen, folder)
        with self.rt.db.session() as conn:
            run_id = repo.agents.start_run(conn, CHAT_JOB_ID, conversation_id)
        self.turns[run_id] = Turn(tools=chosen, model_id=model_id, params=params, project=folder)
        asyncio.get_running_loop().create_task(self._drive(run_id, content))
        return run_id

    async def resume(self, run_id: str) -> None:
        """A decision landed. Wake the parked driver, or start one after a restart."""
        if self.rt.approvals.is_driving(run_id):
            self.rt.approvals.notify(run_id)
            return
        self.turns.setdefault(run_id, Turn(tools=list(DEFAULT_TOOLS)))
        asyncio.get_running_loop().create_task(self._drive(run_id, None))

    async def _drive(self, run_id: str, content: str | None) -> None:
        if not self.rt.approvals.claim(run_id):
            return
        try:
            await self._loop(run_id, content)
        except Exception as exc:  # noqa: BLE001 - a run must fail as a row, never as a traceback
            log.exception("chat agent run %s failed", run_id)
            with self.rt.db.session() as conn:
                repo.agents.set_status(conn, run_id, "failed", error=str(exc)[:400])
        finally:
            self.rt.approvals.release(run_id)
            if run_id in self.turns:
                self.turns[run_id].live_run_id = ""

    async def _loop(self, run_id: str, content: str | None) -> None:
        turn = self.turns[run_id]
        job = self._job(turn.tools, turn.project)
        first = content
        while True:
            if turn.cancelled:
                self._set(run_id, "cancelled", "stopped")
                return
            with self.rt.db.session() as conn:
                run = repo.agents.get_run(conn, run_id)
                if run is None or run.status in ("done", "failed", "cancelled"):
                    return
                calls = repo.tools.for_run(conn, run_id)
            cleared = [c for c in calls if c.status == "approved" and not c.delivered]
            if cleared:
                await loop._run_call(self.rt, job, run_id, cleared[0].id)  # noqa: SLF001
                continue
            if any(c.status == "pending" for c in calls):
                await loop._wait_for_decisions(self.rt, run_id)  # noqa: SLF001
                continue
            done = [c for c in calls if c.status in ("ran", "failed", "denied") and not c.delivered]
            if done:
                loop._deliver(  # noqa: SLF001
                    self.rt, run.conversation_id or "", done, steps=run.steps + 1, run_id=run_id
                )
                continue
            if run.steps >= self.rt.settings.agents.max_steps:
                self._finish(run_id, "reached the step limit")
                return
            answer = await self._generate(run.conversation_id or "", first, turn)
            first = None
            if turn.cancelled:
                continue
            proposed, malformed = gate.parse_calls(answer)
            if not proposed:
                self._finish(run_id, "; ".join(malformed))
                return
            loop._enqueue(self.rt, job, run_id, proposed)  # noqa: SLF001

    async def _generate(self, conversation_id: str, content: str | None, turn: Turn) -> str:
        body = ChatRequest(
            conversation_id=conversation_id,
            content=content,
            model_id=turn.model_id,
            params=turn.params,
            tools=turn.tools,
            project=turn.project or None,
        )
        prepared = await runner.prepare(self.rt.db, self.rt.registry, self.rt.settings, body)
        self.rt.live.start(prepared.run_id, prepared.message_id, prepared.conversation_id)
        turn.live_run_id = prepared.run_id
        # Smart mode chooses on your message; the steps after it stay with that choice.
        turn.model_id = turn.model_id or prepared.model.id
        await generate(self.rt.db, self.rt.live, prepared)
        turn.live_run_id = ""
        with self.rt.db.session() as conn:
            message = repo.messages.get(conn, prepared.message_id)
        return message.content if message else ""

    def cancel(self, run_id: str) -> None:
        """Stop: the live answer keeps what it wrote, nothing waiting for you will run."""
        turn = self.turns.setdefault(run_id, Turn(tools=[]))
        turn.cancelled = True
        with self.rt.db.session() as conn:
            repo.tools.expire_pending(conn, run_id, "the chat turn was stopped")
        if turn.live_run_id:
            self.rt.live.stop(turn.live_run_id, "user_stop")
        if self.rt.approvals.is_driving(run_id):
            self.rt.approvals.notify(run_id)
        else:  # parked across a restart: nobody will wake to write it
            self._set(run_id, "cancelled", "stopped")

    def _finish(self, run_id: str, note: str) -> None:
        self._set(run_id, "done", note)

    def _set(self, run_id: str, status: JobRunStatus, note: str) -> None:
        with self.rt.db.session() as conn:
            repo.agents.set_status(conn, run_id, status, summary=note[:200])
