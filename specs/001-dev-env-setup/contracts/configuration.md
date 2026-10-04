# Configuration Contract: Development Environment Bootstrap

**Feature**: `001-dev-env-setup` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

The contract between an engineer's machine and the suite. `.env.example` is the committed, authoritative statement of it: SC-008 requires that every setting the suite reads at runtime appears here, so no setting is discoverable only by reading code.

**Committed**: `.env.example`, placeholders only.
**Not committed**: `.env`, holding real values, excluded by `.gitignore` (FR-022).

Field types and validation rules are in [data-model.md](./data-model.md) §1.

---

## Settings

| Variable | Type | Required | Default | Placeholder in `.env.example` |
|---|---|---|---|---|
| `BASE_URL` | URL | **Yes** | — | `https://example.com` |
| `BROWSER` | `chromium` \| `firefox` \| `webkit` | No | `chromium` | `chromium` |
| `HEADLESS` | boolean | No | `true` | `true` |
| `TIMEOUT_MS` | integer, 1–300000 | No | `30000` | `30000` |
| `API_BASE_URL` | URL | No | unset | `https://api.example.com` |
| `API_TOKEN` | secret string | No | unset | `replace-me` |
| `ARTIFACTS_DIR` | path | No | `reports/artifacts` | `reports/artifacts` |
| `ALLURE_RESULTS_DIR` | path | No | `reports/allure-results` | `reports/allure-results` |

`BASE_URL` is the only required setting. Everything else has a working default, so copying `.env.example` to `.env` and changing one line is enough to run — which is what keeps SC-001's 15-minute budget realistic.

---

## Example `.env.example`

```dotenv
# Target application under test. The only required setting.
BASE_URL=https://example.com

# Browser for UI tests: chromium | firefox | webkit
BROWSER=chromium

# Run without a visible browser window. Set to false to watch tests run.
HEADLESS=true

# Default timeout for browser operations, in milliseconds (1-300000).
TIMEOUT_MS=30000

# Optional: service endpoint for API tests. Leave unset to skip.
API_BASE_URL=https://api.example.com

# Optional: bearer token for API tests.
# NEVER put a real token in this file - it is committed. Put it in .env instead.
API_TOKEN=replace-me

# Output locations. Both are git-ignored and created on demand.
ARTIFACTS_DIR=reports/artifacts
ALLURE_RESULTS_DIR=reports/allure-results
```

Every value above is a placeholder or a non-sensitive default, satisfying FR-020 and the reviewable form of SC-005.

---

## Loading and failure behaviour

1. `python-dotenv` loads `.env` into the process environment if present. A missing `.env` is not an error at this stage — defaults may suffice for everything except `BASE_URL`.
2. A session-scoped fixture builds the frozen `Settings` model from the environment.
3. A missing or malformed required setting raises during collection, before any test body runs, as a `pytest.UsageError` naming the offending variable and pointing at `.env.example` (FR-023).

Illustrative failure output:

```text
E   pytest.UsageError: Invalid configuration: BASE_URL is required but not set.
E   Copy .env.example to .env and set BASE_URL. See README.md.
```

This is what SC-009 asks for: the message names the missing setting, so the engineer is not left diagnosing an unrelated failure deep in a browser test.

---

## Adding a setting later

The procedure exists because SC-008 is an ongoing property, not a one-time check:

1. Add the field to the `Settings` model with a type and validation rule.
2. Add it to `.env.example` with a placeholder and a comment explaining it.
3. Add it to the table above.

A setting read from `os.environ` anywhere outside the `Settings` model is a contract violation: it becomes invisible to `.env.example`, breaking SC-008 and leaving the next engineer to find it by reading code.

---

## Secret handling

Settled by the Clarifications session of 2026-10-03 and worth restating where someone adding a setting will actually read it:

- Real secrets live in `.env` only. `.env` is git-ignored; `.env.example` is committed with placeholders.
- `API_TOKEN` is typed `SecretStr`, so it is masked in `repr` output and tracebacks.
- **No secret-scanning tooling is in scope.** The protection is the ignore rule, which covers the configuration *file* — it does nothing about a credential pasted directly into a test, fixture, or doc. That case rests on code review. Recorded as a residual risk in the spec's Assumptions.
