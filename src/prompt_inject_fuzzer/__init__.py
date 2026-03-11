"""prompt-inject-fuzzer — Systematic prompt injection testing for LLM applications."""

from prompt_inject_fuzzer.config import ScanConfig, TargetConfig
from prompt_inject_fuzzer.core import Fuzzer, ScanResults, FuzzResult
from prompt_inject_fuzzer.mutators import MutationPipeline
from prompt_inject_fuzzer.payloads import Payload, get_payloads

__version__ = "0.1.0"

__all__ = [
    "Fuzzer",
    "FuzzResult",
    "MutationPipeline",
    "Payload",
    "ScanConfig",
    "ScanResults",
    "TargetConfig",
    "get_payloads",
]
