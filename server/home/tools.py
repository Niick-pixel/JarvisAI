"""Home Assistant for agents: read every device's state freely, and change one only through the
approval gate - a job that wants to unlock the door asks you first, every time."""

from __future__ import annotations

from server.home.client import HomeError
from server.home.hub import Hub
from server.models.home import HomeActionRequest
from server.tools.builtin import ToolContext, ToolResult
from server.tools.sandbox import Denied


def _hub(ctx: ToolContext) -> Hub:
    return Hub(ctx.settings.paths.data_dir)


async def home_devices(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    try:
        found = await _hub(ctx).devices()
    except HomeError as exc:
        raise Denied(str(exc)) from exc
    lines = []
    for d in found:
        reading = f" {d.current:g}{d.unit}" if d.current is not None else ""
        level = f" level {d.level:g}%" if d.level is not None else ""
        lines.append(f"{d.area} | {d.name} ({d.entity_id}): {d.state}{reading}{level}")
    return ToolResult("\n".join(lines) or "No devices.", "home assistant")


async def home_control(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    raw = args.get("value")
    try:
        request = HomeActionRequest(
            entity_id=str(args.get("entity_id", "")),
            action=str(args.get("action", "")),  # type: ignore[arg-type]
            value=float(str(raw)) if raw not in (None, "") else None,
        )
        await _hub(ctx).act(request)
    except (ValueError, HomeError) as exc:
        raise Denied(str(exc)) from exc
    return ToolResult(f"{request.action} sent to {request.entity_id}.", request.entity_id)
