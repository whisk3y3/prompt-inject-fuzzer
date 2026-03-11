"""Homoglyph (visual lookalike) character substitution."""

from __future__ import annotations

import random

from prompt_inject_fuzzer.mutators.base import BaseMutator

# Mapping of ASCII characters to visually similar Unicode characters
HOMOGLYPH_MAP: dict[str, list[str]] = {
    "a": ["\u0430", "\u00e0", "\u00e1", "\u1ea1"],  # Cyrillic а, à, á, ạ
    "c": ["\u0441", "\u00e7", "\u0188"],  # Cyrillic с, ç, ƈ
    "d": ["\u0501", "\u0257"],  # Cyrillic ԁ, ɗ
    "e": ["\u0435", "\u00e8", "\u00e9", "\u0117"],  # Cyrillic е, è, é, ė
    "g": ["\u0261", "\u0123"],  # ɡ, ģ
    "h": ["\u04bb", "\u0570"],  # Cyrillic һ, Armenian հ
    "i": ["\u0456", "\u00ec", "\u00ed", "\u0131"],  # Cyrillic і, ì, í, ı
    "j": ["\u0458", "\u029d"],  # Cyrillic ј, ʝ
    "k": ["\u043a"],  # Cyrillic к
    "l": ["\u04cf", "\u0269", "\u013a"],  # Cyrillic ӏ, ɩ, ĺ
    "m": ["\u043c"],  # Cyrillic м (visually similar in some fonts)
    "n": ["\u0578", "\u0144"],  # Armenian ո, ń
    "o": ["\u043e", "\u00f2", "\u00f3", "\u01a1"],  # Cyrillic о, ò, ó, ơ
    "p": ["\u0440", "\u1d71"],  # Cyrillic р, ᵱ
    "q": ["\u051b"],  # Cyrillic ԛ
    "r": ["\u0433"],  # Cyrillic г (in some fonts)
    "s": ["\u0455", "\u015b"],  # Cyrillic ѕ, ś
    "t": ["\u0442"],  # Cyrillic т
    "u": ["\u0446", "\u00f9", "\u00fa"],  # Cyrillic ц (approximate), ù, ú
    "v": ["\u0475", "\u1d20"],  # Cyrillic ѵ, ᴠ
    "w": ["\u0461"],  # Cyrillic ѡ
    "x": ["\u0445", "\u04b3"],  # Cyrillic х, ҳ
    "y": ["\u0443", "\u00fd"],  # Cyrillic у, ý
    "z": ["\u0290", "\u017a"],  # ʐ, ź
}


class HomoglyphReplacer(BaseMutator):
    """Replace ASCII characters with visually similar Unicode homoglyphs.

    This mutation can bypass keyword-matching and regex-based content
    filters while keeping the payload visually readable to humans
    and potentially interpretable by LLMs.
    """

    name = "homoglyph"

    def __init__(self, intensity: float = 0.3, seed: int | None = None) -> None:
        """Initialize homoglyph replacer.

        Args:
            intensity: Fraction of eligible characters to replace (0.0-1.0).
            seed: Random seed for reproducibility.
        """
        self.intensity = max(0.0, min(1.0, intensity))
        self.rng = random.Random(seed)

    def mutate(self, text: str) -> list[str]:
        variants = [
            self._replace_chars(text, self.intensity),
            self._replace_keywords_only(text),
        ]
        return [v for v in variants if v != text]

    def _replace_chars(self, text: str, intensity: float) -> str:
        """Replace random characters throughout the text."""
        result: list[str] = []
        for char in text:
            lower = char.lower()
            if lower in HOMOGLYPH_MAP and self.rng.random() < intensity:
                replacement = self.rng.choice(HOMOGLYPH_MAP[lower])
                result.append(replacement if char.islower() else replacement.upper())
            else:
                result.append(char)
        return "".join(result)

    def _replace_keywords_only(self, text: str) -> str:
        """Replace characters only in security-sensitive keywords."""
        keywords = [
            "ignore", "system", "instructions", "override", "prompt",
            "admin", "bypass", "disable", "safety", "restrict",
        ]
        result = text
        for keyword in keywords:
            idx = result.lower().find(keyword.lower())
            if idx != -1:
                original = result[idx : idx + len(keyword)]
                replaced = self._replace_chars(original, intensity=0.5)
                result = result[:idx] + replaced + result[idx + len(keyword) :]
        return result
