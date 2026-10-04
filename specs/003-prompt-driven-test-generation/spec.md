# Feature Specification: Prompt-Driven Test Generation

**Feature Branch**: `003-prompt-driven-test-generation` *(no branch created — `main` is the only branch and nothing is committed yet)*

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "also for an input related to jira like generate tests for TC-345 then app needs to ready the key directly from the prompt which user specifies rather than a one off integration where tests are created for a specific jira only or requirements"

## Clarifications

### Session 2026-10-03

- Q: What does "generate tests" produce? -> A: A **non-runnable test skeleton** - real test files with names, markers and docstrings, bodies skipped as unimplemented.
- Q: What performs the generation? -> A: An **interactive AI assistant** working in the repository. The platform deterministically extracts the key, retrieves the ticket, and hands off structured content; it does not call a language model and adds no model credential. Generation therefore cannot run unattended.
- Q: What happens when artifacts already exist for a ticket? -> A: **Refuse by default**; overwrite only on an explicit operator instruction.
- Correction applied 2026-10-04 (cross-feature analysis finding X5, HIGH): FR-017 now also requires the generating identity and a ticket content digest. Neither is needed by this feature. The identity exists solely so feature 004 can enforce its author-may-not-approve policy, which was unenforceable without it - and the information is only available at generation time, so recording it later is impossible. This was the single item blocking feature 004 from being built.
- Correction applied 2026-10-04 (cross-feature analysis finding X2, HIGH): FR-009 as written forbade any ticket key in a committed file that affects runtime behaviour, which would have outlawed the provenance marker feature 005 requires for attribution and run selection. FR-009 now distinguishes a key that *limits* the platform to one ticket (forbidden) from one that *records an artifact's origin* (required).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for tests by naming a ticket in ordinary language (Priority: P1)

A QA engineer types a request in their own words — "generate tests for TC-345" — and the platform works out which ticket they mean, fetches it, and produces test artifacts for it. The engineer does not look up an issue id, pass a flag in a particular position, or edit any file to say which ticket is in play. They name the ticket the way they would to a colleague.

**Why this priority**: This is the feature. Everything else supports it. On its own it delivers the whole value: say which ticket, get tests for it.

**Independent Test**: Give the platform the phrase "generate tests for TC-345" and confirm it resolves `TC-345`, fetches that ticket, and produces artifacts naming it. Fully testable alone.

**Acceptance Scenarios**:

1. **Given** a request containing exactly one ticket key, **When** it is submitted, **Then** that key is extracted and the matching ticket is fetched.
2. **Given** the same phrasing with a different key, **When** it is submitted, **Then** the new key is used with no change to any file in the repository.
3. **Given** a request where the key appears in a different position ("for TC-345 generate tests", "TC-345: write tests"), **When** it is submitted, **Then** the key is still extracted correctly.
4. **Given** a key written in lower or mixed case ("tc-345"), **When** it is submitted, **Then** it is recognised and normalised to the canonical form.
5. **Given** a ticket URL rather than a bare key, **When** it is submitted, **Then** the key is extracted from the URL.

---

### User Story 2 - Works for any ticket without code changes (Priority: P1)

A team member uses the platform for a ticket in a project nobody anticipated. It works. Nothing in the repository names a particular ticket, project, or requirement, so there is no file to edit and no special case to add — which is the difference between a capability and a one-off script.

**Why this priority**: Equal to Story 1 because it is the actual complaint behind the request. A version of Story 1 that worked only for `TC-345` would satisfy the words and miss the point entirely.

**Independent Test**: Run the platform against several keys from different projects in succession and confirm each works, then search the repository for any hard-coded ticket or project reference and find none.

**Acceptance Scenarios**:

1. **Given** keys from two different projects, **When** each is requested in turn, **Then** both succeed with no configuration change between them.
2. **Given** the repository's committed files, **When** they are searched for ticket keys, **Then** no ticket key appears outside documentation examples and test fixtures.
3. **Given** a newly created ticket the platform has never seen, **When** it is requested, **Then** it is handled identically to any other.

---

### User Story 3 - Understand what happened when the request is unclear (Priority: P2)

An engineer's request has no recognisable ticket key, or names a ticket that does not exist, or mentions several. Rather than guessing, failing silently, or producing tests for the wrong ticket, the platform says what it found and what it needs.

**Why this priority**: The failure modes here are the ones that quietly waste an afternoon — tests generated against a mistyped key look perfectly fine until someone reads them. Guessing wrong is worse than refusing.

**Independent Test**: Submit a request with no key, one with a nonexistent key, and one with several keys; confirm each produces a distinct, actionable response.

**Acceptance Scenarios**:

1. **Given** a request with no recognisable key, **When** it is submitted, **Then** the response says no ticket key was found and shows the form expected.
2. **Given** a key that does not exist or is not visible, **When** it is submitted, **Then** the response distinguishes that from a malformed key.
3. **Given** a request mentioning several keys, **When** it is submitted, **Then** the platform states which keys it found and does not silently act on only one of them.
4. **Given** a request that mentions a key but asks for something other than test generation ("why did TC-345 fail?"), **When** it is submitted, **Then** the platform does not generate tests as a side effect of the key being present.

---

### User Story 4 - Trace a generated artifact back to its ticket (Priority: P2)

Someone reading a generated test months later can tell which ticket it came from, and when — so when the ticket changes, it is obvious which tests need revisiting.

**Why this priority**: Generated artifacts without provenance become unexplained code that nobody dares delete. Recording the source costs almost nothing at generation time and is impossible to reconstruct afterwards.

**Independent Test**: Generate for a ticket, then confirm the artifact records the key, the ticket's summary, and when it was generated.

**Acceptance Scenarios**:

1. **Given** a generated artifact, **When** it is read, **Then** it names the ticket key it derives from.
2. **Given** a generated artifact, **When** it is read, **Then** it records the ticket's summary and the time of generation, so a later reader can tell whether the ticket has moved on.
3. **Given** a ticket that has changed since generation, **When** the artifact is compared with the ticket, **Then** the difference is discoverable without rerunning generation.

---

### Edge Cases

- **No key in the input**: Must say so and show the expected form, not generate something generic.
- **Several keys in one input**: Must report all keys found rather than silently acting on the first.
- **Lower or mixed case key** (`tc-345`, `Tc-345`): Must be recognised and normalised.
- **Key inside a URL** (`.../browse/TC-345`): Must be extracted.
- **Key-like text that is not a key** (`COVID-19`, `ISO-8601`, `UTF-8`, a date like `2026-10`): Must not be treated as a ticket key, or every mention of a standard produces a spurious lookup.
- **Key in a code block or quoted text**: Ambiguous whether it is a request or an example; behaviour must be defined rather than accidental.
- **Nonexistent or invisible ticket**: Must be distinguishable from a malformed key, and must inherit the "not found or not visible" honesty of the Jira integration.
- **Ticket with no acceptance criteria**: A ticket may be a one-line title. Must produce something honest about having little to work from rather than inventing requirements.
- **Ticket whose content is an image or attachment**: The text may be empty while the real requirement is in a screenshot. Must not silently treat that as an empty requirement.
- **Very large ticket**: A long description with many comments must not be truncated silently in a way that drops requirements.
- **Non-ASCII ticket content**: Must survive into the generated artifact unmangled.
- **Artifacts already exist for that ticket**: Regeneration is refused by default, naming the existing artifact and how to overwrite deliberately.
- **Ticket changed since last generation**: Must be discoverable; the platform must not quietly present stale artifacts as current.
- **Jira unavailable or unconfigured**: Must fail with the cause named, inheriting feature 002's behaviour, and must not block tests that make no Jira request.
- **Request intent is not test generation**: A key being present must not by itself trigger generation.

## Requirements *(mandatory)*

### Functional Requirements

**Key extraction from free-form input**

- **FR-001**: The platform MUST accept a free-form natural-language request and extract the ticket key from it, without requiring the key in a fixed position or flag.
- **FR-002**: Key extraction MUST recognise the canonical ticket key form — a project code followed by a separator and a number — independent of surrounding words and punctuation.
- **FR-003**: Key extraction MUST be case-insensitive and MUST normalise the key to its canonical form before use.
- **FR-004**: Key extraction MUST recognise a key embedded in a ticket URL as well as a bare key.
- **FR-005**: Key extraction MUST NOT treat key-like text that is not a ticket key as one. Known non-ticket patterns (standards identifiers, dates, version strings) MUST NOT produce a lookup.
- **FR-006**: When no key is found, the platform MUST report that explicitly and show the expected form, and MUST NOT proceed with generation.
- **FR-007**: When several keys are found, the platform MUST report every key found and MUST NOT silently act on a subset.
- **FR-008**: The platform MUST distinguish a malformed key from a well-formed key that does not exist or is not visible.

**Genericity — the core constraint**

- **FR-009**: No committed file may contain a ticket key, project key, or requirement text that **limits the platform's behaviour** to a particular ticket - no special case, no lookup table, no conditional keyed on a ticket. A ticket key recording the **provenance of a generated artifact** is explicitly permitted and is in fact required, so that a generated test can be traced and selected by its source ticket. The distinction is whether the key constrains the platform (forbidden) or records where an artifact came from (required). Documentation examples and test fixtures remain permitted and MUST NOT affect runtime behaviour.
- **FR-010**: Handling a ticket from a project not previously used MUST require zero changes to committed files and zero configuration changes beyond what the Jira integration already needs.
- **FR-011**: The set of tickets the platform can handle MUST be bounded only by what the configured Jira credentials can read, not by anything enumerated in the repository.

**Generation**

- **FR-012**: Given a resolved ticket, the platform MUST produce a **test skeleton**: real test files containing test function names, the appropriate markers, and docstrings stating the behaviour each test must prove, with bodies that do not yet assert anything. Skeletons MUST be placed according to the repository's existing directory conventions, and MUST be syntactically valid and collectable by the test runner.
- **FR-013**: Generation MUST be split into a deterministic part owned by the platform and an authoring part performed by an AI assistant working interactively in the repository. The platform MUST extract the key, retrieve the ticket, and present its content in a documented structured form for authoring. The platform MUST NOT call a language model itself, MUST NOT require a model credential, and MUST NOT add a dependency for generation.
- **FR-014**: Where a ticket contains little usable requirement text, the platform MUST say so rather than inventing requirements to fill the gap.
- **FR-015**: Where a ticket's requirement content is not text — an image or attachment — the platform MUST state that the text was empty and that non-text content was present, rather than reporting an empty requirement.
- **FR-016**: Generation MUST NOT silently discard ticket content. Where input is truncated for any reason, the artifact MUST record that truncation occurred.

**Provenance and regeneration**

- **FR-017**: Every generated artifact MUST record the ticket key it derives from, that ticket's summary, the time of generation, a digest of the ticket's text content at that time, and **the identity that performed the generation**. The identity is required by feature 004's approver policy (its FR-022), which cannot enforce "the approver may not be the author" without knowing the author - and authorship is only knowable at generation time. The content digest is what makes FR-020's staleness check answerable without regenerating.
- **FR-018**: A generated artifact MUST be distinguishable from a hand-written one, so a reader knows what they are looking at.
- **FR-019**: Regeneration for a ticket that already has artifacts MUST be **refused by default**, naming the existing artifact and the explicit instruction required to overwrite it. Overwriting MUST happen only on that explicit instruction, never as a default or a side effect.
- **FR-020**: Whether a ticket has changed since its artifacts were generated MUST be discoverable without rerunning generation.

**Inherited constraints**

- **FR-021**: Ticket retrieval MUST go through the project's own Jira REST integration (feature 002). No MCP server, assistant connector, or other external tooling may be in the runtime path, and no Jira capability may require an AI assistant to be present.
- **FR-022**: Jira failures MUST surface with the cause named, reusing feature 002's error taxonomy rather than a new one.
- **FR-023**: This feature MUST NOT make Jira a precondition for running the test suite. Tests that make no ticket request MUST be unaffected when Jira is unavailable or unconfigured.
- **FR-024**: Credentials MUST remain in the local uncommitted environment file, read through the existing validated settings model, and MUST NOT appear in any generated artifact, log line, or error message.

**Verification**

- **FR-025**: Key extraction MUST be verifiable without network access, across the full range of input forms and non-key patterns in FR-002 to FR-005.
- **FR-026**: The platform MUST provide a way to see which key it extracted from a given input without performing generation, so extraction can be diagnosed independently.

**Skeleton honesty**

A skipped test that looks like a test is the main hazard of choosing skeletons over a plan: it can read as coverage while proving nothing.

- **FR-027**: A skeleton's unimplemented body MUST cause the test to report as **skipped, with a reason identifying it as an unimplemented generated skeleton**. A skeleton MUST NOT be capable of reporting as passed.
- **FR-028**: The platform MUST provide a way to list every unimplemented skeleton in the repository, with its source ticket, so outstanding generated work cannot accumulate unnoticed.
- **FR-029**: The deterministic part of the platform (FR-013) MUST be runnable unattended and verifiable without network access. The absence of an AI assistant MUST NOT prevent extraction, retrieval, hand-off, or scaffolding from completing.
- **FR-030**: The repository's assistant-facing guidance MUST document the skeleton conventions an assistant must follow - where files go, naming, markers, docstring content, the skip mechanism of FR-027, and the provenance fields of FR-017 - so authoring does not depend on a human explaining them each time.

### Key Entities

- **Generation Request**: The user's free-form input, plus the keys extracted from it and the intent detected. The thing that must be interpreted rather than parsed rigidly.
- **Ticket Key**: A project code and number identifying one ticket. Case-insensitive on input, canonical on use. Distinguishable from key-like text that is not a ticket.
- **Resolved Ticket**: The ticket content retrieved for a key — summary, description, acceptance criteria — supplied by the Jira integration.
- **Generated Artifact**: What generation produces, carrying provenance: source key, ticket summary, generation time, and a marker distinguishing it from hand-written work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A request naming a ticket in ordinary language yields artifacts for that ticket with zero flags, zero file edits, and zero lookups of internal identifiers.
- **SC-002**: Tickets from at least three different projects are handled in succession with zero changes to committed files between them.
- **SC-003**: A search of committed files for ticket keys finds zero occurrences outside documentation examples and test fixtures, and zero occurrences that affect runtime behaviour.
- **SC-004**: Key extraction is correct for 100% of the input forms in FR-002 to FR-004 — bare key, key anywhere in a sentence, any letter case, and key inside a URL.
- **SC-005**: Zero false positives across a documented set of key-like non-keys (standards identifiers, dates, version strings).
- **SC-006**: Each of the four unclear-input cases — no key, malformed key, nonexistent key, several keys — produces a distinct and actionable response; zero of them produce generated artifacts.
- **SC-007**: 100% of generated artifacts record their source ticket key, the ticket summary, and the generation time.
- **SC-008**: 100% of generated artifacts are identifiable as generated without reading their content closely.
- **SC-009**: Zero hand-made changes are lost by a regeneration that the operator did not explicitly ask to overwrite.
- **SC-010**: Whether a ticket has changed since generation is answerable from the artifact and the ticket alone, with zero regenerations needed to find out.
- **SC-011**: The platform's deterministic path - key extraction, ticket retrieval, hand-off, and skeleton scaffolding - runs to completion with zero AI assistants and zero assistant connectors present, and in an unattended environment. Only the authoring step requires an assistant, and no part of the platform requires an MCP server or connector at any time.
- **SC-012**: The full test suite passes with no network access and with no Jira configured; key-extraction verification requires neither.
- **SC-013**: The configured credential appears in zero generated artifacts, log lines, and error messages.
- **SC-014**: Zero generated skeletons report as passed; 100% report as skipped with a reason naming them as unimplemented generated skeletons.
- **SC-015**: Every unimplemented skeleton in the repository is discoverable in one listing, with its source ticket; zero are findable only by reading files.
- **SC-016**: 100% of generated skeletons are syntactically valid and collectable by the test runner on first generation, with zero collection errors.
- **SC-017**: A regeneration attempt against an existing artifact is refused in 100% of cases without an explicit overwrite instruction, and zero hand-made changes are lost.

## Assumptions

Reasonable defaults chosen where the description did not specify a detail. Each is a candidate for revision during `/speckit.clarify` or `/speckit.plan`.

- **Builds on feature 002**: Ticket retrieval is feature 002's Jira client. This feature adds interpretation of the request and generation of artifacts; it does not add a second way to reach Jira. Feature 002 must be implemented first.
- **The example key form is illustrative**: `TC-345` in the request is an example, not a constraint. Any project code is supported (FR-010), and nothing special is done for `TC`.
- **One ticket per generation**: A request naming several keys is reported rather than fanned out. Batch generation across many tickets is a later feature if wanted; reporting (FR-007) is deliberately the behaviour here rather than silently processing one of them.
- **Acceptance criteria may live anywhere in the ticket**: Teams put them in the description, in a custom field, or in comments. The platform reads the ticket's text content broadly rather than assuming one field holds them.
- **Generated artifacts are reviewed before use**: Nothing generated is assumed correct or complete. Artifacts are a starting point a human refines, which is why provenance (FR-017) and the generated marker (FR-018) matter more than polish.
- **Generation is interactive, by deliberate choice** *(resolved: Clarifications, 2026-10-03)*: the platform does the deterministic work and an assistant authors the skeleton bodies. Consequence accepted: **test generation cannot run in CI or unattended**. What can run unattended is everything else - extraction, retrieval, hand-off, scaffolding, and the skeleton listing (FR-029). The trade bought zero new dependencies and zero model credentials. If unattended generation is later required, that is a model-calling feature of its own, not a change to this one.
- **Skeletons are a staging post, not an output**: the chosen deliverable is deliberately not runnable, so FR-027 and FR-028 exist to stop skipped skeletons being mistaken for coverage or quietly accumulating. A skeleton nobody implements is waste, and the listing in FR-028 is what makes that visible.
- **Selectors cannot be inferred from ticket text**: A ticket describes behaviour, not markup. Any browser-driven test derived from a ticket alone cannot know real selectors, so generated UI artifacts will need the recorded-draft workflow from feature 001 to become runnable. This is a property of the problem, not a gap in the design.
- **No caching of ticket content**: Tickets are fetched when requested, consistent with feature 002.
- **Supported platforms carry over**: Windows and Linux. macOS remains unsupported.
- **Feature 001 and 002 rules remain in force**: the dependency floor, `.env`/`.gitignore` with no secret scanning, configuration through the validated settings model, no MCP at runtime, parallel-safe fixtures and artifact paths.
- **Canonical terms** *(normalised 2026-10-04, finding X4)*: a **test design** is the reviewable artifact for a ticket - test names, markers, and the docstrings stating the behaviour each test must prove. A **skeleton** is a test design in its unimplemented state, before bodies exist. **Completed automation** is a test design whose bodies have been written. The three terms name three states of one artifact, not three artifacts.
- **No project constitution in force**: `.specify/memory/constitution.md` is still the unfilled template. This is now the third feature specified without governance gates.
