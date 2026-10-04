"""Shared constants and helpers for the approval-gate tests.

A module of their own rather than ``conftest.py``: importing a conftest from a
test module creates a second module instance.
"""

from __future__ import annotations

from pathlib import Path

DESIGN = '''\
"""Tests derived from TC-345: Checkout rejects an expired card

generated-by: ai-qa
ticket: TC-345
ticket-summary: Checkout rejects an expired card
ticket-updated: 2026-10-04T09:12:33.000+0000
ticket-digest: abc123def456
generated-at: 2026-10-04T10:05:11Z
generated-by-identity: author@example.com
"""

from __future__ import annotations

import pytest

from ai_qa.generate.sentinel import skip_reason

pytestmark = [pytest.mark.ui, pytest.mark.ticket("TC-345")]


# --- ai-qa: generated test functions below ---


def test_expired_card_is_rejected():
    """Checkout refuses an expired card and shows the user why."""
    pytest.skip(skip_reason())


def test_expired_card_error_names_the_reason():
    """The refusal message states that the card has expired."""
    pytest.skip(skip_reason())
'''


def implement_one(path: Path) -> None:
    """Write a real body for the first test - the act approval authorises."""
    source = path.read_text(encoding="utf-8")
    source = source.replace(
        '''def test_expired_card_is_rejected():
    """Checkout refuses an expired card and shows the user why."""
    pytest.skip(skip_reason())''',
        '''def test_expired_card_is_rejected():
    """Checkout refuses an expired card and shows the user why."""
    assert True''',
        1,
    )
    path.write_text(source, encoding="utf-8")
