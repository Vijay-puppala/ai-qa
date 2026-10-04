"""Querying issues, and the no-truncation guarantee (US4, SC-011)."""

from __future__ import annotations

import httpx
import pytest

from jira_fixtures import issue_payload, json_response

pytestmark = pytest.mark.jira


def _page(keys, token=None, is_last=False):
    return json_response(
        200,
        {
            "issues": [issue_payload(k) for k in keys],
            "nextPageToken": token,
            "isLast": is_last,
        },
    )


def test_search_exhausts_every_page(mock_jira) -> None:
    """SC-011: a multi-page result set yields all issues, zero truncation."""
    client = mock_jira(
        [
            _page(["TC-1", "TC-2"], token="p2"),
            _page(["TC-3", "TC-4"], token="p3"),
            _page(["TC-5"], token=None, is_last=True),
        ]
    )

    keys = [i.key for i in client.search("project = TC")]

    assert keys == ["TC-1", "TC-2", "TC-3", "TC-4", "TC-5"]


def test_search_forwards_the_page_token(mock_jira) -> None:
    """Token pagination, not offsets - offsets drift (research R6)."""
    seen: list[object] = []

    pages = [_page(["TC-1"], token="p2"), _page(["TC-2"], token=None, is_last=True)]

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json

        seen.append(_json.loads(request.content).get("nextPageToken"))
        return pages[len(seen) - 1]

    list(mock_jira(handler).search("project = TC"))

    assert seen == [None, "p2"]


def test_search_hits_the_non_deprecated_endpoint(mock_jira) -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return _page(["TC-1"], is_last=True)

    list(mock_jira(handler).search("project = TC"))

    assert paths == ["/rest/api/3/search/jql"]


def test_search_is_lazy(mock_jira) -> None:
    """A caller taking the first result must not pay for every page."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _page(["TC-%d" % len(calls)], token="next")

    client = mock_jira(handler)
    first = next(iter(client.search("project = TC")))

    assert first.key == "TC-1"
    assert len(calls) == 1, "search fetched more pages than the caller consumed"


def test_an_unknown_field_is_reported_as_a_rejected_query(mock_jira) -> None:
    """Jira answers 200 + empty list for an unknown field, not 400.

    Verified live: ``POST /search/jql`` does not reject ``bogusfield = 1``, so
    without an explicit validation step a typo is indistinguishable from
    "nothing matched" - the cause confusion FR-014 forbids. ``validate_jql``
    asks Jira's own parser instead.
    """
    from ai_qa.jira import JiraQueryError

    client = mock_jira(
        [
            json_response(
                200,
                {"queries": [{"query": "bogusfield = 1", "errors": ["Field 'bogusfield' does not exist"]}]},
            )
        ]
    )

    with pytest.raises(JiraQueryError) as caught:
        client.validate_jql("bogusfield = 1")

    assert "bogusfield" in str(caught.value)


def test_a_valid_query_passes_validation(mock_jira) -> None:
    client = mock_jira([json_response(200, {"queries": [{"query": "project = TC", "errors": []}]})])

    client.validate_jql("project = TC")  # must not raise
