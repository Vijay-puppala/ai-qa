"""Read models for Jira issues (FR-005, FR-006).

Frozen: nothing mutates a fetched issue. Absent optional fields degrade to an
empty value rather than raising - an issue with no description is normal, and
failing to read it would be wrong.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from ai_qa.jira import adf


class JiraIssue(BaseModel):
    """The subset of a ticket the platform reads.

    ``project_key`` and ``raw`` are additions beyond FR-005's five fields: the
    first is needed wherever behaviour is scoped per project, and ``raw`` is an
    escape hatch so a caller needing a field this model omits is not blocked
    on a code change.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    project_key: str
    summary: str
    description: str = ""
    status: str = ""
    issue_type: str = ""
    labels: tuple[str, ...] = ()
    raw: dict[str, Any] = {}

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "JiraIssue":
        """Project a v3 issue response, flattening the ADF description."""
        fields = payload.get("fields") or {}
        key = str(payload.get("key", ""))
        status = (fields.get("status") or {}).get("name") or ""
        issue_type = (fields.get("issuetype") or {}).get("name") or ""
        return cls(
            key=key,
            project_key=key.split("-", 1)[0] if "-" in key else key,
            summary=fields.get("summary") or "",
            description=adf.to_text(fields.get("description")),
            status=status,
            issue_type=issue_type,
            labels=tuple(fields.get("labels") or ()),
            raw=payload,
        )

    def text_content(self) -> str:
        """Summary plus description - what a ticket says, as one string.

        Used by feature 003 for the brief and for the staleness digest.
        """
        return f"{self.summary}\n\n{self.description}".strip()


class IssueQueryPage(BaseModel):
    """One page of query results.

    Public so a caller can page manually, but ``JiraClient.search`` returns an
    exhausting iterator instead, which is what makes "zero silent truncation"
    (SC-011) structural rather than a thing callers must remember.
    """

    model_config = ConfigDict(frozen=True)

    issues: tuple[JiraIssue, ...] = ()
    next_page_token: str | None = None
    is_last: bool = True
