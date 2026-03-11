"""Payload data structures for prompt injection testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from prompt_inject_fuzzer.config import PayloadCategory, Severity


@dataclass
class Payload:
    """A single injection payload with metadata."""

    text: str
    category: PayloadCategory
    name: str = ""
    description: str = ""
    severity: Severity = Severity.MEDIUM
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    mutations_applied: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Generate a unique identifier for this payload."""
        import hashlib

        return hashlib.sha256(self.text.encode()).hexdigest()[:12]
