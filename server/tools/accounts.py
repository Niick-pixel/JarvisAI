"""Gmail and GitHub tools (server/connections). Reads run freely; drafts and comments ask first."""

from __future__ import annotations

from typing import Any

from server.tools.builtin import ToolContext, ToolResult
from server.tools.tooldef import Runner, Tool


def _account(name: str) -> Runner:
    async def run(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
        # Imported here: the connections package reaches back into tools for ToolResult.
        from server.connections import tools

        result: ToolResult = await getattr(tools, name)(ctx, args)
        return result

    return run


def _issue(args: dict[str, Any]) -> str:
    return f"{args.get('repo', '')}#{str(args.get('number', '')).lstrip('#')}"


def _service(name: str) -> Any:
    service = "gmail" if name.startswith("email_") else "github"
    return lambda args: service


def _tool(name: str, summary: str, args: tuple[str, ...], example: str, **kw: Any) -> Tool:
    return Tool(
        name=name,
        summary=summary,
        side_effect=kw.get("side_effect", False),
        target_kind="none",
        args=args,
        example=example,
        run=_account(name),
        target=kw.get("target", _service(name)),
    )


ACCOUNT_TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        _tool(
            "email_search",
            "Search the user's Gmail with Gmail search syntax (from:, subject:, is:unread, "
            "newer_than:7d). Returns id, date, sender, subject and a snippet.",
            ("query", "limit"),
            '{"tool": "email_search", "args": {"query": "is:unread newer_than:2d"}}',
        ),
        _tool(
            "email_read",
            "Read one Gmail message in full, by the id email_search returned.",
            ("id",),
            '{"tool": "email_read", "args": {"id": "48213"}}',
        ),
        _tool(
            "email_draft",
            "Save a draft in the user's Gmail Drafts. Never sends.",
            ("to", "subject", "body"),
            '{"tool": "email_draft", "args": {"to": "a@b.com", "subject": "Hi", "body": "..."}}',
            side_effect=True,
            target=lambda a: f"draft to {a.get('to', '')}",
        ),
        _tool(
            "github_notifications",
            "The user's unread GitHub notifications.",
            ("limit",),
            '{"tool": "github_notifications", "args": {}}',
        ),
        _tool(
            "github_search",
            "Search GitHub issues and pull requests (GitHub search syntax, e.g. "
            "'is:pr is:open author:@me' or 'repo:owner/name is:issue label:bug').",
            ("query", "limit"),
            '{"tool": "github_search", "args": {"query": "is:pr is:open review-requested:@me"}}',
        ),
        _tool(
            "github_read",
            "Read one GitHub issue or pull request with its comments.",
            ("repo", "number"),
            '{"tool": "github_read", "args": {"repo": "owner/name", "number": 12}}',
            target=_issue,
        ),
        _tool(
            "github_comment",
            "Post a comment on a GitHub issue or pull request as the user.",
            ("repo", "number", "body"),
            '{"tool": "github_comment", "args": {"repo": "o/n", "number": 12, "body": "..."}}',
            side_effect=True,
            target=_issue,
        ),
    )
}
