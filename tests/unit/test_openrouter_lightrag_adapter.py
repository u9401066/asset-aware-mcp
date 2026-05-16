"""OpenRouter backend helpers should stay OpenAI-compatible and bounded."""

from __future__ import annotations

import sys
import types
from importlib import import_module
from typing import ClassVar

import pytest

lightrag_adapter = import_module("src.infrastructure.lightrag_adapter")


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    requests: ClassVar[list[dict]] = []

    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def post(self, url: str, *, headers: dict, json: dict) -> _FakeResponse:
        self.requests.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse({"choices": [{"message": {"content": "draft summary"}}]})


@pytest.mark.asyncio
async def test_openrouter_model_complete_uses_openai_compatible_chat_api(
    monkeypatch,
) -> None:
    fake_httpx = types.SimpleNamespace(AsyncClient=_FakeAsyncClient)
    _FakeAsyncClient.requests.clear()
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(lightrag_adapter.settings, "openrouter_api_key", "sk-or-test")
    monkeypatch.setattr(
        lightrag_adapter.settings,
        "openrouter_base_url",
        "https://openrouter.ai/api/v1/",
    )
    monkeypatch.setattr(
        lightrag_adapter.settings,
        "openrouter_model",
        "liquid/lfm-2.5-1.2b-instruct:free",
    )

    result = await lightrag_adapter.openrouter_model_complete(
        "Summarize this citation span",
        system_prompt="Answer tersely.",
    )

    assert result == "draft summary"
    request = _FakeAsyncClient.requests[0]
    assert request["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer sk-or-test"
    assert request["json"]["model"] == "liquid/lfm-2.5-1.2b-instruct:free"
    assert request["json"]["messages"][0] == {
        "role": "system",
        "content": "Answer tersely.",
    }


@pytest.mark.asyncio
async def test_openrouter_model_complete_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr(lightrag_adapter.settings, "openrouter_api_key", "")
    monkeypatch.setattr(lightrag_adapter.settings, "openai_api_key", "")

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        await lightrag_adapter.openrouter_model_complete("hello")
