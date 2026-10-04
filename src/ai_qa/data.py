"""YAML test-data loading (FR-017).

The only use of YAML in this project. Configuration never comes from here -
it comes from the environment, validated by :mod:`ai_qa.config`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

#: Test data lives beside the tests, not in the support package.
DATA_DIR: Path = Path(__file__).resolve().parents[2] / "tests" / "data"


def load(name: str, *, data_dir: Path | None = None) -> dict[str, Any]:
    """Load a YAML test-data file and return its top-level mapping.

    ``name`` may be given with or without the ``.yaml`` suffix.

    Uses ``yaml.safe_load`` only. The data is committed and trusted, but
    ``safe_load`` costs nothing and removes arbitrary object construction from
    the loader outright.

    Raises:
        FileNotFoundError: naming both the requested file and the directory
            searched, so a typo is distinguishable from a missing fixture.
        ValueError: if the file does not parse to a mapping, so a malformed
            data file is distinguishable from a failing assertion.
    """
    directory = data_dir if data_dir is not None else DATA_DIR
    filename = name if name.endswith((".yaml", ".yml")) else f"{name}.yaml"
    path = directory / filename

    if not path.is_file():
        available = sorted(p.name for p in directory.glob("*.y*ml")) if directory.is_dir() else []
        raise FileNotFoundError(
            f"Test data file {filename!r} not found in {directory}. "
            f"Available: {available or 'none'}"
        )

    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Test data file {path} must contain a top-level mapping of case "
            f"names to case bodies, got {type(parsed).__name__}"
        )

    return parsed


def case(name: str, case_name: str, *, data_dir: Path | None = None) -> Any:
    """Return a single named case from a test-data file."""
    cases = load(name, data_dir=data_dir)
    if case_name not in cases:
        raise KeyError(
            f"Case {case_name!r} not found in {name!r}. Available: {sorted(cases)}"
        )
    return cases[case_name]
