"""Ollama. Autodetected on its default port; reached through its OpenAI-compatible surface.

Ollama does not return logprobs, so the x-ray toggle is absent for its models rather than
greyed-out-and-lying (BRIEF.md 4.3).
"""

from __future__ import annotations

import httpx

from server.models.provider import ModelInfo, ProviderKind
from server.providers import names
from server.providers.openai_compat import OpenAICompatProvider


class OllamaProvider(OpenAICompatProvider):
    kind: ProviderKind = "ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 600.0) -> None:
        super().__init__(base_url, name="ollama", kind="ollama", timeout=timeout)

    async def list_models(self) -> list[ModelInfo]:
        """/api/tags carries the real context length and file size; /v1/models does not."""
        async with self._client() as client:
            resp = await client.get("/api/tags", timeout=10.0)
            resp.raise_for_status()
            entries = resp.json().get("models", [])
            out: list[ModelInfo] = []
            for entry in entries:
                name = str(entry.get("name", ""))
                if not name:
                    continue
                details = entry.get("details") or {}
                out.append(
                    ModelInfo(
                        id=f"ollama:{name}",
                        provider="ollama",
                        display_name=name,
                        ctx_len_max=(shown := await self._show(client, name))[0],
                        quant=details.get("quantization_level"),
                        size_bytes=entry.get("size"),
                        supports_logprobs=False,
                        supports_prefix=False,
                        supports_vision=shown[1] or names.looks_visual(name),
                    )
                )
        return out

    async def _show(self, client: httpx.AsyncClient, name: str) -> tuple[int, bool]:
        """Its context length, and whether Ollama says it can see ("vision" in capabilities)."""
        try:
            resp = await client.post("/api/show", json={"model": name}, timeout=10.0)
            resp.raise_for_status()
            shown = resp.json()
            info = shown.get("model_info") or {}
            vision = "vision" in (shown.get("capabilities") or [])
            for key, value in info.items():
                if key.endswith(".context_length"):
                    return int(value), vision
            return self.default_ctx, vision
        except Exception:  # noqa: BLE001 - fall back to the documented default
            return self.default_ctx, False
