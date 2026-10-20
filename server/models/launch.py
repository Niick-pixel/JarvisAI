"""What `make dev` did about llama.cpp, and why (PLAN.md 8.3)."""

from __future__ import annotations

from pydantic import BaseModel


class LaunchStatus(BaseModel):
    autostart: bool
    started: bool
    """True only when this process spawned the server. A backend you started yourself is left
    alone, and says so rather than being restarted underneath you."""
    pid: int | None = None
    model_path: str = ""
    ctx_len: int = 0
    command: list[str] = []
    """The exact argv, so you can run it yourself when something about it is wrong."""
    log_path: str = ""
    detail: str = ""
    """Plain sentence: what happened, or the reason nothing did."""
    loading: bool = False
    """llama-server is starting and reading the model: the chat cannot answer yet."""
    load_stage: str = ""
    """Where the load is, from llama-server's own log: reading, placing layers, warming up."""
    load_started_at: float = 0.0
    """Unix seconds."""
    load_expected_s: float = 0.0
    """How long this model took last time (or a guess from its size the first time)."""
