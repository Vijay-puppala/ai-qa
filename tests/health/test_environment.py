"""Environment health checks (FR-019, FR-026, FR-027).

These five tests *are* the setup verification mechanism. A single
``uv run pytest -m healthcheck`` confirms the environment rather than asking
an engineer to run four commands and read the output correctly.

Two properties matter as much as the assertions:

* **Independence.** One test per capability, so three simultaneous problems
  report as three failures rather than stopping at the first (SC-009).
* **Diagnostic failure.** Each failure names the missing prerequisite or the
  setup step that was skipped, not just the symptom.
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.healthcheck

#: The eight dependencies FR-004 mandates, as (import name, distribution name).
DECLARED_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("pytest", "pytest"),
    ("pytest_playwright", "pytest-playwright"),
    ("playwright", "playwright"),
    ("allure_pytest", "allure-pytest"),
    ("yaml", "PyYAML"),
    ("pydantic", "pydantic"),
    ("httpx", "httpx"),
    ("dotenv", "python-dotenv"),
)


# --- US1: dependencies -------------------------------------------------------


@pytest.mark.parametrize(
    ("import_name", "distribution"),
    DECLARED_DEPENDENCIES,
    ids=[dist for _, dist in DECLARED_DEPENDENCIES],
)
def test_declared_dependency_is_installed(import_name: str, distribution: str) -> None:
    """Every dependency FR-004 declares imports and reports a version.

    Parametrised so a missing package names itself. Deliberately does not
    request the ``settings`` fixture: this must pass before ``.env`` exists,
    which is what keeps User Story 1 independent of User Story 3.
    """
    try:
        importlib.import_module(import_name)
    except ImportError as exc:  # pragma: no cover - environment failure path
        pytest.fail(
            f"Dependency {distribution!r} is not importable ({exc}). "
            f"Run 'uv sync --locked' to install the locked dependency set."
        )

    try:
        installed = version(distribution)
    except PackageNotFoundError:  # pragma: no cover - environment failure path
        pytest.fail(
            f"Dependency {distribution!r} imports but has no installed "
            f"distribution metadata. Run 'uv sync --locked'."
        )

    assert installed, f"{distribution} reported an empty version"


def test_python_version_is_pinned_312() -> None:
    """The interpreter is the pinned 3.12, not whatever the machine had.

    Guards FR-002's exact pin. ``requires-python = ">=3.12"`` would resolve
    against a newer system interpreter and pass silently; this fails loudly.
    """
    major, minor = sys.version_info[:2]
    assert (major, minor) == (3, 12), (
        f"Expected Python 3.12 (pinned in .python-version and requires-python), "
        f"got {major}.{minor}. Run 'uv sync --locked' so uv provisions 3.12."
    )


# --- US2: browser ------------------------------------------------------------


@pytest.mark.ui
def test_browser_launches_and_renders(page) -> None:
    """A real browser starts and renders content.

    Uses a ``data:`` URL rather than a live site so environment verification
    never depends on network reachability or an external site's uptime - an
    offline machine would otherwise report a broken environment that is fine.
    """
    page.goto("data:text/html,<h1 id='probe'>ai-qa healthcheck</h1>")
    assert page.text_content("#probe") == "ai-qa healthcheck", (
        "Browser launched but did not render expected content. If this fails "
        "with a missing-executable error, run: "
        "uv run playwright install chromium firefox webkit"
    )


# --- US3: configuration ------------------------------------------------------


def test_configuration_loads_and_validates(settings) -> None:
    """Configuration loads from the environment and validates (FR-023).

    Failure surfaces as a ``pytest.UsageError`` from the fixture naming the
    offending setting, so a misconfigured environment is reported as a
    configuration problem rather than an unrelated test failure.
    """
    assert str(settings.base_url).startswith(("http://", "https://")), (
        f"BASE_URL must be an absolute http/https URL, got {settings.base_url!r}"
    )
    assert settings.browser in {"chromium", "firefox", "webkit"}
    assert 0 < settings.timeout_ms <= 300_000


def test_settings_are_immutable(settings) -> None:
    """The settings model is frozen, which is what makes its session scope safe.

    If this fails, the session-scoped fixture became shared mutable state and
    the parallel-safety claim in SC-012 no longer holds.
    """
    with pytest.raises(ValidationError):
        settings.browser = "firefox"  # type: ignore[misc]


# --- US4: exploration CLI ----------------------------------------------------


def test_playwright_cli_is_project_local() -> None:
    """The Playwright CLI responds, resolved from this project's environment.

    Invoked through ``sys.executable -m`` rather than a ``PATH`` lookup: the
    interpreter running the test is then necessarily the interpreter providing
    the CLI, so this check is structurally incapable of passing against a
    global or Node-based copy at a different version (FR-011, FR-012).
    """
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"Playwright CLI did not respond (exit {result.returncode}). "
        f"Run 'uv sync --locked'.\nstderr: {result.stderr.strip()}"
    )
    # The CLI prints "Version 1.63.0" - the trailing token is what matters.
    reported = result.stdout.strip().split()[-1]
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", reported), (
        f"Unexpected CLI output: {result.stdout.strip()!r}"
    )

    installed = version("playwright")
    assert reported == installed, (
        f"CLI reports {reported} but the installed playwright distribution is "
        f"{installed} - the CLI is not resolving to this project's pinned copy."
    )


# --- Jira integration (feature 002) ------------------------------------------


def test_jira_settings_validate_when_configured(settings) -> None:
    """Jira settings load and validate - but only when they are present.

    Skips rather than fails on a machine with no Jira configuration. An
    optional integration must never become a precondition for running the
    suite (feature 002, FR-016 and SC-008).
    """
    if not settings.jira_configured:
        pytest.skip("Jira is not configured on this machine - optional integration")

    assert str(settings.jira_base_url).startswith(("http://", "https://"))
    assert "@" in (settings.jira_email or "")
    assert 0 < settings.jira_timeout_s <= 300


# --- US5: reporting ----------------------------------------------------------


def test_allure_reporting_is_registered(pytestconfig: pytest.Config) -> None:
    """``allure-pytest`` is registered with the plugin manager (FR-024)."""
    assert pytestconfig.pluginmanager.hasplugin("allure_pytest"), (
        "allure-pytest is not registered as an active plugin. "
        "Run 'uv sync --locked'."
    )

    alluredir = pytestconfig.getoption("allure_report_dir")
    assert alluredir, (
        "No Allure results directory configured. --alluredir must be set in "
        "[tool.pytest.ini_options] addopts so a bare 'uv run pytest' emits "
        "result data without a remembered flag (FR-016)."
    )
