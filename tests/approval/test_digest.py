"""The X1 property, asserted directly (FR-017 as corrected).

This is the first thing to verify in this feature. If a body edit changes the
digest, then approving a design and then implementing it voids the approval
that permitted the implementation - and the 003 -> 004 -> 005 workflow
deadlocks. The whole chain rests on this test.
"""

from __future__ import annotations

from ai_qa.approval.digest import design_digest, design_digest_for, covered_test_names

from approval_fixtures import DESIGN, implement_one


def test_implementing_a_body_does_not_void_the_approval(design) -> None:
    """The X1 property. Writing automation is the act approval authorises."""
    before = design_digest_for(design)

    implement_one(design)

    assert design_digest_for(design) == before, (
        "a body edit changed the design digest - approving then implementing "
        "would void the approval that permitted the implementation"
    )


def test_formatting_and_comments_do_not_change_it(design) -> None:
    before = design_digest_for(design)
    source = design.read_text(encoding="utf-8")
    design.write_text(source.replace("import pytest", "import pytest  # noqa"), encoding="utf-8")

    assert design_digest_for(design) == before


def test_editing_a_docstring_voids_the_approval() -> None:
    """The docstring states the behaviour under review, so it is reviewed."""
    changed = DESIGN.replace("shows the user why", "shows the reason")
    assert design_digest(changed) != design_digest(DESIGN)


def test_renaming_a_test_voids_the_approval() -> None:
    changed = DESIGN.replace("test_expired_card_is_rejected", "test_expired_card_refused")
    assert design_digest(changed) != design_digest(DESIGN)


def test_removing_a_test_voids_the_approval() -> None:
    cut = DESIGN.split("def test_expired_card_error_names_the_reason")[0]
    assert design_digest(cut) != design_digest(DESIGN)


def test_changing_a_marker_voids_the_approval() -> None:
    changed = DESIGN.replace('pytest.mark.ticket("TC-345")', 'pytest.mark.ticket("TC-999")')
    assert design_digest(changed) != design_digest(DESIGN)


def test_covered_test_names_are_recorded_so_nothing_needs_inferring() -> None:
    """FR-014: "what exactly was approved?" must be answerable."""
    assert covered_test_names(DESIGN) == (
        "test_expired_card_is_rejected",
        "test_expired_card_error_names_the_reason",
    )
