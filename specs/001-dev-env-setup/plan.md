# Implementation Plan: Development Environment Bootstrap

**Branch**: `001-dev-env-setup` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-dev-env-setup/spec.md`

## Summary

Stand up a reproducible Python 3.12 test-automation environment managed entirely by `uv`, containing pytest with Playwright browser automation, Allure result reporting, YAML-driven test data, and a validated `.env` configuration layer — then prove it works through a health-check test module that asserts each capability independently, so a single `pytest` run is the environment's verification gate.

The technical approach rests on four decisions, each resolved in [research.md](./research.md):

1. **`uv` provisions the interpreter**, not just the packages. `.python-version` plus `requires-python = "==3.12.*"` makes `uv sync` download and pin CPython 3.12 on any machine, so the only thing a new engineer installs is `uv` itself.
2. **Every command runs through `uv run`**, which removes virtual-environment activation from the documented setup. This is what makes one command set work identically on Windows and Linux (FR-029) and what guarantees the Playwright CLI resolves to the project-pinned version rather than a global copy (FR-012).
3. **Configuration uses `pydantic.BaseModel` + `python-dotenv` directly**, not `pydantic-settings`. FR-004 permits additions only where a requirement cannot otherwise be met, and FR-023 is fully satisfiable with the mandated packages.
4. **Parallel-safety is a design constraint applied now**, not a feature. Function-scoped fixtures and per-test artifact paths cost nothing today and make FR-016/SC-012 true without a later refactor.

5. **Dependency upgrades are a documented manual procedure**, not tooling. `uv lock --upgrade` followed by a mandatory browser re-install, committed as its own change (FR-005, FR-028). No update bot, which would require the CI pipeline this feature excludes.

Net dependency additions beyond the eight mandated packages: **zero**.

## Technical Context

**Language/Version**: Python 3.12, pinned via `.python-version` and `requires-python = "==3.12.*"`, downloaded and managed by `uv` (local system Python is 3.14.7 and is deliberately not used)

**Primary Dependencies**: `pytest`, `pytest-playwright`, `playwright`, `allure-pytest`, `PyYAML`, `pydantic`, `httpx`, `python-dotenv` — the FR-004 set, unchanged. `pytest-base-url` arrives transitively via `pytest-playwright` and supplies `--base-url`.

**Storage**: N/A. Test data is committed YAML read at test time (FR-017); runtime configuration comes from an uncommitted `.env` (FR-023). No database, no persistence layer.

**Testing**: pytest. Registered markers `healthcheck`, `ui`, `api`, `smoke`. Health-check tests are selectable alone via `-m healthcheck` (FR-019).

**Target Platform**: Windows 11 (primary development platform) and Linux (unattended runs). Both are verification targets for SC-002. macOS is **not supported** by this feature — untested, and `README.md` must say so explicitly (FR-029).

**Project Type**: Test-automation framework driven by a CLI test runner — a single Python project with a small importable support package plus a test tree. Not a service; nothing is deployed.

**Performance Goals**: Health-check suite completes in under 60 s (SC-007). Clean checkout to first passing run under 15 min (SC-001), dominated by interpreter, dependency, and browser downloads.

**Constraints**: Python and `uv` only — no Node.js, no second package manager (FR-013, SC-011), even though Node 26.8.2 happens to be present on this machine. Serial execution by default but no fixture or artifact path may assume it (FR-016, SC-012). No secrets in version control, enforced by `.gitignore` convention alone with no scanning tooling (FR-022, Clarifications 2026-10-03). Setup requires network access for three downloads: interpreter, packages, browsers.

**Scale/Scope**: Bootstrap only. One health-check module of five tests, one example YAML data file, one page-object base class. Zero tests against any real application under test — the spec's "target application is not yet known" assumption holds.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status: PASS — vacuously.** `.specify/memory/constitution.md` is the unmodified Spec Kit template: every principle is still a `[PRINCIPLE_N_NAME]` / `[PRINCIPLE_N_DESCRIPTION]` placeholder, and the governance section is `[GOVERNANCE_RULES]`. There are no ratified principles for this plan to comply with or violate, so no gate can meaningfully fail.

This is worth stating plainly rather than recording as a pass: **the gate is empty, not satisfied.** Running `/speckit.constitution` would give later features real gates to check. Doing it before implementation of this feature is cheap; doing it after means this environment — the foundation every later feature inherits — was never checked against the project's own principles.

Pre-Phase 0 evaluation: no violations (no principles exist to violate).
Post-Phase 1 re-evaluation: unchanged — see [Post-Design Constitution Re-Check](#post-design-constitution-re-check).

## Project Structure

### Documentation (this feature)

```text
specs/001-dev-env-setup/
├── plan.md              # This file
├── research.md          # Phase 0 output — 10 resolved decisions
├── data-model.md        # Phase 1 output — configuration, test data, artifact entities
├── quickstart.md        # Phase 1 output — clean-checkout validation walkthrough
├── contracts/
│   ├── commands.md      # Command contract: setup, run, verify, record
│   └── configuration.md # `.env` settings contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit.specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
pyproject.toml              # Project metadata, dependencies, [tool.pytest.ini_options]
uv.lock                     # Committed resolved versions (FR-005)
.python-version             # "3.12" — uv provisions this interpreter
.env.example                # Committed, placeholder values only (FR-020)
.gitignore                  # Excludes .env, .venv, caches, reports/ (FR-022)
README.md                   # Prerequisites, setup commands, upgrade procedure (FR-028, FR-029)
CLAUDE.md                   # Assistant-facing layout and conventions (FR-014)

src/ai_qa/
├── __init__.py
├── config.py               # pydantic models + dotenv loading, fail-fast validation (FR-023)
├── data.py                 # YAML test-data loader (FR-017)
└── pages/
    ├── __init__.py
    └── base.py             # Page-object base class (FR-017)

tests/
├── conftest.py             # Shared fixtures: settings, test data, artifact paths (FR-017)
├── health/
│   └── test_environment.py # Five independent capability tests (FR-019)
├── ui/
│   └── .gitkeep            # Browser-driven tests (FR-017)
├── api/
│   └── .gitkeep            # Service tests via httpx (FR-017)
└── data/
    └── example.yaml        # YAML test data (FR-017)

reports/                    # Generated, git-ignored (FR-018)
├── allure-results/         # Allure result data (FR-024)
└── artifacts/              # Screenshots, traces, videos (FR-010)
```

**Structure Decision**: A single Python project using a `src/` layout for the importable support package (`src/ai_qa/`) and a sibling `tests/` tree. The five separations FR-017 requires map to real directories: tests by kind (`tests/ui/`, `tests/api/`, plus `tests/health/` for verification), shared fixtures (`tests/conftest.py`), page objects (`src/ai_qa/pages/`), test data (`tests/data/`), and generated artifacts (`reports/`).

Support code lives in `src/ai_qa/` rather than inside `tests/` for two reasons: it is importable and unit-testable in its own right, and the `src/` layout prevents tests from accidentally importing the package from the working directory instead of the installed environment — which would mask packaging errors that only appear on a clean checkout, the exact failure mode SC-003 exists to catch.

`pytest` configuration lives in `[tool.pytest.ini_options]` inside `pyproject.toml` rather than a separate `pytest.ini`, keeping one configuration file for the project (FR-001, FR-016).

Documentation is split by audience, per the 2026-10-03 clarification: `README.md` carries prerequisites, the ordered setup commands, and the dependency upgrade procedure for humans; `CLAUDE.md` carries directory layout, naming and fixture conventions, and the rules a recorded `codegen` draft must be refactored to meet (FR-014). The split exists because the two go stale differently — setup commands change when tooling changes, conventions change when the test suite grows — and because `CLAUDE.md` is loaded automatically in this project, making FR-014's "discoverable without per-session setup" a structural property rather than a hope that someone reads a link.

## Phase 0: Research

Complete — see [research.md](./research.md). Ten decisions resolved, zero `NEEDS CLARIFICATION` markers remaining. The five clarifications already settled in the spec's Clarifications session were taken as given and not re-litigated.

Highest-consequence findings:

- **`uv python` makes the interpreter a managed dependency.** This is what collapses the prerequisite list and is verified against the locally installed `uv` 0.12.22.
- **`pydantic-settings` is a separate distribution** from `pydantic` in v2. Had the plan reached for `BaseSettings` reflexively, it would have added a dependency FR-004 does not permit. `BaseModel` plus `python-dotenv` covers FR-023 exactly.
- **Allure's result files are UUID-named by construction**, so FR-024's collision-freedom is satisfied with no extra work; the per-test artifact paths under FR-010 are the part that needs deliberate design.
- **`playwright install-deps` requires root on Linux** and is not needed on Windows. This is the one genuine per-platform divergence FR-029 must document.
- **The lock-refresh command must be distinct from the setup command** (R11). `uv sync --locked` deliberately fails on a stale lock; `uv lock --upgrade` is the only thing that rewrites it. Keeping them separate is what makes "deliberately updated" in FR-005 enforceable rather than aspirational.

## Phase 1: Design

Complete. Artifacts:

| Artifact | Contents |
|---|---|
| [data-model.md](./data-model.md) | `Settings` model fields, validation rules, and failure messages; test-data file shape; artifact path construction rules |
| [contracts/commands.md](./contracts/commands.md) | Every command in the documented workflow: purpose, inputs, exit-code semantics, which requirement it satisfies |
| [contracts/configuration.md](./contracts/configuration.md) | The `.env` contract — each setting's name, type, required/optional status, default, and placeholder |
| [quickstart.md](./quickstart.md) | Clean-checkout walkthrough with expected outcomes, mapped to success criteria |

Contracts are included because this project does expose interfaces, just not network ones: a command surface that engineers and CI invoke, and a configuration surface that the `.env` contract defines. Both are things a consumer depends on and that can break compatibly or incompatibly, which is what makes them contracts worth writing down.

### Post-Design Constitution Re-Check

Unchanged from the pre-Phase 0 evaluation: **PASS, vacuously.** No principles exist. The design added no dependency beyond the FR-004 floor, introduced no second toolchain, and created no component whose complexity would need justification under a typical simplicity principle — so had the usual Spec Kit default principles been ratified, this design would be expected to clear them. That is an inference, not a verified result, and it is not a substitute for ratifying the constitution.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations to justify — the Constitution Check is empty rather than passed, and the design adds nothing requiring justification: zero dependencies beyond the mandated eight, one project, no second toolchain, no abstraction layer introduced ahead of a demonstrated need.

## Spec Deltas Discovered During Planning

Places where the design is at odds with the spec's literal wording. These are the spec needing a touch-up rather than the design needing a change, and none is a judgement call I should make silently.

| Spec text | What the design does | Recommended resolution |
|---|---|---|
| ~~**SC-011**: "Setup requires exactly two prerequisites outside the repository — a Python 3.12 interpreter and `uv`"~~ | `uv` provisions the interpreter, so the only external prerequisite is `uv`. One, not two. | **Resolved 2026-10-03** at the user's direction. SC-011 now reads "exactly one prerequisite"; FR-002 gained an explicit provisioning obligation and an exact-pin requirement; the "required language version absent or wrong" edge case changed from *detect and fail* to *provision*. |
| **FR-015**: `README.md` must document "that recording requires an attached display" | Still true, but the sharper constraint found in research is that `codegen` also cannot run against the default headless mode and is workstation-only by nature. | Keep FR-015 as written; no change needed. Recording this only so the stronger wording in `contracts/commands.md` is not mistaken for scope creep. |

| ~~**FR-026** enumerates **four** capabilities a single invocation confirms: test runner, browser, exploration CLI, reporting integration~~ | The design builds **five** health-check tests, because FR-019 and SC-004 both additionally require configuration validation. | **Resolved 2026-10-03** at the user's direction. FR-026 now enumerates all five, including configuration validation, matching FR-019 and SC-004. Was finding I3 from `/speckit.analyze`. |

**Status**: all three deltas closed. SC-011 and FR-026 were approved and applied on 2026-10-03; FR-015 needed no change. No outstanding spec-vs-design discrepancies.

Note that applying the SC-011 correction made the spec *stricter*, not more convenient: the prerequisite count dropped from two to one, FR-002 acquired an obligation the design must now meet (provision the interpreter when absent, with a pin narrow enough that another minor version cannot satisfy it), and the related edge case changed from "detect and fail" to "provision". The plan already satisfies all three via R1.
