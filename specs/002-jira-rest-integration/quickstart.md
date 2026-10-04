# Quickstart Validation: Jira REST Integration

**Feature**: `002-jira-rest-integration` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

How to prove this feature works. This is the validation walkthrough, not `README.md` — the README is a deliverable of implementation (FR-020) and is written for someone using the integration rather than verifying it.

Commands and exit codes: [contracts/jira-client.md](./contracts/jira-client.md). Settings: [contracts/configuration.md](./contracts/configuration.md).

**Scenarios 1–4 need no Jira credentials and no network.** That is the point of FR-018 and SC-009: most of this feature is verifiable offline, and the suite must stay runnable on a machine that has never heard of Jira.

---

## Prerequisite

Feature 001's environment, already set up. Nothing new to install — this feature adds no dependencies (SC-002).

```bash
uv run pytest -m healthcheck    # expect 14 passed, unchanged
```

---

## Scenario 1 — Nothing breaks without Jira (validates SC-008, FR-016)

Do this **first**, with no Jira settings in `.env`.

```bash
uv run pytest
```

**Expected**: the full suite passes. Jira tests skip (not fail); every non-Jira test produces its normal result.

| Validates | How |
|---|---|
| SC-008 | 100% of non-Jira tests unaffected with Jira entirely absent |
| FR-016 | Jira is not a precondition for running the suite |

This is the regression that matters most. If adding a Jira integration makes an unconfigured machine fail, the feature has made the project worse regardless of what else works.

---

## Scenario 2 — Offline behaviour of the whole client (validates SC-009, FR-018)

```bash
uv run pytest -m jira
```

**Expected**: all Jira tests pass with **no network access**. Reads, queries, pagination, comments, transitions, every error class, and the ADF flattener are all exercised against `httpx.MockTransport`.

Confirm no test reaches a real site (SC-017):

```bash
grep -rn "atlassian.net" tests/ | grep -v "example\|your-site"
```

**Expected**: no output. Any live hostname in a test is a defect.

---

## Scenario 3 — Credential never leaks (validates SC-006)

```bash
uv run pytest tests/jira/test_redaction.py -v
```

Then the direct check — force a failing Jira test with a known sentinel token and search the **entire** run output, including Allure artifacts:

```bash
JIRA_API_TOKEN=SENTINEL-abc123 uv run pytest -m jira 2>&1 | grep -c "SENTINEL-abc123"
grep -rc "SENTINEL-abc123" reports/ 2>/dev/null
```

**Expected**: `0` from both. The token must not appear in any message, traceback, log line, or captured report artifact.

Allure attachments are the path people forget: a report gets shared with a test lead, and an unredacted traceback travels with it.

---

## Scenario 4 — Live read (validates SC-001, FR-019, US1)

Needs real credentials. Configure per [contracts/configuration.md](./contracts/configuration.md). A read-scoped token is sufficient — this client never writes.

```bash
uv run python -m ai_qa.jira check                 # FR-019: verifies auth, touches no issue
uv run python -m ai_qa.jira issue AIQA-1          # expect key, summary, description, status, type
uv run python -m ai_qa.jira issue NOSUCH-99999    # expect exit 4, "not found or not visible"
uv run python -m ai_qa.jira search "project = AIQA ORDER BY created DESC"
```

**Expected**: `check` reports the authenticated account. The issue read returns all five FR-005 fields with a readable description (ADF flattened). The missing key exits **4**, distinctly from an auth failure (**3**).

Confirm pagination is real (SC-011): run a search matching more issues than one page carries and confirm the count matches Jira's own, with nothing silently truncated.

---

## Scenario 5 — Failure causes are distinguishable (validates SC-005, FR-014)

```bash
uv run pytest tests/jira/test_errors.py -v
```

**Expected**: seven causes, seven distinct errors, each naming the Jira host (FR-017):

| Cause | Error | CLI exit |
|---|---|---|
| Settings missing/incomplete | `JiraConfigError` | 2 |
| 401 | `JiraAuthError` | 3 |
| 403 | `JiraForbiddenError` | 3 |
| 404 | `JiraNotFoundError` | 4 |
| 400 on search | `JiraQueryError` | 7 |
| 429 after retries | `JiraRateLimitError` | 6 |
| Network/timeout/5xx | `JiraUnavailableError` | 6 |

Also confirm the negative rule from R7: a 401 is attempted **once**, not retried. Retrying it cannot succeed and only delays a clear error.

---

## Coverage summary

| User Story | Priority | Scenario |
|---|---|---|
| 1 — Read an issue | P1 | 2, 4 |
| 2 — Configure without committing credentials | P2 | 3 |
| 3 — Fail clearly when unavailable | P2 | 1, 5 |
| 4 — Find issues by query | P3 | 2, 4 |

All 11 success criteria are exercised: SC-002 and SC-003 by inspection (no dependency added, no connector in the runtime path); SC-001 and SC-011 in Scenario 4; SC-004 and SC-006 in Scenario 3; SC-005 and SC-007 in Scenario 5; SC-008 and SC-009 in Scenarios 1 and 2; SC-010 by cross-checking the `Settings` model against `.env.example`.

> **Scope change, 2026-10-04**: the write-safeguard, live-write and write-cannot-fail-a-test scenarios were removed with the write capability. Scenarios renumbered; nothing in this feature now modifies Jira.
