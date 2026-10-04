"""The credential must appear in zero error messages (FR-010, SC-006)."""

from __future__ import annotations

import httpx
import pytest

from ai_qa.jira import JiraNotFoundError, JiraUnavailableError, redact

from jira_fixtures import SENTINEL_TOKEN, json_response

pytestmark = pytest.mark.jira


def test_token_is_masked_in_settings_repr() -> None:
    from jira_fixtures import jira_settings

    assert SENTINEL_TOKEN not in repr(jira_settings())


def test_authorization_header_value_is_masked_whole() -> None:
    """A pattern that masks only the first word leaves the token intact."""
    masked = redact("Authorization: Bearer abc123xyz", None)
    assert "abc123xyz" not in masked


def test_token_absent_from_a_failed_request_message(mock_jira) -> None:
    client = mock_jira([json_response(404, {"errorMessages": [f"token {SENTINEL_TOKEN} bad"]})])

    with pytest.raises(JiraNotFoundError) as caught:
        client.get_issue("TC-1")

    assert SENTINEL_TOKEN not in str(caught.value)


def test_token_absent_from_a_transport_failure(mock_jira) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"refused while sending {SENTINEL_TOKEN}", request=request)

    with pytest.raises(JiraUnavailableError) as caught:
        mock_jira(handler).get_issue("TC-1")

    assert SENTINEL_TOKEN not in str(caught.value)
