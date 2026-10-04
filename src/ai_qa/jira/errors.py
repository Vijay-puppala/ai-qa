"""Jira failure taxonomy and credential redaction (FR-010, FR-014, FR-017).

Seven causes must be distinguishable, and zero of them may report a cause that
is not theirs (SC-005). Every error carries the host it was talking to, so a
misconfigured ``JIRA_BASE_URL`` is diagnosable without reading code.
"""

from __future__ import annotations

import re

from pydantic import SecretStr

#: Masks the *whole* header value, not just the first word. A pattern of
#: ``\S+`` would leave "Bearer <token>" with the token intact, which is the
#: part that matters.
_AUTH_HEADER = re.compile(r"(?i)(authorization\s*[:=]\s*)[^\r\n,}'\"]+")


def redact(text: str, token: SecretStr | str | None = None) -> str:
    """Strip credentials from a string (FR-010).

    Applied at error **construction**, not at display time, so a traceback
    captured into an Allure artifact is already clean - the report is the
    artifact most likely to be shared outside the team, and a traceback is
    where a credential actually surfaces.
    """
    cleaned = _AUTH_HEADER.sub(r"\1***", text)
    if token is not None:
        raw = token.get_secret_value() if isinstance(token, SecretStr) else str(token)
        if raw:
            cleaned = cleaned.replace(raw, "***")
    return cleaned


class JiraError(Exception):
    """Base for every Jira failure. Always names the host (FR-017)."""

    def __init__(
        self,
        message: str,
        *,
        host: str | None = None,
        token: SecretStr | str | None = None,
    ) -> None:
        self.host = host
        where = f" [site: {host}]" if host else ""
        super().__init__(redact(message, token) + where)


class JiraConfigError(JiraError):
    """Settings missing or incomplete. Raised before any request is sent."""


class JiraAuthError(JiraError):
    """401 - the credentials were rejected."""


class JiraForbiddenError(JiraError):
    """403 - authenticated, but not permitted."""


class JiraNotFoundError(JiraError):
    """404 - the issue or endpoint is absent, or not visible to this account.

    Jira answers 404 for both a genuinely missing issue and one the account
    cannot see, and the response does not distinguish them. Messages must not
    assert the issue does not exist, or someone goes hunting for a deleted
    ticket that is merely invisible.
    """


class JiraQueryError(JiraError):
    """400 on a search - the query was rejected. Carries Jira's own reason."""


class JiraRateLimitError(JiraError):
    """429 after the retry budget is exhausted. Carries the advertised delay."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kw: object) -> None:
        self.retry_after = retry_after
        super().__init__(message, **kw)  # type: ignore[arg-type]


class JiraUnavailableError(JiraError):
    """Network failure, timeout, or 5xx after retries."""
