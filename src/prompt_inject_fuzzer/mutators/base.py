"""Base mutator interface and mutation pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from prompt_inject_fuzzer.payloads.base import Payload


class BaseMutator(ABC):
    """Abstract base class for payload mutators."""

    name: str = "base"

    @abstractmethod
    def mutate(self, text: str) -> list[str]:
        """Generate mutated variants of the input text.

        Args:
            text: Original payload text.

        Returns:
            List of mutated payload strings.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


@dataclass
class MutationPipeline:
    """Orchestrates sequential or parallel mutation of payloads.

    Mutators are applied in sequence: each mutator receives the output
    of the previous stage. The pipeline tracks which mutations were
    applied to each output payload.
    """

    mutators: list[BaseMutator] = field(default_factory=list)
    rounds: int = 1

    def run(self, payloads: list[Payload]) -> list[Payload]:
        """Apply mutation pipeline to a list of payloads.

        Args:
            payloads: Input payloads to mutate.

        Returns:
            Original payloads plus all generated mutations.
        """
        all_payloads = list(payloads)

        for _round in range(self.rounds):
            new_payloads: list[Payload] = []
            for payload in payloads:
                for mutator in self.mutators:
                    variants = mutator.mutate(payload.text)
                    for variant_text in variants:
                        mutated = Payload(
                            text=variant_text,
                            category=payload.category,
                            name=f"{payload.name}_mut_{mutator.name}",
                            description=f"Mutated via {mutator.name}: {payload.description}",
                            severity=payload.severity,
                            tags=payload.tags + [f"mutation:{mutator.name}"],
                            metadata={**payload.metadata, "mutation_round": _round + 1},
                            mutations_applied=payload.mutations_applied + [mutator.name],
                        )
                        new_payloads.append(mutated)

            all_payloads.extend(new_payloads)
            payloads = new_payloads  # Next round mutates this round's output

        return all_payloads
