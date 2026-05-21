from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from app.config import settings


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    def complete(self, system: str, user: str, *, temperature: float = 0.3) -> LLMResponse: ...


class AnthropicProvider:
    def __init__(self, model: str | None = None) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._model = model or settings.anthropic_model

    def complete(self, system: str, user: str, *, temperature: float = 0.3) -> LLMResponse:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )


class OllamaProvider:
    """Stub for local Ollama; not the default. Enable with TINTIN_LLM_PROVIDER=ollama."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or settings.ollama_model
        self._host = settings.ollama_host

    def complete(self, system: str, user: str, *, temperature: float = 0.3) -> LLMResponse:
        import httpx

        r = httpx.post(
            f"{self._host}/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"temperature": temperature},
                "stream": False,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        text = data.get("message", {}).get("content", "")
        # Ollama doesn't report tokens uniformly; estimate.
        return LLMResponse(
            text=text,
            input_tokens=len(system + user) // 4,
            output_tokens=len(text) // 4,
        )


def get_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown TINTIN_LLM_PROVIDER: {settings.llm_provider}")
