"""Shared fixtures (FR-017).

Parallel-safety rules in force here (FR-016, SC-012):

* Every fixture is function-scoped, with one documented exception below.
* No artifact path is a fixed filename - all derive from the test's node ID,
  which is unique within a run, so concurrent tests cannot collide.

Enabling parallel execution later must not require editing this file.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_qa.config import Settings

_UNSAFE = re.compile(r"[^A-Za-z0-9]+")
_MAX_SEGMENT = 120


def sanitise_node_id(node_id: str) -> str:
    """Turn a pytest node ID into a filesystem-safe path segment.

    Node IDs contain ``/``, ``::`` and ``[]``, which are invalid or awkward in
    Windows paths - and Windows is the primary platform. Long parametrised IDs
    are truncated with a hash suffix so the result stays unique while keeping
    clear of the Windows path limit.
    """
    slug = _UNSAFE.sub("-", node_id).strip("-")
    if len(slug) <= _MAX_SEGMENT:
        return slug
    digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:8]
    return f"{slug[: _MAX_SEGMENT - 9]}-{digest}"


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Validated configuration for the run.

    Session-scoped by deliberate exception to the function-scope rule: the
    model is frozen and derived purely from the process environment, and under
    parallel execution each worker is a separate process with its own copy, so
    there is no shared mutable state to race on (see data-model.md section 1).

    Lazy by design. A test that does not request this fixture runs without a
    ``.env`` present - which is what keeps the environment health checks
    independent of configuration being set up yet.
    """
    try:
        loaded = Settings.from_env()
    except ValidationError as exc:
        # Report the environment variable name the engineer edits in .env,
        # not the model field name - they differ only by case, and naming the
        # wrong one sends them looking in the wrong file.
        variables = ", ".join(
            "_".join(str(part) for part in error["loc"]).upper() or "<model>"
            for error in exc.errors()
        )
        raise pytest.UsageError(
            f"Invalid configuration: {variables}. "
            f"Copy .env.example to .env and set the listed value(s). "
            f"See README.md.\n\n{exc}"
        ) from exc

    loaded.ensure_output_dirs()
    return loaded


@pytest.fixture
def artifact_dir(request: pytest.FixtureRequest) -> Path:
    """Per-test directory for generated evidence (FR-010).

    Unique per test by construction, so parallel workers cannot overwrite one
    another's screenshots or traces.
    """
    base = Path("reports/artifacts") / sanitise_node_id(request.node.nodeid)
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture(scope="session")
def base_url(settings: Settings) -> str:
    """Target base URL, overriding the one from ``pytest-base-url``.

    Overriding this name is what wires ``BASE_URL`` from ``.env`` into
    Playwright's relative-URL handling, so ``page.goto("/login")`` works.

    Must be **session**-scoped: ``pytest-base-url`` installs a session-scoped
    autouse fixture that requests ``base_url``, and a function-scoped override
    raises ``ScopeMismatch`` for every test in the suite. Safe at session scope
    for the same reason as ``settings`` - an immutable value derived from the
    process environment.
    """
    return str(settings.base_url).rstrip("/")

# --------------------------------------------------------------------------
# Ticket attribution and run scoping (feature 005, FR-021, FR-010)
# --------------------------------------------------------------------------
#
# VERIFIED EMPIRICALLY, and it overturns the obvious assumption:
# `@pytest.mark.ticket("TC-345")` produces **no Allure label at all**.
# allure-pytest maps *bare* markers to `tag` labels but drops markers that
# carry arguments. Without the hook below, FR-021/FR-023 and SC-008 are
# unachievable - and nothing looks broken: reports render perfectly with every
# test unattributed. That is the quietest failure mode in the design.


def pytest_addoption(parser: pytest.Parser) -> None:
    """``--ticket TC-345`` selects a ticket's tests.

    Not ``-m``: that evaluates marker *names*, so `-m ticket` selects every
    ticketed test regardless of key. Not ``-k`` either: that matches names, so
    it would both miss correctly-marked tests and match unrelated ones.
    """
    parser.addoption(
        "--ticket",
        action="store",
        default=None,
        help="run only tests marked with this ticket key",
    )


def _ticket_of(item: pytest.Item) -> str | None:
    marker = item.get_closest_marker("ticket")
    if marker and marker.args:
        return str(marker.args[0]).upper()
    return None


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    wanted = config.getoption("--ticket")
    if not wanted:
        return
    wanted = str(wanted).upper()
    selected, deselected = [], []
    for item in items:
        (selected if _ticket_of(item) == wanted else deselected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Write the ticket marker's argument as an Allure label.

    This is the hook referred to above. ``allure.dynamic.label`` is used
    rather than a static decorator because the value comes from the marker at
    run time.
    """
    ticket = _ticket_of(item)
    if not ticket:
        return
    try:
        import allure

        allure.dynamic.label("ticket", ticket)
    except Exception:  # pragma: no cover - reporting must never fail a test
        pass
