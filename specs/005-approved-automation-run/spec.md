# Feature Specification: Approved Automation Run & Reporting

**Feature Branch**: `005-approved-automation-run` *(no branch created — `main` is the only branch and nothing is committed yet)*

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "once approved generate automation tests and run them with allure reports"

## Scope Boundary

This specification deliberately does **not** re-specify things the earlier features already cover. What is new here is the step between approval and a report:

| Already specified elsewhere | Where |
|---|---|
| Test designs (skeletons) produced from a ticket | Feature 003 |
| Approval required before automation is written | Feature 004 |
| Result data emitted by a run with no extra flags | Feature 001, FR-024 — **implemented** |
| Pipelines run existing scripts only, never generate | Feature 004, FR-023/FR-024 |

**New in this feature**: turning an approved design into runnable automation, running it, and producing a report that someone who did not run it can read.

## Clarifications

### Session 2026-10-04

- Q: How is a viewable report produced, given the project's one-prerequisite constraint? -> A: **No external renderer.** The platform generates a self-contained report from the result data using only the existing toolchain - zero additional prerequisites. The Allure command-line tool stays documented as an optional path for anyone who wants the full Allure report.
  - Allure Report 3 was considered and rejected: it removes the Java requirement but is npm-only and requires Node.js, which features 001 and 002 deliberately excluded (001 FR-013, SC-011; 002 command contract). It would have swapped one forbidden prerequisite for another.
- Q: What is the default scope of the run immediately after completion? -> A: **The completed ticket's tests first**, with the full suite offered as an explicit follow-up rather than run automatically.
- Q: What happens when newly completed automation fails on its first run? -> A: **Repair only clearly test-side mechanical errors, never assertion failures.** Anything ambiguous is escalated to a human.
- Correction applied 2026-10-04 (cross-feature analysis finding X3, MEDIUM): FR-039 justified its rule by saying an altered assertion changes "what was approved". That reason was false - a skeleton contains no assertions, so none was ever approved. The rule stands; its stated reason now refers to the docstring's claimed behaviour, which is what the approval actually covers. The wrong reason mattered because it is what someone would reason from when judging an edge case.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn an approved design into working automation (Priority: P1)

An engineer has an approved test design whose tests are still unimplemented. They ask the platform to complete them, and the skeletons become real tests that exercise the application. Nothing is implemented for a design that is not approved — the gate from feature 004 holds.

**Why this priority**: This is the step the platform is currently missing. Feature 003 produces designs, feature 004 approves them, and nothing yet turns an approved design into something that runs.

**Independent Test**: Take an approved design with unimplemented tests, run the completion step, and confirm the tests are no longer reported as unimplemented skeletons.

**Acceptance Scenarios**:

1. **Given** an approved design with unimplemented tests, **When** completion is requested, **Then** the tests gain real bodies and stop being reported as unimplemented skeletons.
2. **Given** a design that is pending, rejected, or covered by a stale approval, **When** completion is requested, **Then** it is refused by the approval gate with the reason named.
3. **Given** a design where some tests are already implemented, **When** completion is requested, **Then** only the unimplemented ones are completed and the already-implemented ones are left untouched.
4. **Given** completed automation, **When** it is inspected, **Then** it records the ticket and the approval that authorised it.

---

### User Story 2 - Run the automation and get a report (Priority: P1)

The engineer runs the newly completed tests and gets a report of what passed, what failed, and why — not just terminal output that scrolls away.

**Why this priority**: Equal to Story 1. Automation that has never been run is not known to work, and a run whose outcome cannot be read afterwards does not help anyone.

**Independent Test**: Run the completed tests and confirm a readable report is produced covering every test in the run.

**Acceptance Scenarios**:

1. **Given** completed automation, **When** it is run, **Then** every test's outcome appears in the report.
2. **Given** a failing test, **When** the report is read, **Then** the failure reason and the captured evidence for it are reachable from the report.
3. **Given** a run, **When** the report is produced, **Then** no extra flags beyond the documented command are needed to get result data.
4. **Given** a report, **When** it is opened by someone who did not run the tests, **Then** it is readable without access to the original terminal session and without installing any tool beyond a standard web browser or text viewer.

---

### User Story 3 - Trace a run back to its ticket and approval (Priority: P2)

Someone reading a report can tell which ticket the tests came from and which approval authorised them, so a result can be reported back to the people who asked for the work.

**Why this priority**: Without this, a report is a list of test names with no connection to the request that produced them, and the ticket-to-test traceability built up across features 003 and 004 stops at the point it becomes most useful.

**Independent Test**: Complete and run automation for a known ticket, then confirm the report identifies that ticket and the approval.

**Acceptance Scenarios**:

1. **Given** a run of tests derived from a ticket, **When** the report is read, **Then** each such test is attributable to its source ticket.
2. **Given** a report, **When** it is read, **Then** the approval that authorised the automation is identifiable.
3. **Given** tests from several tickets in one run, **When** the report is read, **Then** results can be grouped by ticket.

---

### User Story 4 - Tell a product bug apart from a broken test (Priority: P2)

A newly completed test fails on its first run. The engineer can tell whether the application is wrong or the test is wrong, without re-reading the ticket and the test side by side.

**Why this priority**: The first run of new automation fails often, and for both reasons. If the platform treats every first-run failure as "the test needs fixing", real defects get papered over — which is the worst possible failure for a QA platform.

**Independent Test**: Complete a test against a known-good application path and a known-broken one, and confirm the report's evidence distinguishes the two cases.

**Acceptance Scenarios**:

1. **Given** a newly completed test that fails, **When** the report is read, **Then** the evidence captured is sufficient to judge whether the application or the test is at fault.
2. **Given** a failing test, **When** the outcome is recorded, **Then** the platform does not assert which of the two causes applies.
3. **Given** a first run with failures, **When** the step completes, **Then** failures are reported as outcomes rather than treated as an error in the completion step itself.
4. **Given** a test failing on an assertion, **When** the platform considers repair, **Then** no repair is attempted and the failure is escalated for a human to judge.

---

### User Story 5 - Run only what is relevant (Priority: P3)

Having completed automation for one ticket, the engineer runs just those tests to get fast feedback, rather than waiting for the whole suite.

**Why this priority**: A convenience that becomes important as the suite grows, but the platform is useful without it — the full suite can always be run.

**Independent Test**: Complete automation for one ticket and run only that ticket's tests, confirming the others are not executed.

**Acceptance Scenarios**:

1. **Given** completed automation for a ticket, **When** a run is requested for that ticket, **Then** only its tests execute.
2. **Given** a run scoped to one ticket, **When** the report is produced, **Then** it states its scope explicitly and does not imply anything about tests it did not execute.
3. **Given** a completed ticket, **When** the run finishes, **Then** a full-suite run is offered as an explicit next step rather than started automatically.

---

### Edge Cases

- **Design not approved, or approval stale**: Completion must be refused by feature 004's gate with the specific state named; this feature must not provide a route around it.
- **Design partially implemented**: Only unimplemented tests are completed; existing bodies must not be overwritten.
- **New test fails on first run**: Must be reported as an outcome, not as a failure of the completion step.
- **New test is flaky**: Passing once must not be treated as proof the automation is correct; a flaky result must be visible rather than averaged away.
- **Application under test unreachable**: Must be distinguishable from a test failure — a wrong `BASE_URL` is not a product defect.
- **Report viewer not installed**: Result data must still be produced and the run must still succeed.
- **No result data produced**: An empty report must be reported as such, not presented as a clean run.
- **Run collected zero tests**: Must be treated as a failure condition, not a pass — a run that tested nothing is not a green run.
- **Tests from several tickets in one run**: Results must remain attributable per ticket.
- **Parallel execution enabled**: Report and evidence must remain correct and uncollided, honouring feature 001's parallel-safety rules.
- **Very large run**: Report production must not become the slowest part of the workflow, and must not silently truncate results.
- **Non-ASCII content in test names or failure messages**: Must survive into the report unmangled.
- **Pipeline context**: Completion must not run in a pipeline — feature 004 forbids tests appearing for the first time during a pipeline run. Only running and reporting may happen there.
- **Credentials in reports**: No credential may appear in a report, an attachment, or captured evidence.
- **Failure class cannot be determined**: Must be treated as ineligible for repair. Ambiguity resolves towards escalation, never towards editing the test.
- **An element is not found because the feature is not built yet**: Indistinguishable from a wrong selector, so element-not-found is deliberately ineligible for repair - repairing it would erase an unimplemented-feature finding.
- **A repair would weaken or remove an assertion**: Must be refused and escalated. That is a change to what was approved, not a repair.
- **Repair succeeds but the test still fails**: Both facts must be reported - the mechanical fault was fixed and the test still does not pass.
- **Repair budget exhausted**: Must stop and report what was attempted, never continue indefinitely.
- **Ticket-scoped run passes while the wider suite is broken**: The report must state its scope so a narrow pass is not read as suite-wide confidence.

## Requirements *(mandatory)*

### Functional Requirements

**Completing approved automation**

- **FR-001**: The platform MUST provide a step that turns an approved test design's unimplemented tests into runnable automation.
- **FR-002**: Completion MUST be refused unless a currently-applicable approval exists for the design, enforced by feature 004's gate rather than by a separate check in this feature.
- **FR-003**: A refusal MUST name whether the design is pending, rejected, or covered by a stale approval.
- **FR-004**: Completion MUST NOT overwrite test bodies that already exist. Only unimplemented tests may be completed.
- **FR-005**: Completed automation MUST record its source ticket and the approval that authorised it.
- **FR-006**: Completed automation MUST follow the repository's existing test conventions — placement, naming, markers, fixture rules, and artifact path rules — rather than introducing new ones.
- **FR-007**: After completion, the affected tests MUST no longer be reported as unimplemented skeletons.
- **FR-008**: Completion MUST NOT occur during a pipeline run, consistent with the prohibition on tests appearing for the first time in a pipeline.

**Running**

- **FR-009**: The platform MUST be able to run the tests belonging to a given ticket, and MUST be able to run the full suite.
- **FR-010**: The default scope of a run immediately after completion MUST be the completed ticket's tests only. A full-suite run MUST be offered as an explicit, documented follow-up step and MUST NOT be started automatically.
- **FR-011**: A run that collects zero tests MUST be reported as a failure condition, not as a successful run.
- **FR-012**: Inability to reach the application under test MUST be reported distinctly from a test failure.
- **FR-013**: Running MUST honour the repository's existing execution rules — serial by default, parallel-safe fixtures, per-test artifact paths.

**Reporting**

- **FR-014**: A run MUST produce structured result data covering every executed test, with no flags beyond the documented run command. This reuses the result-data capability already delivered in feature 001 rather than adding a second mechanism.
- **FR-015**: The platform MUST generate a self-contained report from the result data that a person who did not perform the run can read, requiring no tool beyond a standard web browser or text viewer.
- **FR-016**: For a failing test, the failure reason and its captured evidence MUST be reachable from the report.
- **FR-017**: Result data that is empty or absent MUST be reported as such, never presented as a clean run.
- **FR-018**: Report production MUST NOT silently truncate results for a large run.
- **FR-019**: No credential may appear in a report, an attachment, or any captured evidence.
- **FR-020**: Reports and result data MUST be written to the repository's existing generated-output location and MUST remain excluded from version control.

**Traceability**

- **FR-021**: Each test derived from a ticket MUST be attributable to that ticket in the report.
- **FR-022**: The approval that authorised a test's automation MUST be identifiable from the report.
- **FR-023**: Where a run covers several tickets, results MUST be groupable by ticket.

**Judging failures**

- **FR-024**: For a failing test, the platform MUST capture enough evidence for a human to judge whether the application or the test is at fault.
- **FR-025**: The platform MUST NOT assert which of those two causes applies.
- **FR-026**: Test failures MUST be reported as run outcomes and MUST NOT be treated as an error in the completion step. Automated repair is permitted only within the strict limits of FR-036 to FR-041.
- **FR-027**: A test that passes on one run MUST NOT be recorded as proven correct on that basis alone; an unstable result MUST remain visible rather than being averaged away.

**Inherited constraints**

- **FR-028**: This feature MUST NOT weaken the approval gate of feature 004, and MUST NOT provide any route that completes automation without an applicable approval.
- **FR-029**: No MCP server, assistant connector, or other external tooling may be required at runtime for running tests or producing result data.
- **FR-030**: Any new third-party dependency or external prerequisite MUST be justified against the dependency floor and the prerequisite count established in feature 001.

**Report generation without a renderer**

These follow from the decision to generate the report in-project rather than adopt an external renderer.

- **FR-031**: Report generation MUST use only the project's existing toolchain. It MUST add zero new third-party dependencies and zero external prerequisites beyond the single setup prerequisite already established.
- **FR-032**: The generated report MUST identify itself as a project-generated summary rather than an Allure report, and MUST NOT imply Allure feature parity. It does not provide a run timeline, historical trends, or an attachment browser.
- **FR-033**: Rendering the same result data with the Allure command-line tool MUST remain documented as an optional path for anyone who wants the full Allure report, and MUST NOT be required by any success criterion of this feature.
- **FR-034**: The report MUST make each failing test's captured evidence reachable, and MUST state what has to accompany the report for a recipient to view that evidence.

**Run scope**

- **FR-035**: Every report MUST state the scope of the run it covers, so a ticket-scoped pass is never readable as confidence about tests that did not execute.

**Limits on automated repair**

The platform may fix mechanical breakage in freshly authored tests. It may not make a failing test pass. These requirements exist to keep that line sharp, because the easiest way to turn a red assertion green is to weaken it - which would convert this platform into a way of hiding defects.

- **FR-036**: Automated repair MAY be attempted **only** for failures in this closed list of mechanical, test-side error classes: import or collection errors, syntax errors, missing or misused fixtures, unregistered markers, and misuse of the test framework's own API.
- **FR-037**: Automated repair MUST NOT be attempted for: assertion failures, element-not-found, timeouts, response-status mismatches, or any failure not on the FR-036 list.
- **FR-038**: Where the failure class cannot be determined with confidence, the failure MUST be treated as ineligible for repair. Ambiguity MUST resolve towards escalation, never towards editing the test.
- **FR-039**: A repair MUST NOT change what a test asserts. Any repair that would alter, weaken, or remove an assertion MUST be refused and escalated. The reason is not that the assertion itself was approved - a skeleton has no assertions - but that each assertion **implements the behaviour its docstring claims**, and that claimed behaviour is exactly what the approval covers. Changing an assertion therefore changes what the test proves about the application without anyone reviewing the change.
- **FR-040**: Repair attempts MUST be bounded by an explicit limit, and every attempt MUST be recorded with what was changed and why. Exhausting the limit MUST stop and report what was attempted.
- **FR-041**: A report covering a run in which repairs occurred MUST disclose that per test, so a passing result is never presented without the fact that the test was modified to get there.
- **FR-042**: Automated repair MUST NOT occur during a pipeline run.

### Key Entities

- **Approved Design**: An approved set of tests for a ticket, some or all still unimplemented. The input to completion.
- **Completed Automation**: A runnable test carrying its source ticket and authorising approval.
- **Run**: One execution of a chosen set of tests, producing result data and evidence.
- **Result Data**: The structured per-test outcomes a run emits. Already delivered by feature 001.
- **Report**: The readable rendering of result data, shareable with someone who did not perform the run.
- **Failure Evidence**: What is captured for a failing test — message, screenshot, trace, video — sufficient to judge cause without re-running.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of completion attempts against a design that is pending, rejected, or stale are refused; zero proceed.
- **SC-002**: Zero existing test bodies are overwritten by completion.
- **SC-003**: After completion, zero of the affected tests are still reported as unimplemented skeletons.
- **SC-004**: 100% of completed tests record their source ticket and authorising approval.
- **SC-005**: 100% of executed tests appear in the run's result data.
- **SC-006**: For 100% of failing tests, the failure reason and captured evidence are reachable from the report.
- **SC-007**: A report is readable by someone with no access to the original run session, with zero reliance on terminal scrollback.
- **SC-008**: 100% of tests derived from a ticket are attributable to that ticket in the report.
- **SC-009**: A run collecting zero tests is reported as a failure in 100% of cases; zero are reported as passing.
- **SC-010**: An unreachable application under test is distinguished from a test failure in 100% of cases.
- **SC-011**: Zero credentials appear in any report, attachment, or captured evidence, verified by searching a failed run's complete output.
- **SC-012**: Zero generated files appear as version-control candidates after a run and report.
- **SC-013**: Zero completions occur during a pipeline run.
- **SC-014**: Report production for a suite of up to 1,000 tests completes in under 60 seconds and truncates zero results.
- **SC-015**: Zero assistant connectors or external tooling are required to run tests or emit result data.
- **SC-016**: Any external prerequisite added by this feature is documented and justified, and the total remains stated accurately in setup documentation.
- **SC-017**: Report generation requires zero external prerequisites beyond the project's single setup prerequisite, and adds zero new third-party dependencies.
- **SC-018**: The generated report is readable in 100% of cases with nothing beyond a standard web browser or text viewer.
- **SC-019**: Zero success criteria of this feature depend on the Allure command-line tool being installed.
- **SC-020**: 100% of runs immediately after completion are scoped to the completed ticket; zero full-suite runs start automatically.
- **SC-021**: 100% of reports state the scope of the run they cover.
- **SC-022**: Zero repair attempts are made on assertion failures, element-not-found, timeouts, response-status mismatches, or failures whose class could not be determined.
- **SC-023**: Zero repairs change, weaken, or remove what a test asserts.
- **SC-024**: 100% of repair attempts are recorded with what changed and why, and 100% of reports covering a repaired test disclose the repair.
- **SC-025**: Zero repairs occur during a pipeline run.

## Assumptions

Reasonable defaults chosen where the description did not specify a detail. Each is a candidate for revision during `/speckit.clarify` or `/speckit.plan`.

- **Depends on features 001 to 004**: result data and run mechanics from 001, ticket access from 002, test designs from 003, and the approval gate from 004. Only 001 is implemented today, so this feature sits at the end of a four-feature chain.
- **"Generate automation tests" means completing approved skeletons**, not generating from scratch. Feature 003 produces the design and feature 004 approves it; this feature fills in the bodies. Generating tests that bypass the design and approval steps would contradict feature 004 outright.
- **Completion is authored interactively**, consistent with feature 003's clarified decision: the platform does the deterministic work and an AI assistant writes the test bodies. Consequence carried forward — completion cannot run unattended, which is also what feature 004's pipeline prohibition requires.
- **Selectors come from the application, not the ticket**: a browser-driven test cannot be completed from ticket text alone. Completion of UI tests is expected to use the recorded-draft workflow from feature 001, against a reachable application.
- **Allure is the reporting mechanism**: the user named Allure, and feature 001 already installed the integration and emits result data. This feature does not introduce a second reporting mechanism.
- **Result data already works**: feature 001's FR-024 is implemented and verified. Rendering it is what this feature adds.
- **The report is generated in-project, not rendered by an external tool** *(resolved: Clarifications, 2026-10-04)*: the platform reads its own result data and produces a self-contained report using only the existing toolchain. Trade accepted: this is **not** an Allure report - no run timeline, no historical trend, no attachment browser - and FR-032 requires it to say so rather than let a reader assume parity. In exchange, the project's single-prerequisite property survives, every machine and pipeline can produce a readable report, and nothing new is installed. Anyone wanting the full Allure report can still install the Allure CLI and render the same result data (FR-033).
- **Allure Report 3 was considered and rejected**: it does remove the Java runtime the Allure 2 CLI needs, but it is distributed only through npm and requires Node.js. Features 001 and 002 excluded a Node toolchain deliberately - 001's Question 1 chose Python-only over Playwright MCP for exactly that reason, FR-013 forbids a toolchain outside Python and `uv`, and 002's command contract treats any Node-requiring command as a breaking change. Adopting Allure 3 would have swapped one forbidden prerequisite for another. A secondary unknown also went unresolved: whether Allure 3 consumes the results the installed `allure-pytest` already emits, or needs a different Python adapter.
- **No reporting back to the ticket system**: publishing results as a Jira comment is out of scope here, and as of 2026-10-04 is not possible at all — feature 002 was narrowed to a read-only client and has no write capability. Adding one would be a new feature, not a configuration change.
- **Fast feedback first, regression explicitly second** *(resolved: Clarifications, 2026-10-04)*: a run after completion covers the completed ticket only, and the full suite is an offered follow-up. The risk accepted is that a new test breaking an existing one is not noticed until the follow-up runs, which is why FR-035 requires every report to state its scope - a narrow green must never read as a broad one.
- **Repair is limited to mechanical faults** *(resolved: Clarifications, 2026-10-04)*: the platform may fix a test that cannot run; it may not make a failing test pass. The eligibility list in FR-036 is closed and FR-038 fails closed, so a failure class that cannot be identified is escalated rather than edited. Element-not-found and timeouts are deliberately **excluded** even though they are the commonest test-side faults in browser automation, because they are indistinguishable from a feature that was never built - repairing one would erase a genuine finding. The cost is that some real test-side breakages still need a human; that is the intended trade.
- **No report retention or history policy**: reports go to the existing generated-output location and are not accumulated, archived, or published anywhere. Trend reporting across runs is a separate feature.
- **Supported platforms carry over**: Windows and Linux. macOS remains unsupported.
- **Features 001 to 004 rules remain in force**: dependency floor, one external prerequisite, `.env`/`.gitignore` with no secret scanning, configuration through the validated settings model, no MCP at runtime, serial-by-default and parallel-safe execution, skeleton conventions, and the approval gate.
- **Canonical terms** *(normalised 2026-10-04, finding X4)*: a **test design** is the reviewable artifact for a ticket - test names, markers, and the docstrings stating the behaviour each test must prove. A **skeleton** is a test design in its unimplemented state, before bodies exist. **Completed automation** is a test design whose bodies have been written. The three terms name three states of one artifact, not three artifacts.
- **No project constitution in force**: `.specify/memory/constitution.md` is still the unfilled template. This is the fifth feature specified without governance gates.
