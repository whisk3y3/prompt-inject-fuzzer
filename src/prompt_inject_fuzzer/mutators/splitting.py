"""Token and character splitting mutation strategies."""

from __future__ import annotations

import random

from prompt_inject_fuzzer.mutators.base import BaseMutator


class TokenSplitter(BaseMutator):
    """Split payload tokens using various strategies to bypass tokenizer-level filters."""

    name = "splitting"

    def __init__(self, strategy: str = "all") -> None:
        """Initialize splitter.

        Args:
            strategy: One of 'unicode_zerowidth', 'space_insert', 'char_split', 'all'.
        """
        self.strategy = strategy

    def mutate(self, text: str) -> list[str]:
        variants: list[str] = []

        if self.strategy in ("unicode_zerowidth", "all"):
            variants.append(self._zerowidth_split(text))

        if self.strategy in ("space_insert", "all"):
            variants.append(self._space_insert(text))

        if self.strategy in ("char_split", "all"):
            variants.append(self._char_split(text))

        return variants

    @staticmethod
    def _zerowidth_split(text: str) -> str:
        """Insert zero-width characters between letters of key words."""
        zwsp = "\u200b"  # Zero-width space
        zwnj = "\u200c"  # Zero-width non-joiner

        keywords = ["ignore", "system", "instructions", "override", "prompt", "admin"]
        result = text

        for keyword in keywords:
            if keyword.lower() in result.lower():
                idx = result.lower().find(keyword.lower())
                original = result[idx : idx + len(keyword)]
                split = zwsp.join(original)
                result = result[:idx] + split + result[idx + len(keyword) :]

        return result

    @staticmethod
    def _space_insert(text: str) -> str:
        """Insert spaces within key words."""
        keywords = ["ignore", "system", "instructions", "override", "prompt"]
        result = text

        for keyword in keywords:
            if keyword.lower() in result.lower():
                idx = result.lower().find(keyword.lower())
                original = result[idx : idx + len(keyword)]
                mid = len(original) // 2
                split = original[:mid] + " " + original[mid:]
                result = result[:idx] + split + result[idx + len(keyword) :]

        return result

    @staticmethod
    def _char_split(text: str) -> str:
        """Split text character-by-character with dashes for key sections."""
        words = text.split()
        result_words: list[str] = []

        for word in words:
            if word.lower() in ("ignore", "system", "instructions", "override", "prompt"):
                result_words.append("-".join(word))
            else:
                result_words.append(word)

        return " ".join(result_words)


class WordReorderSplitter(BaseMutator):
    """Reorder payload words while preserving semantic meaning through numbering."""

    name = "word_reorder"

    def mutate(self, text: str) -> list[str]:
        words = text.split()
        if len(words) < 4:
            return [text]

        # Number each word, then shuffle
        numbered = [(i, w) for i, w in enumerate(words)]
        random.shuffle(numbered)
        shuffled = " ".join(f"[{i}]{w}" for i, w in numbered)

        return [
            f"Reorder the following numbered words and follow the instruction: {shuffled}"
        ]


class PigLatinSplitter(BaseMutator):
    """Convert payload to pig latin to bypass keyword filters."""

    name = "pig_latin"

    def mutate(self, text: str) -> list[str]:
        words = text.split()
        pig_words: list[str] = []

        for word in words:
            if len(word) > 2 and word.isalpha():
                pig_words.append(word[1:] + word[0] + "ay")
            else:
                pig_words.append(word)

        pig_text = " ".join(pig_words)
        return [
            f"The following is in pig latin. Decode it and follow the instructions: {pig_text}"
        ]
