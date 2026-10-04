"""Read-only Jira REST client (FR-001 to FR-007).

One client serves both call paths - tooling constructs it directly, tests
receive it from a fixture - so the two cannot diverge in behaviour or in
failure handling (FR-004, research R9).

**This client has no method that modifies Jira.** That is a property of the
type, not a configuration flag: write operations were deferred out of this
feature on 2026-10-04, so there is no write code to enable. FR-007 states the
prohibition and ``tests/jira/test_no_write.py`` enforces it.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from typing import Any

import httpx

from ai_qa.config import Settings
from ai_qa.jira.errors import (
    JiraAuthError,
    JiraConfigError,
    JiraForbiddenError,
    JiraNotFoundError,
    JiraQueryError,
    JiraRateLimitError,
    JiraUnavailableError,
)
from ai_qa.jira.models import IssueQueryPage, JiraIssue

#: Retry only these. Retrying an ordinary 4xx cannot succeed and only turns a
#: clear error into a slow one (research R7).
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3

#: Fields requested explicitly, so a response stays small and predictable.
_DEFAULT_FIELDS = ("summary", "description", "status", "issuetype", "labels")


class JiraClient:
    """Direct REST access to Jira Cloud. Read-only."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        if not settings.jira_configured:
            raise JiraConfigError(
                "Jira is not configured. Set JIRA_BASE_URL, JIRA_EMAIL and "
                "JIRA_API_TOKEN in .env - see .env.example."
            )
        self._settings = settings
        self._token = settings.jira_api_token
        self._sleep = sleep
        self.host = str(settings.jira_base_url).rstrip("/")
        self._client = httpx.Client(
            base_url=self.host,
            auth=(settings.jira_email or "", (self._token.get_secret_value() if self._token else "")),
            timeout=httpx.Timeout(settings.jira_timeout_s),
            transport=transport,
            headers={"Accept": "application/json"},
        )

    # ---------------------------------------------------------------- lifecycle

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JiraClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------- reads

    def whoami(self) -> dict[str, Any]:
        """Verify authentication and report the account (FR-019).

        Touches no issue, so it is safe to run as a credential check.
        """
        return self._request("GET", "/rest/api/3/myself")

    def get_issue(self, key: str, *, fields: Sequence[str] | None = None) -> JiraIssue:
        """Fetch one issue by key (FR-005)."""
        wanted = ",".join(fields or _DEFAULT_FIELDS)
        payload = self._request(
            "GET", f"/rest/api/3/issue/{key}", params={"fields": wanted}, subject=key
        )
        return JiraIssue.from_api(payload)

    def validate_jql(self, jql: str) -> None:
        """Raise ``JiraQueryError`` if Jira considers the query invalid.

        Needed because ``POST /search/jql`` answers **200 with an empty issue
        list** for an unknown field rather than 400 - verified live. Without
        this, a typo'd field name is indistinguishable from "nothing matched",
        which is exactly the cause confusion FR-014 forbids.

        Costs one extra request, so it is called by the CLI rather than by
        every ``search``: a test that already knows its JQL is valid should not
        pay for the check on every call.
        """
        payload = self._request(
            "POST", "/rest/api/3/jql/parse", json={"queries": [jql]}
        )
        for parsed in payload.get("queries") or ():
            errors = parsed.get("errors") or []
            if errors:
                raise JiraQueryError(
                    "Jira rejected the query: " + "; ".join(str(e) for e in errors),
                    host=self.host,
                    token=self._token,
                )

    def search_page(
        self,
        jql: str,
        *,
        fields: Sequence[str] | None = None,
        page_token: str | None = None,
        max_results: int = 50,
    ) -> IssueQueryPage:
        """One page of query results, token-paginated (research R6).

        Uses ``POST /search/jql``; the offset-based ``GET /search`` is
        deprecated on Cloud and carries offset drift, where an issue changing
        mid-iteration can cause a result to be skipped or returned twice.
        """
        body: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": list(fields or _DEFAULT_FIELDS),
        }
        if page_token:
            body["nextPageToken"] = page_token
        payload = self._request("POST", "/rest/api/3/search/jql", json=body, is_search=True)
        issues = tuple(JiraIssue.from_api(i) for i in payload.get("issues") or ())
        token = payload.get("nextPageToken")
        return IssueQueryPage(
            issues=issues,
            next_page_token=token,
            is_last=bool(payload.get("isLast", token is None)),
        )

    def search(
        self, jql: str, *, fields: Sequence[str] | None = None, max_results: int = 50
    ) -> Iterator[JiraIssue]:
        """Every issue matching ``jql``, across all pages (FR-006, SC-011).

        Returns an exhausting iterator rather than a page, so a caller cannot
        accidentally read only the first page. That is what makes "zero silent
        truncation" a property of the design instead of a thing to remember.
        """
        token: str | None = None
        while True:
            page = self.search_page(
                jql, fields=fields, page_token=token, max_results=max_results
            )
            yield from page.issues
            if page.is_last or not page.next_page_token:
                return
            token = page.next_page_token

    # ---------------------------------------------------------------- internals

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        subject: str | None = None,
        is_search: bool = False,
    ) -> dict[str, Any]:
        last_retry_after: float | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = self._client.request(method, path, params=params, json=json)
            except httpx.TimeoutException as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise JiraUnavailableError(
                        f"Jira did not respond within {self._settings.jira_timeout_s}s: {exc}",
                        host=self.host,
                        token=self._token,
                    ) from exc
                self._backoff(attempt, None)
                continue
            except httpx.HTTPError as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise JiraUnavailableError(
                        f"Could not reach Jira: {exc}", host=self.host, token=self._token
                    ) from exc
                self._backoff(attempt, None)
                continue

            status = response.status_code

            if status in _RETRY_STATUS and attempt < _MAX_ATTEMPTS:
                last_retry_after = _retry_after(response)
                self._backoff(attempt, last_retry_after)
                continue

            self._raise_for_status(response, subject=subject, is_search=is_search,
                                   retry_after=_retry_after(response) or last_retry_after)
            try:
                return response.json()
            except ValueError as exc:
                raise JiraUnavailableError(
                    f"Jira returned a non-JSON response ({status})",
                    host=self.host,
                    token=self._token,
                ) from exc

        raise JiraUnavailableError(  # pragma: no cover - loop always returns or raises
            "Jira request exhausted its retry budget", host=self.host, token=self._token
        )

    def _backoff(self, attempt: int, retry_after: float | None) -> None:
        self._sleep(retry_after if retry_after is not None else 0.5 * (2 ** (attempt - 1)))

    def _raise_for_status(
        self,
        response: httpx.Response,
        *,
        subject: str | None,
        is_search: bool,
        retry_after: float | None,
    ) -> None:
        status = response.status_code
        if status < 400:
            return

        detail = _detail(response)
        host, token = self.host, self._token

        if status == 400 and is_search:
            raise JiraQueryError(f"Jira rejected the query: {detail}", host=host, token=token)
        if status == 401:
            raise JiraAuthError(
                "Jira rejected the credentials (401). Check JIRA_EMAIL and "
                f"JIRA_API_TOKEN. {detail}",
                host=host,
                token=token,
            )
        if status == 403:
            raise JiraForbiddenError(
                f"Access denied by Jira (403). {detail}", host=host, token=token
            )
        if status == 404:
            what = f"Issue {subject!r}" if subject else f"Endpoint {response.url.path!r}"
            raise JiraNotFoundError(
                f"{what} was not found or is not visible to this account (404). {detail}",
                host=host,
                token=token,
            )
        if status == 429:
            raise JiraRateLimitError(
                f"Jira rate-limited this request after {_MAX_ATTEMPTS} attempts. {detail}",
                retry_after=retry_after,
                host=host,
                token=token,
            )
        raise JiraUnavailableError(
            f"Jira returned {status} after {_MAX_ATTEMPTS} attempts. {detail}",
            host=host,
            token=token,
        )


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return (response.text or "").strip()[:200]
    if isinstance(body, dict):
        messages = body.get("errorMessages") or []
        if messages:
            return "; ".join(str(m) for m in messages)[:300]
        errors = body.get("errors")
        if errors:
            return str(errors)[:300]
    return ""
