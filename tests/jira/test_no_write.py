"""FR-007 is a prohibition, so it needs its own test.

Write operations were deferred out of this feature on 2026-10-04. The
requirement flipped from a capability to a prohibition, and a prohibition that
nothing asserts is one a future contributor can quietly undo.
"""

from __future__ import annotations

import inspect
import re

import pytest

from ai_qa.jira import JiraClient

pytestmark = pytest.mark.jira

_FORBIDDEN = {
    "add_comment",
    "transition_issue",
    "create_issue",
    "update_issue",
    "delete_issue",
    "add_attachment",
    "edit_issue",
}


def test_client_exposes_no_mutating_method() -> None:
    present = _FORBIDDEN.intersection(dir(JiraClient))
    assert not present, f"write methods reintroduced without a spec change: {sorted(present)}"


def test_client_issues_no_mutating_http_verb() -> None:
    """The only POST in this client is the search endpoint.

    Checked against the source so a new PUT/PATCH/DELETE cannot slip in
    unnoticed - FR-007 forbids writing to Jira in any form.
    """
    source = inspect.getsource(JiraClient)

    for verb in ('"PUT"', '"PATCH"', '"DELETE"'):
        assert verb not in source, f"mutating verb {verb} found in JiraClient"

    # POST is not inherently a write: Jira uses it for two read-only
    # operations. Rather than count POSTs - which fired a false positive when
    # JQL validation was added - assert every POST targets a known read-only
    # endpoint. A POST anywhere else is a write and must fail here.
    read_only_post_paths = {"/rest/api/3/search/jql", "/rest/api/3/jql/parse"}
    posts = re.findall(r'"POST",\s*"([^"]+)"', source)

    assert posts, "expected at least the search POST"
    unexpected = sorted(set(posts) - read_only_post_paths)
    assert not unexpected, f"POST to non-read-only endpoint(s): {unexpected}"
