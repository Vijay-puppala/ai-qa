---

description: "Task list for Jira REST Integration"
---

# Tasks: Jira REST Integration

**Input**: Design documents from `/specs/002-jira-rest-integration/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Test tasks are included because the spec *requires* them. FR-018 and SC-009 mandate that the integration be verifiable with no network access, and SC-005 and SC-009 are negative criteria ("zero of X") that can only be demonstrated by tests. These are deliverables, not optional scaffolding.

**Organization**: Grouped by user story. One structural exception is called out in Phase 7.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4 from [spec.md](./spec.md)
- Exact file paths included

## Path Conventions

Single project at repository root. New code in `src/ai_qa/jira/`, tests in `tests/jira/`. Every command runs through `uv run`.

---

## Phase 1: Setup

- [X] T001 Add `jira` to the registered markers in `pyproject.toml` under `[tool.pytest.ini_options]` — `--strict-markers` is on, so an unregistered marker is an error
- [X] T002 [P] Create `src/ai_qa/jira/__init__.py` exporting the public surface named in `contracts/jira-client.md`: `JiraClient`, the error classes, `JiraIssue`, `IssueQueryPage`
- [X] T003 Add the four Jira fields to the `Settings` model in `src/ai_qa/config.py`, with constraints quoted verbatim from `data-model.md` §1: `jira_base_url: HttpUrl | None` (default `None`, trailing slash stripped on load); `jira_email: str | None` (must contain `@` when set); `jira_api_token: SecretStr | None` (masked in `repr`, never logged); `jira_timeout_s: float` (default `30.0`, `gt=0`, `le=300`) — FR-008
- [X] T004 Add the cross-field validation rule from `data-model.md` §1 to `Settings`: **partial credentials are an error** — if any of base_url/email/token is set, all three must be. Setting two of three otherwise produces an authentication failure against Jira when the real problem is local — FR-011
- [X] T005 Extend `_ENV_PREFIXES` in `src/ai_qa/config.py` with the seven new variable names so they remain visible to the `.env.example` cross-check (SC-010)

**Checkpoint**: `uv run pytest -m healthcheck` still passes; settings load with no Jira configuration present.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites for every user story.

- [X] T006 Create the error taxonomy in `src/ai_qa/jira/errors.py`: `JiraError` base plus `JiraConfigError`, `JiraAuthError`, `JiraForbiddenError`, `JiraNotFoundError`, `JiraQueryError`, `JiraRateLimitError`, `JiraUnavailableError`. Every error carries the Jira host it was talking to — FR-014, FR-017
- [X] T007 Implement `redact(text, token)` in `src/ai_qa/jira/errors.py`: strips `Authorization` header values and replaces the token's literal value with `***`. Applied at error **construction**, not display, so a traceback captured into an Allure artifact is already clean — FR-010, SC-006
- [X] T008 [P] Implement `to_text(adf)` in `src/ai_qa/jira/adf.py` handling `paragraph`, `text`, `hardBreak`, `heading`, `bulletList`, `orderedList`, `listItem`, `codeBlock`, `blockquote`. Any **unrecognised node degrades to the concatenated text of its children** and must never raise. A plain string passes through unchanged — R2
- [X] T009 [P] Create `JiraIssue` and `IssueQueryPage` in `src/ai_qa/jira/models.py` as frozen models, with fields per `data-model.md` §2: `key`, `project_key` (text before the first `-`), `summary`, `description` (ADF-flattened), `status`, `issue_type`, `labels`, `raw`. A missing or null `description` becomes `""` and must not raise
- [X] T010 Create `tests/jira/conftest.py` with the `mock_jira` factory fixture building a `JiraClient` over `httpx.MockTransport` with caller-supplied canned responses — function-scoped. This is what makes the whole feature offline-testable with no new dependency — FR-018, R5
- [X] T011 Implement the `JiraClient` constructor in `src/ai_qa/jira/client.py`: raises `JiraConfigError` before any network call when Jira settings are absent or incomplete; accepts an optional `transport` for test injection; HTTP Basic auth from `jira_email` + `jira_api_token`; explicit `httpx.Timeout` from `jira_timeout_s` on every request — FR-011, FR-013, R1

**Checkpoint**: a client can be constructed over `MockTransport` and raises a config error without settings.

---

## Phase 3: User Story 1 - Read a Jira issue (Priority: P1) 🎯 MVP

**Goal**: Fetch a ticket's content by key through the project's own REST client.

**Independent Test**: With canned responses, request an issue and confirm key, summary, description, status and issue type come back; confirm 404/401/403 produce distinct errors.

- [X] T012 [US1] Implement `get_issue(key)` in `src/ai_qa/jira/client.py`: `GET /rest/api/3/issue/{key}`, flatten the ADF description via `adf.to_text`, return a frozen `JiraIssue` — FR-005
- [X] T013 [US1] Map response codes to the taxonomy in `get_issue`: 404 → `JiraNotFoundError` worded **"not found or not visible to this account"** (Jira answers 404 for both, and asserting the issue does not exist sends people hunting for a deleted ticket that is merely invisible), 401 → `JiraAuthError`, 403 → `JiraForbiddenError` — FR-014
- [X] T014 [P] [US1] Add `tests/jira/test_client_read.py` covering the happy path: all five FR-005 fields present, `project_key` derived correctly
- [X] T015 [P] [US1] Add tests to `tests/jira/test_client_read.py` for an ADF description with nested formatting and for an **unrecognised node type**, asserting content survives and nothing raises
- [X] T016 [P] [US1] Add a test asserting non-ASCII summary and description survive the round trip unmangled

**Checkpoint**: MVP — ticket content is retrievable, offline-testable, with honest 404 wording.

---

## Phase 4: User Story 2 - Configure without committing credentials (Priority: P2)

**Goal**: Credentials live in `.env` only; every setting is named in the committed example.

**Independent Test**: Copy the example, set values, confirm a request works; confirm `.env` is ignored and the example holds no real value.

- [X] T017 [US2] Append the Jira block to `.env.example` using the exact content in `contracts/configuration.md`, including the explicit warning on `JIRA_API_TOKEN` that real tokens belong in `.env` because this file is committed — FR-009, SC-004
- [X] T018 [P] [US2] Add `tests/jira/test_redaction.py` asserting the token appears in zero error messages, and that `SecretStr` masks it in `repr` — FR-010, SC-006
- [X] T019 [US2] Ensure a settings validation failure raises reporting the **environment variable** name (`JIRA_BASE_URL`), not the model field name, reusing feature 001's `pytest.UsageError` path — FR-011
- [X] T020 [P] [US2] Add a test for each of T004's three cross-field rules, asserting each is rejected at load with the offending variables named
- [X] T021 [US2] Add a health-check test to `tests/health/test_environment.py` asserting Jira settings validate **when configured**, and are skipped when not — must not fail on a machine with no Jira configuration (FR-016 of this feature's spec)
- [X] T022 [P] [US2] Verify `git check-ignore -v .env` and that `git status --porcelain` lists no credential-bearing file — FR-012

**Checkpoint**: configuration is secret-safe and fully described by the committed example.

---

## Phase 5: User Story 3 - Fail clearly when Jira is unavailable (Priority: P2)

**Goal**: Every failure names its cause; Jira being down never affects unrelated tests.

**Independent Test**: Point at an unreachable host; confirm bounded failure naming the host, while a non-Jira test still passes.

- [X] T023 [US3] Implement the retry policy in `src/ai_qa/jira/client.py`: retry **only** on 429 and 5xx, at most 3 attempts, honouring `Retry-After` when present, otherwise exponential backoff — FR-015, R7
- [X] T024 [US3] Ensure 400/401/403/404 are **never** retried. Retrying these cannot succeed and only turns a clear error into a slow one. With writes out of scope every operation is idempotent, so a retry cannot cause a duplicate side effect — R7
- [X] T025 [US3] Map network failures and timeouts to `JiraUnavailableError`, naming the host and the cause, failing within the configured timeout rather than hanging — FR-013, FR-017
- [X] T026 [P] [US3] Add `tests/jira/test_errors.py` asserting all seven failure causes produce distinct error types, each naming the host — FR-014, SC-005
- [X] T027 [P] [US3] Add a test asserting a 401 is attempted **once**, not retried
- [X] T028 [P] [US3] Add a test asserting the full suite passes with Jira entirely unconfigured — Jira tests skip, non-Jira tests unaffected — FR-016, SC-008
- [X] T029 [P] [US3] Add a test asserting a 429 response honours the advertised `Retry-After` and gives up after the bounded attempts with `JiraRateLimitError`

**Checkpoint**: Jira is no longer able to take the suite down.

---

## Phase 6: User Story 4 - Find issues by query (Priority: P3)

**Goal**: Retrieve every issue matching a query, across all pages.

**Independent Test**: Query a canned multi-page result set and confirm all issues return.

- [X] T030 [US4] Implement `search_page(jql, ...)` in `src/ai_qa/jira/client.py` using `POST /rest/api/3/search/jql` with `nextPageToken` pagination — the offset-based `GET /search` is deprecated and carries offset drift (R6)
- [X] T031 [US4] Implement `search(jql, ...)` returning a **lazy iterator that follows tokens to exhaustion**, so a caller cannot accidentally read only the first page — FR-006, SC-011
- [X] T032 [US4] Map a 400 on search to `JiraQueryError` carrying Jira's own rejection reason — FR-014
- [X] T033 [P] [US4] Add `tests/jira/test_search.py` asserting a three-page canned result set yields every issue with zero truncation — SC-011
- [X] T034 [P] [US4] Add a test asserting a malformed query raises `JiraQueryError` with the reason included

**Checkpoint**: all four user stories independently functional.

---

## Phase 7: CLI

- [X] T035 Create `src/ai_qa/jira/__main__.py` with standard-library `argparse` and three subcommands: `check`, `issue`, `search` — a CLI framework would be a new dependency (FR-003, R12)
- [X] T036 Implement `check`: verify authentication and report the authenticated account **without touching an issue** — this is FR-019's confirmation step
- [X] T037 Implement the exit-code mapping from `contracts/jira-client.md`: 0 success, 2 config, 3 auth/authz, 4 not found, 6 unavailable/rate-limited, 7 query rejected. **Code 5 is deliberately left unused** — it previously meant "write refused locally", and reserving rather than reusing it means a script written against the earlier contract cannot silently misread a different failure
- [X] T038 [P] Add `tests/jira/test_cli.py` asserting each exit code for its cause

**Checkpoint**: both call paths from FR-004 exist and share one client.

---

## Phase 8: Polish & Cross-Cutting

- [X] T039 Document Jira setup in `README.md`: the four settings, how to obtain an API token, that a read-scoped token suffices because this client never writes, and the `uv run python -m ai_qa.jira check` confirmation step — FR-020
- [X] T040 [P] Add to `CLAUDE.md` that Jira access goes through this project's REST integration and that **no assistant connector or MCP server may be used for it**, so the constraint survives a future contributor — FR-021
- [X] T041 [P] Verify SC-006 by running a failing Jira test with a sentinel token and searching the complete run output **and** `reports/` for it — expect zero occurrences
- [X] T042 [P] Verify SC-009 by running the full suite with no network access to any Jira site — expect all pass
- [X] T043 [P] Verify SC-010 by cross-checking every `Settings` Jira field against `.env.example` — expect zero drift in either direction
- [X] T044 [P] Verify SC-002 and SC-003: `uv.lock` gained zero new third-party dependencies, and no Jira capability requires an assistant or connector at runtime

- [X] T045 [P] Add a test asserting `JiraClient` exposes **no mutating method** - no `add_comment`, `transition_issue`, or any other write - so FR-007's prohibition is enforced by the suite rather than by memory. The requirement flipped from a capability to a prohibition when writes were deferred on 2026-10-04, and a prohibition needs its own test or a future contributor can quietly undo it — FR-007
- [X] T046 [P] Verify SC-001 end to end against a live site: an engineer with a valid token retrieves a known issue's content on the first attempt, using only the documented setup steps — SC-001, FR-019
- [X] T047 [P] Add a test asserting every request is bounded by the configured timeout, using a delayed `MockTransport` response - T023 implements the timeout but nothing currently asserts the bound is honoured — SC-007, FR-013
- [X] T048 [P] Close the traceability gap for the constraint requirements no single task owns, verifying each by inspection and recording the result: **FR-001** (all Jira access is direct REST), **FR-002** (no MCP, connector, or external tooling in the runtime path) — these are satisfied by the design rather than by a discrete step, so citing them here is what makes them auditable

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies. T003 → T004 → T005 in order (fields, then rules over them, then the prefix list)
- **Phase 2** depends on Phase 1. **Blocks all user stories.** T011 depends on T006 (errors) and T003 (settings)
- **Phase 3 (US1)** depends on Phase 2. **MVP**
- **Phase 4 (US2)** depends on T003/T004. Independent of US1's client work
- **Phase 5 (US3)** depends on T011 and T006
- **Phase 6 (US4)** depends on T011; independent of US1's `get_issue`
- **Phase 7** depends on every client method it exposes
- **Phase 8** depends on all of the above

### Shared write points (not parallelizable despite different stories)

`src/ai_qa/jira/client.py` is touched by T011, T012, T013, T023, T024, T025, T030, T031, T032. None of these carry `[P]`. `src/ai_qa/config.py` is touched by T003, T004, T005 — also sequential.

---

## Parallel Execution Examples

- **Phase 2**: T008, T009, T009 are different files — run together. T006 and T007 share `errors.py`, so they are sequential.
- **Phase 3**: T014, T015, T016 all add to `test_client_read.py` — sequential with each other, parallel to nothing else in the phase.
- **Phase 9**: T040–T044 are independent verifications — run together.

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (T001–T016)**: a working, offline-testable Jira read client. That alone unblocks feature 003, which only needs ticket retrieval.

**Then**: US2 (T017–T022) for credential safety, US3 (T023–T029) to stop Jira outages affecting the suite. Both are P2 and independent of each other.

**Write operations were removed from this feature on 2026-10-04.** Nothing needs them: feature 004 keeps its approval records in the repository and feature 005 rules Jira reporting out of scope. The designs survive in research R3, R4 and R10 for whichever feature adds writes later.

**Three traps worth naming:**

1. **`pydantic-settings` is a separate package in pydantic v2.** The idiomatic `BaseSettings` import is not available from the mandated dependency, and reaching for it breaks FR-004's floor. Use `BaseModel` plus `python-dotenv` — T003.
2. **Returning a page instead of an exhausting iterator from `search()`** reintroduces silent truncation. SC-011 is only structural because the iterator follows tokens to exhaustion — T031.

---

## Phase 9: Convergence

Appended by `/speckit.converge` on 2026-10-04 after assessing the code against
this feature's spec, plan, tasks and contracts. Each item traces to the source
that requires it and the kind of gap found.

- [X] T049 Add the session-scoped `jira_client` fixture to `tests/jira/conftest.py`, building a `JiraClient` from real `Settings` and **skipping** the test when Jira is not configured, then use it in at least one test so FR-004's test-runtime path is actually exercised per FR-004 and `contracts/jira-client.md` (missing). Only `mock_jira` exists today, so the runtime half of "one client, two call paths" is unbuilt and the contract's named fixture is absent — session scope for the same reason `settings` is in feature 001, no mutable per-test state
- [X] T050 Add a test asserting every Jira field on the `Settings` model appears in `.env.example` and vice versa, driven off `_ENV_PREFIXES`, per SC-010 (partial). Parity was verified once by hand with zero drift, but SC-010 is an **ongoing** property and nothing currently prevents someone adding a setting without documenting it — which is exactly the invisible-configuration failure the criterion exists to stop
- [X] T051 Correct the stale annotations in `plan.md` that still reference `FR-022`–`FR-029` and `test_safeguards.py` (lines 31, 81, 91, 144, 152, 161), per the 2026-10-04 write-scope deferral recorded in `spec.md` (contradicts). The requirements and the test file they name no longer exist; the Risks and Complexity rows about comment idempotency and flaky transitions describe a capability that was removed

---

## Phase 10: Convergence

Second convergence pass, 2026-10-04, after T046 was verified against the live
Jira site and T049-T051 were completed. The previous Convergence phase is left
untouched above.

- [X] T052 Isolate `tests/jira/test_cli.py::test_unconfigured_exits_config` from the real `.env` so it asserts the unconfigured path regardless of what is on the machine, per SC-009 and FR-011 (contradicts). It currently pops `JIRA_*` from `os.environ`, but `Settings.from_env()` calls `load_dotenv()` and reads them back from the file - so the test **fails** on any machine with real credentials, and only ever passed because none existed. Point dotenv at an empty file or inject an unconfigured `Settings`; a test whose result depends on the developer's local secrets is not a test
- [X] T053 Handle, or explicitly record as a limitation, the case where Jira answers a malformed query with **200 and an empty issue list** instead of 400, per SC-005 and FR-014 (partial). Verified live: `search "bogusfield = 1"` exits 0 rather than 7, because `/search/jql` does not reject an unknown field. The client is correct for the response it receives - it is the spec's assumption that a bad query always yields a distinguishable error that does not hold on this endpoint. Either detect unknown field names before sending, or amend SC-005 to say so rather than leaving a criterion that cannot be met
- [X] T054 Fix word-boundary truncation in `ai_qa.generate.scaffold.target_path`, which is feature 003's code, per `plan: file naming` and 003 FR-012 (partial). Generating DC-11 produced `test_build_login_screen_ui_with_validation_and_passwo.py` - a 48-character cut mid-word that needed a manual rename. Truncate on a word boundary or cap the slug at a few whole words. Recorded here because the evidence surfaced during this feature's live verification; move it to 003's task list if you would rather it live there

---

## Phase 11: Convergence

Third convergence pass, 2026-10-04. Phases 9 and 10 are left untouched above.

- [ ] T055 Document the client's full public surface in `contracts/jira-client.md`, per that contract's own compatibility notes and FR-019 (partial). `validate_jql`, `whoami` and `close` are implemented but undescribed, and the constructor takes an undocumented `sleep` parameter that the retry tests inject. The contract declares that changing the public surface is a breaking change, so a method it does not list cannot be reasoned about by a caller - and `validate_jql` in particular is load-bearing: it is the only reason an unknown JQL field reports as a rejected query rather than as "no matches". This drift is the trace of fixing finding F5 in the previous pass
