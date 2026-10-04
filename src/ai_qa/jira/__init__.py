"""Direct Jira Cloud REST access for the AI-QA platform (feature 002).

Read-only by design: write operations were deferred on 2026-10-04 once it was
established that nothing in the project needs them. No MCP server, assistant
connector, or other external tooling is involved at any point (FR-002).
"""

from ai_qa.jira.client import JiraClient
from ai_qa.jira.errors import (
    JiraAuthError,
    JiraConfigError,
    JiraError,
    JiraForbiddenError,
    JiraNotFoundError,
    JiraQueryError,
    JiraRateLimitError,
    JiraUnavailableError,
    redact,
)
from ai_qa.jira.models import IssueQueryPage, JiraIssue

__all__ = [
    "IssueQueryPage",
    "JiraAuthError",
    "JiraClient",
    "JiraConfigError",
    "JiraError",
    "JiraForbiddenError",
    "JiraIssue",
    "JiraNotFoundError",
    "JiraQueryError",
    "JiraRateLimitError",
    "JiraUnavailableError",
    "redact",
]
