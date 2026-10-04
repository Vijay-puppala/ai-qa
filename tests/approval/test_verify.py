"""The pipeline gate: fail the run, name every offender (FR-026, FR-038, FR-039).

``verify`` is the same command an engineer runs locally, so a pipeline failure
must be reproducible before pushing - which means identical results for the
same repository state (SC-020).
"""

from __future__ import annotations

import pytest

from ai_qa.approval import __main__ as cli
from ai_qa.approval import records
from ai_qa.approval.digest import covered_test_names, design_digest_for
from ai_qa.config import Settings


@pytest.fixture
def run_verify(monkeypatch, records_dir):
    def runner(root, **overrides):
        settings = Settings(
            base_url="https://example.com",
            approval_records_dir=records_dir,
            **overrides,
        )
        monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda c, **kw: settings))
        return cli.main(["verify", "--root", str(root)])

    return runner


def _approve(design, records_dir) -> None:
    records.write(
        records.DecisionRecord(
            decision="approved",
            ticket="TC-345",
            design_path=str(design).replace("\\", "/"),
            design_digest=design_digest_for(design),
            approver="reviewer@example.com",
            author="author@example.com",
            policy_require_second_person=True,
            timestamp=records.now_stamp(),
            test_names=covered_test_names(design.read_text(encoding="utf-8")),
        ),
        root=records_dir,
    )


def test_an_unapproved_design_fails_the_run(design, run_verify, capsys) -> None:
    """FR-026: not executed, and not skipped-and-passed."""
    code = run_verify(design.parent.parent)

    assert code == cli.EXIT_UNAPPROVED
    err = capsys.readouterr().err
    assert str(design.name) in err


def test_the_failure_names_every_offender_and_its_remedy(design, run_verify, capsys) -> None:
    """FR-038: a failure reporting only a count costs several pipeline runs."""
    second = design.parent / "test_other_area.py"
    second.write_text(design.read_text(encoding="utf-8").replace("TC-345", "TC-346"), encoding="utf-8")

    run_verify(design.parent.parent)

    err = capsys.readouterr().err
    assert "test_checkout_expired_card.py" in err
    assert "test_other_area.py" in err
    assert err.count("remedy:") == 2


def test_an_approved_design_passes(design, run_verify, records_dir) -> None:
    _approve(design, records_dir)
    assert run_verify(design.parent.parent) == cli.EXIT_OK


def test_handwritten_tests_are_not_blocked(handwritten, run_verify) -> None:
    """FR-029: blocking every hand-written test is how a gate gets disabled."""
    assert run_verify(handwritten.parent.parent) == cli.EXIT_OK


def test_two_runs_over_the_same_state_agree(design, run_verify, capsys) -> None:
    """SC-020: a pipeline failure must be reproducible locally."""
    first_code = run_verify(design.parent.parent)
    first = capsys.readouterr().err
    second_code = run_verify(design.parent.parent)
    second = capsys.readouterr().err

    assert first_code == second_code
    assert first == second


def test_verify_makes_no_network_request() -> None:
    """FR-025, SC-011: a pipeline verifies with no credentials, no network."""
    import inspect

    source = inspect.getsource(cli) + inspect.getsource(records)
    for forbidden in ("httpx", "requests", "urllib.request", "JiraClient"):
        assert forbidden not in source, f"approval verification reached for {forbidden}"
