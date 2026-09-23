"""Turning a GGUF filename into what a person would call the model.

`C:\\Users\\you\\AppData\\Local\\Jarvis\\models\\Qwen3-8B-Q4_K_M.gguf` is a path, not a name. The
UI showed exactly that, because the old code split on "/" and Windows paths have none.
"""

from __future__ import annotations

import re

QUANT = re.compile(
    r"[-_.](?:I?Q\d(?:_[0-9A-Z]+)*|F16|BF16|F32|FP16|MXFP4)(?=[-_.]|$)", re.IGNORECASE
)
ACRONYMS = {"gpt": "GPT", "oss": "OSS", "moe": "MoE", "vl": "VL", "r1": "R1", "qwq": "QwQ"}
NOISE = re.compile(r"[-_.](?:gguf|instruct|chat|it|imat(?:rix)?)(?=[-_.]|$)", re.IGNORECASE)


def basename(path: str) -> str:
    return re.split(r"[\\/]", path)[-1]


def quant_of(filename: str) -> str | None:
    match = QUANT.search(basename(filename).removesuffix(".gguf"))
    return match.group(0)[1:].upper() if match else None


def friendly(path: str) -> str:
    """`Qwen3-8B-Q4_K_M.gguf` -> `Qwen3 8B`; `llama-3.1-8b-instruct-q4_k_m` -> `Llama 3.1 8B`."""
    stem = basename(path)
    stem = re.sub(r"\.gguf$", "", stem, flags=re.IGNORECASE)
    stem = QUANT.sub("", stem)
    stem = NOISE.sub("", stem)
    words = [w for w in re.split(r"[-_ ]+", stem) if w]
    if not words:
        return "Local model"
    out = []
    for word in words:
        if word.lower() in ACRONYMS:
            out.append(ACRONYMS[word.lower()])
        elif re.fullmatch(r"\d+(\.\d+)?[bm]", word, re.IGNORECASE):
            out.append(word.upper())  # 8b -> 8B
        elif word.islower():
            out.append(word[0].upper() + word[1:])  # llama -> Llama, keeps qwen3 -> Qwen3
        else:
            out.append(word)
    return " ".join(out)
