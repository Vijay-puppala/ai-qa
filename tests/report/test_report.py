"""The report: self-contained, honest about its scope, and never silent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_qa.report import build, read_results, render


def _result(tmp_path: Path, **over) -> Path:
    body = {
        "uuid": over.get("uuid", "u1"),
        "name": over.get("name", "test_expired_card_is_rejected"),
        "fullName": over.get("full_name", "tests.ui.test_x#test_expired_card_is_rejected"),
        "status": over.get("status", "passed"),
        "start": 1000,
        "stop": 1250,
        "labels": over.get("labels", [{"name": "ticket", "value": "TC-345"}]),
    }
    if over.get("failure"):
        body["statusDetails"] = {"message": over["failure"], "trace": over.get("trace", "tb")}
    path = tmp_path / f"{body['uuid']}-result.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_results_are_projected_from_the_real_schema(tmp_path) -> None:
    _result(tmp_path)
    results = read_results(tmp_path)

    assert len(results) == 1
    assert results[0].ticket == "TC-345"
    assert results[0].duration_ms == 250


def test_failure_message_and_trace_are_available(tmp_path) -> None:
    """Verified present in real allure-pytest output - no extra capture needed."""
    _result(tmp_path, status="failed", failure="AssertionError: nope", trace="line 1\nline 2")
    r = read_results(tmp_path)[0]

    assert r.failure_message == "AssertionError: nope"
    assert "line 2" in (r.failure_trace or "")


def test_a_test_without_a_ticket_label_is_grouped_as_unattributed(tmp_path) -> None:
    """The first symptom of the conftest ticket hook being broken."""
    _result(tmp_path, labels=[{"name": "suite", "value": "ui"}])
    summary = build(read_results(tmp_path), scope="full suite")

    assert "Unattributed" in summary.by_ticket


def test_scope_is_mandatory_and_appears_first(tmp_path) -> None:
    """SC-021: a ticket-scoped green must never read as suite-wide."""
    _result(tmp_path)
    html = render(build(read_results(tmp_path), scope="ticket TC-345 only"))

    assert "Scope: ticket TC-345 only" in html
    assert html.index("Scope:") < html.index("Ticket TC-345")


def test_report_states_it_is_not_an_allure_report(tmp_path) -> None:
    """FR-032: a reader assuming parity hunts for history that is not there."""
    _result(tmp_path)
    html = render(build(read_results(tmp_path), scope="full suite"))

    assert "not an Allure" in html
    assert "no run timeline" in html.lower() or "no historical trend" in html.lower()


def test_report_makes_zero_external_requests(tmp_path) -> None:
    """SC-018: renders offline and on a locked-down machine."""
    _result(tmp_path)
    html = render(build(read_results(tmp_path), scope="full suite"))

    for host in ("cdn.", "fonts.googleapis", "unpkg", "jsdelivr", "http://", "https://"):
        assert host not in html, f"report reached out to {host}"


def test_an_empty_run_is_rendered_as_a_failure(tmp_path) -> None:
    """FR-011, FR-017: a run that tested nothing is not a clean run."""
    summary = build([], scope="ticket NOSUCH-1 only")
    html = render(summary)

    assert summary.empty
    assert "ZERO tests" in html


def test_a_repaired_pass_is_disclosed(tmp_path) -> None:
    """FR-041: passing because a tool edited the test is a different claim."""
    _result(tmp_path)
    results = read_results(tmp_path)
    html = render(build(results, scope="full suite", repaired={results[0].full_name}))

    assert "REPAIRED" in html


def test_a_credential_never_reaches_the_report(tmp_path) -> None:
    """SC-011: the report is the artifact most likely to leave the team."""
    _result(
        tmp_path,
        status="failed",
        failure="auth failed with Authorization: Bearer SENTINEL-abc123",
        trace="Authorization: Bearer SENTINEL-abc123",
    )
    html = render(build(read_results(tmp_path), scope="full suite"))

    assert "SENTINEL-abc123" not in html


def test_results_are_not_truncated_for_a_large_run(tmp_path) -> None:
    """FR-018: no silent truncation."""
    for i in range(250):
        _result(tmp_path, uuid=f"u{i}", name=f"test_{i}", full_name=f"m#test_{i}")
    summary = build(read_results(tmp_path), scope="full suite")
    html = render(summary)

    assert summary.collected == 250
    assert "test_249" in html
