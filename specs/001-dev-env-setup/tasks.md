---

description: "Task list for Development Environment Bootstrap"
---

# Tasks: Development Environment Bootstrap

**Input**: Design documents from `/specs/001-dev-env-setup/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: The health-check tests in this list are **not optional**. FR-019 and FR-026 make them the mechanism by which setup is verified — they are the feature's deliverable, not test scaffolding around it. No separate TDD test layer is requested, so there are no tests-before-implementation tasks.

**Organization**: Tasks are grouped by user story. Each story adds its own health-check test, so every story is independently verifiable by running `uv run pytest -m healthcheck` after completing it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

## Path Conventions

Single project at repository root: `src/ai_qa/` for the importable support package, `tests/` for the test tree, `reports/` for generated output. Per the Structure Decision in [plan.md](./plan.md).

**Every command below runs through `uv run`.** There is no virtual-environment activation step on any platform (R9).

---

## Phase 1: Setup

**Purpose**: Bring the repository into existence as a version-controlled, dependency-managed Python project.

- [X] T001 Initialize a git repository at the repository root `D:\coderepo\ai-qa` — no VCS exists yet, and the ignore rules in T002 have no effect until it does (spec Assumptions: "Repository is not yet under version control")
- [X] T002 Create `.gitignore` excluding `.env`, `.venv/` (the isolated project-local environment of FR-006), `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `reports/`, `test-results/`, and Playwright's browser cache — satisfies FR-018 and FR-022. Must precede any command that generates files, or the first `git status` is noise
- [X] T003 Create `pyproject.toml` with a `[project]` table: `name = "ai-qa"`, `version = "0.1.0"`, and `requires-python = "==3.12.*"` — this is the single committed configuration file required by FR-001, and the exact pin is required by FR-002; `>=3.12` would resolve against this machine's Python 3.14.7 and silently defeat it (R1)
- [X] T004 [P] Create `.python-version` containing `3.12` so `uv` provisions the pinned interpreter rather than requiring one be pre-installed — FR-002, SC-011, R1
- [X] T005 Add all eight dependencies in one command: `uv add pytest pytest-playwright playwright allure-pytest PyYAML pydantic httpx python-dotenv`, then confirm `uv.lock` is created and committed — FR-003, FR-004, FR-005, and FR-006 (installs into an isolated project-local `.venv/`). Add nothing else: FR-004 permits additions only where a requirement cannot otherwise be met
- [X] T006 Install browser binaries: `uv run playwright install chromium firefox webkit` — FR-008. Not covered by `uv sync`, which is why FR-008 demands it be a separate documented step
- [X] T007 Create the directory skeleton from the plan's source tree: `src/ai_qa/pages/`, `tests/health/`, `tests/ui/`, `tests/api/`, `tests/data/`, with `.gitkeep` in `tests/ui/` and `tests/api/` — FR-017

**Checkpoint**: `uv sync --locked` succeeds and `uv run python -c "import pytest"` works.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites shared by every user story. Nothing in Phase 3+ can start until these are done.

- [X] T008 Add `[tool.pytest.ini_options]` to `pyproject.toml`: `testpaths = ["tests"]`, `--strict-markers`, registered markers `healthcheck`, `ui`, `api`, `smoke`, and `addopts` fixing `--alluredir=reports/allure-results`, `--output=reports/artifacts`, `--screenshot=only-on-failure`, `--tracing=retain-on-failure` — FR-016, FR-024. `--strict-markers` is load-bearing: without it a mistyped `-m healthchek` runs zero tests and reports success, the worst failure for a verification gate (R8)
- [X] T009 [P] Create `src/ai_qa/__init__.py` (empty package marker)
- [X] T010 Create the `Settings` model in `src/ai_qa/config.py` as a `pydantic.BaseModel` subclass with `model_config = ConfigDict(frozen=True)` and these fields, constraints quoted verbatim from [data-model.md](./data-model.md) §1: `base_url: HttpUrl` (required, "Must parse as an absolute `http`/`https` URL"); `browser: Literal["chromium", "firefox", "webkit"]` (default `"chromium"`); `headless: bool` (default `True`); `timeout_ms: int` (default `30000`, `gt=0`, `le=300000`); `api_base_url: HttpUrl | None` (default `None`); `api_token: SecretStr | None` (default `None`, "Never logged or included in `repr`"); `artifacts_dir: Path` (default `reports/artifacts`); `allure_results_dir: Path` (default `reports/allure-results`) — FR-023. Do **not** add `pydantic-settings`: in pydantic v2 it is a separate distribution, and FR-004 forbids an addition when `BaseModel` plus `python-dotenv` already satisfies the requirement (R3)
- [X] T011 [P] Create the YAML test-data loader in `src/ai_qa/data.py` using `yaml.safe_load` only (never `yaml.load`), resolving paths relative to `tests/data/`, raising `FileNotFoundError` naming both the requested file and the directory searched, and rejecting any file that parses to something other than a mapping with a message naming the file — FR-017, [data-model.md](./data-model.md) §2
- [X] T012 [P] Create `tests/data/example.yaml` with a top-level mapping of case identifiers to case bodies, matching the shape in [data-model.md](./data-model.md) §2 — FR-017
- [X] T013 Create `tests/conftest.py` with the node-ID-derived artifact path fixture: function-scoped, replacing each run of non-alphanumeric characters in the test's node ID with a single `-`, truncating to 120 characters with a short hash suffix when longer (Windows path-length limit, and Windows is the primary platform), returning a per-test directory under `reports/artifacts/` — FR-010, SC-012, [data-model.md](./data-model.md) §3
- [X] T014 [P] Create the page-object base class in `src/ai_qa/pages/base.py` accepting a Playwright `Page` in its constructor — FR-017. Keep it minimal; no application-specific page objects exist yet
- [X] T015 Create `tests/health/test_environment.py` as an empty module with the `pytestmark = pytest.mark.healthcheck` module-level marker, so each story can append its own capability test — FR-019

**Checkpoint**: `uv run pytest -m healthcheck` collects the empty module without error; `uv run pytest --collect-only` shows `tests/` discovered via `testpaths`.

---

## Phase 3: User Story 1 - Bootstrap a working environment from a clean checkout (Priority: P1) 🎯 MVP

**Goal**: An engineer with only `uv` installed can clone, follow `README.md`, and reach a passing health-check run with no undocumented step.

**Independent Test**: On a machine with no prior project state, run only the commands in `README.md` and confirm `uv run pytest -m healthcheck` passes.

- [X] T016 [US1] Add the dependency-import health-check test to `tests/health/test_environment.py`: assert every one of the eight declared dependencies imports and reports a version, failing with a message naming the missing package and pointing at the `uv sync --locked` step — FR-019, FR-027, SC-009. Must not request the settings fixture, so this test passes before `.env` exists (US3)
- [X] T017 [US1] Write `README.md` covering: `uv` as the **sole** prerequisite (Python is provisioned, not installed — SC-011); supported platforms Windows and Linux with an explicit statement that macOS is untested and unsupported (FR-029, R12); every setup command in execution order with the Linux-only `uv run playwright install-deps` called out separately as root-requiring; the `uv run pytest -m healthcheck` verification command; and how to run the full suite — FR-028
- [X] T018 [US1] Verify the clean-checkout path end to end: from a fresh clone with no `.venv/`, run the documented commands in order and confirm each exits `0` and the health check passes — validates SC-002 and quickstart Scenario 1
- [X] T019 [US1] Verify idempotence: re-run `uv sync --locked` and `uv run playwright install chromium firefox webkit` over the built environment and confirm both exit `0` as no-ops with no manual cleanup — FR-007, quickstart Scenario 6
- [X] T020 [US1] Time the clean-checkout run and confirm it completes in under 15 minutes including downloads, and that the health-check suite alone completes in under 60 seconds — SC-001, SC-007

**Checkpoint**: MVP complete. The environment is reproducible, documented, and self-verifying.

---

## Phase 4: User Story 2 - Run a real browser-based test (Priority: P2)

**Goal**: Browser automation works visibly and unattended, and failures leave diagnostic evidence.

**Independent Test**: Run the browser health-check test once headless and once with `--headed`; both pass.

- [X] T021 [US2] Add the browser-launch health-check test to `tests/health/test_environment.py`: launch Chromium via the `page` fixture, navigate to a `data:` URL, and assert on its content — failing with a message naming the `playwright install` step when binaries are missing. Use a `data:` URL, not a real site, so environment verification never depends on network reachability or an external site's uptime (R10)
- [X] T022 [P] [US2] Confirm headless is the default and `--headed` is the documented opt-in, with no configuration change needed for either — FR-009
- [X] T023 [US2] Verify failure evidence: force a browser test failure and confirm `reports/artifacts/<sanitised-node-id>/` is created containing a screenshot and trace, and that the directory name contains the failing test's node ID — FR-010
- [X] T024 [US2] Document the headed-run command and the browser-override command (`--browser firefox`) in `README.md` — FR-009
- [X] T025 [US2] Confirm the browser test and a report run both succeed on a machine with no display attached — SC-010

**Checkpoint**: Browser automation verified in both modes, with evidence capture working.

---

## Phase 5: User Story 3 - Configure environment-specific values without committing secrets (Priority: P2)

**Goal**: Configuration comes from an uncommitted `.env`, validated at startup, with no real value anywhere in version control.

**Independent Test**: Copy `.env.example` to `.env`, set a value, confirm the suite reads it; delete `.env` and confirm the failure names the missing setting.

- [X] T026 [US3] Create `.env.example` naming all eight settings with placeholder or non-sensitive default values only, each with an explanatory comment, and an explicit warning on `API_TOKEN` that real tokens belong in `.env` because this file is committed — use the exact content in [contracts/configuration.md](./contracts/configuration.md) — FR-020, SC-005, SC-008
- [X] T027 [US3] Add the session-scoped `settings` fixture to `tests/conftest.py`: load `.env` via `python-dotenv`, build the frozen `Settings` model, and re-raise any `pydantic.ValidationError` as a `pytest.UsageError` naming the offending field and pointing at `.env.example` — FR-021, FR-023, SC-009. The fixture must be **lazy** (instantiated only when first requested) so tests that need no configuration still run without a `.env`
- [X] T028 [US3] Add the configuration-validation health-check test to `tests/health/test_environment.py`: assert settings load and validate, failing with a message naming the offending setting — FR-019, FR-026. This is the fifth capability test; FR-026's enumeration was corrected on 2026-10-03 to include it
- [X] T029 [P] [US3] Verify `.env` is ignored: `git check-ignore -v .env` confirms exclusion, and `git status --porcelain` after a full suite run lists zero generated files — FR-022, SC-006
- [X] T030 [US3] Verify fail-fast behaviour: move `.env` aside, run `uv run pytest -m healthcheck`, and confirm the error names `BASE_URL` rather than failing somewhere unrelated — SC-009, quickstart Scenario 3
- [X] T031 [US3] Document the `.env.example` → `.env` copy step in `README.md` with both shell variants (`cp` and PowerShell `Copy-Item`) — FR-028, FR-029

**Checkpoint**: Configuration is validated, secret-safe, and fully described by the committed example.

---

## Phase 6: User Story 4 - Explore an application and record a draft test (Priority: P3)

**Goal**: An engineer can record a draft test from a live browser session, and an AI assistant can refactor it against the repository's own conventions.

**Independent Test**: Run `uv run playwright codegen https://example.com`, interact, and confirm runnable code is emitted.

- [X] T032 [US4] Add the CLI-availability health-check test to `tests/health/test_environment.py`: invoke the Playwright CLI as a subprocess using `sys.executable -m playwright --version`, confirming FR-011 (available with no install step beyond FR-006 and FR-008) and assert it exits `0` and reports a version. Must **not** use `shutil.which("playwright")`, which would find whatever is first on `PATH` and can be satisfied by a foreign global copy — FR-012, FR-019, R5
- [X] T033 [US4] Write `CLAUDE.md` at the repository root covering the directory layout from FR-017, test naming conventions, the registered markers, the function-scoped fixture rule and the node-ID artifact path rule, and what a recorded `codegen` draft must be refactored to meet before it is committed — FR-014. Must be separate from `README.md`, which stays human-facing setup documentation
- [X] T034 [US4] Document the recording workflow in `README.md`: the `uv run playwright codegen <url>` command, the `--output` flag, how to verify the tool is available (`uv run playwright --version`), and that recording requires an attached display and is workstation-only — FR-015 (all three clauses)
- [X] T035 [US4] Verify project-local resolution: confirm the version printed by `uv run playwright --version` matches `playwright` in `uv.lock`, and that no documented command invokes `npx` or any Node.js tool — FR-013, SC-011. Node 26.8.2 is present on this machine, so this is a real failure mode, not a theoretical one

**Checkpoint**: Recording works and the repository can teach an assistant its own conventions.

---

## Phase 7: User Story 5 - Produce a shareable test report (Priority: P3)

**Goal**: A suite run emits structured result data with no extra flags, renderable into a report by anyone with the optional viewer.

**Independent Test**: Run `uv run pytest` and confirm result files appear in `reports/allure-results/`.

- [X] T036 [US5] Add the reporting-integration health-check test to `tests/health/test_environment.py`: assert `allure-pytest` is registered with the pytest plugin manager, failing with a message naming the missing package — FR-019, FR-024
- [X] T037 [US5] Verify result data is emitted by a bare `uv run pytest` with no additional flags (proving `--alluredir` is active via `addopts`), that filenames are UUID-based and therefore collision-free, and that `reports/allure-results/` is git-ignored — FR-016, FR-024, FR-018
- [X] T038 [US5] Document report rendering in `README.md`: `allure serve reports/allure-results`, flagged as optional and requiring the separately installed Allure CLI plus a Java runtime, and confirm a missing Allure CLI does not fail the test run — FR-025. Java 1.8.0_503 is present on this machine; the Allure CLI is not

**Checkpoint**: All five stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting requirements that span stories, plus the final success-criteria sweep.

- [X] T039 Document the dependency upgrade procedure in `README.md`: `uv lock --upgrade` to refresh the lock, the **mandatory** `uv run playwright install chromium firefox webkit` afterwards to re-match version-locked browser binaries, and committing the refreshed `uv.lock` as its own change — FR-005, FR-028, R11
- [X] T040 Verify no setup command rewrites `uv.lock`: run `uv sync --locked` and confirm `git diff --stat uv.lock` shows no change, which is what makes FR-005's "deliberately updated" enforceable rather than aspirational — quickstart Scenario 7
- [ ] T041 [P] Verify reproducibility across machines: set up a second clean checkout on the same OS and confirm `uv.lock` resolves identically with zero differences — SC-003
- [X] T042 Verify the full setup on Linux in addition to Windows, including the root-requiring `uv run playwright install-deps` step — SC-002 requires both supported platforms
- [X] T043 [P] Review for parallel-readiness: confirm every fixture in `tests/conftest.py` is function-scoped except the frozen `settings` fixture, that no artifact path is a fixed filename, and that enabling parallel execution would require no change to any fixture, test, or artifact path — SC-012
- [X] T044 [P] Review the committed file set for secrets: confirm `.env.example` is the only committed configuration file, that every value in it is a placeholder, and that no `.env` appears in git history — SC-005. Note the clarified decision: no scanning tooling is in scope, so this is a human review and does not cover a credential pasted inline into a test or doc
- [X] T045 Confirm every setting the suite reads at runtime is named in `.env.example` by cross-checking against the `Settings` model — zero settings discoverable only by reading code — SC-008

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: No dependencies. T001 → T002 must be in that order (ignore rules need a repository). T003 → T005 (dependencies need a project table). T005 → T006 (browser install needs the `playwright` package installed)
- **Phase 2 (Foundational)**: Depends on Phase 1 complete. **Blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2. No dependency on other stories — this is the MVP
- **Phase 4 (US2)**: Depends on Phase 2. Independent of US1's tasks, though US1 should land first for a coherent delivery
- **Phase 5 (US3)**: Depends on Phase 2, specifically T010 (the `Settings` model) for T027
- **Phase 6 (US4)**: Depends on Phase 2. T033 (`CLAUDE.md`) depends on T007 for the layout it documents
- **Phase 7 (US5)**: Depends on Phase 2 and T008 (`addopts` must carry `--alluredir`)
- **Phase 8 (Polish)**: Depends on all stories complete. T042 needs a Linux machine; T041 needs a second machine

### Story independence

Each story appends its own capability test to the shared `tests/health/test_environment.py`. That file is the one shared write point across stories, so tasks touching it (T016, T021, T028, T032, T036) are **not** parallelizable with each other despite belonging to different stories.

---

## Parallel Execution Examples

**Phase 1**: T004 runs parallel to T003.

**Phase 2**: T009, T011, T012, T014 are all different files with no interdependencies — run together. T010 and T013 are sequential against them only where `conftest.py` imports the config module.

**Phase 5**: T029 and T031 run parallel to each other (verification vs. documentation, different files).

**Phase 8**: T041, T043, T044 are independent reviews — run together. T039 and T040 are sequential (document the procedure, then verify the property it relies on).

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1).** That is T001–T020: a reproducible, documented, self-verifying environment. It delivers the spec's P1 story completely and is a legitimate stopping point if priorities change.

**Incremental delivery after MVP**: US2 (browser) and US3 (configuration) are both P2 and independent of each other — either can go first. US4 and US5 are P3 polish on a working platform.

**Two sequencing traps worth naming:**

1. **T002 before anything generates files.** Write `.gitignore` before the first `uv sync`, or `.venv/` and caches land in the first `git status` and someone commits them.
2. **T027's fixture must be lazy.** If `conftest.py` instantiates `Settings` at import time rather than inside the fixture, every test fails without a `.env` — including US1's dependency-import test, which breaks the MVP's independence from US3.

**One open spec delta** (see [plan.md](./plan.md) Spec Deltas): FR-026 enumerates four verification capabilities; FR-019 and SC-004 enumerate five. These tasks build five (T016, T021, T028, T032, T036), following the two artifacts that agree. If FR-026's list is treated as authoritative instead, T028 would be dropped and configuration validation would go unverified.

---

## Implementation Status — 2026-10-03

**42 of 45 tasks complete.** Three remain open, all blocked on hardware rather than work:

### Update — Linux verification completed 2026-10-03

**44 of 45 tasks complete.** T025 and T042 were closed by a Docker run on
Ubuntu 26.04.1 LTS with a cold `uv` cache and **no Python installed at all**
(`python3: command not found`):

| Evidence | Result |
|---|---|
| `DISPLAY` / `WAYLAND_DISPLAY` | both unset - genuinely no display (closes T025 / SC-010) |
| `uv sync --locked` | exit 0, 9.9 s, provisioned Python 3.12.15 from nothing |
| `uv.lock` after cold-cache sync | byte-identical to the host lock |
| `playwright install-deps` (root) | exit 0 |
| Health checks with no display | 14 passed in 3.93 s |
| Full suite + Allure | 14 passed, 100 result files |
| Idempotent re-run | exit 0, 14 passed |

The cold-cache, different-OS lock match is stronger evidence for SC-003 than
the same-machine check, but T041 stays open because SC-003 is worded as two
checkouts on *the same* operating system.

| Task | Criterion | Why still open |
|---|---|---|
| T041 | SC-003 | Needs a second Windows machine. Partially covered: a second clean checkout on this machine and a cold-cache Linux sync both resolved `uv.lock` identically. Either run it on another Windows box, or reword SC-003 to drop the same-OS clause. |

### Linux finding: browser install step order

`playwright install chromium` before `install-deps` exits **0** - the
missing-system-libraries output is a warning, not a failure, so SC-002 is not
violated. The exit code of the *three-browser* command before `install-deps`
was not measured (Firefox and WebKit need more libraries than Chromium).
Rather than leave that unknown, `README.md` now documents the Linux step as a
single `playwright install --with-deps ...` run, verified exit 0, which orders
the libraries before the browsers and removes the question.

Verified on this machine: 14 health-check tests pass in ~1.5 s; clean-checkout
setup reaches a green run in 7 s with warm caches; `uv sync --locked` leaves
`uv.lock` untouched; failure evidence lands in per-test directories; the
missing-`.env` path reports `Invalid configuration: BASE_URL`.

### Deviations from the task list as written

1. **`README.md` had to exist before T005.** `pyproject.toml` declares
   `readme = "README.md"`, so the editable install's build backend failed
   without it. A stub was created during Phase 1 and T017 replaced it. The task
   list should have ordered a placeholder README into Phase 1.
2. **`base_url` had to be session-scoped, not function-scoped.**
   `pytest-base-url` (transitive via `pytest-playwright`) installs a
   session-scoped autouse fixture that requests `base_url`; a function-scoped
   override raises `ScopeMismatch` for *every* test. Safe at session scope for
   the same reason as `settings` — an immutable value derived from the process
   environment. Recorded in `CLAUDE.md` so it is not "fixed" back.
3. **Health-check count is 14, not 5.** FR-019 requires one independent test
   per capability; the dependency check is parametrised across all eight
   packages, and two extra guards were added (interpreter is 3.12, settings are
   frozen). Still one failure per distinct problem, which is what SC-009 asks.
