"""The scaffold is byte-predictable, and carries provenance (FR-017, FR-018)."""

from __future__ import annotations

import pytest

from ai_qa.generate import scaffold
from ai_qa.generate.brief import build
from ai_qa.jira.models import JiraIssue

PROVENANCE_FIELDS = [
    "generated-by",
    "ticket",
    "ticket-summary",
    "ticket-updated",
    "ticket-digest",
    "generated-at",
    "generated-by-identity",
]


def _issue(**kw: object) -> JiraIssue:
    base = dict(
        key="TC-345",
        project_key="TC",
        summary="Checkout rejects an expired card",
        description="An expired card must be refused and the reason shown.",
        status="In Progress",
        issue_type="Bug",
        labels=("checkout",),
        raw={},
    )
    base.update(kw)
    return JiraIssue(**base)  # type: ignore[arg-type]


def test_all_seven_provenance_fields_are_written(tmp_path) -> None:
    target = tmp_path / "test_x.py"
    target.write_text(scaffold.render(build(_issue()), identity="dev@example.com"), encoding="utf-8")

    fields = scaffold.read_provenance(target)
    for name in PROVENANCE_FIELDS:
        assert name in fields, f"provenance field {name!r} missing"
    assert fields["ticket"] == "TC-345"
    assert fields["generated-by-identity"] == "dev@example.com"


def test_identity_is_recorded_for_feature_004() -> None:
    """Needed by 004's author-may-not-approve policy, knowable only now."""
    rendered = scaffold.render(build(_issue()), identity="someone@example.com")
    assert "generated-by-identity: someone@example.com" in rendered


def test_generated_files_are_distinguishable_from_hand_written(tmp_path) -> None:
    gen = tmp_path / "test_gen.py"
    hand = tmp_path / "test_hand.py"
    gen.write_text(scaffold.render(build(_issue())), encoding="utf-8")
    hand.write_text("def test_hand():\n    assert True\n", encoding="utf-8")

    assert scaffold.is_generated(gen)
    assert not scaffold.is_generated(hand)


def test_scaffold_is_byte_predictable_apart_from_the_timestamp() -> None:
    """Everything above the delimiter is derived from the ticket alone."""
    a = scaffold.render(build(_issue()), identity="x@y.z")
    b = scaffold.render(build(_issue()), identity="x@y.z")

    strip = lambda s: "\n".join(l for l in s.splitlines() if not l.startswith("generated-at:"))
    assert strip(a) == strip(b)


def test_scaffold_carries_the_ticket_marker() -> None:
    """005 needs it for attribution and run scoping."""
    assert 'pytest.mark.ticket("TC-345")' in scaffold.render(build(_issue()))


def test_file_is_named_for_behaviour_not_the_ticket() -> None:
    path = scaffold.target_path(build(_issue()))
    assert "tc_345" not in path.name
    assert "checkout" in path.name
