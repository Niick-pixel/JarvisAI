"""Reasoning models write their thinking inline, between `<think>` tags. It is theirs, not yours.

Qwen3, DeepSeek-R1 and their relatives emit `<think>…</think>` before the answer. That text is
worth being able to open, and worthless everywhere else: fed back as history it wastes context
and the model's own guidance says not to; handed to memory extraction it gets saved as "facts"
about you ("Wait, the user might be new…"). One parser, used everywhere those decisions are made.

Two shapes exist. Most templates let the model open the tag itself. Some put `<think>` into the
prompt, so the output starts mid-thought and only the closing tag appears.
"""

from __future__ import annotations

import re

OPEN, CLOSE = "<think>", "</think>"
_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def split(text: str) -> tuple[str, str, bool]:
    """(thinking, answer, still_thinking) - the last is True mid-stream, before `</think>`."""
    if CLOSE in text and OPEN not in text.split(CLOSE, 1)[0]:
        thought, answer = text.split(CLOSE, 1)
        return thought.strip(), answer.lstrip(), False
    start = text.find(OPEN)
    if start == -1:
        return "", text, False
    end = text.find(CLOSE, start)
    if end == -1:
        return text[start + len(OPEN) :].strip(), text[:start].rstrip(), True
    thought = text[start + len(OPEN) : end]
    answer = text[:start] + text[end + len(CLOSE) :]
    return thought.strip(), answer.strip(), False


def strip(text: str) -> str:
    """Just the answer. A reply still mid-thought has no answer yet, so it is empty."""
    return split(text)[1]


def strip_all(text: str) -> str:
    """For utility output that should never contain thinking but might anyway."""
    cleaned = _BLOCK.sub("", text)
    return strip(cleaned)
