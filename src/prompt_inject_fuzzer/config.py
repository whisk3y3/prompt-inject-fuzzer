"""Configuration models for prompt-inject-fuzzer."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class TargetType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class MutationStrategy(str, Enum):
    ENCODING = "encoding"
    SPLITTING = "splitting"
    HOMOGLYPH = "homoglyph"
    LANGUAGE = "language"
    SEMANTIC = "semantic"


class PayloadCategory(str, Enum):
    DIRECT_INJECTION = "direct_injection"
    INDIRECT_INJECTION = "indirect_injection"
    CONTEXT_MANIPULATION = "context_manipulation"
    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_HIJACKING = "role_hijacking"
    DELIMITER_ESCAPE = "delimiter_escape"
    DATA_EXFILTRATION = "data_exfiltration"


class DetectionMethod(str, Enum):
    STRING_MATCH = "string_match"
    SEMANTIC = "semantic"
    BEHAVIORAL = "behavioral"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TargetConfig(BaseModel):
    """Configuration for the LLM target under test."""

    type: TargetType = TargetType.OPENAI
    endpoint: str | None = None
    model: str = "gpt-4o"
    api_key: str | None = None
    system_prompt: str = "You are a helpful assistant."
    temperature: float = 0.0
    max_tokens: int = 1024
    headers: dict[str, str] = Field(default_factory=dict)
    body_template: str | None = None
    timeout: float = 30.0

    def get_endpoint(self) -> str:
        """Resolve endpoint from type if not explicitly set."""
        if self.endpoint:
            return self.endpoint
        endpoints = {
            TargetType.OPENAI: "https://api.openai.com/v1/chat/completions",
            TargetType.ANTHROPIC: "https://api.anthropic.com/v1/messages",
            TargetType.OLLAMA: "http://localhost:11434/api/chat",
        }
        if self.type in endpoints:
            return endpoints[self.type]
        raise ValueError(f"Endpoint required for target type: {self.type}")


class MutationConfig(BaseModel):
    """Configuration for payload mutation pipeline."""

    enabled: bool = True
    strategies: list[MutationStrategy] = Field(
        default_factory=lambda: [
            MutationStrategy.ENCODING,
            MutationStrategy.SPLITTING,
            MutationStrategy.HOMOGLYPH,
        ]
    )
    rounds: int = 3
    semantic_model: str = "local"


class MultiTurnConfig(BaseModel):
    """Configuration for multi-turn chain attacks."""

    enabled: bool = False
    max_chain_depth: int = 5
    delay_between_turns: float = 1.0


class DetectionConfig(BaseModel):
    """Configuration for injection success detection."""

    methods: list[DetectionMethod] = Field(
        default_factory=lambda: [DetectionMethod.STRING_MATCH, DetectionMethod.BEHAVIORAL]
    )
    sensitivity: str = "medium"
    custom_indicators: list[str] = Field(default_factory=list)
    baseline_samples: int = 3


class ReportConfig(BaseModel):
    """Configuration for output reporting."""

    format: str = "markdown"
    output_path: str = "report"
    include_logs: bool = True
    severity_threshold: Severity = Severity.LOW


class ScanConfig(BaseModel):
    """Top-level scan configuration."""

    target: TargetConfig = Field(default_factory=TargetConfig)
    payload_categories: list[PayloadCategory] = Field(
        default_factory=lambda: [
            PayloadCategory.DIRECT_INJECTION,
            PayloadCategory.INSTRUCTION_OVERRIDE,
            PayloadCategory.DELIMITER_ESCAPE,
            PayloadCategory.DATA_EXFILTRATION,
        ]
    )
    custom_payloads_path: str | None = None
    mutations: MutationConfig = Field(default_factory=MutationConfig)
    multi_turn: MultiTurnConfig = Field(default_factory=MultiTurnConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    reporting: ReportConfig = Field(default_factory=ReportConfig)
    concurrency: int = 5
    delay: float = 0.5
    verbose: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path) -> ScanConfig:
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScanConfig:
        """Load configuration from a dictionary."""
        return cls.model_validate(data)
