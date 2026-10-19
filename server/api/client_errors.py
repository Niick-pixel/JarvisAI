"""Errors the window hit, written to jarvis.log: a crash in the UI leaves a trace you can send."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/client-errors", tags=["diagnostics"])
log = logging.getLogger("jarvis.ui")


class ClientError(BaseModel):
    where: str = Field(max_length=200)
    message: str = Field(max_length=8000)


@router.post("")
def report(error: ClientError) -> dict[str, str]:
    log.error("UI error in %s: %s", error.where, error.message)
    return {"status": "logged"}
