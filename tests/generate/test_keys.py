"""Key extraction: every input form, and every key-like non-key.

SC-004 is "100% of input forms" and SC-005 is "zero false positives" - both
exhaustive claims over input sets, which is only testable because extraction
is a pure function of its input (FR-025).
"""

from __future__ import annotations

import pytest

from ai_qa.generate.keys import Outcome, Reason, extract

ACCEPTED_FORMS = [
    "generate tests for TC-345",
    "for TC-345 generate tests",
    "TC-345: write tests",
    "tc-345",
    "Tc-345",
    "https://site.atlassian.net/browse/TC-345",
    "https://site.atlassian.net/jira/software/c/projects/TC/boards/1?selectedIssue=TC-345",
]

NON_KEYS = [
    ("we follow ISO-8601 for dates", Reason.DENYLISTED_PREFIX),
    ("COVID-19 regression suite", Reason.DENYLISTED_PREFIX),
    ("encoding is UTF-8", Reason.DENYLISTED_PREFIX),
    ("see CVE-2026-1234", Reason.DENYLISTED_PREFIX),
    ("RFC-7231 says so", Reason.DENYLISTED_PREFIX),
    ("sprint SPRINT-2026 ends soon", Reason.YEAR_LIKE),
    ("build BUILD-12345678 failed", Reason.NUMBER_TOO_LONG),
]


@pytest.mark.parametrize("text", ACCEPTED_FORMS)
def test_every_accepted_form_yields_the_key(text: str) -> None:
    result = extract(text)
    assert result.outcome is Outcome.ONE
    assert result.keys == ("TC-345",), f"{text!r} -> {result.keys}"


@pytest.mark.parametrize(("text", "reason"), NON_KEYS)
def test_key_like_non_keys_are_never_accepted(text: str, reason: Reason) -> None:
    """A bare regex accepts all of these. FR-005 forbids a lookup for any."""
    result = extract(text)
    assert result.keys == (), f"{text!r} wrongly accepted {result.keys}"
    assert reason in {r.reason for r in result.rejected}


def test_a_bare_date_is_not_even_a_candidate() -> None:
    """``2026-10`` cannot match: a project code must start with a letter."""
    result = extract("sprint ending 2026-10")
    assert result.keys == ()
    assert result.rejected == ()


def test_rejections_are_returned_not_swallowed() -> None:
    """An engineer whose real key was filtered must see which rule fired."""
    result = extract("ISO-8601 and UTF-8")
    assert {r.candidate for r in result.rejected} == {"ISO-8601", "UTF-8"}


def test_no_key_is_reported_as_none() -> None:
    assert extract("please write some tests").outcome is Outcome.NONE
    assert extract("").outcome is Outcome.NONE


def test_several_keys_are_all_reported() -> None:
    """FR-007: acting on one of several looks like success and hides the rest."""
    result = extract("tests for TC-345 and TC-346 and PLATFORM-12")
    assert result.outcome is Outcome.MANY
    assert set(result.keys) == {"TC-345", "TC-346", "PLATFORM-12"}


def test_a_real_key_next_to_a_non_key_still_works() -> None:
    result = extract("per ISO-8601, write tests for TC-345")
    assert result.keys == ("TC-345",)
    assert result.rejected[0].candidate == "ISO-8601"


def test_extraction_needs_no_network() -> None:
    """FR-025: pure function, no I/O. Asserted by there being nothing to patch."""
    import inspect

    from ai_qa.generate import keys

    source = inspect.getsource(keys)
    for forbidden in ("httpx", "requests", "urllib", "socket", "JiraClient"):
        assert forbidden not in source, f"extraction reached for {forbidden}"
