"""llama.cpp server: the primary provider.

It is the only backend that gives us all three of per-token logprobs, an exact tokenizer, and raw
prefix continuation - which is why the x-ray (4.3) and live steering (4.4) are built against it.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from server.models.params import SamplingParams
from server.models.provider import Capabilities, ModelInfo, ProviderInfo, ProviderKind
from server.providers import forcing, names
from server.providers.base import (
    PromptMessage,
    ProviderError,
    StreamItem,
    Token,
    Usage,
    capabilities_for,
)
from server.providers.httpsse import iter_sse_json
from server.providers.llamacpp_wire import probabilities, stop_reason

FALLBACK_TEMPLATE_NOTE = "chat template applied locally (backend has no /apply-template)"


class LlamaCppProvider:
    kind: ProviderKind = "llamacpp"

    def __init__(self, base_url: str, name: str = "llama.cpp", timeout: float = 600.0) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._props: dict[str, Any] = {}
        self._used_fallback_template = False

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout)

    async def info(self) -> ProviderInfo:
        caps = capabilities_for("llamacpp")
        try:
            async with self._client() as client:
                resp = await client.get("/props", timeout=5.0)
                resp.raise_for_status()
                self._props = resp.json()
                caps = Capabilities(
                    logprobs=True,
                    prefix_continuation=True,
                    embeddings=True,
                    tokenize=await self._has_tokenize(client),
                )
        except Exception as exc:  # noqa: BLE001 - surfaced verbatim in the UI
            return ProviderInfo(
                name=self.name,
                kind="llamacpp",
                base_url=self.base_url,
                online=False,
                capabilities=caps,
                detail=f"{type(exc).__name__}: {exc}",
            )
        models = [m.id for m in await self.list_models()]
        return ProviderInfo(
            name=self.name,
            kind="llamacpp",
            base_url=self.base_url,
            online=True,
            capabilities=caps,
            models=models,
        )

    async def _has_tokenize(self, client: httpx.AsyncClient) -> bool:
        try:
            resp = await client.post("/tokenize", json={"content": "x"}, timeout=5.0)
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    async def list_models(self) -> list[ModelInfo]:
        props = self._props or {}
        path = str(props.get("model_path") or "")
        gen = props.get("default_generation_settings") or {}
        ctx = int(gen.get("n_ctx") or props.get("n_ctx") or 4096)
        filename = names.basename(path) or "loaded model"
        return [
            ModelInfo(
                # The bare filename, on every OS: this is what the downloader pins and the
                # launcher matches, and on Windows it used to be the whole path, so they never met.
                id=f"llamacpp:{filename}",
                provider="llamacpp",
                display_name=names.friendly(filename) if path else "Local model",
                quant=names.quant_of(filename),
                ctx_len_max=ctx,
                file_path=path or None,
                supports_logprobs=True,
                supports_prefix=True,
            )
        ]

    async def count_tokens(self, text: str, model_id: str) -> int | None:
        try:
            async with self._client() as client:
                resp = await client.post("/tokenize", json={"content": text}, timeout=30.0)
                resp.raise_for_status()
                return len(resp.json().get("tokens", []))
        except Exception:  # noqa: BLE001 - caller falls back to an estimate and labels it
            return None

    async def build_prompt(
        self, messages: list[PromptMessage], thinking: bool | None = None
    ) -> str:
        """Prefer the model's own chat template; fall back to ChatML and say we did.

        `thinking` reaches the template as `enable_thinking`, which is how Qwen3-style models are
        told to answer directly. Templates without the variable ignore it.
        """
        payload: dict[str, Any] = {"messages": [m.model_dump() for m in messages]}
        if thinking is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": thinking}
        try:
            async with self._client() as client:
                resp = await client.post("/apply-template", json=payload, timeout=15.0)
                if resp.status_code == 200:
                    prompt = resp.json().get("prompt")
                    if isinstance(prompt, str) and prompt:
                        self._used_fallback_template = False
                        return prompt
        except Exception:  # noqa: BLE001
            pass
        self._used_fallback_template = True
        return chatml_prompt(messages)

    async def stream(
        self,
        messages: list[PromptMessage],
        params: SamplingParams,
        *,
        model_id: str,
        ctx_len: int,
        assistant_prefix: str | None = None,
    ) -> AsyncIterator[StreamItem]:
        prompt = await self.build_prompt(messages, params.thinking)
        if assistant_prefix:
            # Continuing the same prefix means llama.cpp reuses the KV cache for it.
            prompt += assistant_prefix

        def complete(
            text: str, n_predict: int, stop: list[str] | None
        ) -> AsyncIterator[StreamItem]:
            return self._complete(text, params, n_predict, stop)

        if params.min_thinking_tokens and params.thinking is not False:
            stream = forcing.forced(complete, prompt, params.max_tokens, params.min_thinking_tokens)
        else:
            stream = complete(prompt, params.max_tokens, None)
        async for item in stream:
            yield item

    async def _complete(
        self, prompt: str, params: SamplingParams, n_predict: int, stop: list[str] | None
    ) -> AsyncIterator[StreamItem]:
        body: dict[str, Any] = {
            "prompt": prompt,
            "n_predict": n_predict,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "top_k": params.top_k,
            "repeat_penalty": params.repeat_penalty,
            "seed": params.seed,
            "n_probs": params.n_probs,
            "cache_prompt": True,
            "stream": True,
        }
        if stop:
            body["stop"] = stop
        started = time.perf_counter()
        async with self._client() as client:
            try:
                async with client.stream("POST", "/completion", json=body) as resp:
                    if resp.status_code != 200:
                        detail = (await resp.aread()).decode(errors="replace")[:400]
                        raise ProviderError(f"llama.cpp returned {resp.status_code}: {detail}")
                    async for chunk in iter_sse_json(resp):
                        item = self._chunk_to_item(chunk, started)
                        if item is not None:
                            yield item
            except httpx.HTTPError as exc:
                raise ProviderError(f"llama.cpp connection failed: {exc}") from exc

    def _chunk_to_item(self, chunk: dict[str, Any], started: float) -> StreamItem | None:
        text = chunk.get("content") or ""
        if chunk.get("stop"):
            timings = chunk.get("timings") or {}
            return Usage(
                prompt_tokens=int(timings.get("prompt_n") or 0),
                gen_tokens=int(timings.get("predicted_n") or 0),
                prompt_eval_ms=int(timings.get("prompt_ms") or 0),
                gen_ms=int(timings.get("predicted_ms") or (time.perf_counter() - started) * 1000),
                stop_reason=stop_reason(chunk),
            )
        if not text:
            return None
        logprob, top = probabilities(chunk)
        return Token(
            text=text,
            logprob=logprob,
            top_alternatives=top,
            timing_ms=(time.perf_counter() - started) * 1000,
        )


def chatml_prompt(messages: list[PromptMessage]) -> str:
    parts = [f"<|im_start|>{m.role}\n{m.content}<|im_end|>\n" for m in messages]
    return "".join(parts) + "<|im_start|>assistant\n"
