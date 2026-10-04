"""Runtime configuration, loaded from the environment and validated on startup.

Configuration originates solely from the local ``.env`` file (FR-023). YAML is
never a configuration source here - it carries test data only.

Note on ``pydantic-settings``: in pydantic v2 ``BaseSettings`` lives in a
separate distribution. FR-004 permits a new dependency only where a requirement
cannot otherwise be met, and FR-023 is fully satisfied by ``BaseModel`` plus
``python-dotenv``, so that package is deliberately not used (research R3).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, model_validator

#: Every setting the suite reads must appear in ``.env.example`` (SC-008).
#: Anything read from ``os.environ`` outside this model is a contract violation.
_ENV_PREFIXES: tuple[str, ...] = (
    "BASE_URL",
    "BROWSER",
    "HEADLESS",
    "TIMEOUT_MS",
    "API_BASE_URL",
    "API_TOKEN",
    "ARTIFACTS_DIR",
    "ALLURE_RESULTS_DIR",
    # Jira (feature 002) - optional; all three credentials together or none.
    "JIRA_BASE_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "JIRA_TIMEOUT_S",
    # Approval gate (feature 004).
    "APPROVAL_REQUIRE_SECOND_PERSON",
    "APPROVAL_RECORDS_DIR",
)


class Settings(BaseModel):
    """Validated runtime configuration.

    Frozen so the session-scoped fixture that holds it cannot be mutated by one
    test and observed by another. Combined with it being derived purely from the
    process environment, this is what makes a session scope safe under parallel
    execution, where each worker is a separate process (SC-012).
    """

    model_config = ConfigDict(frozen=True)

    base_url: HttpUrl
    browser: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    timeout_ms: int = Field(default=30_000, gt=0, le=300_000)
    api_base_url: HttpUrl | None = None
    api_token: SecretStr | None = None
    artifacts_dir: Path = Path("reports/artifacts")
    allure_results_dir: Path = Path("reports/allure-results")

    # --- Jira integration (feature 002). All optional: the suite must run with
    # --- no Jira configuration at all (FR-016), so absence is valid and it is
    # --- *use* without configuration that fails, not load.
    jira_base_url: HttpUrl | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None
    jira_timeout_s: float = Field(default=30.0, gt=0, le=300)

    # --- Approval gate (feature 004). The default must require a second
    # --- person: a gate that self-approves by default is not a gate.
    approval_require_second_person: bool = True
    approval_records_dir: Path = Path("approvals")

    @model_validator(mode="after")
    def _jira_email_shape(self) -> "Settings":
        if self.jira_email is not None and "@" not in self.jira_email:
            raise ValueError("JIRA_EMAIL must be an email address")
        return self

    @model_validator(mode="after")
    def _jira_credentials_all_or_none(self) -> "Settings":
        """Partial Jira credentials are a configuration error (FR-011).

        Setting two of the three otherwise produces an authentication failure
        against Jira when the real problem is local - which sends the engineer
        to the wrong place entirely.
        """
        present = {
            "JIRA_BASE_URL": self.jira_base_url is not None,
            "JIRA_EMAIL": self.jira_email is not None,
            "JIRA_API_TOKEN": self.jira_api_token is not None,
        }
        if any(present.values()) and not all(present.values()):
            missing = sorted(name for name, ok in present.items() if not ok)
            raise ValueError(
                "Jira is partially configured: set all of JIRA_BASE_URL, "
                "JIRA_EMAIL and JIRA_API_TOKEN together, or none of them. "
                "Missing: " + ", ".join(missing)
            )
        return self

    @property
    def jira_configured(self) -> bool:
        """True when all three Jira credentials are present."""
        return (
            self.jira_base_url is not None
            and self.jira_email is not None
            and self.jira_api_token is not None
        )

    @classmethod
    def from_env(cls, *, dotenv_path: str | os.PathLike[str] | None = None) -> "Settings":
        """Load ``.env`` if present, then build and validate the model.

        A missing ``.env`` is not an error on its own - every setting except
        ``BASE_URL`` has a working default. Validation failure is what reports
        the problem, naming the offending field (FR-023).
        """
        load_dotenv(dotenv_path=dotenv_path, override=False)

        raw = {
            key.lower(): os.environ[key]
            for key in _ENV_PREFIXES
            if os.environ.get(key, "") != ""
        }
        return cls(**raw)

    def ensure_output_dirs(self) -> None:
        """Create the generated-output directories on demand (FR-018)."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.allure_results_dir.mkdir(parents=True, exist_ok=True)
