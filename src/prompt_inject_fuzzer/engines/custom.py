"""Custom REST endpoint and Ollama target adapters."""

from __future__ import annotations

import json
import time

import httpx

from prompt_inject_fuzzer.config import TargetConfig
from prompt_inject_fuzzer.engines.base import BaseEngine, TargetResponse


class CustomEngine(BaseEngine):
    """Adapter for arbitrary REST API endpoints.

    Uses a configurable body template with {payload} placeholder.
    """

    def __init__(self, config: TargetConfig) -> None:
        super().__init__(config)
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={"Content-Type": "application/json", **config.headers},
        )

    async def send(
        self,
        payload: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> TargetResponse:
        template = self.config.body_template or '{"message": "{payload}"}'
        body_str = template.replace("{payload}", payload.replace('"', '\\"'))

        start = time.monotonic()
        try:
            body = json.loads(body_str)
            response = await self.client.post(
                self.config.get_endpoint(),
                json=body,
            )
            latency = (time.monotonic() - start) * 1000

            data = response.json() if response.content else {}
            text = self._extract_text(data)

            return TargetResponse(
                text=text,
                raw=data,
                status_code=response.status_code,
                latency_ms=latency,
                error=None if response.status_code == 200 else f"HTTP {response.status_code}",
            )

        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return TargetResponse(
                text="",
                raw={},
                status_code=0,
                latency_ms=latency,
                error=str(e),
            )

    async def baseline(self) -> TargetResponse:
        return await self.send("Hello, how can you help me today?")

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Best-effort text extraction from unknown response formats."""
        # Common response field names
        for key in ("response", "text", "content", "message", "output", "answer", "reply"):
            if key in data:
                val = data[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, dict) and "content" in val:
                    return str(val["content"])
                if isinstance(val, list) and val:
                    first = val[0]
                    if isinstance(first, str):
                        return first
                    if isinstance(first, dict):
                        return str(first.get("text", first.get("content", "")))

        return json.dumps(data)

    async def close(self) -> None:
        await self.client.aclose()


class OllamaEngine(BaseEngine):
    """Adapter for Ollama local model API."""

    def __init__(self, config: TargetConfig) -> None:
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=config.timeout)

    async def send(
        self,
        payload: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> TargetResponse:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.config.system_prompt},
        ]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": payload})

        body = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
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
                text = data.get("message", {}).get("content", "")
                return TargetResponse(
                    text=text,
                    raw=data,
                    status_code=200,
                    latency_ms=latency,
                    model=self.config.model,
                )
            else:
                return TargetResponse(
                    text="",
                    raw={},
                    status_code=response.status_code,
                    latency_ms=latency,
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return TargetResponse(
                text="",
                raw={},
                status_code=0,
                latency_ms=latency,
                error=str(e),
            )

    async def baseline(self) -> TargetResponse:
        return await self.send("Hello, how can you help me today?")

    async def close(self) -> None:
        await self.client.aclose()
