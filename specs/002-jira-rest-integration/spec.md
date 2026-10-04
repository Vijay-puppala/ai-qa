# Feature Specification: Jira REST Integration

**Feature Branch**: `002-jira-rest-integration` *(no branch created — `main` is the only branch and nothing is committed yet)*

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Jira REST integration for the AI-QA platform. All Jira calls must go through Jira's REST API directly from this project, authenticated with credentials read from the local .env file via the existing Settings model. Do NOT use any MCP integration for this project — MCP must not be a runtime dependency of the test suite. The integration must cover the Jira calls the platform needs when a Jira-related request is made (reading an issue by key, and whatever else the platform requires). Must add zero dependencies beyond httpx, which is already declared. Credentials must never be committed."

## Clarifications

### Session 2026-10-03

- Q: Does the platform only read from Jira, or must it also write back? → A: Read, comment, **and transition** issues. ~~The widest scope: the platform may move real tickets through a real workflow.~~ **SUPERSEDED 2026-10-04 — see the Session 2026-10-04 entry below.**
- Q: Are Jira calls made during test runs, outside them by tooling, or both? → A: Both. A shared client used by offline tooling and, where useful, by tests at runtime.

### Session 2026-10-04

- Q: Should Jira write access stay in this feature's scope, given that no feature in the project now needs it? -> A: **No - defer writes to a later feature.** This feature becomes a read-only client. Verified before deciding: feature 004 keeps its approval records in the repository and needs no Jira writes, and feature 005 explicitly puts reporting back to the ticket system out of scope. The write half served no user story in this spec and no caller anywhere in the project.
  - Removed: the write half of FR-007; FR-022 to FR-029 (the eight write safeguards); SC-012 to SC-017; six write-path edge cases; the three write-related settings; and the comment-idempotency design.
  - Rationale for deferring rather than keeping: writes were the platform's only destructive surface, and eight safeguard requirements existed to contain a risk nothing had asked to take. Re-adding them is cheap once a caller exists; having built unneeded write access to a live system of record is not.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a Jira issue from the platform (Priority: P1)

A QA engineer, or an AI assistant working in the repository, needs the content of a Jira ticket — its summary, description, and acceptance criteria — in order to write or review tests for it. They ask the platform for the issue by key and get its content back, without opening a browser and without the platform depending on any external assistant tooling.

**Why this priority**: This is the capability the whole feature exists for. Every other story supports it. On its own it delivers value: ticket content in hand, in the repository, reproducibly.

**Independent Test**: With valid credentials configured, request a known issue by key and confirm its summary and description come back. Fully testable alone.

**Acceptance Scenarios**:

1. **Given** valid credentials and a reachable Jira site, **When** an issue is requested by its key, **Then** the issue's key, summary, description, status, and issue type are returned.
2. **Given** an issue key that does not exist, **When** it is requested, **Then** the failure says the issue was not found and names the key, distinctly from a permission or authentication failure.
3. **Given** an issue the credentials may not view, **When** it is requested, **Then** the failure says access was denied rather than reporting the issue as missing.
4. **Given** an issue whose description contains non-ASCII text and rich formatting, **When** it is requested, **Then** the text is returned intact and readable.

---

### User Story 2 - Configure Jira access without committing credentials (Priority: P2)

An engineer sets up Jira access on their machine by copying the committed example configuration and filling in their own site URL, account, and API token. Their token never leaves their machine. A teammate reading the repository can see exactly which settings are required without being told.

**Why this priority**: An API token is a real credential with the holder's full Jira permissions. Getting this wrong once — a token in a commit — means revoking it and rewriting history. It ships alongside the first capability, not after.

**Independent Test**: Copy the example configuration, set the Jira values, confirm a request succeeds, then confirm the local configuration file is excluded from version control and the example contains no real value.

**Acceptance Scenarios**:

1. **Given** the committed example configuration, **When** an engineer reads it, **Then** every Jira setting is named with a placeholder, and no real site, account, or token appears.
2. **Given** Jira settings are absent from the local configuration, **When** a Jira request is attempted, **Then** the failure names the specific missing settings and points at the example file.
3. **Given** a configured token, **When** any failure, log line, or error output is produced, **Then** the token does not appear in it in any form.
4. **Given** a completed setup, **When** version-control status is inspected, **Then** no file containing a real token is a candidate for commit.

---

### User Story 3 - Fail clearly when Jira is unavailable (Priority: P2)

An engineer runs the test suite while Jira is down, their token has expired, or they are offline. The platform tells them plainly that Jira is unreachable and why — and tests that have nothing to do with Jira still run and still pass.

**Why this priority**: An integration that makes the whole suite fail when an external service hiccups is worse than no integration. This is what keeps Jira from becoming a hard dependency of test execution, and it must be designed in rather than added after the first bad morning.

**Independent Test**: Point the configuration at an unreachable host and confirm the Jira request fails with a message naming the cause, while a non-Jira test in the same run still passes.

**Acceptance Scenarios**:

1. **Given** an unreachable Jira host, **When** a Jira request is made, **Then** it fails within a bounded time with a message naming the host and the cause, rather than hanging.
2. **Given** invalid or revoked credentials, **When** a Jira request is made, **Then** the failure says authentication was rejected and suggests checking the token, distinctly from "not found".
3. **Given** Jira is unreachable, **When** the full test suite runs, **Then** tests that make no Jira request are unaffected and the run's outcome for them is unchanged.
4. **Given** Jira returns a rate-limit response, **When** a request is made, **Then** the platform respects the advertised retry delay and does not retry immediately in a tight loop.

---

### User Story 4 - Find issues by query (Priority: P3)

An engineer needs every ticket in a release, or every ticket with a given label, rather than one known key — to review test coverage across a batch of work.

**Why this priority**: A multiplier on Story 1 rather than a new capability, and only useful once single-issue reading is proven. Not required for the feature to deliver value.

**Independent Test**: Issue a query for a small known set of issues and confirm the expected keys come back, including across more than one page of results.

**Acceptance Scenarios**:

1. **Given** valid credentials, **When** a query is made for issues matching a condition, **Then** the matching issues are returned with the same fields as a single-issue request.
2. **Given** a query matching more results than one response can carry, **When** it is made, **Then** all matching issues are retrievable rather than silently truncated at the first page.
3. **Given** a malformed query, **When** it is made, **Then** the failure says the query was rejected and includes the reason Jira gave.

---

### Edge Cases

- **Jira settings entirely absent**: An engineer runs a Jira-dependent operation with no Jira configuration at all. Must name the missing settings rather than failing with an authentication error against an empty host.
- **Site URL with or without trailing slash, or with a path**: Both forms must work; a doubled or missing slash must not produce a confusing 404.
- **Token revoked mid-session**: A previously working token starts being rejected. Must report an authentication failure, not a transient network problem.
- **Issue exists but the account cannot see it**: Jira may answer "not found" for a permission problem. The reported message must not assert the issue does not exist when that cannot be distinguished.
- **Rate limiting**: Jira returns a throttling response with a retry delay. Must honour the delay; must not retry indefinitely.
- **Slow or hanging Jira**: Every request must have a bounded timeout, so a stalled Jira cannot stall a test run indefinitely.
- **Proxy or restricted network**: Requests may need to traverse a corporate proxy. The failure must distinguish "blocked by network" from "rejected by Jira".
- **Very large issue**: An issue with a long description or very many fields must not break parsing or flood output.
- **Rich-text description**: Jira descriptions may be structured rather than plain text. The returned text must remain usable for reading and for test authoring.
- **Non-ASCII content**: Issue text in any language must survive the round trip unmangled, on both supported platforms.
- **Jira unreachable during an unrelated test run**: Must not fail tests that never touch Jira.
- **Secrets in failure output**: A failed request must not include the token in its message, traceback, or any captured report artifact.

## Requirements *(mandatory)*

### Functional Requirements

**Integration approach**

- **FR-001**: All Jira access MUST be made by this project directly against Jira's REST API.
- **FR-002**: The project MUST NOT depend on any MCP server, assistant connector, or other external tooling at runtime for Jira access. No Jira capability may require an AI assistant to be present.
- **FR-003**: The integration MUST add zero new third-party dependencies. The already-declared HTTP client dependency MUST be sufficient, per the dependency floor rule of feature 001 (FR-004 there).
- **FR-004**: Jira access MUST be usable both from test code at runtime and from tooling outside a test run, through one shared client so the two paths cannot diverge in behaviour or in failure handling.

**Operations**

- **FR-005**: The platform MUST be able to retrieve a single issue by its key, returning at minimum: key, summary, description, status, and issue type.
- **FR-006**: The platform MUST be able to retrieve multiple issues matching a query, with all matching results retrievable rather than truncated at the first page.
- **FR-007**: The Jira operations in scope are **read-only**: read an issue by key, and query issues. The platform MUST NOT write to Jira in any form - no comments, no transitions, no field edits, no attachments, no issue creation. Adding a write capability requires a specification change for a feature that needs it, not an implementation decision here.

**Configuration and credentials**

- **FR-008**: Jira configuration MUST be read from the local uncommitted environment file through the project's existing validated settings mechanism, consistent with how all other configuration is handled.
- **FR-009**: Every Jira setting MUST be named in the committed example configuration file with a placeholder or non-sensitive value only.
- **FR-010**: The Jira credential MUST be held as a protected value that is masked in any representation of the settings, and MUST NOT appear in any error message, log line, traceback, or captured report artifact.
- **FR-011**: Missing or malformed Jira settings MUST produce a failure naming the specific settings at fault and pointing at the example file, before any network request is attempted.
- **FR-012**: No committed file may contain a real Jira site, account, or token.

**Failure behaviour**

- **FR-013**: Every Jira request MUST have a bounded timeout, so an unresponsive Jira cannot stall a run indefinitely.
- **FR-014**: Failures MUST be distinguishable by cause — configuration missing, authentication rejected, access denied, issue not found, query rejected, rate limited, and network unreachable MUST each report differently.
- **FR-015**: A rate-limit response MUST be handled by honouring the delay Jira advertises, with a bounded number of retries rather than indefinite retrying.
- **FR-016**: Jira being unavailable MUST NOT affect tests that make no Jira request. Jira MUST NOT become a precondition for running the suite.
- **FR-017**: A failure MUST name the Jira site host it was talking to, so a misconfigured site URL is diagnosable without reading code.

**Verification**

- **FR-018**: The integration MUST be testable without network access to a live Jira site, so the suite remains runnable offline and in an unattended environment.
- **FR-019**: The documented setup MUST include a way for an engineer to confirm their Jira credentials work, separate from running the full suite.

**Documentation**

- **FR-020**: Setup documentation MUST state the required Jira settings, how to obtain an API token, and the confirmation step from FR-019.
- **FR-021**: The repository's assistant-facing guidance MUST state that Jira access goes through the project's own REST integration and that no assistant connector may be used for it, so the constraint survives contact with a future contributor.

### Key Entities

- **Jira Settings**: The site URL, account identity, and API token, plus any default project scope. Read from the local environment file, validated before use, never committed.
- **Jira Issue**: The subset of a ticket the platform reads — key, summary, description, status, issue type. Identified uniquely by its key.
- **Issue Query**: A request for a set of issues matching a condition, with pagination so a large result set is fully retrievable.
- **Jira Failure**: The distinguishable outcomes of a failed request — configuration, authentication, authorization, not-found, rejected-query, rate-limited, network. What makes a problem diagnosable from its message alone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer with a valid token can retrieve a known issue's content on the first attempt, using only the documented setup steps and no undocumented step.
- **SC-002**: Zero third-party dependencies are added to the project by this feature.
- **SC-003**: Zero assistant connectors or external tooling are required at runtime for any Jira capability — the platform's Jira features work with no AI assistant present.
- **SC-004**: A review of the committed file set finds zero real Jira sites, accounts, or tokens.
- **SC-005**: Each of the seven failure causes in FR-014 produces a distinct, actionable message; zero of them report a cause that is not theirs.
- **SC-006**: The configured credential appears in zero error messages, log lines, tracebacks, or captured report artifacts, verified by searching a failed run's complete output.
- **SC-007**: Every Jira request completes or fails within its configured timeout; zero requests hang indefinitely.
- **SC-008**: With Jira unreachable, 100% of tests that make no Jira request still produce their normal result.
- **SC-009**: The full suite, including the Jira integration's own tests, passes with no network access to any Jira site.
- **SC-010**: Every Jira setting the platform reads is named in the committed example configuration; zero are discoverable only by reading code.
- **SC-011**: A query returning more results than a single response can carry yields all matching issues; zero silent truncation.

## Assumptions

Reasonable defaults chosen where the description did not specify a detail. Each is a candidate for revision during `/speckit.clarify` or `/speckit.plan`.

- **Atlassian Cloud, token authentication**: The target is Atlassian Cloud (the site observed in this session is a Cloud site), authenticated with an account identity plus an API token. Server/Data Center personal access tokens and interactive OAuth flows are out of scope; both are additions rather than changes if needed later.
- **Credentials are per-engineer, not shared**: Each engineer uses their own token, so Jira permissions and audit trails stay attributable. No service account is assumed.
- **The platform reads Jira and never writes to it** *(resolved: Clarifications, 2026-10-04, superseding the 2026-10-03 decision)*: scope is read and query. Writes were specified first and then deferred once features 004 and 005 both went another way - 004 keeps its audit trail in the repository, 005 rules Jira reporting out of scope. Consequence: the platform has **no destructive capability at all**, so the eight safeguards that existed to contain one are gone with it. A read-scoped API token now suffices, which it could not under the earlier scope.
- **Offline-capable verification**: The integration's own tests use recorded or simulated Jira responses rather than a live site, so SC-009 holds and the suite stays runnable in an unattended environment. Verifying against a real site is a separate, documented, manual step (FR-019).
- **Test generation is not in this feature**: This feature delivers Jira *access*. Turning ticket content into test code is a further feature; what this one must do is make the ticket content available.
- **No caching in this feature**: Issues are fetched when requested. A cache would need an invalidation policy nothing has asked for yet.
- **A read-scoped token is sufficient and preferred**: because the platform never writes, the API token needs only read permission. Jira's own tokens carry the holder's full permissions and cannot be narrowed, so this is advice rather than an enforceable constraint - but it means a leaked token from this project cannot be used through it to change anything.
- **Supported platforms carry over**: Windows and Linux, per feature 001. macOS remains unsupported.
- **Feature 001's rules remain in force**: The dependency floor, the `.env`/`.gitignore` convention with no secret-scanning tooling, configuration through the validated settings model, and function-scoped fixtures with parallel-safe artifact paths all apply here unchanged.
- **No project constitution in force**: `.specify/memory/constitution.md` is still the unfilled template, so this specification is not constrained by project principles. Running `/speckit.constitution` is still outstanding from feature 001.
