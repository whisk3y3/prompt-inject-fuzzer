"""Command-line interface for prompt-inject-fuzzer."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

from prompt_inject_fuzzer.config import (
    MutationStrategy,
    PayloadCategory,
    ScanConfig,
    TargetConfig,
    TargetType,
)
from prompt_inject_fuzzer.core import Fuzzer
from prompt_inject_fuzzer.payloads import get_payload_count

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """prompt-inject-fuzzer — Systematic prompt injection testing for LLM applications."""
    pass


@main.command()
@click.option("--target", type=click.Choice(["openai", "anthropic", "ollama", "custom"]), default="openai")
@click.option("--model", default="gpt-4o", help="Model name/identifier")
@click.option("--api-key", envvar="LLM_API_KEY", help="API key (or set LLM_API_KEY env var)")
@click.option("--endpoint", default=None, help="Custom API endpoint URL")
@click.option("--system-prompt", default="You are a helpful assistant.", help="Target system prompt")
@click.option("--categories", default=None, help="Comma-separated payload categories")
@click.option("--mutations", default="encoding,splitting,homoglyph", help="Comma-separated mutation strategies")
@click.option("--rounds", default=1, help="Mutation rounds")
@click.option("--concurrency", default=5, help="Max concurrent requests")
@click.option("--delay", default=0.5, help="Delay between requests (seconds)")
@click.option("--output", default="results.json", help="Output file path")
@click.option("--config", "config_path", default=None, help="Path to YAML config file")
@click.option("--body-template", default=None, help="Body template for custom endpoints")
@click.option("--verbose", is_flag=True, help="Verbose output")
def scan(
    target: str,
    model: str,
    api_key: str | None,
    endpoint: str | None,
    system_prompt: str,
    categories: str | None,
    mutations: str,
    rounds: int,
    concurrency: int,
    delay: float,
    output: str,
    config_path: str | None,
    body_template: str | None,
    verbose: bool,
) -> None:
    """Run a prompt injection scan against an LLM target."""
    console.print("[bold]prompt-inject-fuzzer[/bold] v0.1.0")
    console.print()

    # Load config from file or build from CLI args
    if config_path:
        scan_config = ScanConfig.from_yaml(config_path)
    else:
        # Parse categories
        payload_cats = None
        if categories:
            payload_cats = [PayloadCategory(c.strip()) for c in categories.split(",")]

        # Parse mutations
        mutation_strats = [MutationStrategy(m.strip()) for m in mutations.split(",") if m.strip()]

        target_config = TargetConfig(
            type=TargetType(target),
            model=model,
            api_key=api_key,
            endpoint=endpoint,
            system_prompt=system_prompt,
            body_template=body_template,
        )

        scan_config = ScanConfig(
            target=target_config,
            payload_categories=payload_cats or [
                PayloadCategory.DIRECT_INJECTION,
                PayloadCategory.INSTRUCTION_OVERRIDE,
                PayloadCategory.DELIMITER_ESCAPE,
                PayloadCategory.DATA_EXFILTRATION,
            ],
            concurrency=concurrency,
            delay=delay,
            verbose=verbose,
        )
        scan_config.mutations.strategies = mutation_strats
        scan_config.mutations.rounds = rounds

    # Validate API key
    if not scan_config.target.api_key and scan_config.target.type != TargetType.OLLAMA:
        console.print("[red]Error: API key required. Set --api-key or LLM_API_KEY env var.[/red]")
        raise SystemExit(1)

    # Run scan
    fuzzer = Fuzzer(config=scan_config)
    results = fuzzer.run()

    # Print summary
    results.summary()

    # Save results
    output_path = Path(output)
    with open(output_path, "w") as f:
        json.dump(results.to_dict(), f, indent=2)

    console.print(f"\n[dim]Results saved to {output_path}[/dim]")


@main.command()
@click.option("--input", "input_path", required=True, help="Path to results JSON file")
@click.option("--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
@click.option("--output", default="report", help="Output file path (without extension)")
def report(input_path: str, fmt: str, output: str) -> None:
    """Generate a report from scan results."""
    with open(input_path) as f:
        data = json.load(f)

    if fmt == "markdown":
        md = _generate_markdown_report(data)
        output_file = f"{output}.md"
        with open(output_file, "w") as f:
            f.write(md)
    else:
        output_file = f"{output}.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

    console.print(f"Report saved to {output_file}")


@main.command()
def info() -> None:
    """Show payload library information."""
    console.print("[bold]Payload Library[/bold]")
    console.print()

    counts = get_payload_count()
    total = sum(counts.values())

    for cat, count in counts.items():
        console.print(f"  {cat.value}: {count} payloads")

    console.print(f"\n  [bold]Total: {total} payloads[/bold]")


def _generate_markdown_report(data: dict) -> str:
    """Generate a Markdown report from results data."""
    summary = data.get("summary", {})
    results = data.get("results", [])

    lines = [
        "# Prompt Injection Fuzzing Report",
        "",
        "## Summary",
        "",
        f"- **Total Payloads Tested:** {summary.get('total_payloads', 0)}",
        f"- **Successful Injections:** {summary.get('successful_injections', 0)}",
        f"- **Success Rate:** {summary.get('success_rate', 0):.1%}",
        f"- **Scan Duration:** {summary.get('duration_seconds', 0):.1f}s",
        "",
        "## Findings",
        "",
    ]

    successes = [r for r in results if r.get("detection", {}).get("detected")]

    if not successes:
        lines.append("No successful injections detected.")
    else:
        for i, r in enumerate(successes, 1):
            p = r.get("payload", {})
            d = r.get("detection", {})
            resp = r.get("response", {})

            lines.extend([
                f"### Finding {i}: {p.get('name', 'Unknown')}",
                "",
                f"- **Severity:** {p.get('severity', 'unknown').upper()}",
                f"- **Category:** {p.get('category', 'unknown')}",
                f"- **Detection Confidence:** {d.get('confidence', 0):.0%}",
                f"- **Detection Method:** {d.get('method', 'unknown')}",
                f"- **Mutations Applied:** {', '.join(p.get('mutations', [])) or 'none'}",
                "",
                "**Payload (truncated):**",
                f"```",
                p.get("text", "")[:200],
                "```",
                "",
                "**Response (truncated):**",
                f"```",
                resp.get("text", "")[:300],
                "```",
                "",
            ])

    lines.extend([
        "## Remediation",
        "",
        "Findings should be evaluated against the OWASP LLM Top 10:",
        "",
        "- **LLM01: Prompt Injection** — Implement input validation, instruction hierarchy, and output filtering",
        "- **LLM02: Insecure Output Handling** — Sanitize model outputs before use in downstream systems",
        "- **LLM07: Insecure Plugin Design** — Validate tool invocations and enforce least privilege",
        "",
        "---",
        "*Generated by [prompt-inject-fuzzer](https://github.com/whisk3y3/prompt-inject-fuzzer)*",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
