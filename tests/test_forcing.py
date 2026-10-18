"""Heavy thinking: a model that tries to stop thinking early is told to wait, until the budget."""

from __future__ import annotations

from collections.abc import AsyncIterator

from server.providers import forcing
from server.providers.base import StreamItem, Token, Usage


class Model:
    """Thinks in 3-token bursts and then tries to close </think>; answers once allowed to."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str] | None]] = []

    async def complete(
        self, prompt: str, left: int, stop: list[str] | None
    ) -> AsyncIterator[StreamItem]:
        self.calls.append((prompt, stop))
        for word in ("a", "b", "c"):
            yield Token(text=word)
        if stop:
            yield Usage(gen_tokens=3, stop_reason="stop_word")  # halted at </think>
            return
        for word in ("</think>", "answer"):
            yield Token(text=word)
        yield Usage(gen_tokens=5, stop_reason="eos")


async def run(min_thinking: int, max_tokens: int = 100) -> tuple[str, Usage, Model]:
    model = Model()
    text, usage = "", Usage()
    async for item in forcing.forced(model.complete, "Q:", max_tokens, min_thinking):
        if isinstance(item, Token):
            text += item.text
        else:
            usage = item
    return text, usage, model


async def test_it_keeps_thinking_until_the_budget_then_answers() -> None:
    text, usage, model = await run(min_thinking=7)
    assert text.count("Wait") + text.count("Hmm") == 2
    assert text.endswith("</think>answer")
    # Two nudges, the stop at the budget, then a resume with no stop to write the answer.
    assert [stop for _, stop in model.calls] == [["</think>"]] * 3 + [None]
    assert model.calls[1][0].startswith("Q:abc\n\nWait")  # continues from exactly where it was
    assert usage.stop_reason == "eos" and usage.gen_tokens == 3 + 3 + 3 + 5


async def test_without_a_budget_it_is_one_ordinary_completion() -> None:
    text, _, model = await run(min_thinking=0)
    assert text == "abc</think>answer" and len(model.calls) == 1 and model.calls[0][1] is None


async def test_a_stubborn_model_is_let_go_after_the_nudge_limit() -> None:
    _, _, model = await run(min_thinking=10_000)
    assert len(model.calls) == forcing.MAX_NUDGES + 1
