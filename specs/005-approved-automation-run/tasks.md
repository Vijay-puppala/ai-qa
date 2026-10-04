---

description: "Task list for Approved Automation Run & Reporting"
---

# Tasks: Approved Automation Run & Reporting

**Input**: Design documents from `/specs/005-approved-automation-run/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Test tasks are required, not optional. SC-022 and SC-023 are negative criteria — *zero* repairs on ineligible failures, *zero* repairs changing assertions — and a negative is only demonstrable by test. The classifier and the assertion digest are the feature's safety boundary; untested, they are an intention.

**⛔ Upstream dependency**: this feature sits on 002, 003 and 004. **None is implemented, and 003 and 004 have no plan.** Tasks needing them are marked `⛔BLOCKED` with the feature named. Phases 1, 2, 4 and 7 are fully actionable today.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 from [spec.md](./spec.md)

## Path Conventions

New code in `src/ai_qa/report/` and `src/ai_qa/automation/`, tests in `tests/report/`. Every command runs through `uv run`.

---

## Phase 1: Setup

- [X] T001 Add `ticket` to the registered markers in `pyproject.toml` under `[tool.pytest.ini_options]` — `--strict-markers` is on
- [X] T002 [P] Create `src/ai_qa/report/__init__.py` (read-side projection package — no authority to change anything)
- [X] T003 [P] Create `src/ai_qa/automation/__init__.py` (the package holding the two components that *can* change things)
- [X] T004 [P] Create `tests/report/fixtures/` with canned Allure result files matching the **verified** schema — keys `description, fullName, historyId, labels, name, parameters, start, status, stop, testCaseId, titlePath, uuid` — including at least one `status: failed` record carrying `statusDetails.message` and `statusDetails.trace`

**Checkpoint**: packages importable; fixtures match the real plugin's output shape.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites. Everything here is actionable now and independent of 002–004.

- [X] T005 Add a `pytest_runtest_setup` (or equivalent) hook to `tests/conftest.py` that reads the `ticket` marker's argument and writes an Allure label `{name: "ticket", value: "<KEY>"}` — **this is mandatory, not a convenience.** Verified empirically: `@pytest.mark.ticket("TC-345")` produces **no label at all**, because `allure-pytest` maps bare markers to `tag` labels but drops markers carrying arguments. Without this hook FR-021, FR-023 and SC-008 are unachievable and **nothing looks broken** — reports render correctly with every test unattributed (R2, data-model §1.1)
- [X] T006 Add a `--ticket` option and a collection-time filter to `tests/conftest.py`, selecting by the `ticket` marker's **argument**. Not `-m`, which evaluates marker names and so cannot discriminate by key; not `-k`, which matches names (R4)
- [X] T007 [P] Implement the pure failure classifier in `src/ai_qa/automation/classify.py` returning `ELIGIBLE` or `ESCALATE`, keyed **only on exception type** — never on message text. `ELIGIBLE` (closed list, verbatim from FR-036): collection and import errors, `SyntaxError`, pytest fixture lookup errors, unregistered-marker errors, and `TypeError`/`AttributeError` from test-framework API misuse. **Default is `ESCALATE`, unconditionally** — a failure mode introduced by a future dependency upgrade must land on the safe side without anyone remembering to classify it (FR-036, FR-038)
- [X] T008 [P] Implement the assertion digest in `src/ai_qa/automation/digest.py`: parse the test file, locate the test function, collect in source order every `assert` statement's normalised source plus every recognised assertion helper call (`expect(...)`, `pytest.raises(...)`), strip comments, collapse whitespace, hash. Formatting, comments, variable names outside assertions, imports, fixtures and setup code may change freely; assertion text may not (FR-039, R7)
- [ ] T009 [P] Implement the append-only repair log in `src/ai_qa/automation/repairlog.py` writing JSON Lines to `reports/repair-log.jsonl`, keyed by `test_full_name`, with fields per `data-model.md` §2: `attempt`, `timestamp`, `verdict`, `failure_type`, `changed`, `digest_before`, `digest_after`, `outcome`, `notes`. `outcome` is one of `repaired`, `refused_assertion_changed`, `escalated`, `budget_exhausted`, `still_failing`. Every string passes through feature 002's `redact()` — FR-040
- [X] T010 Implement the result projection in `src/ai_qa/report/read.py` building `TestResult` per `data-model.md` §1, including `failure_message` from `statusDetails.message` and `failure_trace` from `statusDetails.trace`, `ticket` from the `ticket` label, and `evidence_paths` derived from the sanitised node ID under `reports/artifacts/`
- [X] T011 Implement `RunSummary` in `src/ai_qa/report/summary.py` with `scope` **mandatory, not optional** — SC-021 requires every report to state its scope, and the only way to guarantee that is to make the field impossible to omit. Include `collected`, where **zero is a failure, not a pass**
- [X] T012 Implement the renderer in `src/ai_qa/report/render.py` producing one self-contained `reports/report.html` with inline CSS and **zero external requests** — no CDN, no web font, no analytics. Standard library only; a templating engine is a dependency FR-031 forbids
- [X] T013 [P] Add `tests/report/test_classify.py` covering every `ELIGIBLE` and `ESCALATE` class from T007 **plus an exception type the classifier has never seen**, asserting it escalates — SC-022's fail-closed property
- [X] T014 [P] Add `tests/report/test_digest.py` asserting the digest is unchanged by reformatting, added comments, renaming a non-asserted variable and changed setup code; and changed by altering, weakening or removing any assertion — SC-023
- [X] T015 [P] Add `tests/report/test_read.py` asserting the projection against the T004 fixtures, **including a test that the `ticket` label is present on a marked test** — the regression guard for T005's silent failure mode
- [X] T016 [P] Add `tests/report/test_render.py` asserting zero external URLs in the output, the scope header present and first, and the "not an Allure report" provenance line present — FR-032, SC-018

**Checkpoint**: the safety boundary and the report pipeline are built and tested, with no upstream feature required.

---

## Phase 3: User Story 1 - Complete an approved design (Priority: P1) ⛔ BLOCKED

**Goal**: Turn an approved design's unimplemented tests into runnable automation.

**Independent Test**: With an approved design, run completion and confirm the tests stop being reported as unimplemented skeletons.

- [ ] T017 ⛔BLOCKED (needs **004**) [US1] Implement the approval gate check in `src/ai_qa/automation/complete.py`, delegating to feature 004's gate rather than reimplementing it, and refusing when pending, rejected, or stale — distinguishing all three — FR-002, FR-003
- [ ] T018 ⛔BLOCKED (needs **003**) [US1] Implement unimplemented-skeleton detection in `src/ai_qa/automation/complete.py` using feature 003's skip sentinel — do not invent a second mechanism (R5)
- [ ] T019 ⛔BLOCKED (needs **002**) [US1] Retrieve ticket content for authoring context via feature 002's `JiraClient` — one call site, per the Integration Points table in `plan.md`
- [ ] T020 [US1] Implement the CI guard in `src/ai_qa/automation/complete.py`: refuse when `CI` or a known vendor variable is set, naming the reason. Two layers, because relying on "the pipeline does not call this" puts the guarantee in a file this repository does not control — FR-008, R10
- [ ] T021 [US1] Ensure completion **never overwrites an existing test body**; only tests still carrying the skeleton sentinel may be completed — FR-004, SC-002
- [ ] T022 ⛔BLOCKED (needs **004**) [US1] Record the source ticket and the authorising approval on completed automation, as `ticket` and `approval` markers/labels — FR-005, SC-004

**Checkpoint**: completion is gated, non-destructive, and impossible in a pipeline.

---

## Phase 4: User Story 2 - Run and get a report (Priority: P1)

**Goal**: Run tests and produce a readable report. Fully actionable today.

**Independent Test**: Run the suite, generate the report, open it in a browser with networking disabled.

- [ ] T023 [US2] Implement the `run` subcommand in `src/ai_qa/automation/__main__.py` with `--ticket` and `--full-suite`, using standard-library `argparse` — FR-009
- [ ] T024 [US2] Treat runner exit code **5 (no tests collected) as a failure**, never a pass. A mistyped `--ticket` must not produce a confident green run — FR-011, SC-009, R8
- [ ] T025 [US2] Report inability to reach the application under test **distinctly from a test failure** — a wrong `BASE_URL` is not a product defect — FR-012, SC-010
- [ ] T026 [US2] Implement the `report` subcommand writing `reports/report.html`, joining the repair log by `full_name`, and reporting empty result data **as empty rather than as a clean run** — FR-014, FR-017
- [X] T027 [P] [US2] Render the per-test detail required by `contracts/report-format.md`: name, status, duration, failure message, collapsed traceback, and relative evidence links into `reports/artifacts/` — FR-016, SC-006
- [X] T028 [P] [US2] Render the evidence note stating that `reports/artifacts/` must accompany the report for links to resolve — the honest consequence of linking rather than embedding — FR-034
- [X] T029 [P] [US2] Pass every string entering the report through feature 002's `redact()` — the report is the artifact most likely to leave the team, and a traceback is where a credential surfaces — FR-019, SC-011

**Checkpoint**: a run produces a shareable report with no new prerequisite.

---

## Phase 5: User Story 3 - Trace back to ticket and approval (Priority: P2)

**Goal**: A report says which ticket and which approval its tests came from.

**Independent Test**: Run a ticket's tests; confirm the report groups them under that ticket.

- [X] T030 [US3] Group results by the `ticket` label in `src/ai_qa/report/summary.py`, with unlabelled tests in a **visible `Unattributed` group** — hiding them would hide a traceability gap, and a large `Unattributed` group is the first symptom of T005's hook being broken — FR-021, FR-023, SC-008
- [ ] T031 ⛔BLOCKED (needs **004**) [US3] Render the authorising approval identifier per test from the `approval` label — FR-022
- [X] T032 [P] [US3] Add a test asserting results from several tickets in one run remain attributable per ticket — SC-008
- [X] T033 [P] [US3] Add a test asserting an unlabelled test appears in `Unattributed` rather than being dropped

**Checkpoint**: ticket-to-test traceability reaches the report.

---

## Phase 6: User Story 4 - Product bug vs broken test (Priority: P2)

**Goal**: Repair mechanical faults only; never make a failing assertion pass.

**Independent Test**: Confirm an assertion failure is never repaired and a fixture fault is.

- [ ] T034 [US4] Implement the `repair` subcommand in `src/ai_qa/automation/__main__.py` with `--max-attempts` and `--dry-run`, classifying each failure via T007 and handing off only `ELIGIBLE` ones — FR-026, FR-036
- [ ] T035 [US4] Enforce the digest guard around every repair: compare T008's digest before and after, and **refuse** any repair whose digest changed, recording `refused_assertion_changed` and escalating — FR-039, SC-023
- [ ] T036 [US4] Bound attempts by `--max-attempts`; exhaustion stops and reports what was attempted, never continuing indefinitely — FR-040
- [ ] T037 [US4] Implement the CI guard on `repair`, refusing when a CI environment is detected — FR-042, SC-025
- [ ] T038 [US4] Render **repair disclosure** per test in the report, visually distinct from an ordinary pass. A test passing because a tool modified it is a materially different claim from one passing as authored, and a reader skimming for green must not miss it — FR-041, SC-024
- [ ] T039 [P] [US4] Add a test asserting a Jira/report write failure **does not fail an otherwise passing test** — reporting is a side effect of a run, not a verdict on the software under test — FR-028
- [X] T040 [P] [US4] Add a test asserting a repair attempt on an `AssertionError`, an element-not-found and a timeout is **never made** — SC-022
- [ ] T041 [P] [US4] Add a test asserting a flaky result is surfaced rather than averaged away, and that one pass is not recorded as proof of correctness — FR-027

**Checkpoint**: the platform can fix broken tests but cannot hide broken products.

---

## Phase 7: User Story 5 - Run only what is relevant (Priority: P3)

**Goal**: Scoped runs for fast feedback, with regression explicit.

**Independent Test**: Run one ticket's tests; confirm others do not execute and the report states the narrow scope.

- [ ] T042 [US5] Make the default scope after completion the **completed ticket's tests only**, and **offer** the full-suite run as an explicit follow-up rather than starting it — FR-010, SC-020
- [ ] T043 [P] [US5] Add a test asserting a ticket-scoped run executes only that ticket's tests
- [ ] T044 [P] [US5] Add a test asserting the report's scope header names the ticket and test count for a scoped run — SC-021

**Checkpoint**: all five stories functional (US1 and parts of US3 pending upstream).

---

## Phase 8: Polish & Cross-Cutting

- [ ] T045 Implement the `skeletons` subcommand listing every unimplemented skeleton with its source ticket (read-only, safe anywhere) — FR-007
- [ ] T046 Implement the exit-code mapping from `contracts/commands.md`: 0 success, 1 tests failed, 2 config, 3 gate refusal, 4 CI refusal, 5 **zero collected**, 6 digest refused, 7 budget exhausted, 8 report failure. Code 6 is the guard working, not a malfunction
- [ ] T047 [P] Document the `complete` / `run` / `report` / `repair` / `skeletons` commands in `README.md`, including the report's limitations and the optional Allure CLI path — FR-033
- [ ] T048 [P] Add the repair boundary and the `ticket` marker convention to `CLAUDE.md` — what may be repaired, what may never be, and that assertions are off limits
- [X] T049 [P] Verify SC-011 by running a failing test with a sentinel token and searching the full run output **and** `reports/report.html` for it — expect zero
- [X] T050 [P] Verify SC-018 by opening the report with networking disabled, and `grep -c 'https\?://cdn\|fonts\|unpkg\|jsdelivr' reports/report.html` — expect 0
- [ ] T051 [P] Verify SC-014: report generation for 1,000 tests completes under 60 seconds with zero truncation
- [X] T052 [P] Verify SC-017 by searching `tests/` for any live hostname — expect none outside fixtures and examples

- [ ] T053 [P] Add a test asserting the platform **states evidence without claiming a cause** for a failing test: the output must not assert whether the application or the test is at fault. This is the guardrail that stops the platform editorialising about a failure it cannot diagnose, and without it the natural implementation drift is towards a confident wrong answer — FR-025, FR-024
- [ ] T054 [P] Verify that running honours the repository's existing execution rules: serial by default, every fixture function-scoped except the two documented exceptions, and per-test artifact paths. Reuse feature 001's parallel-readiness review rather than writing a second one — FR-013
- [X] T055 [P] Verify SC-012: `git status --porcelain` lists zero generated files after a run and a report - no `reports/`, no repair log, no rendered HTML appears as a commit candidate — SC-012, FR-020
- [ ] T056 [P] Close the traceability gap for the requirements no single task owns, verifying each by inspection: **FR-018** (no silent truncation for a large run, measured by T051), **FR-029** (no MCP or connector required to run tests or emit result data), **FR-030** (any new dependency or prerequisite justified - this feature adds none), **FR-037** (the excluded repair classes, enforced by T007 and tested by T040), **SC-019** (zero success criteria depend on the Allure CLI)

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies
- **Phase 2** depends on Phase 1. **Blocks all user stories.** T010 depends on T005's label contract; T012 depends on T010 and T011
- **Phase 3 (US1)** ⛔ depends on 002, 003 and 004. T020 and T021 are actionable now
- **Phase 4 (US2)** depends on Phase 2 only — **actionable today**
- **Phase 5 (US3)** depends on T005 and T030; T031 blocked on 004
- **Phase 6 (US4)** depends on T007, T008, T009 — **actionable today**
- **Phase 7 (US5)** depends on T006 — **actionable today**
- **Phase 8** depends on the phases it documents; T045 needs 003's sentinel

### Shared write points (not parallelizable)

`tests/conftest.py` — T005, T006. `src/ai_qa/automation/__main__.py` — T023, T026, T034, T045, T046. `src/ai_qa/report/render.py` — T012, T027, T028, T029, T038. None carry `[P]` against each other.

---

## Parallel Execution Examples

- **Phase 1**: T002, T003, T004 are different files — run together
- **Phase 2**: T007, T008, T009 are three independent pure modules — run together; then T013, T014, T015, T016 as four independent test files
- **Phase 6**: T039, T040, T041 are independent tests — run together
- **Phase 8**: T047–T052 are independent documentation and verification — run together

---

## Implementation Strategy

**Build Phase 1 + Phase 2 first (T001–T016).** This is the whole safety boundary — classifier, digest, repair log — plus the report pipeline, and **none of it needs 002, 003 or 004.** It is 16 tasks of genuinely independent value, and it front-loads the two components most worth getting right.

**Then Phase 4 (T023–T029)**: running and reporting works against the existing suite today. Combined with Phase 2 this delivers a usable report for feature 001's tests, with no upstream dependency at all.

**Then Phase 6 and Phase 7**, both actionable. **Phase 3 last**, when 002, 003 and 004 exist.

**Three traps worth naming:**

1. **T005 is the silent one.** Without the ticket-label hook, every report renders perfectly and attributes nothing. Bare markers *do* become `tag` labels, which makes the wrong assumption easy. T015 exists specifically to catch it.
2. **T007's default must be `ESCALATE`.** An allowlist with a permissive default is not an allowlist. Verify with the unknown-exception case in T013.
3. **T011's `scope` must be non-optional.** If it can be omitted it eventually will be, and a ticket-scoped green will be read as suite-wide confidence.
