"""Gmail and GitHub as agent tools. Reading is free; anything that writes - a draft, a comment -
goes through the approval gate like every other side effect. What comes back is data: the agent
loop wraps it in the same envelope as a web page, so an email cannot give Jarvis orders."""

from __future__ import annotations

import asyncio
from typing import Any

from server.connections.github import GitHub, GitHubError
from server.connections.gmail import Gmail, GmailError
from server.connections.store import Accounts
from server.tools.builtin import ToolContext, ToolResult
from server.tools.sandbox import Denied


def _gmail(ctx: ToolContext) -> Gmail:
    accounts = Accounts(ctx.settings.paths.data_dir)
    saved = accounts.get("gmail")
    if not saved:
        raise Denied("Gmail is not connected. Connect it in Settings > Accounts.")
    return Gmail(str(saved.get("address", "")), accounts.credential("gmail"))


def _github(ctx: ToolContext) -> GitHub:
    accounts = Accounts(ctx.settings.paths.data_dir)
    if not accounts.get("github"):
        raise Denied("GitHub is not connected. Connect it in Settings > Accounts.")
    return GitHub(accounts.credential("github"))


def _limit(args: dict[str, Any], default: int) -> int:
    try:
        return max(1, min(int(str(args.get("limit", default))), 25))
    except ValueError:
        return default


async def email_search(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = str(args.get("query", "")).strip() or "in:inbox"
    try:
        out = await asyncio.to_thread(_gmail(ctx).search, query, _limit(args, 10))
    except GmailError as exc:
        raise Denied(str(exc)) from exc
    return ToolResult(out, "gmail")


async def email_read(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    try:
        out = await asyncio.to_thread(_gmail(ctx).read, str(args.get("id", "")))
    except GmailError as exc:
        raise Denied(str(exc)) from exc
    return ToolResult(out, "gmail")


async def email_draft(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    to, subject = str(args.get("to", "")), str(args.get("subject", ""))
    try:
        out = await asyncio.to_thread(_gmail(ctx).draft, to, subject, str(args.get("body", "")))
    except GmailError as exc:
        raise Denied(str(exc)) from exc
    return ToolResult(out, f"draft to {to}")


async def github_notifications(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    try:
        return ToolResult(await _github(ctx).notifications(_limit(args, 20)), "github")
    except GitHubError as exc:
        raise Denied(str(exc)) from exc


async def github_search(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = str(args.get("query", "")).strip() or "involves:@me is:open"
    try:
        return ToolResult(await _github(ctx).search(query, _limit(args, 15)), "github")
    except GitHubError as exc:
        raise Denied(str(exc)) from exc


def _issue(args: dict[str, Any]) -> tuple[str, int]:
    repo, number = str(args.get("repo", "")).strip(), str(args.get("number", "")).lstrip("#")
    if "/" not in repo or not number.isdigit():
        raise Denied('Give "repo" as owner/name and "number" as the issue or PR number.')
    return repo, int(number)


async def github_read(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    repo, number = _issue(args)
    try:
        return ToolResult(await _github(ctx).read(repo, number), f"{repo}#{number}")
    except GitHubError as exc:
        raise Denied(str(exc)) from exc


async def github_comment(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    repo, number = _issue(args)
    try:
        url = await _github(ctx).comment(repo, number, str(args.get("body", "")))
    except GitHubError as exc:
        raise Denied(str(exc)) from exc
    return ToolResult(f"Comment posted: {url}", f"{repo}#{number}")
