"""`.env.example` is the configuration contract, and it must stay accurate.

SC-008 and SC-010 are **ongoing** properties, not one-time checks: every
setting the suite reads must be named in the committed example, so no setting
is discoverable only by reading code. Verifying it once by hand does not stop
the next person adding a field and forgetting the example - this test does.
"""

from __future__ import annotations

import pathlib

from ai_qa.config import Settings, _ENV_PREFIXES


def _documented() -> set[str]:
    text = pathlib.Path(".env.example").read_text(encoding="utf-8")
    return {
        line.split("=", 1)[0].strip()
        for line in text.splitlines()
        if "=" in line and not line.strip().startswith("#")
    }


def test_every_setting_the_model_reads_is_documented() -> None:
    """SC-010: zero settings discoverable only by reading the code."""
    missing = sorted(set(_ENV_PREFIXES) - _documented())
    assert not missing, (
        f"these settings are read but absent from .env.example: {missing}. "
        "Adding a setting takes three edits: the Settings model, "
        "_ENV_PREFIXES, and .env.example."
    )


def test_env_example_documents_nothing_the_model_ignores() -> None:
    """The reverse drift: a documented setting nothing reads is a lie."""
    extra = sorted(_documented() - set(_ENV_PREFIXES))
    assert not extra, (
        f".env.example documents settings the model does not read: {extra}"
    )


def test_every_prefix_has_a_matching_model_field() -> None:
    """_ENV_PREFIXES and the model must not drift apart either."""
    fields = set(Settings.model_fields)
    orphans = sorted(n for n in _ENV_PREFIXES if n.lower() not in fields)
    assert not orphans, f"_ENV_PREFIXES names non-existent fields: {orphans}"


def test_base_url_is_the_only_required_setting() -> None:
    """The documented promise: copy the example, set one value, run."""
    required = sorted(
        name for name, f in Settings.model_fields.items() if f.is_required()
    )
    assert required == ["base_url"]
