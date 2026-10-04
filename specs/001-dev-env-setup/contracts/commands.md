# Command Contract: Development Environment Bootstrap

**Feature**: `001-dev-env-setup` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

This project's public interface is a command surface, not a network API. Engineers and (later) CI depend on these commands and their exit codes, so they are specified here as a contract: changing a command's name, required arguments, or exit-code semantics is a breaking change to everyone's muscle memory and every pipeline.

Every command is given in `uv run` form. There is no activation step on any platform (R9).

---

## Prerequisites

| Prerequisite | Version | Why | Obtained from |
|---|---|---|---|
| `uv` | ≥ 0.5 | Provisions the interpreter, resolves dependencies, runs every command | <https://docs.astral.sh/uv/getting-started/installation/> |

That is the complete list, and SC-011 requires it to stay that length. Python itself is **not** a prerequisite — `uv` downloads the pinned 3.12 interpreter (R1).

**Supported platforms**: Windows and Linux. macOS is untested and unsupported (R12); `README.md` must state that rather than leave it to inference (FR-029).

| Optional | Version | Needed for |
|---|---|---|
| Allure CLI | ≥ 2.20 | Rendering result data into a browsable report. Requires a Java runtime (1.8+). Not needed for any verification check. |

---

## Setup commands

Run in this order from the repository root. Each must exit `0` before the next is meaningful.

### 1. `uv sync --locked`

| | |
|---|---|
| **Purpose** | Provision CPython 3.12 if absent, create `.venv/`, install the exact versions in `uv.lock` |
| **Inputs** | `pyproject.toml`, `uv.lock`, `.python-version` |
| **Exit 0** | Environment matches the lock file exactly |
| **Non-zero** | Lock file is stale relative to `pyproject.toml`, or a download failed. **Does not re-resolve** — staleness is an error, which is what protects SC-003 |
| **Network** | Required — interpreter and packages |
| **Satisfies** | FR-003, FR-005, FR-006, FR-007 |

### 2. `uv run playwright install chromium firefox webkit`

| | |
|---|---|
| **Purpose** | Download browser binaries, which `uv sync` does not cover |
| **Exit 0** | All three browsers present in the Playwright cache |
| **Non-zero** | Download failure or unsupported platform |
| **Network** | Required |
| **Re-run when** | The `playwright` package is upgraded — binaries are version-matched to the library |
| **Satisfies** | FR-008 |

### 2a. `uv run playwright install-deps` — **Linux only**

| | |
|---|---|
| **Purpose** | Install the OS shared libraries browsers link against |
| **Platform** | Linux only. Not needed and not available on Windows |
| **Requires** | Root/`sudo` |
| **Satisfies** | FR-029 — the one genuine per-platform divergence in this contract |

### 3. `cp .env.example .env` *(PowerShell: `Copy-Item .env.example .env`)*

| | |
|---|---|
| **Purpose** | Create the local, uncommitted configuration file, then edit in real values |
| **Exit 0** | `.env` exists |
| **Caution** | Never edit `.env.example` with real values — it is committed (FR-020) |
| **Satisfies** | FR-019, FR-021, FR-022 |

This is the only command whose syntax differs between shells, and the difference is a file copy rather than anything project-specific.

---

## Verification

### `uv run pytest -m healthcheck`

The verification gate. Per the spec's clarification, verification is these tests — not a list of commands a person runs and eyeballs (FR-026).

| | |
|---|---|
| **Purpose** | Assert each environment capability independently |
| **Exit 0** | All five health-check tests pass: dependencies import, browser launches, Allure plugin registered, Playwright CLI responds, settings validate |
| **Non-zero** | At least one capability missing. Each failure names the missing prerequisite or step (SC-009) |
| **Runtime** | Under 60 s on a correctly set up environment (SC-007) |
| **Network** | Not required — the browser check uses a `data:` URL (R10) |
| **Satisfies** | FR-019, FR-026, FR-027; verifies SC-004 |

`--strict-markers` is enabled, so a mistyped `-m healthchek` is an immediate error rather than a zero-test run reporting success (R8).

---

## Running tests

| Command | Purpose |
|---|---|
| `uv run pytest` | Full suite. Allure results and artifact paths are already configured via `addopts`, so this behaves identically to a fully specified invocation (FR-016) |
| `uv run pytest -m ui` | Browser-driven tests only |
| `uv run pytest -m api` | Service tests only |
| `uv run pytest --headed` | Run with a visible browser. Requires a display (FR-009) |
| `uv run pytest --browser firefox` | Override the configured browser |

**Exit codes** are pytest's standard set: `0` all passed, `1` tests failed, `2` interrupted, `3` internal error, `4` usage error, `5` no tests collected. A pipeline must treat `5` as failure — a run that collected nothing is not a passing run.

---

## Exploration and recording

### `uv run playwright codegen <url>`

| | |
|---|---|
| **Purpose** | Drive a browser, record interactions, emit runnable test code to refactor (User Story 4) |
| **Requires** | An attached display — this is interactive and inherently workstation-only. It cannot run on a headless CI machine, and that is not a defect |
| **Output** | Generated code printed to the inspector window for copying; `--output <file>` writes it to disk |
| **Resolution** | Via `uv run`, so it is always the project-pinned Playwright, never a global or Node-based copy (FR-012, R5) |
| **Satisfies** | FR-011, FR-015 |

### `uv run playwright --version`

Prints the project-pinned Playwright version. The health-check test performs this check as a subprocess through `sys.executable` rather than by `PATH` lookup, so it cannot be satisfied by a foreign copy (R5).

---

## Upgrading dependencies

A deliberate, documented procedure — not something any setup command does as a side effect (FR-005, R11). Run all three steps together.

### 1. `uv lock --upgrade`

| | |
|---|---|
| **Purpose** | Re-resolve dependencies to their newest compatible versions and rewrite `uv.lock` |
| **Exit 0** | Lock refreshed |
| **Note** | The **only** command in this contract that rewrites the lock. `uv sync --locked` deliberately fails on a stale lock instead of updating it, so versions cannot drift accidentally |

### 2. `uv run playwright install chromium firefox webkit`

**Mandatory after step 1**, not optional. Browser binaries are version-matched to the `playwright` package; skipping this leaves binaries that no longer match the upgraded library, and the resulting launch error does not mention the upgrade that caused it.

### 3. Commit `uv.lock` as its own change

A version bump must be reviewable on its own rather than buried in an unrelated diff (FR-005).

**Then re-verify**: `uv run pytest -m healthcheck` before trusting the upgraded environment.

---

## Reporting

| Command | Purpose | Notes |
|---|---|---|
| `uv run pytest` | Writes Allure result data to `reports/allure-results/` | Configured by default in `addopts`; no flag to remember (FR-024) |
| `allure serve reports/allure-results` | Renders results as a browsable report | **Optional.** Requires the separately installed Allure CLI and a Java runtime. Not needed for SC-004 (FR-025) |

---

## Compatibility notes

What would constitute a breaking change to this contract, and therefore needs a deliberate decision rather than a drive-by edit:

- Renaming a marker (`healthcheck`, `ui`, `api`, `smoke`) — breaks documented commands and any pipeline selecting them.
- Moving `--alluredir` or artifact output out of `addopts` — a bare `uv run pytest` would stop producing results, silently.
- Requiring Python as a manual prerequisite — reintroduces the version-mismatch failure R1 removed, and breaks SC-011's one-prerequisite bound.
- Adding any command that requires Node.js or a second package manager — prohibited by FR-013 and measured by SC-011.
- Making any setup command rewrite `uv.lock` — collapses the separation that makes FR-005's "deliberately updated" enforceable.
