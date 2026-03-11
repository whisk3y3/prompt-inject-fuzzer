"""Load custom payloads from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from prompt_inject_fuzzer.config import PayloadCategory, Severity
from prompt_inject_fuzzer.payloads.base import Payload


def load_payloads(path: str | Path) -> list[Payload]:
    """Load payloads from a YAML or JSON file.

    Expected format:
        payloads:
          - text: "injection payload text"
            category: "direct_injection"
            name: "custom_payload_1"
            description: "Description of what this tests"
            severity: "high"
            tags: ["custom", "my-org"]

    Args:
        path: Path to YAML or JSON payload file.

    Returns:
        List of Payload objects.
    """
    path = Path(path)

    if path.suffix in (".yaml", ".yml"):
        with open(path) as f:
            data = yaml.safe_load(f)
    elif path.suffix == ".json":
        with open(path) as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported payload file format: {path.suffix}")

    raw_payloads = data.get("payloads", [])
    payloads: list[Payload] = []

    for entry in raw_payloads:
        payload = Payload(
            text=entry["text"],
            category=PayloadCategory(entry.get("category", "direct_injection")),
            name=entry.get("name", ""),
            description=entry.get("description", ""),
            severity=Severity(entry.get("severity", "medium")),
            tags=entry.get("tags", []),
            metadata=entry.get("metadata", {}),
        )
        payloads.append(payload)

    return payloads
