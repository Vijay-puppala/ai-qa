# Phase 0 Research: Jira REST Integration

**Feature**: `002-jira-rest-integration` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

Twelve decisions, each as Decision / Rationale / Alternatives considered. The spec's clarifications are settled input.

**Scope change, 2026-10-04**: write operations were deferred out of this feature. **R3, R4 and R10 are marked DEFERRED** and retained unchanged — they will be correct and needed when a later feature adds writes. The remaining nine decisions all still apply to the read-only client.

The hard constraints from the user shape almost every decision below: **REST only, no MCP at runtime** (FR-002) and **zero new dependencies** (FR-003). The second one bites more often than it looks — several conventional answers in this space are libraries.

---

## R1: Authentication

**Decision**: HTTP Basic auth with account email as username and an Atlassian API token as password, passed via `httpx`'s `auth=(email, token)`.

**Rationale**: This is Atlassian Cloud's supported mechanism for scripted access and needs no library — `httpx` handles the header. OAuth 2.0 (3LO) would require an interactive browser consent flow and a token-refresh story, neither of which fits a test suite or an unattended run, and the client registration is per-site admin work. The token carries the holder's full permissions, which is precisely why FR-023 and FR-025 impose local allow-lists: Jira will authorise anything the engineer could do by hand, so the restraint has to live in our code.

**Alternatives considered**:
- *OAuth 2.0 (3LO)* — rejected: interactive consent, refresh handling, admin setup. Wrong shape for unattended use.
- *Personal access tokens* — rejected: Server/Data Center only; the target is Cloud.
- *Forwarding the session's MCP connector* — rejected outright by FR-002.

## R2: API version and the description problem

**Decision**: Jira Cloud REST API **v3** (`/rest/api/3/`), plus a small in-project Atlassian Document Format (ADF) to plain-text flattener.

**Rationale**: This is the decision most likely to be got wrong by assumption, so it is worth being explicit. On v3 an issue's `description` comes back as **ADF JSON**, not a string — so `issue["fields"]["description"]` is a nested document tree. v2 returns a plain string instead, which looks more convenient and is the tempting shortcut.

v3 is chosen anyway because it is the current Cloud API and the one Atlassian develops against, and because comment and transition payloads (R4, R3) need ADF regardless — picking v2 for reads would mean straddling two API versions for one feature. The cost is a flattener handling `paragraph`, `text`, `hardBreak`, `heading`, `bulletList`/`orderedList`/`listItem`, `codeBlock`, and `blockquote`, with any unrecognised node degrading to the concatenated text of its children. That is roughly forty lines and zero dependencies, and it satisfies the spec's edge case requiring rich text to stay usable for test authoring.

**Alternatives considered**:
- *API v2 for reads* — rejected: simpler today, but mixes API versions within one feature and builds on the older surface.
- *`expand=renderedFields` for HTML* — rejected: converts the problem from "parse ADF" to "parse HTML", which is worse without a dependency.
- *A markdown/ADF conversion library* — rejected: FR-003 forbids the dependency.

## R3: Transitions are ids, not names (DEFERRED)

> **Deferred 2026-10-04.** Write operations were removed from this feature's scope (see the spec's Clarifications, Session 2026-10-04). This research is retained unchanged because it will be correct and needed by whichever later feature adds writes — it is not wrong, just not yet used.

**Decision**: Resolve a target status name to a transition id at call time via `GET /rest/api/3/issue/{key}/transitions`, then `POST` that id. Refuse locally, before any lookup, if the requested status is not in the configured allow-list.

**Rationale**: `POST /transitions` takes a transition **id**, and those ids are workflow-specific — they differ between projects and are not stable across workflow edits. So a configured allow-list of human-readable status names (FR-025) has to be resolved per issue, and the available transitions depend on the issue's *current* status. This produces two genuinely different failures the spec requires to be distinguishable: "we refuse this status" (checked locally against the allow-list, no request sent) versus "Jira's workflow does not offer this transition from the current status" (discovered from the lookup). Collapsing them would leave an engineer unable to tell a policy block from a workflow reality.

**Alternatives considered**:
- *Configure transition ids directly* — rejected: unreadable configuration, and breaks silently whenever a workflow is edited.
- *Skip the lookup and guess the id* — rejected: wrong by construction across projects.

## R4: Comment idempotency (DEFERRED)

> **Deferred 2026-10-04.** Write operations were removed from this feature's scope (see the spec's Clarifications, Session 2026-10-04). This research is retained unchanged because it will be correct and needed by whichever later feature adds writes — it is not wrong, just not yet used.

**Decision**: Embed a deterministic signature in each posted comment body — derived from the issue key, a logical event key, and the run identifier — and before posting, scan the issue's existing comments for that signature. If present, skip.

**Rationale**: Jira's comment API has no idempotency key, so FR-027 cannot be satisfied by the protocol. A signature in the body is the only mechanism available without server-side state. The scan costs one extra GET per comment write, which is acceptable because comment writes are rare compared with reads. The signature must be visibly machine-oriented so a human reading the ticket understands why it is there.

**Alternatives considered**:
- *Local state file tracking posted comments* — rejected: breaks across machines and CI runners, and FR-027's guarantee would silently lapse whenever state was lost.
- *Search API lookup instead of fetching comments* — rejected: comment bodies are not reliably searchable by substring, and the search index lags writes.
- *Accept duplicates* — rejected by FR-027; a retried suite would spam a real ticket.

## R5: Offline testability without a new dependency

**Decision**: `httpx.MockTransport`, injected into the client at construction.

**Rationale**: FR-018 and SC-009 require the whole suite to pass with no network access, and FR-029 forbids the integration's own tests from touching a live Jira. The conventional answer is a mocking library such as `respx` or `vcrpy` — both are new dependencies and therefore forbidden by FR-003. `httpx` ships `MockTransport`, which takes a handler mapping requests to responses and is sufficient for every scenario here, including error codes, `Retry-After` headers, and paginated responses. This is a case where the dependency constraint cost nothing, because the capability was already in a mandated package.

**Alternatives considered**:
- *`respx`* — rejected: nicer API, but a new dependency FR-003 does not permit.
- *A live test Jira project* — rejected: violates FR-029 and SC-009, and makes the suite depend on Atlassian's uptime.
- *Hand-rolled fake HTTP server* — rejected: more code than `MockTransport` and introduces port binding into tests.

## R6: Search and pagination

**Decision**: `POST /rest/api/3/search/jql`, paginating with the `nextPageToken` the response carries, until the response reports the last page.

**Rationale**: The long-standing `GET /rest/api/3/search` with `startAt`/`maxResults` is deprecated on Cloud in favour of the token-paginated endpoint. Building on the deprecated form would mean a migration before this feature is a year old. Token pagination also removes the offset-drift bug class, where an issue changing during iteration can cause a result to be skipped or returned twice — which matters for SC-011's "zero silent truncation".

**Alternatives considered**:
- *`GET /search` with offsets* — rejected: deprecated, plus offset drift.
- *Fetch only the first page* — rejected by SC-011.

## R7: Timeouts, retries, and rate limiting

**Decision**: An explicit `httpx.Timeout` on every request, configurable with a default of 30 seconds. Retry **only** on 429 and 5xx, at most three attempts, honouring `Retry-After` when present and otherwise backing off exponentially. Never retry 4xx other than 429.

**Rationale**: FR-013 requires bounded timeouts and FR-015 requires honouring the advertised delay. The important negative rule is not retrying ordinary 4xx: retrying a 401 cannot succeed and only delays a clear error, and retrying a write that may have partially applied risks duplicate side effects. Three attempts keeps the worst case bounded so a throttled Jira cannot stretch a run indefinitely.

**Alternatives considered**:
- *Retry everything* — rejected: turns a clear auth failure into a slow one, and risks duplicate writes.
- *No retries* — rejected: a single 429 would fail a run that would have succeeded a second later.
- *A retry library (`tenacity`)* — rejected: new dependency.

## R8: Credential masking

**Decision**: Hold the token as `pydantic.SecretStr`; build every error message through a redaction helper that strips `Authorization` headers and replaces any occurrence of the token's value with `***`.

**Rationale**: `SecretStr` alone is not enough for SC-006. It protects the settings object's `repr`, but the credential also travels in a request header, and `httpx` exceptions can carry the request. Allure captures a failed test's output, so an unredacted traceback would persist the token into a report artifact that gets shared. The redaction helper is the backstop for the paths `SecretStr` does not cover.

**Alternatives considered**:
- *Rely on `SecretStr`* — rejected: does not cover request headers or exception payloads.
- *Disable exception chaining* — rejected: destroys diagnostic value to solve a narrower problem than redaction solves.

## R9: One client, two call paths

**Decision**: A single `JiraClient` class. Tooling constructs it directly; tests receive it through a session-scoped fixture that builds it from settings.

**Rationale**: FR-004 requires both paths through one client so they cannot diverge. The subtle risk in answering "both" to Question 2 is two code paths with different error handling, where the tooling path is well-behaved and the test path quietly swallows failures. One class, one error taxonomy, injected differently, removes that.

Session scope for the fixture is safe for the same reason it was safe for `settings` in feature 001 — the client holds no mutable per-test state — and it avoids rebuilding a connection pool per test.

**Alternatives considered**:
- *Separate client for tests* — rejected: the divergence FR-004 exists to prevent.
- *Module-level singleton* — rejected: untestable; cannot inject `MockTransport`.

## R10: Where writes are gated (DEFERRED)

> **Deferred 2026-10-04.** Write operations were removed from this feature's scope (see the spec's Clarifications, Session 2026-10-04). This research is retained unchanged because it will be correct and needed by whichever later feature adds writes — it is not wrong, just not yet used.

**Decision**: Enforce all four safeguards (writes enabled, project allow-list, status allow-list, dry-run) inside `JiraClient`, before any request is constructed — not in the CLI, not in a pytest fixture, not at the call sites.

**Rationale**: FR-022 to FR-025 must hold on both call paths from R9. A guard in the CLI would not protect a test, and a guard in a fixture would not protect tooling. Putting them in the one place both paths funnel through makes the guarantee structural rather than a convention every future caller must remember. It also makes them directly testable with `MockTransport`: a refused write sends no request at all, which is the observable property SC-012 and SC-013 assert.

**Alternatives considered**:
- *Guard at call sites* — rejected: every new caller is a chance to forget.
- *Guard in a pytest plugin* — rejected: leaves the tooling path unguarded.

## R11: Code layout

**Decision**: `src/ai_qa/jira/` containing `client.py`, `models.py`, `errors.py`, `adf.py`, and `__main__.py`. Jira settings extend the existing `Settings` model in `src/ai_qa/config.py`.

**Rationale**: A subpackage keeps the integration's surface obvious and reviewable, and keeps the ADF flattener and error taxonomy out of the general-purpose modules. Settings go in the existing model rather than a parallel one because feature 001's rules require a single validated configuration source with every setting named in `.env.example` — a second settings object would create exactly the invisible-configuration problem SC-010 forbids.

**Alternatives considered**:
- *Flat modules in `src/ai_qa/`* — rejected: the integration is six concerns, not one.
- *A separate `JiraSettings` model loaded independently* — rejected: splits the configuration contract.

## R12: The tooling entry point

**Decision**: `python -m ai_qa.jira` (run as `uv run python -m ai_qa.jira`), argument parsing with the standard library's `argparse`. Subcommands: `check`, `issue`, `search`, `comment`, `transition`.

**Rationale**: FR-019 needs a credential-confirmation step separate from running the suite, which `check` provides — it verifies authentication and reports the authenticated account without touching an issue. `argparse` is standard library, so FR-003 holds; `click` or `typer` would be new dependencies. `python -m` avoids declaring a console script and the reinstall that entry-point registration implies.

**Alternatives considered**:
- *`click`/`typer`* — rejected: new dependency.
- *A console script entry point* — rejected: needs a reinstall to register, which complicates the clean-checkout flow feature 001 verified.
- *No CLI, tests only* — rejected: fails FR-004's tooling path and FR-019.

---

## Resolved unknowns

| Unknown | Resolved by |
|---|---|
| How to authenticate without interactive flows? | R1 — Basic auth with API token |
| How is `description` obtained as usable text? | R2 — v3 plus an in-project ADF flattener |
| How does a status name become a transition? | R3 — per-issue transition lookup |
| How can comments be idempotent with no idempotency key? | R4 — signature embedded in the body |
| How can writes be tested without a live Jira? | R5 — `httpx.MockTransport` |
| How is a large result set fully retrieved? | R6 — `nextPageToken` pagination |
| Which failures may be retried? | R7 — 429 and 5xx only, bounded |
| How is the token kept out of Allure artifacts? | R8 — `SecretStr` plus a redaction helper |
| How do the two call paths stay consistent? | R9 — one client, injected differently |
| Where are the write safeguards enforced? | R10 (DEFERRED) — inside the client, pre-request. Retained for whichever feature adds writes |
