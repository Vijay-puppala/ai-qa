"""The repair boundary: fix what cannot run, never make a failure pass.

SC-022 and SC-023 are negative criteria, which is only testable because both
decisions are pure functions of their inputs.
"""

from __future__ import annotations

import pytest

from ai_qa.automation import (
    ELIGIBLE_TYPES,
    ESCALATE_TYPES,
    Verdict,
    assertion_digest,
    classify,
    explain,
    repair_changed_assertions,
)

BASE = '''
def test_total_matches_expectation():
    """The basket total matches what the user was quoted."""
    expected = 5
    total = compute()
    assert total == expected
'''


@pytest.mark.parametrize("name", sorted(ELIGIBLE_TYPES))
def test_mechanical_faults_are_eligible(name: str) -> None:
    assert classify(name) is Verdict.ELIGIBLE


@pytest.mark.parametrize("name", sorted(ESCALATE_TYPES))
def test_product_side_failures_are_never_repaired(name: str) -> None:
    """SC-022: zero repair attempts on these."""
    assert classify(name) is Verdict.ESCALATE


@pytest.mark.parametrize(
    "name",
    ["SomeFutureErrorNobodyClassified", "ZeroDivisionError", "", None],
)
def test_an_unrecognised_failure_fails_closed(name) -> None:
    """FR-038: ambiguity resolves towards escalation, never towards editing.

    A failure mode introduced by a future dependency upgrade must land on the
    safe side without anyone remembering to classify it.
    """
    assert classify(name) is Verdict.ESCALATE


def test_element_not_found_is_excluded_deliberately() -> None:
    """The commonest test-side fault in browser automation - and excluded.

    It is indistinguishable from a feature that was never built, so repairing
    it would sometimes erase a genuine finding.
    """
    assert classify("ElementNotFoundError") is Verdict.ESCALATE
    assert "erase a real finding" in explain("ElementNotFoundError")


def test_a_fully_qualified_name_is_classified_on_its_leaf() -> None:
    assert classify("playwright._impl._errors.TimeoutError") is Verdict.ESCALATE
    assert classify("builtins.SyntaxError") is Verdict.ELIGIBLE


# ----------------------------------------------------------- assertion digest


def test_reformatting_does_not_change_the_digest() -> None:
    changed = BASE.replace("total = compute()", "total = compute()  # fixed call")
    assert not repair_changed_assertions(BASE, changed)


def test_fixing_a_mechanical_fault_is_permitted() -> None:
    """The repair this feature exists to allow."""
    broken = BASE.replace("compute()", "comput()")
    assert not repair_changed_assertions(broken, BASE)


def test_weakening_an_assertion_is_refused() -> None:
    """SC-023: the shortest path to green, closed off."""
    weakened = BASE.replace("assert total == expected", "assert total is not None")
    assert repair_changed_assertions(BASE, weakened)


def test_deleting_an_assertion_is_refused() -> None:
    gutted = BASE.replace("    assert total == expected", "    pass")
    assert repair_changed_assertions(BASE, gutted)


def test_adding_an_assertion_is_also_a_change() -> None:
    extra = BASE + "    assert total > 0\n"
    assert repair_changed_assertions(BASE, extra)


def test_the_known_hole_is_documented_not_pretended_away() -> None:
    """Changing a value an assertion depends on is NOT caught.

    The digest compares assertion *text*. This asserts the documented
    limitation so nobody later mistakes it for a guarantee: the remaining risk
    is carried by bounded attempts, the logged digests, and the report
    disclosing every repaired pass.
    """
    moved_goalposts = BASE.replace("expected = 5", "expected = 0")
    assert not repair_changed_assertions(BASE, moved_goalposts)


def test_digest_can_be_scoped_to_one_test() -> None:
    two = BASE + '''
def test_other():
    """Another behaviour."""
    assert 1 == 1
'''
    edited_other = two.replace("assert 1 == 1", "assert 2 == 2")
    assert not repair_changed_assertions(two, edited_other, "test_total_matches_expectation")
    assert repair_changed_assertions(two, edited_other, "test_other")


def test_expect_calls_count_as_assertions() -> None:
    page = '''
def test_ui():
    """Playwright style."""
    expect(page.locator("#x")).to_have_text("hello")
'''
    weakened = page.replace('to_have_text("hello")', "to_be_visible()")
    assert assertion_digest(page) != assertion_digest(weakened)
