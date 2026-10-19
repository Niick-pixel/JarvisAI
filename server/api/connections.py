"""Settings > Accounts: connect Gmail or GitHub, see which account, disconnect.

Connecting checks the credential against the service first, so a typo is caught here and not the
first time an agent tries to read your mail.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from server.connections.github import GitHub, GitHubError
from server.connections.gmail import Gmail, GmailError
from server.connections.store import Accounts
from server.deps import State
from server.errors import SovereignError
from server.models.connections import AccountName, AccountStatus, GitHubConnect, GmailConnect

router = APIRouter(prefix="/api/connections", tags=["connections"])


def _accounts(state: State) -> Accounts:
    return Accounts(state.settings.paths.data_dir)


def _status(accounts: Accounts) -> list[AccountStatus]:
    names: tuple[AccountName, ...] = ("gmail", "github")
    return [
        AccountStatus(name=n, connected=True, who=str(saved.get("who", "")))
        if (saved := accounts.get(n))
        else AccountStatus(name=n)
        for n in names
    ]


@router.get("")
def status(state: State) -> list[AccountStatus]:
    return _status(_accounts(state))


@router.put("/gmail")
async def connect_gmail(body: GmailConnect, state: State) -> list[AccountStatus]:
    address = body.address.strip()
    try:
        await asyncio.to_thread(Gmail(address, body.app_password).verify)
    except GmailError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc
    accounts = _accounts(state)
    accounts.save("gmail", body.app_password.replace(" ", ""), address=address, who=address)
    return _status(accounts)


@router.put("/github")
async def connect_github(body: GitHubConnect, state: State) -> list[AccountStatus]:
    token = body.token.strip()
    try:
        login = await GitHub(token).login()
    except GitHubError as exc:
        raise SovereignError("invalid_request", str(exc)) from exc
    accounts = _accounts(state)
    accounts.save("github", token, who=login)
    return _status(accounts)


@router.delete("/{name}")
def disconnect(name: AccountName, state: State) -> list[AccountStatus]:
    accounts = _accounts(state)
    accounts.remove(name)
    return _status(accounts)
