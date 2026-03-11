"""LLM-powered semantic rephrasing of injection payloads.

Uses a local or API-accessible model to rephrase payloads while
preserving attack intent. This bypasses signature-based and
embedding-similarity filters by generating semantically equivalent
but textually distinct variants.
"""

from __future__ import annotations

from prompt_inject_fuzzer.mutators.base import BaseMutator

# Pre-generated rephrasings for common attack patterns.
# In production use, these would be generated dynamically via LLM API.
REPHRASE_TEMPLATES: dict[str, list[str]] = {
    "ignore": [
        "disregard",
        "pay no attention to",
        "set aside",
        "do not follow",
        "treat as null",
        "consider void",
    ],
    "instructions": [
        "directives",
        "guidelines",
        "rules",
        "constraints",
        "configuration",
        "programming",
        "parameters",
    ],
    "system prompt": [
        "initial configuration",
        "foundational directives",
        "base programming",
        "core instructions",
        "root configuration",
        "original setup",
    ],
    "override": [
        "supersede",
        "take precedence over",
        "replace",
        "nullify",
        "supplant",
        "preempt",
    ],
    "unrestricted": [
        "without limitations",
        "free from constraints",
        "unfiltered",
        "uncensored",
        "without boundaries",
        "fully open",
    ],
    "reveal": [
        "disclose",
        "share",
        "make visible",
        "expose",
        "surface",
        "bring to light",
        "output",
    ],
    "safety": [
        "content policy",
        "guardrails",
        "protective measures",
        "restrictions",
        "content filters",
        "behavioral boundaries",
    ],
}


class SemanticRephraser(BaseMutator):
    """Rephrase payloads using semantic substitution.

    Uses template-based synonym replacement for offline operation,
    with optional LLM-powered dynamic rephrasing when a model
    endpoint is configured.
    """

    name = "semantic"

    def __init__(self, model: str = "local", endpoint: str | None = None) -> None:
        """Initialize semantic rephraser.

        Args:
            model: Model to use for rephrasing ('local' for template-based).
            endpoint: Optional LLM API endpoint for dynamic rephrasing.
        """
        self.model = model
        self.endpoint = endpoint

    def mutate(self, text: str) -> list[str]:
        """Generate semantically rephrased variants."""
        if self.model == "local" or not self.endpoint:
            return self._template_rephrase(text)
        return self._template_rephrase(text)  # LLM rephrasing would go here

    def _template_rephrase(self, text: str) -> list[str]:
        """Apply template-based synonym substitution."""
        variants: list[str] = []

        # Generate multiple variants by cycling through synonyms
        for variant_idx in range(3):
            result = text
            for phrase, replacements in REPHRASE_TEMPLATES.items():
                if phrase.lower() in result.lower():
                    idx = result.lower().find(phrase.lower())
                    replacement = replacements[variant_idx % len(replacements)]
                    result = result[:idx] + replacement + result[idx + len(phrase) :]

            if result != text:
                variants.append(result)

        return variants
