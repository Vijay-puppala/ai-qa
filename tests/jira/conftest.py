"""Offline Jira fixtures (FR-018, SC-009, research R5).

``httpx.MockTransport`` is what makes this feature testable with no network
and no new dependency: the conventional answers (``respx``, ``vcrpy``) are both
packages the dependency floor forbids, and httpx already ships what is needed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import httpx
import pytest

from ai_qa.jira import JiraClient
from jira_fixtures import jira_settings

@pytest.fixture
def mock_jira() -> Callable[..., JiraClient]:
    """Build a client over canned responses.

    Accepts either a handler callable or a sequence of ``httpx.Response``
    returned in order, which is what the retry and pagination tests need.
    """

    def factory(
        responses: Sequence[httpx.Response] | Callable[[httpx.Request], httpx.Response],
        **settings_overrides: object,
    ) -> JiraClient:
        if callable(responses):
            handler = responses
        else:
            queue = list(responses)

            def handler(request: httpx.Request) -> httpx.Response:  # type: ignore[misc]
                return queue.pop(0) if queue else httpx.Response(500, json={})

        return JiraClient(
            jira_settings(**settings_overrides),
            transport=httpx.MockTransport(handler),
            sleep=lambda _s: None,  # never actually wait in tests
        )

    return factory


@pytest.fixture(scope="session")
def jira_client(settings):
    """A client built from **real** settings - FR-004's runtime call path.

    Session-scoped for the same reason ``settings`` is in feature 001: no
    mutable per-test state, and it avoids rebuilding a connection pool per
    test.

    **Skips** when Jira is not configured rather than failing. An optional
    integration must never become a precondition for running the suite
    (FR-016, SC-008) - a machine with no Jira token still gets a green run.
    """
    if not settings.jira_configured:
        pytest.skip("Jira is not configured on this machine - optional integration")
    client = JiraClient(settings)
    try:
        yield client
    finally:
        client.close()
