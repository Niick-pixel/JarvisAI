"""Heavy thinking: budget forcing, so a reasoning model thinks at least as long as asked.

A reasoning model decides for itself when it has thought enough, and often decides early. Budget
forcing (Muennighoff et al., "s1: Simple test-time scaling", 2025) overrules that: generation is
stopped at `</think>`, and while the thinking is shorter than the budget a short nudge ("Wait,
...") is appended and the model continues from exactly there. Each continuation reuses the KV
cache, so this costs only the extra tokens it buys - which is the point: more tokens of
reasoning, measurably better answers on hard problems.

It needs raw prompt control, so it runs on llama.cpp. Providers that only take chat messages get
thinking switched on and nothing more.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from server.providers.base import StreamItem, Token, Usage

END_THINK = "</think>"
MAX_NUDGES = 6
"""A model that keeps trying to stop is told to continue this many times, then allowed to."""
NUDGES = (
    "\n\nWait, let me double-check that.",
    "\n\nWait, is there another way to look at this?",
    "\n\nHmm, let me verify each step before answering.",
    "\n\nWait, what could I be missing?",
)

Complete = Callable[[str, int, list[str] | None], AsyncIterator[StreamItem]]
"""(prompt, tokens left, stop strings) -> the stream of one completion."""


async def forced(
    complete: Complete, prompt: str, max_tokens: int, min_thinking: int
) -> AsyncIterator[StreamItem]:
    generated = ""
    spent = 0
    nudges = 0
    total = Usage()
    while True:
        forcing = spent < min_thinking and nudges < MAX_NUDGES
        usage = Usage()
        async for item in complete(
            prompt + generated, max_tokens - spent, [END_THINK] if forcing else None
        ):
            if isinstance(item, Token):
                generated += item.text
                spent += 1
                yield item
            else:
                usage = item
        total = Usage(
            prompt_tokens=total.prompt_tokens or usage.prompt_tokens,
            gen_tokens=total.gen_tokens + usage.gen_tokens,
            prompt_eval_ms=total.prompt_eval_ms + usage.prompt_eval_ms,
            gen_ms=total.gen_ms + usage.gen_ms,
            stop_reason=usage.stop_reason,
        )
        # Stopped at </think>, which only happens because we asked it to. Under budget: say "wait"
        # and let it keep thinking. Budget met: resume with no stop, so it closes the thinking
        # itself and writes the answer.
        if usage.stop_reason != "stop_word" or spent >= max_tokens:
            yield total
            return
        if spent < min_thinking and nudges < MAX_NUDGES:
            nudge = NUDGES[nudges % len(NUDGES)]
            nudges += 1
            generated += nudge
            yield Token(text=nudge)
