"""The deterministic hand-off from platform to authoring assistant (R3).

Making the brief a concrete artifact rather than an in-memory hand-off is what
lets the deterministic half be tested on its own, with no assistant involved -
which is exactly what FR-029 requires.
"""

from __future__ import annotations

import hashlib
from typing import NamedTuple

from ai_qa.jira.models import JiraIssue

#: Clip very long ticket text. FR-016: truncation must never be silent.
MAX_DESCRIPTION_CHARS = 20_000


class Brief(NamedTuple):
    key: str
    summary: str
    description: str
    issue_type: str
    status: str
    labels: tuple[str, ...]
    content_digest: str
    truncated: bool
    warnings: tuple[str, ...]

    def render(self) -> str:
        lines = [
            f"# Brief for {self.key}",
            "",
            f"**Summary**: {self.summary}",
            f"**Type**: {self.issue_type}    **Status**: {self.status}",
        ]
        if self.labels:
            lines.append("**Labels**: " + ", ".join(self.labels))
        lines += ["", "## Description", "", self.description or "_(empty)_"]
        if self.warnings:
            lines += ["", "## Warnings", ""] + [f"- {w}" for w in self.warnings]
        lines += [
            "",
            "## Conventions",
            "",
            "Follow the skeleton conventions in CLAUDE.md. Do not restate them here -",
            "a copy in every brief guarantees the two diverge.",
        ]
        return "\n".join(lines) + "\n"


def content_digest(text: str) -> str:
    """Digest of a ticket's text, for the staleness check (FR-020)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def build(issue: JiraIssue) -> Brief:
    """Project an issue into a brief, with the two mandatory warnings."""
    description = issue.description
    truncated = len(description) > MAX_DESCRIPTION_CHARS
    if truncated:
        description = description[:MAX_DESCRIPTION_CHARS]

    warnings: list[str] = []

    if truncated:
        warnings.append(
            f"Description was TRUNCATED at {MAX_DESCRIPTION_CHARS} characters. "
            "Requirements may be missing - read the ticket directly before "
            "treating this brief as complete (FR-016)."
        )

    has_attachments = bool((issue.raw.get("fields") or {}).get("attachment"))
    if not description.strip():
        if has_attachments:
            warnings.append(
                "The description text is EMPTY but the ticket has non-text "
                "content (attachments or images). The requirement is probably "
                "in there - this is not an empty requirement (FR-015)."
            )
        else:
            warnings.append(
                "The ticket has little usable requirement text. Say so rather "
                "than inventing requirements to fill the gap (FR-014)."
            )
    elif len(description.strip()) < 40:
        warnings.append(
            "The ticket has very little requirement text. Do not invent "
            "requirements to fill the gap (FR-014)."
        )

    return Brief(
        key=issue.key,
        summary=issue.summary,
        description=description,
        issue_type=issue.issue_type,
        status=issue.status,
        labels=issue.labels,
        content_digest=content_digest(issue.text_content()),
        truncated=truncated,
        warnings=tuple(warnings),
    )
