"""Writing the generated file's deterministic half (R4, R8).

Split at the file level, not the function level: everything above the
delimiter is byte-predictable from the ticket and therefore assertable, and
the provenance header exists even if authoring is interrupted - a half-finished
file with no provenance is the worst outcome (FR-017).
"""

from __future__ import annotations

import datetime as _dt
import subprocess
from pathlib import Path

from ai_qa.generate.brief import Brief

DELIMITER = "# --- ai-qa: generated test functions below ---"

#: FR-018: a generated artifact must be distinguishable from a hand-written one.
GENERATED_MARKER = "generated-by: ai-qa"


def generating_identity() -> str:
    """Who is running generation, from git config.

    Recorded in provenance **for feature 004**, which cannot enforce "the
    approver may not be the author" without it - and authorship is only
    knowable now. Reconstructing it later is impossible.
    """
    try:
        out = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        return "unknown"


def provenance_block(brief: Brief, *, ticket_updated: str = "", identity: str | None = None) -> str:
    """The seven provenance fields, one per line (contracts/skeleton-format.md)."""
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return "\n".join(
        [
            GENERATED_MARKER,
            f"ticket: {brief.key}",
            f"ticket-summary: {brief.summary}",
            f"ticket-updated: {ticket_updated}",
            f"ticket-digest: {brief.content_digest}",
            f"generated-at: {now}",
            f"generated-by-identity: {identity or generating_identity()}",
        ]
    )


def render(brief: Brief, *, kind: str = "ui", ticket_updated: str = "", identity: str | None = None) -> str:
    """The scaffold: docstring with provenance, imports, markers, delimiter."""
    truncation_note = ""
    if brief.truncated:
        truncation_note = (
            "\n    WARNING: the source ticket text was TRUNCATED when this file was\n"
            "    generated. Requirements may be missing - read the ticket directly.\n"
        )
    return f'''"""Tests derived from {brief.key}: {brief.summary}
{truncation_note}
{provenance_block(brief, ticket_updated=ticket_updated, identity=identity)}
"""

from __future__ import annotations

import pytest

from ai_qa.generate.sentinel import skip_reason

pytestmark = [pytest.mark.{kind}, pytest.mark.ticket("{brief.key}")]


{DELIMITER}
'''


def target_path(brief: Brief, *, kind: str = "ui", root: Path | str = "tests") -> Path:
    """Where the generated file goes.

    Named after the behaviour area, not the ticket: a ticket is a unit of work
    and a test file is a unit of behaviour.
    """
    cleaned = "".join(c if c.isalnum() else "_" for c in brief.summary.lower())
    words = [w for w in cleaned.split("_") if w]

    # Truncate on a WORD boundary, never mid-word. A plain [:48] cut produced
    # `test_build_login_screen_ui_with_validation_and_passwo.py` for DC-11,
    # which had to be renamed by hand.
    slug_words: list[str] = []
    for word in words:
        candidate = "_".join([*slug_words, word])
        if slug_words and len(candidate) > 44:
            break
        slug_words.append(word)

    slug = "_".join(slug_words) or brief.key.lower().replace("-", "_")
    return Path(root) / kind / f"test_{slug}.py"


def read_provenance(path: Path) -> dict[str, str]:
    """Parse a generated file's provenance block back out (FR-020)."""
    fields: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    head = text.split('"""')[1] if text.count('"""') >= 2 else ""
    for line in head.splitlines():
        if ":" in line:
            name, _, value = line.partition(":")
            name = name.strip()
            if name in {
                "generated-by",
                "ticket",
                "ticket-summary",
                "ticket-updated",
                "ticket-digest",
                "generated-at",
                "generated-by-identity",
            }:
                fields[name] = value.strip()
    return fields


def is_generated(path: Path) -> bool:
    """FR-018: generated artifacts are identifiable without reading closely."""
    try:
        return GENERATED_MARKER in path.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover
        return False
