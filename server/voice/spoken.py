"""What a voice should say: the words of an answer, not its formatting.

Every path to the speaker - voice mode, "read aloud", briefings, trading alerts - passes through
here, so an emoji is never read out by its Unicode name ("grinning face with smiling eyes"), a
bullet is never "asterisk", and a code block is mentioned rather than spelled out.
"""

from __future__ import annotations

import re
import unicodedata

CODE_BLOCK = re.compile(r"```.*?(```|$)", re.S)
INLINE_CODE = re.compile(r"`([^`]*)`")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
URL = re.compile(r"https?://\S+|www\.\S+")
LINE_MARK = re.compile(r"^\s{0,3}(#{1,6}|>|[-*+•]|\d+[.)])\s+", re.M)
EMPHASIS = re.compile(r"[*_~|#]+")
SPACES = re.compile(r"[ \t]+")
# Joiners and selectors that glue emoji sequences together; alone they are silent but confuse TTS.
GLUE = {"‍", "︎", "️", "⃣"}


def _is_pictograph(ch: str) -> bool:
    if ch in GLUE:
        return True
    if "\U0001f1e6" <= ch <= "\U0001f1ff":  # regional indicators (flags)
        return True
    if "\U0001f3fb" <= ch <= "\U0001f3ff":  # skin tones
        return True
    # Symbols from arrows up - emoji, dingbats, pictographs. Below that (°, ©, ™) Piper reads well.
    return ch >= "\u2190" and unicodedata.category(ch) == "So"


def for_speech(text: str) -> str:
    out = CODE_BLOCK.sub(" I've put the code on screen. ", text)
    out = INLINE_CODE.sub(r"\1", out)
    out = IMAGE.sub("", out)
    out = LINK.sub(r"\1", out)
    out = URL.sub("a link", out)
    out = LINE_MARK.sub("", out)
    out = EMPHASIS.sub("", out)
    out = "".join(ch for ch in out if not _is_pictograph(ch))
    lines = (SPACES.sub(" ", line).strip() for line in out.splitlines())
    return "\n".join(line for line in lines if line)
