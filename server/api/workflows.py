"""Workflows by example: draft a scheduled agent from your words or from a chat, and see how each
one has been doing. Drafts are never saved here - creating one goes through /api/agents/jobs."""

from __future__ import annotations

from fastapi import APIRouter

from server.agents import drafting
from server.db import repo
from server.deps import State
from server.errors import NotFound
from server.models.workflows import DraftRequest, JobDraft, JobStats

router = APIRouter(prefix="/api/agents", tags=["agents"])
RECENT = 14


@router.post("/drafts")
async def draft(body: DraftRequest, state: State) -> JobDraft:
    return await drafting.draft(state.db, state.registry, state.settings, body.description)


@router.post("/drafts/from-conversation/{conversation_id}")
async def draft_from_chat(conversation_id: str, state: State) -> JobDraft:
    with state.db.session() as conn:
        if repo.conversations.get(conn, conversation_id) is None:
            raise NotFound("Conversation")
    request, used = drafting.example(state.db, conversation_id)
    return await drafting.draft(
        state.db, state.registry, state.settings, request, used_tools=used or None
    )


@router.get("/dashboard")
def dashboard(state: State) -> list[JobStats]:
    out: list[JobStats] = []
    with state.db.session() as conn:
        for job in repo.agents.list_jobs(conn):
            rows = conn.execute(
                "SELECT status, started_at, finished_at FROM job_runs WHERE job_id = ?"
                " ORDER BY started_at DESC",
                (job.id,),
            ).fetchall()
            finished = [r for r in rows if r["finished_at"]]
            durations = [(r["finished_at"] - r["started_at"]) / 1000 for r in finished]
            out.append(
                JobStats(
                    job_id=job.id,
                    runs=len(rows),
                    ok=sum(r["status"] == "done" for r in rows),
                    failed=sum(r["status"] == "failed" for r in rows),
                    waiting=sum(r["status"] == "waiting_approval" for r in rows),
                    recent=[r["status"] for r in reversed(rows[:RECENT])],
                    last_finished_at=finished[0]["finished_at"] if finished else None,
                    avg_seconds=sum(durations) / len(durations) if durations else None,
                )
            )
    return out
