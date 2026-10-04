"""CLI exit codes are a contract (FR-019, research R12).

A script reacts to the cause, not the message, so each cause gets its own code.
"""

from __future__ import annotations

import httpx
import pytest

from ai_qa.config import Settings
from ai_qa.jira import JiraClient, __main__ as cli
from jira_fixtures import issue_payload, jira_settings, json_response

pytestmark = pytest.mark.jira


@pytest.fixture
def run_cli(monkeypatch):
    """Invoke the CLI against canned responses."""

    def runner(argv, responses, settings: Settings | None = None):
        monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda cls, **kw: settings or jira_settings()))
        queue = list(responses)

        def handler(request: httpx.Request) -> httpx.Response:
            return queue.pop(0) if queue else json_response(500, {})

        real_init = JiraClient.__init__

        def patched(self, st, *, transport=None, sleep=None):
            real_init(self, st, transport=httpx.MockTransport(handler), sleep=lambda _s: None)

        monkeypatch.setattr(cli.JiraClient, "__init__", patched)
        return cli.main(argv)

    return runner


def test_check_succeeds_and_touches_no_issue(run_cli, capsys) -> None:
    code = run_cli(["check"], [json_response(200, {"displayName": "Ada"})])

    assert code == cli.EXIT_OK
    assert "Ada" in capsys.readouterr().out


def test_issue_prints_the_ticket(run_cli, capsys) -> None:
    code = run_cli(["issue", "TC-345"], [json_response(200, issue_payload())])

    out = capsys.readouterr().out
    assert code == cli.EXIT_OK
    assert "TC-345" in out
    assert "expired card" in out


def test_unconfigured_exits_config(monkeypatch) -> None:
    """A local problem gets its own code, separate from a Jira rejection.

    Isolated from the real ``.env``. Clearing ``os.environ`` is not enough:
    ``Settings.from_env()`` calls ``load_dotenv()`` and reads the credentials
    straight back off disk, so the earlier version of this test **failed on any
    machine with real credentials** and only ever passed because none existed.
    A test whose result depends on the developer's local secrets is not a test.

    ``from_env``'s own loading behaviour is covered by
    ``tests/test_settings_contract.py``; this asserts the CLI's exit-code
    mapping for an unconfigured client.
    """
    unconfigured = Settings(base_url="https://example.com")
    assert not unconfigured.jira_configured
    monkeypatch.setattr(cli.Settings, "from_env", classmethod(lambda c, **kw: unconfigured))

    assert cli.main(["check"]) == cli.EXIT_CONFIG


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, cli.EXIT_AUTH),
        (403, cli.EXIT_AUTH),
        (404, cli.EXIT_NOT_FOUND),
        (500, cli.EXIT_UNAVAILABLE),
    ],
)
def test_failure_causes_map_to_their_own_exit_code(run_cli, status, expected) -> None:
    assert run_cli(["issue", "TC-1"], [json_response(status, {})] * 3) == expected


def test_rejected_query_has_its_own_code(run_cli) -> None:
    """The CLI validates the JQL first, so the parser's verdict is what fires.

    Jira answers 200 + an empty issue list for an unknown field, so relying on
    the search call to reject it would silently exit 0.
    """
    code = run_cli(
        ["search", "bad = 1"],
        [json_response(200, {"queries": [{"query": "bad = 1", "errors": ["Field 'bad' does not exist"]}]})],
    )
    assert code == cli.EXIT_QUERY


def test_exit_code_five_is_reserved_not_reused() -> None:
    """It meant "write refused locally" before writes were deferred.

    Reserving rather than reusing it means a script written against the
    earlier contract cannot silently misread a different failure.
    """
    codes = {
        v for k, v in vars(cli).items() if k.startswith("EXIT_") and isinstance(v, int)
    }
    assert 5 not in codes
