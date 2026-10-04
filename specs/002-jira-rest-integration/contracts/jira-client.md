# Client & CLI Contract: Jira REST Integration

**Feature**: `002-jira-rest-integration` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Two consumer-facing surfaces: a Python API that tests and tooling call, and a CLI. Both are things callers depend on, so changes to names, signatures, raised errors, or exit codes are breaking changes.

> **Scope change, 2026-10-04**: this client is **read-only**. `add_comment` and `transition_issue`, the four write safeguards, and the `comment` / `transition` subcommands were deferred out of this feature once it was confirmed nothing needs them — feature 004 keeps its approval records in the repository, and feature 005 rules Jira reporting out of scope. The designs are preserved in research R3, R4 and R10 for whichever feature adds writes later.

Error classes: [data-model.md](../data-model.md) §3. Settings: [configuration.md](./configuration.md).

---

## Construction

```python
JiraClient(settings: Settings, *, transport: httpx.BaseTransport | None = None)
```

- Raises `JiraConfigError` if Jira settings are absent or incomplete — **before** any network call (FR-011).
- `transport` exists so tests can inject `httpx.MockTransport`. It is the whole reason the suite is offline-testable with no new dependency (FR-018, SC-009, R5).
- One client serves both call paths: tooling constructs it directly, tests receive it from the `jira_client` fixture (FR-004, R9).
- Authentication is HTTP Basic with `jira_email` + `jira_api_token` (R1). Every request carries an explicit timeout from `jira_timeout_s` (FR-013).

**The client has no method that modifies Jira.** That is a property of the type, not a configuration setting — there is no flag that turns writes on, because there is no write code.

---

## Read operations

### `get_issue(key: str) -> JiraIssue`

| | |
|---|---|
| **Does** | `GET /rest/api/3/issue/{key}`, flattens the ADF description, returns a frozen `JiraIssue` |
| **Returns** | `JiraIssue` — key, project_key, summary, description, status, issue_type, labels, raw |
| **Raises** | `JiraNotFoundError` (404 — worded as "not found **or not visible to this account**"), `JiraAuthError` (401), `JiraForbiddenError` (403), `JiraUnavailableError` (network/timeout/5xx), `JiraRateLimitError` (429 after retries) |
| **Satisfies** | FR-005, FR-014, FR-017 |

The 404 wording is deliberate: Jira answers 404 for both an absent issue and one the account cannot see, and those are indistinguishable from the response. Asserting the issue does not exist would send someone hunting for a deleted ticket that is merely invisible.

### `search(jql: str, *, fields: Sequence[str] | None = None) -> Iterator[JiraIssue]`

| | |
|---|---|
| **Does** | `POST /rest/api/3/search/jql`, following `nextPageToken` to exhaustion |
| **Returns** | A lazy iterator over **all** matching issues across every page |
| **Raises** | `JiraQueryError` (400 — carries Jira's own reason), plus the same set as `get_issue` |
| **Satisfies** | FR-006, SC-011 |

Returning an exhausting iterator rather than a page is the design choice that makes SC-011 ("zero silent truncation") structural: a caller cannot accidentally read only the first page. `search_page()` is also public for callers that want manual control.

---

## Redaction

- Every error message is built through `redact()` at construction time, not display time, so a traceback captured into an Allure artifact is already clean (FR-010, SC-006).
- Every error carries the Jira host it was talking to (FR-017), so a misconfigured `JIRA_BASE_URL` is diagnosable without reading code.

---

## Retry policy

Retry **only** on 429 and 5xx, at most 3 attempts, honouring `Retry-After` when present and otherwise backing off exponentially (FR-015, R7).

**Never retried**: 400, 401, 403, 404. Retrying these cannot succeed and only turns a clear failure into a slow one.

With writes out of scope, the ambiguous-failure risk that made retries delicate is gone: every operation here is idempotent by nature, so a retried request cannot cause a duplicate side effect.

---

## CLI

```bash
uv run python -m ai_qa.jira <subcommand> [args]
```

Standard-library `argparse` — a CLI framework would be a new dependency (FR-003, R12).

| Subcommand | Does | Satisfies |
|---|---|---|
| `check` | Verifies authentication, reports the authenticated account. Touches no issue | **FR-019** |
| `issue <KEY>` | Prints an issue's fields | FR-005 |
| `search <JQL>` | Prints all matching issues across all pages | FR-006 |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Configuration error — settings missing or incomplete |
| 3 | Authentication or authorization rejected by Jira |
| 4 | Not found, or not visible to this account |
| 6 | Jira unavailable, timed out, or rate-limited after retries |
| 7 | Query rejected |

**Code 5 is deliberately left unused.** It previously meant "write refused by a local safeguard". Reserving rather than reusing it means a script written against the earlier contract cannot silently misinterpret a different failure, and it stays available if writes return.

---

## Test fixtures

| Fixture | Scope | Provides |
|---|---|---|
| `jira_client` | session | A `JiraClient` built from settings. Skips the test if Jira is not configured — so an unconfigured machine skips rather than fails (FR-016, SC-008) |
| `mock_jira` | function | Factory building a `JiraClient` over `httpx.MockTransport` with caller-supplied canned responses. Every test of this feature uses it |

`jira_client` is session-scoped for the same reason `settings` is in feature 001 — no mutable per-test state — and it avoids rebuilding a connection pool per test. `mock_jira` is function-scoped because each test supplies its own responses.

---

## Compatibility notes

What constitutes a breaking change here, and therefore needs a deliberate decision:

- Renaming a method, error class, or CLI subcommand, or changing an exit code's meaning.
- **Adding any method that modifies Jira.** Writes were deliberately deferred; re-adding them needs the four safeguards from research R10 and a feature that actually calls them — not a quiet method addition.
- Returning a page instead of an exhausting iterator from `search()` — reintroduces silent truncation.
- Retrying a 4xx other than 429.
- Reusing exit code 5 for a new meaning.
- Adding any dependency, or any MCP/connector call in the runtime path (FR-002, FR-003, SC-002, SC-003).
