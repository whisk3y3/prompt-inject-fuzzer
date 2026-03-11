"""Target engine adapters for LLM APIs."""

from prompt_inject_fuzzer.engines.base import BaseEngine, TargetResponse
from prompt_inject_fuzzer.engines.openai import OpenAIEngine
from prompt_inject_fuzzer.engines.anthropic import AnthropicEngine
from prompt_inject_fuzzer.engines.custom import CustomEngine, OllamaEngine

__all__ = [
    "BaseEngine",
    "TargetResponse",
    "OpenAIEngine",
    "AnthropicEngine",
    "CustomEngine",
    "OllamaEngine",
]
