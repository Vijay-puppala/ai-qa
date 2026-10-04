"""Seven failure causes, seven distinct errors (FR-014, SC-005).

Also covers the negative rule from research R7: an ordinary 4xx is attempted
once and never retried, because retrying it cannot succeed and only turns a
clear error into a slow one.
"""

from __future__ import annotations

import httpx
import pytest

from ai_qa.config import Settings
from ai_qa.jira import (
    JiraAuthError,
    JiraClient,
    JiraConfigError,
    JiraForbiddenError,
    JiraNotFoundError,
    JiraQueryError,
    JiraRateLimitError,
    JiraUnavailableError,
)

from jira_fixtures import issue_payload, json_response

pytestmark = pytest.mark.jira


def test_config_error_is_raised_before_any_request() -> None:
    """FR-011: a local problem must not surface as a Jira failure."""
    with pytest.raises(JiraConfigError) as caught:
        JiraClient(Settings(base_url="https://example.com"))

    assert ".env.example" in str(caught.value)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, JiraAuthError),
        (403, JiraForbiddenError),
        (404, JiraNotFoundError),
        (500, JiraUnavailableError),
    ],
)
def test_status_maps_to_its_own_error(mock_jira, status, expected) -> None:
    client = mock_jira([json_response(status, {})] * 3)
    with pytest.raises(expected):
        client.get_issue("TC-345")


def test_query_rejection_is_not_a_generic_failure(mock_jira) -> None:
    """A 400 on search carries Jira's own reason (FR-014)."""
    client = mock_jira([json_response(400, {"errorMessages": ["Field 'nope' does not exist"]})])

    with pytest.raises(JiraQueryError) as caught:
        list(client.search("nope = 1"))

    assert "does not exist" in str(caught.value)


def test_timeout_becomes_unavailable_not_a_hang(mock_jira) -> None:
    """FR-013, SC-007: a stalled Jira must not stall the run."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(JiraUnavailableError) as caught:
        mock_jira(handler).get_issue("TC-345")

    assert "did not respond within" in str(caught.value)


def test_rate_limit_honours_retry_after_then_gives_up(mock_jira) -> None:
    """FR-015: respect the advertised delay, bounded attempts."""
    slept: list[float] = []
    client = mock_jira([json_response(429, {}, **{"Retry-After": "7"})] * 3)
    client._sleep = slept.append  # noqa: SLF001 - asserting the backoff contract

    with pytest.raises(JiraRateLimitError) as caught:
        client.get_issue("TC-345")

    assert caught.value.retry_after == 7.0
    assert slept == [7.0, 7.0], "did not honour Retry-After on every retry"


def test_401_is_attempted_once_and_never_retried(mock_jira) -> None:
    """Research R7's negative rule, asserted as a call count."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return json_response(401, {})

    with pytest.raises(JiraAuthError):
        mock_jira(handler).get_issue("TC-345")

    assert len(calls) == 1, f"a 401 was retried {len(calls)} times"


def test_5xx_is_retried_then_succeeds(mock_jira) -> None:
    client = mock_jira([json_response(503, {}), json_response(200, issue_payload())])

    assert client.get_issue("TC-345").key == "TC-345"
