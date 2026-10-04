# Phase 1 Data Model: Jira REST Integration

**Feature**: `002-jira-rest-integration` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

Four things with real structure: the settings that configure access, the issue shape read back, the error taxonomy that makes failures diagnosable, and the comment signature that makes writes idempotent. No persistence.

---

## 1. Jira settings — extending the existing `Settings` model

Seven new fields on the existing `Settings` model in `src/ai_qa/config.py` (FR-008). Not a separate model — see the Structure Decision in [plan.md](./plan.md). External contract with placeholders: [contracts/configuration.md](./contracts/configuration.md).

| Field | Type | Required | Default | Validation |
|---|---|---|---|---|
| `jira_base_url` | `HttpUrl \| None` | No | `None` | Absolute `http`/`https`. Trailing slash stripped on load so a doubled slash cannot reach a request path |
| `jira_email` | `str \| None` | No | `None` | Must contain `@` when set |
| `jira_api_token` | `SecretStr \| None` | No | `None` | Masked in `repr`; never logged (FR-010) |
| `jira_timeout_s` | `float` | No | `30.0` | `gt=0`, `le=300` |

### Why every field is optional

The suite must run with no Jira configuration at all (FR-016, SC-008). If `jira_base_url` were required, feature 001's health checks would start failing on every machine without a Jira token — turning an optional integration into a precondition for running any test. So absence is valid, and it is *use* that fails, not *load*.

### Cross-field validation (model-level, runs at load)

Three rules, each catching a misconfiguration that would otherwise surface as a confusing runtime error:

1. **Partial credentials are an error.** If any of `jira_base_url`, `jira_email`, `jira_api_token` is set, all three must be. Setting two of three otherwise produces an authentication failure against Jira when the real problem is local (FR-011).
Only one rule remains after the 2026-10-04 scope change: rules 2 and 3 governed write enablement and were removed with it.
### Failure behaviour

A validation failure raises during settings load, before any network call, reporting the environment variable names at fault — `JIRA_BASE_URL`, not `jira_base_url` — and pointing at `.env.example` (FR-011). This reuses feature 001's existing `pytest.UsageError` path, so the behaviour is identical to a missing `BASE_URL`.

---

## 2. `JiraIssue` and `IssueQueryPage`

Read models in `src/ai_qa/jira/models.py`. Frozen `pydantic.BaseModel` subclasses — nothing mutates a fetched issue.

### `JiraIssue`

| Field | Type | Source | Notes |
|---|---|---|---|
| `key` | `str` | `key` | e.g. `AIQA-123`. The unique identity |
| `project_key` | `str` | derived | Text before the first `-`. What FR-023's allow-list is checked against |
| `summary` | `str` | `fields.summary` | Plain text already |
| `description` | `str` | `fields.description` | **Flattened from ADF** — see §4 |
| `status` | `str` | `fields.status.name` | Human-readable name, not id |
| `issue_type` | `str` | `fields.issuetype.name` | |
| `labels` | `tuple[str, ...]` | `fields.labels` | Empty tuple when absent |
| `raw` | `dict` | whole response | Kept so a caller needing a field this model omits is not blocked on a code change |

The five fields FR-005 mandates are `key`, `summary`, `description`, `status`, `issue_type`. `project_key`, `labels` and `raw` are additions: the first is required to enforce FR-023, and the last is an escape hatch that avoids this model becoming a bottleneck.

**Absent fields degrade, they do not raise.** A missing or null `description` becomes `""`. An issue with no description is normal; failing to read it would be wrong.

### `IssueQueryPage`

| Field | Type | Notes |
|---|---|---|
| `issues` | `tuple[JiraIssue, ...]` | This page's results |
| `next_page_token` | `str \| None` | `None` on the last page |
| `is_last` | `bool` | True when no further page exists |

Pagination is token-based (R6). The client exposes an iterator that follows tokens to exhaustion, so a caller cannot accidentally read only the first page — which is what SC-011's "zero silent truncation" requires. The page model is still public for a caller that wants to page manually.

---

## 3. Error taxonomy

`src/ai_qa/jira/errors.py`. FR-014 requires seven causes to be distinguishable, and SC-005 requires zero of them to report a cause that is not theirs.

```text
JiraError (base)
├── JiraConfigError          # settings missing/incomplete - raised before any request
├── JiraAuthError            # 401 - credentials rejected
├── JiraForbiddenError       # 403 - authenticated but not permitted
├── JiraNotFoundError        # 404 - issue or endpoint absent
├── JiraQueryError           # 400 on a search - query rejected, carries Jira's reason
├── JiraRateLimitError       # 429 after retries exhausted, carries the advertised delay
└── JiraUnavailableError     # network failure, timeout, or 5xx after retries
```

Every error carries the Jira host it was talking to (FR-017) and passes its message through the redaction helper (FR-010).

### The distinction that matters

> `JiraWriteRefusedError` was removed on 2026-10-04 with the write scope. The client has no method that modifies Jira, so there is no local refusal to distinguish from Jira's own 403.

**`JiraNotFoundError` honesty.** Jira answers 404 both for a genuinely absent issue and, in some configurations, for one the account cannot see. The message must therefore say the issue "was not found or is not visible to this account" rather than asserting it does not exist. The spec's edge case requires exactly this, and overstating it sends people hunting for a deleted ticket that is merely invisible.

### Redaction helper

`redact(text: str, token: SecretStr | None) -> str` — strips `Authorization` header values and replaces any occurrence of the token's literal value with `***`. Applied to every error message at construction, not at display time, so a traceback captured into an Allure artifact is already clean (SC-006).

---

## 4. ADF handling

`src/ai_qa/jira/adf.py`. Two functions, both pure.

**`to_text(adf: dict | str | None) -> str`** — flattens an ADF document to plain text. Handles `paragraph`, `text`, `hardBreak`, `heading`, `bulletList`, `orderedList`, `listItem`, `codeBlock`, `blockquote`. Any **unrecognised node degrades to the concatenated text of its children**, so a node type Atlassian adds later loses formatting but never loses content and never raises. Accepts a plain string unchanged, so a v2-shaped response or an already-flattened value passes through.

**`from_text(text: str) -> dict`** — wraps plain text as a minimal ADF document (`doc` → `paragraph` → `text`, splitting on blank lines). Needed because comment bodies must be ADF (R2).

Round-tripping is explicitly **not** a goal: `to_text(from_text(x))` returns `x`, but `from_text(to_text(adf))` loses formatting. Comments the platform posts are plain text by design.

---

## 5. Comment signature — REMOVED

Deferred with the write scope on 2026-10-04. The design is preserved in research R4 for whichever feature adds comment writes later.

---

## Entity mapping to spec

| Spec Key Entity | Where it lives |
|---|---|
| Jira Settings | 7 fields on `Settings` in `src/ai_qa/config.py` — §1 |
| Jira Issue | `JiraIssue` in `src/ai_qa/jira/models.py` — §2 |
| Issue Query | `IssueQueryPage` + the exhausting iterator — §2 |
| Jira Failure | The 8-class taxonomy in `src/ai_qa/jira/errors.py` — §3 |
