"""What a tool declaration is. Its own module so groups of tools can live in their own files."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from server.models.tools import TargetKind
from server.tools.builtin import ToolContext, ToolResult

Runner = Callable[[ToolContext, dict[str, Any]], Awaitable[ToolResult]]


@dataclass(frozen=True)
class Tool:
    name: str
    summary: str
    side_effect: bool
    """Side effects pass the approval gate. Reads are confined by the sandbox instead."""
    target_kind: TargetKind
    args: tuple[str, ...]
    example: str
    run: Runner
    target: Callable[[dict[str, Any]], str]
    """What this call would touch, worked out before it runs, for the approval card and the log."""
