from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

AccountName = Literal["gmail", "github"]


class AccountStatus(BaseModel):
    name: AccountName
    connected: bool = False
    who: str = ""
    """The address or login it is connected as. Never the credential."""


class GmailConnect(BaseModel):
    address: str
    app_password: str


class GitHubConnect(BaseModel):
    token: str
