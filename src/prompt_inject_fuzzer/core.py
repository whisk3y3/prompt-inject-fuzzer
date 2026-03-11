"""Core fuzzer engine — orchestrates payload delivery, mutation, and detection."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from prompt_inject_fuzzer.config import (
    DetectionMethod,
    MutationStrategy,
    ScanConfig,
    Severity,
    TargetConfig,
    TargetType,
)
from prompt_inject_fuzzer.detectors import (
    BaseDetector,
    BehavioralDetector,
    DetectionResult,
    StringMatchDetector,
)
from prompt_inject_fuzzer.engines.base import BaseEngine, TargetResponse
from prompt_inject_fuzzer.engines.openai import OpenAIEngine
from prompt_inject_fuzzer.engines.anthropic import AnthropicEngine
from prompt_inject_fuzzer.engines.custom import CustomEngine, OllamaEngine
from prompt_inject_fuzzer.mutators import (
    Base64Encoder,
    HomoglyphReplacer,
    LanguageMixer,
    MutationPipeline,
    SemanticRephraser,
    TokenSplitter,
)
from prompt_inject_fuzzer.payloads import Payload, get_payloads, load_payloads

console = Console()


@dataclass
class FuzzResult:
    """Result of a single payload test."""

    payload: Payload
    response: TargetResponse
    detection: DetectionResult
    timestamp: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.detection.detected


@dataclass
class ScanResults:
    """Aggregate results from a complete fuzzing scan."""

    results: list[FuzzResult] = field(default_factory=list)
    baseline_response: str = ""
    scan_config: ScanConfig | None = None
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successes(self) -> list[FuzzResult]:
        return [r for r in self.results if r.success]

    @property
    def failures(self) -> list[FuzzResult]:
        return [r for r in self.results if not r.success]

    @property
    def success_rate(self) -> float:
        return len(self.successes) / max(self.total, 1)

    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time

    def by_severity(self, severity: Severity) -> list[FuzzResult]:
        return [r for r in self.successes if r.payload.severity == severity]

    def by_category(self) -> dict[str, list[FuzzResult]]:
        categories: dict[str, list[FuzzResult]] = {}
        for r in self.successes:
            cat = r.payload.category.value
            categories.setdefault(cat, []).append(r)
        return categories

    def summary(self) -> None:
        """Print a formatted summary to the console."""
        console.print()
        console.print("[bold]═══ Scan Summary ═══[/bold]")
        console.print(f"Total payloads tested: {self.total}")
        console.print(f"Successful injections: [red]{len(self.successes)}[/red]")
        console.print(f"Success rate: [yellow]{self.success_rate:.1%}[/yellow]")
        console.print(f"Duration: {self.duration_seconds:.1f}s")

        if self.successes:
            console.print()
            table = Table(title="Successful Injections")
            table.add_column("Severity", style="bold")
            table.add_column("Category")
            table.add_column("Payload Name")
            table.add_column("Confidence")
            table.add_column("Mutations")

            severity_styles = {
                Severity.CRITICAL: "bold red",
                Severity.HIGH: "red",
                Severity.MEDIUM: "yellow",
                Severity.LOW: "green",
                Severity.INFO: "dim",
            }

            for r in sorted(
                self.successes,
                key=lambda x: list(Severity).index(x.payload.severity),
                reverse=True,
            ):
                style = severity_styles.get(r.payload.severity, "")
                table.add_row(
                    f"[{style}]{r.payload.severity.value.upper()}[/{style}]",
                    r.payload.category.value,
                    r.payload.name or r.payload.id,
                    f"{r.detection.confidence:.0%}",
                    ", ".join(r.payload.mutations_applied) or "none",
                )

            console.print(table)

    def to_dict(self) -> dict[str, Any]:
        """Serialize results for JSON export."""
        return {
            "summary": {
                "total_payloads": self.total,
                "successful_injections": len(self.successes),
                "success_rate": self.success_rate,
                "duration_seconds": self.duration_seconds,
            },
            "results": [
                {
                    "payload": {
                        "id": r.payload.id,
                        "name": r.payload.name,
                        "category": r.payload.category.value,
                        "severity": r.payload.severity.value,
                        "text": r.payload.text[:200],
                        "mutations": r.payload.mutations_applied,
                    },
                    "response": {
                        "text": r.response.text[:500],
                        "status_code": r.response.status_code,
                        "latency_ms": r.response.latency_ms,
                    },
                    "detection": {
                        "detected": r.detection.detected,
                        "confidence": r.detection.confidence,
                        "method": r.detection.method,
                        "evidence": r.detection.evidence,
                    },
                }
                for r in self.results
            ],
        }


class Fuzzer:
    """Main fuzzer engine. Orchestrates payload generation, delivery, and analysis."""

    def __init__(
        self,
        target: TargetConfig | None = None,
        config: ScanConfig | None = None,
        mutations: MutationPipeline | None = None,
        chains: list[dict[str, Any]] | None = None,
    ) -> None:
        self.config = config or ScanConfig()
        if target:
            self.config.target = target

        self.mutations = mutations
        self.chains = chains or []
        self.engine = self._build_engine()
        self.detectors = self._build_detectors()

    def _build_engine(self) -> BaseEngine:
        """Instantiate the appropriate target engine."""
        engines = {
            TargetType.OPENAI: OpenAIEngine,
            TargetType.ANTHROPIC: AnthropicEngine,
            TargetType.OLLAMA: OllamaEngine,
            TargetType.CUSTOM: CustomEngine,
        }
        engine_cls = engines.get(self.config.target.type, CustomEngine)
        return engine_cls(self.config.target)

    def _build_detectors(self) -> list[BaseDetector]:
        """Instantiate configured detection classifiers."""
        detector_map = {
            DetectionMethod.STRING_MATCH: StringMatchDetector,
            DetectionMethod.BEHAVIORAL: BehavioralDetector,
        }
        detectors: list[BaseDetector] = []
        for method in self.config.detection.methods:
            if method in detector_map:
                detectors.append(detector_map[method]())
        return detectors or [StringMatchDetector()]

    def _build_mutations(self) -> MutationPipeline | None:
        """Build mutation pipeline from config if not explicitly provided."""
        if self.mutations:
            return self.mutations
        if not self.config.mutations.enabled:
            return None

        strategy_map = {
            MutationStrategy.ENCODING: Base64Encoder,
            MutationStrategy.SPLITTING: TokenSplitter,
            MutationStrategy.HOMOGLYPH: HomoglyphReplacer,
            MutationStrategy.LANGUAGE: LanguageMixer,
            MutationStrategy.SEMANTIC: SemanticRephraser,
        }

        mutators = []
        for strategy in self.config.mutations.strategies:
            if strategy in strategy_map:
                mutators.append(strategy_map[strategy]())

        if not mutators:
            return None

        return MutationPipeline(mutators=mutators, rounds=self.config.mutations.rounds)

    def run(self) -> ScanResults:
        """Execute the fuzzing scan synchronously."""
        return asyncio.run(self.run_async())

    async def run_async(self) -> ScanResults:
        """Execute the fuzzing scan."""
        results = ScanResults(scan_config=self.config, start_time=time.time())

        # Get baseline response
        console.print("[dim]Collecting baseline response...[/dim]")
        baseline = await self.engine.baseline()
        results.baseline_response = baseline.text

        # Load payloads
        payloads = get_payloads(categories=self.config.payload_categories)

        if self.config.custom_payloads_path:
            custom = load_payloads(self.config.custom_payloads_path)
            payloads.extend(custom)

        console.print(f"[dim]Loaded {len(payloads)} base payloads[/dim]")

        # Apply mutations
        pipeline = self._build_mutations()
        if pipeline:
            payloads = pipeline.run(payloads)
            console.print(f"[dim]Expanded to {len(payloads)} payloads after mutation[/dim]")

        # Execute scan
        semaphore = asyncio.Semaphore(self.config.concurrency)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fuzzing...", total=len(payloads))

            async def test_payload(payload: Payload) -> FuzzResult:
                async with semaphore:
                    response = await self.engine.send(payload.text)
                    detection = self._detect(response.text, payload.text, baseline.text)

                    if self.config.delay > 0:
                        await asyncio.sleep(self.config.delay)

                    progress.advance(task)

                    return FuzzResult(
                        payload=payload,
                        response=response,
                        detection=detection,
                    )

            tasks = [test_payload(p) for p in payloads]
            fuzz_results = await asyncio.gather(*tasks)

        results.results = list(fuzz_results)
        results.end_time = time.time()

        return results

    def _detect(self, response_text: str, payload_text: str, baseline_text: str) -> DetectionResult:
        """Run all configured detectors and return the highest-confidence result."""
        best: DetectionResult | None = None

        for detector in self.detectors:
            result = detector.check(response_text, payload_text, baseline_text)
            if best is None or result.confidence > best.confidence:
                best = result

        return best or DetectionResult(
            detected=False, confidence=0.0, method="none", evidence="No detectors ran"
        )
