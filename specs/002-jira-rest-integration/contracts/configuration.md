# Configuration Contract: Jira REST Integration

**Feature**: `002-jira-rest-integration` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Four settings appended to the existing `.env.example` from feature 001. SC-010 requires every setting the platform reads to be named here, so none is discoverable only by reading code.

> **Scope change, 2026-10-04**: write operations were deferred out of this feature. The three write settings — `JIRA_WRITES_ENABLED`, `JIRA_WRITE_PROJECTS`, `JIRA_ALLOWED_TRANSITIONS` — have been **removed**. The client is read-only.

Types and cross-field validation: [data-model.md](../data-model.md) §1.

---

## Settings

| Variable | Type | Required | Default | Placeholder |
|---|---|---|---|---|
| `JIRA_BASE_URL` | URL | No¹ | unset | `https://your-site.atlassian.net` |
| `JIRA_EMAIL` | string | No¹ | unset | `you@example.com` |
| `JIRA_API_TOKEN` | secret | No¹ | unset | `replace-me` |
| `JIRA_TIMEOUT_S` | float, 0–300 | No | `30` | `30` |

¹ Individually optional, but **all three or none** — partial credentials are rejected at load (FR-011).

**All four are optional overall.** The suite must run with no Jira configuration whatsoever (FR-016, SC-008) — an engineer who never touches Jira needs no token, and feature 001's health checks must keep passing on their machine. Absence is valid; *use without configuration* is what fails.

---

## Appended to `.env.example`

```dotenv
# ---------------------------------------------------------------------------
# Jira (optional). Leave unset if you do not use the Jira integration.
# All Jira access is direct REST from this project - no MCP, no connector.
# This client is READ-ONLY: it never comments, transitions, or edits anything.
# Set all three of URL/EMAIL/TOKEN together, or none of them.
# ---------------------------------------------------------------------------

# Your Atlassian Cloud site.
JIRA_BASE_URL=https://your-site.atlassian.net

# The account the API token belongs to.
JIRA_EMAIL=you@example.com

# Create one at: https://id.atlassian.com/manage-profile/security/api-tokens
# NEVER put a real token in this file - it is committed. Put it in .env.
# A read-scoped token is sufficient and preferred: this project never writes.
JIRA_API_TOKEN=replace-me

# Per-request timeout in seconds (1-300).
JIRA_TIMEOUT_S=30
```

Every value is a placeholder or non-sensitive default (FR-009, FR-012, SC-004).

---

## Obtaining a token

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Create an API token, label it for this project
3. Put it in `.env` (git-ignored), **not** `.env.example` (committed)
4. Confirm it works: `uv run python -m ai_qa.jira check`

Step 4 is FR-019's confirmation step — it verifies authentication and reports the authenticated account without touching an issue.

**A read-scoped token is sufficient.** Because the platform never writes, nothing here needs permission to comment or transition. Jira's own tokens carry the holder's full permissions and cannot be narrowed, so this is advice rather than an enforceable constraint — but it means a token leaked from this project cannot be used *through this project* to change anything.

---

## Adding a setting later

Per feature 001's rules, three coordinated edits — the `Settings` model, the `_ENV_PREFIXES` tuple, and `.env.example` — plus the table above. A value read from `os.environ` outside the `Settings` model is a contract violation: it becomes invisible here and breaks SC-010.

---

## Secret handling

- The token lives in `.env` only. `.env` is git-ignored; `.env.example` is committed with placeholders.
- `JIRA_API_TOKEN` is held as a masked secret type, and every error message passes through a redaction helper, so it reaches no log line, traceback, or Allure artifact (FR-010, SC-006).
- **No secret-scanning tooling**, per feature 001's clarified decision. The ignore rule protects the file; a token pasted inline into a test or doc remains a code-review concern.
