"""FR-004's test-runtime call path, through the real client.

Feature 002 requires Jira access "from test code at runtime **and** from
tooling outside a test run, through one shared client". Every other test in
this suite takes the ``MockTransport`` path, so without these the runtime half
is never constructed - a passing suite that proves only half the requirement.

These skip when Jira is unconfigured (FR-016, SC-008), so an engineer with no
token still gets a green run.
"""

from __future__ import annotations

import pytest

from ai_qa.jira import JiraClient

pytestmark = pytest.mark.jira


def test_the_runtime_fixture_yields_a_usable_client(jira_client) -> None:
    """One shared client class on both call paths, not two implementations."""
    assert isinstance(jira_client, JiraClient)
    assert jira_client.host.startswith(("http://", "https://"))


def test_credentials_work_from_test_code(jira_client) -> None:
    """The same check the `check` subcommand performs, from a test.

    Skips when Jira cannot be **reached**, and only fails when Jira actively
    rejects the credentials. Without that distinction this test breaks SC-009
    ("the full suite passes with no network access to any Jira site") for
    anyone who has a token configured but happens to be offline - which is a
    normal state, not a defect.
    """
    from ai_qa.jira import JiraUnavailableError

    try:
        who = jira_client.whoami()
    except JiraUnavailableError as exc:
        pytest.skip(f"Jira is configured but unreachable - no network: {exc}")

    assert who.get("accountId") or who.get("emailAddress") or who.get("displayName")


def test_tooling_and_runtime_share_one_client_class() -> None:
    """FR-004: the two paths cannot diverge because there is one class.

    Runs unconditionally - it needs no credentials, only the import graph.
    """
    from ai_qa.jira import __main__ as cli

    assert cli.JiraClient is JiraClient
