"""Anthropic API target adapter."""

from __future__ import annotations

import time

import httpx

from prompt_inject_fuzzer.config import TargetConfig
from prompt_inject_fuzzer.engines.base import BaseEngine, TargetResponse


class AnthropicEngine(BaseEngine):
    """Adapter for Anthropic messages API."""

    def __init__(self, config: TargetConfig) -> None:
        super().__init__(config)
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={
                "x-api-key": config.api_key or "",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )

    async def send(
        self,
        payload: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> TargetResponse:
        messages: list[dict[str, str]] = []

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": payload})

        body = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": self.config.system_prompt,
            "messages": messages,
        }

        start = time.monotonic()
        try:
            response = await self.client.post(
                self.config.get_endpoint(),
                json=body,
            )
            latency = (time.monotonic() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                text = data["content"][0]["text"]
                tokens = data.get("usage", {}).get("input_tokens", 0) + data.get(
                    "usage", {}
                ).get("output_tokens", 0)
                return TargetResponse(
                    text=text,
                    raw=data,
                    status_code=200,
                    latency_ms=latency,
                    model=data.get("model", self.config.model),
                    tokens_used=tokens,
                )
            else:
                return TargetResponse(
                    text="",
                    raw=response.json() if response.content else {},
                    status_code=response.status_code,
                    latency_ms=latency,
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                )

        except httpx.TimeoutException:
            latency = (time.monotonic() - start) * 1000
            return TargetResponse(
                text="",
                raw={},
                status_code=0,
                latency_ms=latency,
                error="Request timed out",
            )

    async def baseline(self) -> TargetResponse:
        return await self.send("Hello, how can you help me today?")

    async def close(self) -> None:
        await self.client.aclose()
