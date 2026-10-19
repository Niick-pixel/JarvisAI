"""The Files workspace: folders you opened, what is in them, and changes Jarvis proposes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Root(BaseModel):
    id: str
    path: str
    name: str


class RootCreate(BaseModel):
    path: str


class Entry(BaseModel):
    name: str
    path: str
    """Relative to the root, with forward slashes."""
    dir: bool
    size: int = 0


FileKind = Literal["text", "docx"]


class FileContent(BaseModel):
    root: str
    path: str
    kind: FileKind
    text: str
    """For a Word document, one paragraph per line; headings start with #, ## and so on."""
    version: str
    """A hash of the file on disk. A save or an apply against an older version is refused."""
    size: int
    note: str = ""
    can_undo: bool = False


class SaveRequest(BaseModel):
    root: str
    path: str
    text: str
    version: str


class Hunk(BaseModel):
    index: int
    old_start: int
    """1-based line where the change starts in the current file."""
    old: list[str]
    new: list[str]
    before: list[str] = []
    after: list[str] = []
    """A few unchanged lines either side, for reading the change in place."""


class ProposeRequest(BaseModel):
    root: str
    path: str
    instruction: str
    model_id: str | None = None
    thinking: bool | None = None


class Proposal(BaseModel):
    id: str
    root: str
    path: str
    version: str
    summary: str
    hunks: list[Hunk]
    failed: list[str] = []
    """Edits the model asked for whose text could not be found in the file, shown, never guessed."""
    model_id: str = ""
    elapsed_ms: int = 0


class ApplyRequest(BaseModel):
    hunks: list[int] | None = None
    """Which hunks to apply. None applies all of them."""


class FileRef(BaseModel):
    root: str
    path: str


class RunRequest(BaseModel):
    root: str
    command: str


class RunResult(BaseModel):
    command: str
    exit_code: int
    output: str
    elapsed_ms: int
    timed_out: bool = False
