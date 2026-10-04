"""Fixtures for the approval gate. No network anywhere in this feature."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from approval_fixtures import DESIGN

@pytest.fixture
def design(tmp_path: Path) -> Path:
    """A generated design with two unimplemented tests."""
    ui = tmp_path / "tests" / "ui"
    ui.mkdir(parents=True)
    path = ui / "test_checkout_expired_card.py"
    path.write_text(DESIGN, encoding="utf-8")
    return path


@pytest.fixture
def handwritten(tmp_path: Path) -> Path:
    """A hand-written test: outside the gate's scope (FR-029)."""
    ui = tmp_path / "tests" / "ui"
    ui.mkdir(parents=True, exist_ok=True)
    path = ui / "test_handwritten.py"
    path.write_text(
        textwrap.dedent(
            '''
            def test_something():
                """Written by a human, no provenance."""
                assert True
            '''
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def records_dir(tmp_path: Path) -> Path:
    path = tmp_path / "approvals"
    path.mkdir()
    return path


@pytest.fixture
def as_reviewer(monkeypatch):
    """Identify the caller as somebody other than the design's author."""
    from ai_qa.approval import policy

    monkeypatch.setattr(policy, "approver_identity", lambda: "reviewer@example.com")
    return "reviewer@example.com"


@pytest.fixture
def as_author(monkeypatch):
    from ai_qa.approval import policy

    monkeypatch.setattr(policy, "approver_identity", lambda: "author@example.com")
    return "author@example.com"
