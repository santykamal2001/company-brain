"""
LLM-agnostic adapter. All callers use complete() or stream(); they never
touch the underlying SDK directly. Swap providers via LLM_PROVIDER env var.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator

from config import get_settings

settings = get_settings()


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


class LLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        """Yield text tokens as they arrive from the provider."""
        ...

    @abstractmethod
    async def complete_with_cache(
        self,
        system: str,
        cached_prefix: str,
        user: str,
        max_tokens: int = 512,
    ) -> LLMResponse:
        """
        Anthropic prompt-caching variant: cached_prefix is marked ephemeral.
        Falls back to complete() on non-Anthropic providers.
        """
        ...

    @abstractmethod
    async def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> dict | list:
        """Returns parsed JSON. Raises ValueError on parse failure."""
        ...


# ─── Anthropic ────────────────────────────────────────────────────────────────

class ClaudeClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        import anthropic as _anthropic
        self._client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = model or settings.llm_model

    async def complete(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> LLMResponse:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        usage = resp.usage
        return LLMResponse(
            text=resp.content[0].text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )

    async def stream(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as s:
            async for text in s.text_stream:
                yield text

    async def complete_with_cache(self, system: str, cached_prefix: str, user: str, max_tokens: int = 512) -> LLMResponse:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": cached_prefix,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": user},
                    ],
                }
            ],
        )
        usage = resp.usage
        return LLMResponse(
            text=resp.content[0].text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )

    async def complete_json(self, system: str, user: str, max_tokens: int = 1024) -> dict | list:
        resp = await self.complete(system, user + "\n\nRespond with valid JSON only.", max_tokens)
        return _parse_json(resp.text)


# ─── OpenAI ───────────────────────────────────────────────────────────────────

class OpenAIClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = model or settings.llm_model

    async def complete(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    async def stream(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> AsyncIterator[str]:
        async with await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            stream=True,
        ) as s:
            async for chunk in s:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

    async def complete_with_cache(self, system: str, cached_prefix: str, user: str, max_tokens: int = 512) -> LLMResponse:
        return await self.complete(system, cached_prefix + "\n\n" + user, max_tokens)

    async def complete_json(self, system: str, user: str, max_tokens: int = 1024) -> dict | list:
        resp = await self.complete(system, user + "\n\nRespond with valid JSON only.", max_tokens)
        return _parse_json(resp.text)


# ─── Azure OpenAI ─────────────────────────────────────────────────────────────

class AzureOpenAIClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        from openai import AsyncAzureOpenAI
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version="2024-08-01-preview",
        )
        self._model = model or settings.azure_openai_deployment

    async def complete(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    async def stream(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> AsyncIterator[str]:
        async with await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            stream=True,
        ) as s:
            async for chunk in s:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

    async def complete_with_cache(self, system: str, cached_prefix: str, user: str, max_tokens: int = 512) -> LLMResponse:
        return await self.complete(system, cached_prefix + "\n\n" + user, max_tokens)

    async def complete_json(self, system: str, user: str, max_tokens: int = 1024) -> dict | list:
        resp = await self.complete(system, user + "\n\nRespond with valid JSON only.", max_tokens)
        return _parse_json(resp.text)


# ─── Ollama ───────────────────────────────────────────────────────────────────

class OllamaClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        import httpx
        self._http = httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120)
        self._model = model or settings.llm_model

    async def complete(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> LLMResponse:
        resp = await self._http.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(text=data["message"]["content"])

    async def stream(self, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.0) -> AsyncIterator[str]:
        async with self._http.stream(
            "POST",
            "/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": True,
            },
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    async def complete_with_cache(self, system: str, cached_prefix: str, user: str, max_tokens: int = 512) -> LLMResponse:
        return await self.complete(system, cached_prefix + "\n\n" + user, max_tokens)

    async def complete_json(self, system: str, user: str, max_tokens: int = 1024) -> dict | list:
        resp = await self.complete(system, user + "\n\nRespond with valid JSON only.", max_tokens)
        return _parse_json(resp.text)


# ─── Factory ──────────────────────────────────────────────────────────────────

_PROVIDER_MAP: dict[str, type[LLMClient]] = {
    "claude": ClaudeClient,
    "openai": OpenAIClient,
    "azure": AzureOpenAIClient,
    "ollama": OllamaClient,
}


def get_llm(provider: str | None = None, model: str | None = None) -> LLMClient:
    p = (provider or settings.llm_provider).lower()
    cls = _PROVIDER_MAP.get(p)
    if cls is None:
        raise ValueError(f"Unknown LLM provider: {p!r}. Choose from {list(_PROVIDER_MAP)}")
    return cls(model=model)


def get_extraction_llm() -> LLMClient:
    return get_llm(
        provider=settings.extraction_llm_provider,
        model=settings.extraction_llm_model,
    )


def get_context_llm() -> LLMClient:
    return get_llm(
        provider=settings.context_llm_provider,
        model=settings.context_llm_model,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict | list:
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {text[:200]}") from exc
