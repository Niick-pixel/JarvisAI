"""How a model's edit reaches a file: search/replace blocks, a diff of hunks, the hunks you keep.

Rewriting a whole file is too slow and too error-prone for a local model on anything but a short
file. Instead it answers with blocks like aider's:

    <<<<<<< SEARCH
    exact lines from the file
    =======
    what they become
    >>>>>>> REPLACE

Each SEARCH is found in the file - exactly, or failing that line by line ignoring indentation and
trailing spaces - and replaced. A block whose text is not in the file is reported back, never
applied somewhere it might fit. The result is then diffed against the original into hunks, so you
accept or reject each change on its own.
"""

from __future__ import annotations

import difflib
import re

from server.models.files import Hunk

BLOCK = re.compile(
    r"<{5,9} ?SEARCH[^\n]*\n(.*?)\n?={5,9}[^\n]*\n(.*?)\n?>{5,9} ?REPLACE", re.DOTALL
)
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
SUMMARY = re.compile(r"^\s*Summary:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
CONTEXT = 2


def parse(reply: str, original: str) -> tuple[list[tuple[str, str]], str]:
    """(blocks, summary). A reply that is only a fenced copy of the whole file counts as one block
    replacing everything: small models do that despite the instructions."""
    blocks = [(m.group(1), m.group(2)) for m in BLOCK.finditer(reply)]
    found = SUMMARY.search(reply)
    summary = found.group(1).strip() if found else ""
    if not blocks:
        fenced = FENCE.findall(reply)
        if len(fenced) == 1 and len(fenced[0]) >= len(original) * 0.5:
            blocks = [
                (original, fenced[0].rstrip("\n") + ("\n" if original.endswith("\n") else ""))
            ]
    return blocks, summary


def _loose_find(lines: list[str], wanted: list[str]) -> int:
    """Index of the first run of lines equal to `wanted` ignoring surrounding whitespace, or -1."""
    target = [w.strip() for w in wanted]
    if not any(target):
        return -1
    for start in range(len(lines) - len(target) + 1):
        if [line.strip() for line in lines[start : start + len(target)]] == target:
            return start
    return -1


def apply_blocks(text: str, blocks: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """(new text, the SEARCH texts that were not found)."""
    failed: list[str] = []
    for search, replace in blocks:
        if search and search in text:
            text = text.replace(search, replace, 1)
            continue
        lines = text.split("\n")
        wanted = search.split("\n")
        at = _loose_find(lines, wanted)
        if at < 0:
            failed.append(search.strip()[:200])
            continue
        lines[at : at + len(wanted)] = replace.split("\n")
        text = "\n".join(lines)
    return text, failed


def hunks(old: str, new: str) -> list[Hunk]:
    a, b = old.split("\n"), new.split("\n")
    out: list[Hunk] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        out.append(
            Hunk(
                index=len(out),
                old_start=i1 + 1,
                old=a[i1:i2],
                new=b[j1:j2],
                before=a[max(0, i1 - CONTEXT) : i1],
                after=a[i2 : i2 + CONTEXT],
            )
        )
    return out


def apply_hunks(old: str, new: str, keep: set[int] | None) -> str:
    """The original with only the chosen hunks applied (all of them when `keep` is None)."""
    a, b = old.split("\n"), new.split("\n")
    result: list[str] = []
    index = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            result.extend(a[i1:i2])
            continue
        result.extend(b[j1:j2] if keep is None or index in keep else a[i1:i2])
        index += 1
    return "\n".join(result)
