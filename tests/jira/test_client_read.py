"""Reading an issue, and the honesty of its failures (US1).

All offline via ``httpx.MockTransport`` - no test here contacts a live Jira.
"""

from __future__ import annotations

import pytest

from ai_qa.jira import (
    JiraAuthError,
    JiraForbiddenError,
    JiraNotFoundError,
)

from jira_fixtures import issue_payload, json_response

pytestmark = pytest.mark.jira


def test_get_issue_returns_all_mandated_fields(mock_jira) -> None:
    """FR-005: key, summary, description, status and issue type all present."""
    client = mock_jira([json_response(200, issue_payload("TC-345"))])

    issue = client.get_issue("TC-345")

    assert issue.key == "TC-345"
    assert issue.project_key == "TC"
    assert issue.summary == "Checkout rejects an expired card"
    assert issue.status == "In Progress"
    assert issue.issue_type == "Bug"
    assert issue.labels == ("checkout", "payments")


def test_adf_description_is_flattened_to_readable_text(mock_jira) -> None:
    """The v3 description is a document tree, not a string (research R2)."""
    client = mock_jira([json_response(200, issue_payload())])

    issue = client.get_issue("TC-345")

    assert "An expired card must be refused." in issue.description
    assert "- Show the reason" in issue.description
    assert "{" not in issue.description, "description leaked raw ADF JSON"


def test_unknown_adf_node_keeps_its_text(mock_jira) -> None:
    """A node type Atlassian adds later must lose formatting, never content."""
    payload = issue_payload(
        description={
            "type": "doc",
            "content": [
                {"type": "someFutureNode", "content": [{"type": "text", "text": "still here"}]}
            ],
        }
    )
    client = mock_jira([json_response(200, payload)])

    assert "still here" in client.get_issue("TC-345").description


def test_missing_description_is_empty_not_an_error(mock_jira) -> None:
    """An issue with no description is normal; failing to read it would not be."""
    client = mock_jira([json_response(200, issue_payload(description=None))])

    assert client.get_issue("TC-345").description == ""


def test_non_ascii_survives_the_round_trip(mock_jira) -> None:
    payload = issue_payload(
        summary="検索が日本語を受け付ける",
        description={
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Ünïcôde ✓ 中文"}]}
            ],
        },
    )
    client = mock_jira([json_response(200, payload)])

    issue = client.get_issue("TC-345")
    assert issue.summary == "検索が日本語を受け付ける"
    assert "Ünïcôde ✓ 中文" in issue.description


def test_404_does_not_claim_the_issue_does_not_exist(mock_jira) -> None:
    """Jira answers 404 for absent *and* invisible issues (FR-014).

    Asserting non-existence would send someone hunting for a deleted ticket
    that is merely invisible to their account.
    """
    client = mock_jira([json_response(404, {"errorMessages": ["Issue does not exist"]})])

    with pytest.raises(JiraNotFoundError) as caught:
        client.get_issue("NOSUCH-1")

    message = str(caught.value)
    assert "not visible to this account" in message
    assert "NOSUCH-1" in message


def test_401_and_403_are_distinguishable(mock_jira) -> None:
    """FR-014: authentication rejected is not the same as access denied."""
    with pytest.raises(JiraAuthError):
        mock_jira([json_response(401, {})]).get_issue("TC-345")

    with pytest.raises(JiraForbiddenError):
        mock_jira([json_response(403, {})]).get_issue("TC-345")


def test_every_error_names_the_host(mock_jira) -> None:
    """FR-017: a misconfigured JIRA_BASE_URL must be diagnosable."""
    with pytest.raises(JiraNotFoundError) as caught:
        mock_jira([json_response(404, {})]).get_issue("TC-1")

    assert "jira.example.invalid" in str(caught.value)
