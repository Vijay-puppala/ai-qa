# Feature Specification: Development Environment Bootstrap

**Feature Branch**: `001-dev-env-setup` *(no branch created — the project is not yet a git repository)*

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Create the initial development environment for the AI-QA platform. The project must use Python 3.12 and uv for Python dependency management. The project must use: pytest, pytest-playwright, Playwright Python, allure-pytest, PyYAML, pydantic, httpx, python-dotenv. The project must also support Playwright CLI for AI-assisted browser exploration. The project must: (1) Define the Python project configuration in pyproject.toml. (2) Add all required Python dependencies using uv. (3) Install Playwright browsers. (4) Install/configure Playwright CLI and its Claude Code skills. (5) Create pytest configuration. (6) Create the initial project directory structure. (7) Create .env.example. (8) Create .gitignore. (9) Create a basic health-check test. (10) Verify that pytest works. (11) Verify that Playwright can launch a browser. (12) Verify that Playwright CLI is available. (13) Verify that Allure pytest integration is available. (14) Do not store secrets in source control. Dependency installation and environment configuration must be reproducible from a clean checkout. The implementation must document all required setup commands in README.md."

## Clarifications

### Session 2026-10-03

- Q: Is the list of eight packages in FR-004 the complete and final dependency set, or a minimum floor that the plan may add to? → A: Minimum floor — the eight are required; the plan may add more only where a stated requirement cannot otherwise be met, and must name the requirement each addition serves.
- Q: What must actually prevent a secret from reaching version control — repository tooling that blocks it, or the ignore rules plus developer care? → A: Ignore rules only. Real values live in a local `.env` that `.gitignore` excludes; `.env.example` is committed with dummy values. No secret-scanning tooling is in scope.
- Q: What reads YAML in this project — test data files, a structured configuration layer, or both? → A: Test data only. Configuration comes solely from the local environment file; no YAML configuration layer in this feature.
- Q: Does the environment need to run tests in parallel from day one, or is a serial run enough for now? → A: Parallel-ready, not parallel-enabled. Serial by default with no added dependency, but fixture scoping and artifact/result paths must be collision-free per test so parallelism can be enabled later without refactoring.
- Q: Should the four verification checks in SC-004 be tests that `pytest` runs, or documented commands a person runs by hand? → A: Tests. A health-check test module with one test per capability (dependencies import, browser launches, reporting plugin registered, exploration CLI responds), marked so they can be run alone; a bare `pytest` run proves the environment.
- Q: Is macOS a supported platform for this project, or only Windows and Linux? → A: Windows and Linux only, both verification targets. macOS is explicitly unsupported and untested for this feature; `README.md` must say so rather than implying support.
- Q: What should carry the project guidance that an AI assistant reads — `README.md` alone, or a separate assistant-facing file? → A: Both, split by audience. `README.md` carries prerequisites and setup for humans; a committed `CLAUDE.md` carries directory layout, naming and fixture conventions, and the rules a recorded draft must be refactored to meet.
- Q: When dependency versions need updating, who refreshes the lock file and when? → A: A documented manual procedure in `README.md` — an explicit refresh command, a mandatory re-run of the browser installation afterwards, and the refreshed lock committed as its own change. No automated update tooling.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bootstrap a working environment from a clean checkout (Priority: P1)

A QA engineer joins the AI-QA platform, clones the repository onto a machine that has no project tooling installed, opens `README.md`, and follows the documented setup commands in order. Within minutes they have an isolated project environment with every required dependency installed at a pinned version, and they can run the test suite and see it pass. Nothing they needed was missing from the documentation, and nothing they had to work out for themselves.

**Why this priority**: Without this, no other work on the platform can start. This story alone delivers a usable, shareable environment and is the minimum viable product for the feature.

**Independent Test**: On a machine (or container) with no prior project state, clone the repository, run only the commands listed in `README.md`, and confirm the health-check test suite passes. Fully testable on its own and delivers a working development environment.

**Acceptance Scenarios**:

1. **Given** a clean checkout with no project environment present, **When** the engineer runs the documented setup commands in the documented order, **Then** every command succeeds and an isolated project environment exists containing all required dependencies.
2. **Given** a completed setup, **When** the engineer runs the test suite, **Then** the health-check test executes and passes, and the result is reported in a human-readable summary.
3. **Given** two separate clean checkouts set up on different machines of the same supported operating system, **When** both record their resolved dependency versions, **Then** the resolved versions are identical.
4. **Given** a clean checkout, **When** the engineer inspects the committed project configuration, **Then** the required runtime language version and every required dependency is declared there, rather than being installed by an undocumented ad-hoc step.
5. **Given** a machine where the dependency manager is absent, **When** the engineer consults `README.md`, **Then** the documentation states it as the sole prerequisite and how to obtain it, before the project-specific steps begin.

---

### User Story 2 - Run a real browser-based test (Priority: P2)

A QA engineer writes a test that drives a real browser against a web application, runs it locally while watching the browser, then runs the same test unattended with no visible browser window. Both runs work without extra configuration beyond the documented setup.

**Why this priority**: Browser automation is the platform's core purpose. It depends on Story 1 being complete, but it is the first capability that proves the environment is fit for purpose rather than merely installed.

**Independent Test**: After setup, run a single test that opens a browser, loads a page, and asserts on its content — once with the browser visible and once without. Delivers verified browser-automation capability.

**Acceptance Scenarios**:

1. **Given** a completed setup, **When** the engineer runs a test that launches a browser, **Then** the browser starts successfully and the test completes without any missing-browser or missing-system-library error.
2. **Given** a completed setup, **When** the engineer requests a run with the browser window visible, **Then** the browser is displayed; **and When** they request an unattended run, **Then** no browser window appears and the test still executes.
3. **Given** a browser-based test that fails, **When** the run finishes, **Then** diagnostic evidence for the failure is written to a known output location that is excluded from version control.

---

### User Story 3 - Configure environment-specific values without committing secrets (Priority: P2)

A QA engineer needs to point the suite at a specific target environment using a base URL and credentials. They copy the committed example configuration file to their own local configuration file, fill in their values, and run the suite. Their real values never leave their machine, and a teammate reading the repository can still see exactly which settings are required.

**Why this priority**: Credential handling has to be correct from the first commit. Retrofitting it after real values have entered version-control history is expensive and risky, so it ships alongside the first browser capability rather than after it.

**Independent Test**: Copy the example configuration to a local configuration file, set a value, confirm the suite reads it, then confirm the local file is ignored by version control and the example file contains no real value. Delivers verified secret-safe configuration.

**Acceptance Scenarios**:

1. **Given** the committed example configuration file, **When** an engineer reads it, **Then** every setting the suite needs is listed by name with a placeholder or non-sensitive default, and no real credential, token, or private URL is present.
2. **Given** a local configuration file containing real values, **When** the engineer checks what version control would commit, **Then** the local configuration file is excluded and cannot be committed accidentally.
3. **Given** a local configuration file with a target base URL set, **When** the suite runs, **Then** it uses that value; **and** configuration values are validated such that a missing or malformed required setting fails with a message naming the offending setting.
4. **Given** a completed setup, **When** version-control status is inspected, **Then** no environment directory, dependency cache, test artifact, or report output is listed as a candidate for commit.

---

### User Story 4 - Explore an application and record a draft test (Priority: P3)

A QA engineer faces an unfamiliar web application. Rather than hand-inspecting the page and writing selectors from scratch, they launch the browser automation toolchain's own command-line tool, click through the flow they want covered, and it records their interactions as runnable test code. They then hand that generated draft — and the selectors it discovered — to an AI assistant to refactor into a maintainable test.

**Why this priority**: This is a productivity accelerator that depends on the browser capability from Story 2. The platform is still fully usable without it, so it lands after the core is proven.

**Independent Test**: Invoke the command-line tool against a public web page, perform a few interactions, and confirm runnable test code is emitted naming the elements interacted with. Delivers a verified exploration-and-recording workflow.

**Acceptance Scenarios**:

1. **Given** a completed setup, **When** the engineer checks that the command-line tool is present, **Then** the check reports the tool and its version and exits successfully.
2. **Given** the tool is present, **When** the engineer points it at a reachable web page and interacts with the page, **Then** it emits runnable test code reflecting those interactions, with selectors for the elements used.
3. **Given** a clean checkout, **When** the engineer follows `README.md`, **Then** the tool's invocation, its recording workflow, and its requirement for an attached display are documented.
4. **Given** the generated draft code, **When** an AI assistant working in this project is asked to turn it into a maintained test, **Then** the repository's own guidance tells it where such tests live and which conventions to follow, without the engineer having to explain the project layout.

---

### User Story 5 - Produce a shareable test report (Priority: P3)

After a suite run, a QA engineer produces a structured report of the results that can be handed to someone who did not run the tests — a test lead, a release manager — and read without access to the terminal output.

**Why this priority**: Reporting matters for the platform's long-term value but blocks nothing. The plain run summary from Story 1 is enough to develop against.

**Independent Test**: Run the suite with reporting enabled, confirm structured result data is produced in the output location, and confirm that data is excluded from version control. Delivers verified reporting capability.

**Acceptance Scenarios**:

1. **Given** a completed setup, **When** the engineer checks that the reporting integration is installed, **Then** it is listed among the suite's active plugins.
2. **Given** reporting is enabled for a run, **When** the suite finishes, **Then** structured result data for every test is written to the documented output location.
3. **Given** result data exists, **When** the engineer follows `README.md` to view it as a report, **Then** the documentation states the steps and names any prerequisite that is not installed by the project setup.

---

### Edge Cases

- **Required language version absent or wrong**: The machine has no Python 3.12, or only an older or newer interpreter — a newer system Python is the likelier case. Setup must provision the pinned 3.12 interpreter rather than building the environment on whichever interpreter happens to be present, and the version declaration must be narrow enough that a different minor version cannot silently satisfy it.
- **Dependency manager absent**: `uv` is not installed. This is a documented prerequisite, and the failure must point the engineer at that prerequisite rather than at an opaque command-not-found error.
- **Browser binaries not installed**: Dependencies are installed but the browser download step was skipped. A browser-based test must fail with a message naming the missing step, not a generic launch crash.
- **No network, or restricted network**: Setup runs behind a proxy or offline. Dependency and browser downloads will fail; the documentation must state that network access is required for setup and which steps need it.
- **Unattended machine with no display**: No windowing system is available, so a visible-browser run cannot work. The default run mode must not require a display, and the visible mode must be opt-in.
- **Local configuration file missing**: The engineer runs the suite before copying the example configuration. The suite must report which required settings are unset, instead of failing with an unrelated error deep in a test.
- **Secret pasted into the example file**: An engineer edits the committed example rather than their local copy. The repository must make the local copy the obvious place for real values, and the example must carry no real values.
- **Stale browser binaries after a dependency upgrade**: The browser automation library is upgraded but the previously downloaded browsers no longer match it. The documentation must state that the browser installation step is re-run after upgrading.
- **Operating-system differences**: Setup is run on Windows and on a Unix-like system. Documented commands must work on the supported platforms, or the documentation must give the per-platform variant.
- **Pre-existing or partial environment**: Setup is re-run over a half-built or outdated environment. Re-running the documented commands must converge on a correct environment rather than erroring or leaving a mixed state.
- **Report viewer prerequisite absent**: Result data is produced but the tool that renders it into a readable report is not installed. The suite run must still succeed, and the documentation must name the separate prerequisite.
- **Recording session attempted without a display**: An engineer tries to record a draft test on an unattended machine. Recording is inherently interactive and needs an attached display, so the documentation must state this as a workstation-only workflow rather than leaving the engineer to diagnose a launch failure.
- **Command-line tool resolved from outside the project**: A machine has another copy of the browser automation tool installed globally at a different version. Invoking the tool must resolve to the project-local pinned version, so a recorded draft cannot be produced against a version the suite does not use.

## Requirements *(mandatory)*

### Functional Requirements

**Project configuration and dependencies**

- **FR-001**: The project MUST declare its configuration — name, version, required language version, and dependencies — in a single committed project configuration file (`pyproject.toml`).
- **FR-002**: The project MUST require Python 3.12 and MUST declare that requirement in the project configuration file. The declaration MUST be exact enough that no other installed minor version can satisfy it, and where the pinned interpreter is absent from the machine the dependency manager MUST provision it, so that setup never depends on an interpreter having been installed beforehand.
- **FR-003**: The project MUST use `uv` as its sole dependency manager for adding, resolving, and installing Python dependencies.
- **FR-004**: The project MUST declare the following as dependencies: `pytest`, `pytest-playwright`, `playwright`, `allure-pytest`, `PyYAML`, `pydantic`, `httpx`, and `python-dotenv`. This set is a **minimum floor, not a closed set**: further dependencies MAY be declared only where a requirement in this specification cannot otherwise be satisfied, and each addition MUST name the requirement it serves. Dependencies added for convenience, preference, or anticipated future need MUST NOT be declared.
- **FR-005**: The project MUST commit a resolved dependency lock file, so that every clean checkout installs identical dependency versions until the lock file is deliberately updated. "Deliberately updated" means via the documented upgrade procedure (FR-028): the refresh MUST be an explicit command rather than a side effect of a setup command, the browser installation step (FR-008) MUST be re-run afterwards, and the refreshed lock MUST be committed as its own change rather than bundled with unrelated edits. No automated dependency-update tooling is in scope.
- **FR-006**: Dependencies MUST be installed into an isolated, project-local environment that is excluded from version control.
- **FR-007**: The documented setup sequence MUST be idempotent: running it again over an existing or partially built environment MUST converge on a correct environment without manual cleanup.

**Browser automation**

- **FR-008**: Setup MUST include an explicit step that installs the browser binaries required by the browser automation library, and that step MUST be documented in `README.md`.
- **FR-009**: The suite MUST run browsers without a visible window by default, and MUST offer a documented way to run with the browser visible.
- **FR-010**: Browser-run evidence for failures (such as screenshots, traces, or videos) MUST be written to a documented output location that is excluded from version control. Evidence paths MUST be unique per test, so that tests running concurrently cannot overwrite one another's evidence.

**Exploration and test recording**

- **FR-011**: The environment MUST provide the browser automation toolchain's own command-line tool — the one installed by the Python package — for browser exploration and test recording, available without any additional install step beyond FR-006 and FR-008.
- **FR-012**: The command-line tool MUST be invocable through the project's dependency manager, so that it runs against the project-local environment and its pinned versions rather than against a separately installed copy.
- **FR-013**: Setup MUST NOT require a toolchain outside Python and `uv`; the exploration capability MUST be satisfied entirely by the declared Python dependencies.
- **FR-014**: The repository MUST carry assistant-facing project guidance in a committed `CLAUDE.md`, separate from `README.md`, stating where tests live, the directory layout from FR-017, the naming and fixture conventions in force, and the rules a recorded draft must be refactored to meet. It MUST be discoverable without per-session setup. `README.md` remains the human-facing setup document (FR-028) and MUST NOT be the sole carrier of these conventions.
- **FR-015**: `README.md` MUST document how to verify that the command-line tool is available, how to run a recording session, and that recording requires an attached display.

**Test configuration and structure**

- **FR-016**: The project MUST provide a committed test-runner configuration that fixes test discovery paths, naming conventions, default run options, and registered markers, so that an engineer gets identical behaviour from a bare run command as from a fully specified one. Default execution MUST be serial, but neither the configuration nor the shared fixtures may assume serial execution: fixture scoping MUST be chosen so that enabling parallel execution later requires no change to fixture or test code.
- **FR-017**: The project MUST provide an initial directory structure that separates, at minimum: tests by kind (browser-driven versus service/API), shared test fixtures, reusable page interaction objects, test data, and generated output artifacts. Test data MUST be stored as YAML files within the test-data directory, and the suite MUST be able to load them.
- **FR-018**: Every generated-output directory MUST be excluded from version control.
- **FR-019**: The project MUST include a health-check test module containing one independent test per environment capability: every declared dependency imports, a browser launches, the reporting integration is registered, the exploration command-line tool responds, and configuration loads and validates. Each test MUST pass on a correctly set up environment and MUST fail with a message naming the missing prerequisite or step when it is not. The module MUST carry a registered marker (FR-016) so these tests can be selected and run on their own.

**Configuration and secrets**

- **FR-020**: The project MUST commit an example environment configuration file (`.env.example`) that names every setting the suite reads, with placeholder or non-sensitive default values only.
- **FR-021**: The suite MUST read environment-specific values from a local, uncommitted environment file, and the project MUST NOT require any committed file to hold a real credential.
- **FR-022**: The project MUST NOT store secrets, credentials, tokens, or private endpoint values in version control, and the version-control ignore rules MUST exclude local environment files, environment directories, dependency and tool caches, test artifacts, and report output.
- **FR-023**: Configuration values MUST be validated when the suite starts, so that a missing or malformed required setting fails immediately with a message naming the offending setting, rather than surfacing later as an unrelated test failure. Configuration MUST originate solely from the local environment file; YAML MUST NOT be used as a configuration source in this feature.

**Reporting**

- **FR-024**: The suite MUST be able to emit structured result data for a run, to a documented output location, using the installed reporting integration. Result data MUST be written so that tests running concurrently cannot collide.
- **FR-025**: `README.md` MUST document how to turn result data into a readable report, naming any prerequisite not installed by project setup.

**Verification**

- **FR-026**: Setup verification MUST be performed by the health-check tests of FR-019 rather than by commands a person runs by hand, so that a single test-suite invocation confirms all five capabilities: the test runner executes, a browser launches, the exploration command-line tool is available, the reporting integration is registered, and configuration loads and validates.
- **FR-027**: Each verification test MUST report success or failure unambiguously and independently of the others, so that a partially built environment is identified as such — naming which capability is missing — rather than appearing to work.

**Documentation**

- **FR-028**: `README.md` MUST document the prerequisites, every setup command in execution order, the command that runs the health-check tests on their own, and how to run the full suite — sufficient for an engineer to reach a passing run from a clean checkout using no undocumented step. It MUST also document the dependency upgrade procedure of FR-005: the command that refreshes the lock file, the mandatory re-run of the browser installation step afterwards, and the requirement to commit the refreshed lock separately.
- **FR-029**: `README.md` MUST document the supported operating systems — Windows and Linux — and give per-platform command variants wherever the commands differ. It MUST also state explicitly that macOS is untested and unsupported, rather than omitting it and leaving support to be inferred.

### Key Entities

- **Project Configuration**: The committed declaration of the project's identity, required language version, and dependency set. The single source of truth for what the environment contains.
- **Dependency Lock**: The committed record of exactly resolved dependency versions. What makes two clean checkouts identical.
- **Project Environment**: The isolated, machine-local installation of the dependencies. Generated from the Project Configuration and Dependency Lock; never committed.
- **Browser Binaries**: The machine-local browser installations the automation library drives. Installed by an explicit setup step; never committed.
- **Environment Configuration Template**: The committed example listing every setting the suite reads, with placeholders only. The contract describing what an engineer must supply.
- **Local Environment Configuration**: The engineer's own uncommitted file holding real values for the settings named in the template. Never committed.
- **Test Runner Configuration**: The committed settings that fix discovery, defaults, and markers, so suite behaviour does not vary per engineer.
- **Exploration Tool**: The command-line entry point installed with the browser automation dependency, used to record a draft test from a live interaction session. Supplied by the Project Environment, not installed separately.
- **Project Guidance**: `CLAUDE.md` — the committed, assistant-discoverable description of the repository's layout and test conventions, held separately from the human-facing `README.md`. What turns a recorded draft into a maintained test without a human explaining the project each time.
- **Health-Check Tests**: The committed, individually-named tests asserting that each environment capability is correctly set up. Collectively the pass/fail signal for Story 1 and the mechanism by which setup is verified.
- **Test Data**: Committed YAML files supplying inputs to tests. The only use of YAML in this feature; configuration never comes from here.
- **Output Artifacts**: Generated run evidence and structured result data, written to known locations and excluded from version control.
- **Setup Documentation**: `README.md` — the ordered, complete set of prerequisites, commands, and checks. The entry point for every new engineer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer who has never seen the project reaches a passing health-check run from a clean checkout in under 15 minutes of wall-clock time, using only the commands in `README.md` and no undocumented step.
- **SC-002**: 100% of the setup commands documented in `README.md` succeed, in the documented order, on a machine with no prior project state, on each of the two supported operating systems (Windows and Linux).
- **SC-003**: Two independent clean checkouts set up on the same supported operating system resolve to identical dependency versions, with zero differences.
- **SC-004**: A single test-suite invocation on a freshly set up environment passes every health-check test — dependencies import, browser launches, browser-automation command-line tool reports its version, reporting integration registered, configuration validates — with zero manual verification steps required.
- **SC-005**: A review of the committed file set at feature completion finds zero real credentials, tokens, or private endpoint values. `.env.example` is the only committed configuration file, and every value in it is a placeholder or non-sensitive default; no `.env` file is present in the commit history.
- **SC-006**: Version-control status on a freshly set up environment that has run the suite once lists zero generated files — no environment directory, cache, test artifact, or report output appears as a commit candidate.
- **SC-007**: The health-check suite completes in under 60 seconds on a freshly set up environment.
- **SC-008**: Every setting the suite reads at runtime is named in the committed example configuration file — zero settings are discoverable only by reading the code.
- **SC-009**: Each health-check test in SC-004, when its prerequisite is missing, fails with a message naming that missing prerequisite or step rather than raising an unhandled error.
- **SC-010**: A browser-based test and a structured report run can both be produced on a machine with no display attached, with zero configuration beyond the documented setup.
- **SC-011**: Setup requires exactly one prerequisite outside the repository — the dependency manager — which provisions the pinned Python 3.12 interpreter itself. An engineer installs zero interpreters, zero additional language runtimes, and zero additional package managers.
- **SC-012**: Enabling parallel execution requires no change to any fixture, test, or artifact path — verified by review of fixture scopes and output path construction.

## Assumptions

These are reasonable defaults chosen where the feature description did not specify a detail. Each is a candidate for revision during `/speckit.clarify` or `/speckit.plan`.

- **Scope is the environment, not the test suite**: This feature delivers a working, verified environment plus a health-check test. Building out the actual regression suite, page objects for a specific application under test, or API test coverage is out of scope.
- **Supported platforms** *(resolved: Clarifications session, 2026-10-03)*: Windows (primary development platform) and Linux (unattended runs) are supported, and **both are verification targets** for SC-002. macOS is **not supported** by this feature — nothing in the design is platform-specific and it is likely to work, but it is untested, and claiming support that was never exercised would leave the first engineer on a Mac to discover the gap. Promoting macOS requires someone running the documented setup on it and adding it to SC-002's targets.
- **No CI pipeline in this feature**: Setup must be reproducible and must work without a display, so it is CI-ready. Authoring the actual CI workflow is out of scope here.
- **Exploration means record-and-refactor, not agent-driven browsing** *(resolved: Question 1, option B)*: "AI-assisted browser exploration" is satisfied by the command-line tool that ships with the Python browser automation package — the engineer records a flow, then an AI assistant refactors the generated draft against the repository's conventions. An agent driving the browser directly would require a separate Node.js-based server, which FR-013 excludes. Consequence: the `playwright-explore-website` and `playwright-generate-test` assistant skills available in this environment depend on that excluded server and will not be usable in this project. Revisit if hands-off exploration becomes a requirement.
- **Browser coverage**: Chromium is the default browser for the health-check and verification steps. Firefox and WebKit binaries are installed by the standard browser-installation step, but cross-browser verification is not a success criterion for this feature.
- **Secret prevention is file-based, not scanned** *(resolved: Clarifications session, 2026-10-03)*: Secrets are kept out of version control by the `.env` / `.gitignore` / `.env.example` convention alone. No secret-scanning tooling or pre-commit hook is in scope, so this protects against committing the configuration *file*, not against a credential pasted inline into a test, fixture, or documentation file — that case depends on code review. Accepted for a greenfield project with a small team; revisit if the repository becomes public or the team grows.
- **Report rendering prerequisite**: The reporting integration installed via Python produces structured result data. Rendering it into a browsable report requires a separate command-line tool with its own runtime prerequisite; installing that tool is documented but optional, and is not required for SC-004 to pass.
- **Repository is not yet under version control**: The project directory currently contains no git repository. Initialising one is a precondition for the ignore rules in FR-022 to have any effect, and is treated as part of this feature's setup.
- **Mandated technology choices are requirements, not implementation leakage**: This specification normally avoids naming tools. Here the named tools — Python 3.12, `uv`, and the listed packages — *are* the subject of the request, so they are recorded as explicit constraints. Every other technical choice is left to `/speckit.plan`.
- **Target application is not yet known**: The example configuration will name a target base URL setting, but no specific application under test is assumed. The health-check test will not depend on any particular external site being reachable beyond what Story 2 needs.
- **No project constitution in force**: `.specify/memory/constitution.md` is still the unfilled template, so this specification is not constrained by project principles. Consider running `/speckit.constitution` before `/speckit.plan`.
