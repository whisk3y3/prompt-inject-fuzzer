"""Target adapter interface for LLM API communication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from prompt_inject_fuzzer.config import TargetConfig


@dataclass
class TargetResponse:
    """Response from an LLM target."""

    text: str
    raw: dict
    status_code: int
    latency_ms: float
    model: str = ""
    tokens_used: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.status_code == 200 and self.error is None


class BaseEngine(ABC):
    """Abstract base class for LLM target adapters."""

    def __init__(self, config: TargetConfig) -> None:
        self.config = config

    @abstractmethod
    async def send(
        self,
        payload: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> TargetResponse:
        """Send a payload to the target LLM and return the response.

        Args:
            payload: The injection payload text.
            conversation_history: Optional prior messages for multi-turn chains.

        Returns:
            TargetResponse with the model's output.
        """
        ...

    @abstractmethod
    async def baseline(self) -> TargetResponse:
        """Get a baseline response for behavioral comparison.

        Sends a benign query to establish normal model behavior.

        Returns:
            TargetResponse representing baseline behavior.
        """
        ...
