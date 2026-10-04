---

description: "Task list for Prompt-Driven Test Generation"
---

# Tasks: Prompt-Driven Test Generation

**Input**: Design documents from `/specs/003-prompt-driven-test-generation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Required, not optional. SC-004 ("100% of input forms") and SC-005 ("zero false positives") are exhaustive and negative criteria over input sets — only demonstrable by test, and FR-025 requires extraction verifiable without network access.

**⛔ Upstream**: ticket retrieval needs feature **002** (specified, planned, not implemented). Only three tasks depend on it. Phases 1, 2, 5 and most of 7 are actionable today.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4 from [spec.md](./spec.md)

---

## Phase 1: Setup

- [X] T001 [P] Create `src/ai_qa/generate/__init__.py` exporting the public surface
- [X] T002 Create `src/ai_qa/generate/sentinel.py` containing exactly `SKELETON_SENTINEL = "ai-qa:unimplemented"` — **a module for one constant, deliberately.** Features 004 and 005 both import it; a literal repeated in three places drifts by one character and silently breaks detection in two of them, with no error because "no skeletons found" and "nothing to detect" are indistinguishable (R5)
- [X] T003 [P] Create `tests/generate/` with fixture inputs: the five accepted key forms from SC-004 and the five key-like non-keys from SC-005

**Checkpoint**: `sentinel.py` importable — this is what features 004 and 005 build against.

---

## Phase 2: Foundational

- [X] T004 Implement candidate extraction in `src/ai_qa/generate/keys.py` using pattern `\b[A-Za-z][A-Za-z0-9_]{1,9}-\d{1,6}\b`, matched case-insensitively, normalised to upper case — FR-002, FR-003
- [X] T005 Implement the three structural filters in `src/ai_qa/generate/keys.py`, applied **before any network call**, constraints verbatim from `data-model.md` §1: (1) **denylisted prefix** — `ISO`, `UTF`, `RFC`, `ANSI`, `IEEE`, `SHA`, `AES`, `COVID`, `EN`, `BS`, `SI`, `ASCII`, `HTTP`, `IPV`, `MD`, `CVE`; (2) **year-like** — numeric part is four digits in 1900–2199; (3) **number too long** — numeric part exceeds six digits — FR-005
- [X] T006 Implement URL-form extraction in `src/ai_qa/generate/keys.py`: check the path segment after `/browse/`, then a `selectedIssue` query parameter, **then** fall back to the general pattern. URLs contain other digit-hyphen fragments, so the general pattern alone can select the wrong one — FR-004, R9
- [X] T007 Return `ExtractionResult` with `keys`, `rejected` (each carrying `DENYLISTED_PREFIX` \| `YEAR_LIKE` \| `NUMBER_TOO_LONG`) and `outcome` (`ONE` \| `NONE` \| `MANY`). Rejections are **returned, not discarded** — an engineer whose real key was filtered must be able to see which rule fired — data-model §1
- [X] T008 [P] Implement the static AST scan in `src/ai_qa/generate/listing.py`, finding calls to `pytest.skip` whose argument contains the sentinel and reading the ticket from the module's `ticket` marker. **Static, not run-derived**: skips are evaluated at run time, so `--collect-only` finds nothing, and a run-based listing would be stale and need the application reachable — FR-028, R6
- [X] T009 [P] Add `tests/generate/test_keys.py` asserting all five accepted forms yield `TC-345` and all five non-keys yield **zero** accepted keys with the correct rejection reason — SC-004, SC-005
- [X] T010 [P] Add `tests/generate/test_listing.py` asserting the scan finds skeletons, ignores implemented tests, and requires no network or test run

**Checkpoint**: extraction and listing are pure, tested, and independent of feature 002.

---

## Phase 3: User Story 1 - Ask for tests by naming a ticket (Priority: P1) 🎯 MVP

**Goal**: Name a ticket in ordinary language and get a skeleton for it.

**Independent Test**: `generate "generate tests for TC-345"` produces a file with provenance, the `ticket` marker, and sentinel skip bodies.

- [ ] T011 ⛔BLOCKED (needs **002**) [US1] Fetch the ticket by key via `JiraClient.get_issue` and flatten its description with `adf.to_text` — one call site, per the Integration Points table in `plan.md`
- [X] T012 [US1] Implement the brief in `src/ai_qa/generate/brief.py` with the fields in `data-model.md` §2, written to the scratch area **and** printed to stdout. Making the hand-off a concrete artifact is what lets the deterministic half be tested with no assistant involved — R3
- [X] T013 [US1] Add the two **required** brief warnings: little usable requirement text (FR-014), and empty description with non-text content present — the second must say the text was empty *and* that attachments exist, because reporting an empty requirement would be wrong (FR-015)
- [X] T014 [US1] Implement the file scaffold in `src/ai_qa/generate/scaffold.py`: module docstring with the seven-field provenance header, imports, `pytestmark` with `ticket("<KEY>")`, and the delimiter comment. Everything above the delimiter is **byte-predictable from the ticket**, which is what makes it assertable — R4, FR-017
- [X] T015 [US1] Write the provenance header fields per `contracts/skeleton-format.md`: `generated-by: ai-qa`, `ticket`, `ticket-summary`, `ticket-updated`, `ticket-digest`, `generated-at`, `generated-by-identity`. The last is **not needed by this feature** — feature 004's FR-022 requires the design's author, knowable only at generation time (see Spec Deltas in `plan.md`)
- [X] T016 [US1] Implement the `generate` subcommand in `src/ai_qa/generate/__main__.py` (argparse), orchestrating extract → fetch → brief → scaffold → hand off
- [X] T017 [P] [US1] Add `tests/generate/test_scaffold.py` asserting the scaffold is byte-predictable and that all seven provenance fields are present
- [X] T018 [P] [US1] Add `tests/generate/test_brief.py` asserting brief content and both warning cases, offline

**Checkpoint**: MVP — a ticket becomes a reviewable skeleton.

---

## Phase 4: User Story 2 - Works for any ticket without code changes (Priority: P1)

**Goal**: The genericity the original request was actually about.

**Independent Test**: Three different projects in succession, zero committed-file changes between them.

- [X] T019 [US2] Verify no committed file *limits* behaviour to a ticket: `grep -rnE '\b[A-Z]{2,9}-[0-9]{1,6}\b' src/` finds no lookup table, special case, or conditional keyed on a ticket. Provenance keys in generated tests are **expected and required** — FR-009 was corrected on 2026-10-04 to make that distinction explicit — SC-003
- [ ] T020 [US2] Verify three tickets from three different projects generate successfully with zero configuration changes between them — SC-002
- [X] T021 [P] [US2] Add a test asserting the extraction and scaffold paths contain no project-key allow-list — a new project must work untouched (FR-010, FR-011)

**Checkpoint**: a capability, not a one-off.

---

## Phase 5: User Story 3 - Understand an unclear request (Priority: P2)

**Goal**: No key, several keys, or a nonexistent key each report distinctly and generate nothing.

**Independent Test**: Three inputs, three distinct exit codes, zero files created.

- [X] T022 [US3] On `outcome == NONE`, report that no key was found, show the expected form, and **do not proceed** — exit 3 (FR-006)
- [X] T023 [US3] On `outcome == MANY`, report **every** key found and generate nothing — exit 4. Acting on the first of three looks like success and leaves two tickets silently uncovered (FR-007, R10)
- [ ] T024 ⛔BLOCKED (needs **002**) [US3] Distinguish *malformed* (pattern or filters rejected it; never reaches Jira) from *not found or not visible* (well-formed, failed to resolve) — exit 3 versus exit 5, reusing feature 002's wording (FR-008)
- [X] T025 [P] [US3] Add tests asserting each of the four unclear-input cases produces its own exit code and **zero** generated artifacts — SC-006
- [X] T026 [P] [US3] Add a test asserting `extract "why did TC-345 fail?"` reports the key and generates nothing — there is no code path from "a key appeared in text" to "tests were created", which is how the intent edge case is met with no classification at all (R2)

**Checkpoint**: unclear input is diagnosable, never guessed at.

---

## Phase 6: User Story 4 - Trace an artifact to its ticket (Priority: P2)

**Goal**: Provenance on every generated artifact, and ticket change discoverable without regenerating.

**Independent Test**: Read a generated file and tell which ticket, when, and whether the ticket has moved on.

- [X] T027 [US4] Implement regeneration refusal in `src/ai_qa/generate/__main__.py`: if the target file exists, refuse with exit 6, naming the file and the `--force` flag. Overwriting only on that flag — FR-019, SC-009, R7
- [ ] T028 [US4] Implement `--check-stale` on `skeletons`, comparing the stored `ticket-digest` against a fresh digest of the ticket's text. **Compare the digest, not `ticket-updated`** — Jira bumps `updated` for a label or sprint change that never touches the text, so a timestamp comparison would cry stale constantly and teach everyone to ignore it — FR-020, SC-010, R8
- [X] T029 [P] [US4] Add a test asserting `generated-by: ai-qa` makes a generated file distinguishable from a hand-written one — FR-018, SC-008
- [X] T030 [P] [US4] Add a test asserting regeneration refuses by default and preserves hand-made edits — SC-009

**Checkpoint**: all four stories functional.

---

## Phase 7: Polish & Cross-Cutting

- [X] T031 Implement the `extract` subcommand (no generation, no network) — the command FR-026 requires so extraction is diagnosable independently
- [X] T032 Implement the `skeletons` subcommand surfacing the T008 listing — FR-028
- [X] T033 Implement the exit-code mapping from `contracts/commands.md`: 0, 2 config, 3 no key, 4 many keys, 5 not found, 6 file exists, 7 Jira unavailable
- [X] T034 Document the skeleton conventions in `CLAUDE.md`: where files go, naming, markers, the sentinel mechanism, the provenance fields, and the seven-step refactoring checklist for a recorded draft — FR-030
- [X] T035 [P] Document the generate workflow in `README.md`: `extract`, `generate`, `skeletons`, and that regeneration refuses by default
- [X] T036 [P] Verify SC-012: the full suite passes with no network and no Jira configured
- [X] T037 [P] Verify SC-013: no credential appears in any generated artifact, brief, or error message
- [X] T038 [P] Verify SC-014 and FR-027: every generated test reports as **skipped** with the sentinel reason and **zero** report as passed — the reason `skip()` is used in the body rather than `xfail`, which can report `xpass`

- [X] T039 Record truncation in the provenance header whenever ticket content is clipped for any reason, and add a test over an oversized ticket asserting the artifact says so. **Generation must never silently discard requirement text** - a clipped ticket that reads as complete is the worst outcome here, because the missing requirement leaves no trace — FR-016
- [X] T040 [P] Add a test asserting every generated skeleton is syntactically valid and collectable: run `pytest --collect-only` after generation and require zero collection errors. A generated file with a syntax error breaks collection for the **entire** suite, not just its own tests — SC-016, FR-012
- [X] T041 [P] Close the traceability gap for the requirements no single task owns, verifying each by inspection: **FR-012** (skeleton shape, delivered by T014 plus authoring), **FR-013** (deterministic/authoring split, T012 and T014), **FR-021** (retrieval via feature 002, no MCP), **FR-023** (Jira is not a precondition for the suite), **FR-024** (credentials absent from artifacts), **FR-029** (deterministic part runs unattended), **SC-015** (one listing of all skeletons), **SC-017** (regeneration refused by default)

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies. T002 unblocks features 004 and 005 and should land first
- **Phase 2** depends on Phase 1. T004 → T005 → T006 → T007 all edit `keys.py`, so **sequential**
- **Phase 3 (US1)** depends on Phase 2; T011 blocked on 002. **MVP**
- **Phase 4 (US2)** is verification over Phase 3's output
- **Phase 5 (US3)** depends on T007's `outcome`; T024 blocked on 002
- **Phase 6 (US4)** depends on T015's provenance
- **Phase 7** depends on the phases it exposes

### Shared write points (not parallelizable)

`src/ai_qa/generate/keys.py` — T004–T007. `src/ai_qa/generate/__main__.py` — T016, T022, T023, T027, T028, T031, T032, T033. Neither group carries `[P]`.

---

## Parallel Execution Examples

- **Phase 1**: T001, T003 together
- **Phase 2**: T008 runs parallel to the `keys.py` chain; then T009 and T010 together
- **Phase 6**: T029, T030 together
- **Phase 7**: T035–T038 together

---

## Implementation Strategy

**Land T002 first, before anything else.** The sentinel constant is what features 004 and 005 import; shipping it early unblocks their foundational phases even while this feature is in progress.

**MVP = Phase 1 + Phase 2 + Phase 3 (T001–T018)**, of which only T011 needs feature 002. Extraction, filters, listing, brief and scaffold are all buildable and testable today.

**Then Phase 5**, which is pure exit-code and reporting behaviour over Phase 2's output.

**Three traps worth naming:**

1. **T005 is the whole point of FR-005.** The obvious implementation of key extraction is a bare regex, and a bare regex accepts `ISO-8601`, `COVID-19`, `UTF-8` and `CVE-2026-1234`. Without the filters, every mention of a standard in a prompt fetches a ticket.
2. **T002 must be imported, never copied.** A literal sentinel in three features breaks silently.
3. **T028 must compare the digest, not the timestamp.** Jira's `updated` changes for things that do not touch the text.
