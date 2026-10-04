"""The brief, and its two mandatory warnings (FR-014, FR-015, FR-016)."""

from __future__ import annotations

from ai_qa.generate import brief as brief_mod
from ai_qa.jira.models import JiraIssue


def _issue(description: str = "x" * 200, raw: dict | None = None) -> JiraIssue:
    return JiraIssue(
        key="TC-345",
        project_key="TC",
        summary="Checkout rejects an expired card",
        description=description,
        status="Open",
        issue_type="Bug",
        raw=raw or {},
    )


def test_brief_carries_the_ticket_content() -> None:
    b = brief_mod.build(_issue("An expired card must be refused, with a reason shown."))
    assert b.key == "TC-345"
    assert "expired card" in b.description
    assert b.content_digest


def test_thin_ticket_is_flagged_not_filled_in() -> None:
    """FR-014: say so rather than inventing requirements."""
    b = brief_mod.build(_issue("fix it"))
    assert any("invent" in w for w in b.warnings)


def test_empty_text_with_attachments_says_so() -> None:
    """FR-015: an empty description plus an image is not an empty requirement."""
    b = brief_mod.build(_issue("", raw={"fields": {"attachment": [{"id": "1"}]}}))
    joined = " ".join(b.warnings)
    assert "non-text" in joined
    assert "not an empty requirement" in joined


def test_empty_text_without_attachments_is_a_different_warning() -> None:
    b = brief_mod.build(_issue("", raw={"fields": {}}))
    assert not any("non-text" in w for w in b.warnings)
    assert any("little usable" in w for w in b.warnings)


def test_truncation_is_never_silent() -> None:
    """FR-016: a clipped ticket that reads as complete is the worst outcome."""
    b = brief_mod.build(_issue("y" * (brief_mod.MAX_DESCRIPTION_CHARS + 500)))

    assert b.truncated is True
    assert any("TRUNCATED" in w for w in b.warnings)
    assert "TRUNCATED" in b.render()


def test_truncation_is_recorded_in_the_generated_artifact() -> None:
    """FR-016: the artifact itself must say content was clipped."""
    from ai_qa.generate import scaffold

    b = brief_mod.build(_issue("y" * (brief_mod.MAX_DESCRIPTION_CHARS + 500)))
    assert "TRUNCATED" in scaffold.render(b)


def test_brief_points_at_conventions_rather_than_copying_them() -> None:
    """A copy in every brief guarantees the two diverge."""
    rendered = brief_mod.build(_issue()).render()
    assert "CLAUDE.md" in rendered
