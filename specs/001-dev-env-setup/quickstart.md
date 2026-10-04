# Quickstart Validation: Development Environment Bootstrap

**Feature**: `001-dev-env-setup` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

How to prove this feature works, from a clean checkout. This is the validation walkthrough, not the project `README.md` — the README is a deliverable of implementation (FR-028) and will carry the same commands for an audience that wants to use the project rather than verify it.

Command details and exit-code semantics: [contracts/commands.md](./contracts/commands.md). Configuration: [contracts/configuration.md](./contracts/configuration.md).

---

## Prerequisite

Only `uv`. Python is not required on the machine — `uv` provisions the pinned 3.12 interpreter (R1 in [research.md](./research.md)).

**Platforms**: validate on Windows and Linux. macOS is out of scope for this feature (R12), so a macOS run proves nothing about SC-002 either way.

```bash
uv --version    # expect >= 0.5
```

---

## Scenario 1 — Clean-checkout bootstrap (validates User Story 1, P1)

Start from a checkout with no `.venv/`, no `.env`, and no project state.

```bash
uv sync --locked
uv run playwright install chromium firefox webkit
# Linux only, needs root:
# uv run playwright install-deps
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
uv run pytest -m healthcheck
```

**Expected**: every command exits `0`; the final command reports 5 passed in under 60 seconds.

| Validates | How |
|---|---|
| SC-001 | Time the whole block end to end — under 15 minutes including downloads |
| SC-002 | Every command above exits `0`, in this order, on a machine with no prior state — run on **both** Windows and Linux |
| SC-004 | The five health-check tests pass in one invocation, with no manual checks |
| SC-007 | The final command completes in under 60 s |
| SC-011 | Only `uv` was installed beforehand; no other runtime or package manager |

**Reproducibility check (SC-003)**: run the block on a second machine of the same OS and compare `uv.lock` — it must be unchanged, and `uv sync --locked` must not have rewritten it. A non-zero exit here means the lock is stale relative to `pyproject.toml`, which is the failure mode `--locked` exists to surface.

---

## Scenario 2 — Browser automation, visible and unattended (validates User Story 2, P2)

```bash
uv run pytest -m healthcheck -k browser              # unattended, default
uv run pytest -m healthcheck -k browser --headed     # visible window
```

**Expected**: both pass. The first opens no window; the second shows a browser briefly.

To confirm failure evidence (FR-010), temporarily make a browser test fail and check that `reports/artifacts/<sanitised-node-id>/` is created with a screenshot and trace, and that the directory name contains the failing test's node ID. Revert the change afterwards.

---

## Scenario 3 — Secret-safe configuration (validates User Story 3, P2)

```bash
grep BASE_URL .env.example          # shows a placeholder, not a real URL
git check-ignore -v .env            # confirms .env is ignored
git status --porcelain              # after a test run: no reports/, .venv/, or .env
```

**Expected**: `.env.example` contains only placeholders; `.env` is reported as ignored; `git status` lists no generated files.

Then confirm fail-fast validation:

```bash
mv .env .env.bak
uv run pytest -m healthcheck        # expect a UsageError naming BASE_URL
mv .env.bak .env
```

| Validates | How |
|---|---|
| SC-005 | `.env.example` is the only committed config file and holds no real values; no `.env` in history |
| SC-006 | `git status --porcelain` is empty after a full run |
| SC-008 | Every variable the suite reads appears in `.env.example` — cross-check against the `Settings` model |
| SC-009 | The missing-`.env` run names `BASE_URL` rather than failing somewhere unrelated |

---

## Scenario 4 — Exploration and recording (validates User Story 4, P3)

Workstation only — this is interactive and needs a display.

```bash
uv run playwright --version
uv run playwright codegen https://example.com
```

**Expected**: the version command prints the project-pinned Playwright version. `codegen` opens a browser and an inspector; clicking around emits Python test code.

Confirm project-local resolution (FR-012): the printed version must match `playwright` in `uv.lock`, not any globally installed copy. Node 26.8.2 is present on this machine, so also confirm nothing in the documented path invokes `npx` — FR-013 and SC-011 both forbid it.

---

## Scenario 5 — Shareable report (validates User Story 5, P3)

```bash
uv run pytest
ls reports/allure-results            # UUID-named result files, one set per test
```

**Expected**: result data is written with no extra flag, because `--alluredir` is already in `addopts`.

Optional rendering, requiring the separately installed Allure CLI and a Java runtime — Java 1.8.0_503 is present here, the Allure CLI is not:

```bash
allure serve reports/allure-results
```

A missing Allure CLI must not fail the test run (FR-025).

---

## Scenario 6 — Idempotent re-run (validates FR-007)

```bash
uv sync --locked
uv run playwright install chromium firefox webkit
uv run pytest -m healthcheck
```

**Expected**: re-running over an already-built environment exits `0` throughout, with no manual cleanup and no mixed state. Both setup commands are no-ops when everything is current.

---

## Scenario 7 — Dependency upgrade procedure (validates FR-005, FR-028)

Confirms a version bump cannot happen by accident and cannot leave mismatched browsers behind.

```bash
git diff --stat uv.lock        # baseline: unchanged
uv sync --locked               # must NOT rewrite the lock
git diff --stat uv.lock        # still unchanged — this is the point
```

**Expected**: a setup command never rewrites the lock. Then run the deliberate upgrade:

```bash
uv lock --upgrade
uv run playwright install chromium firefox webkit
uv run pytest -m healthcheck
```

**Expected**: `uv.lock` changes only now; browsers are re-matched to the upgraded library; health checks still pass. Verify `README.md` documents all three steps, including that the browser install is mandatory rather than advisory.

Revert with `git checkout uv.lock && uv sync --locked` if you were only validating.

---

## Project guidance review (validates FR-014)

A read rather than a command: confirm `CLAUDE.md` exists, is separate from `README.md`, and states the directory layout, naming and fixture conventions, and what a recorded `codegen` draft must be refactored to meet. Pass condition: an assistant given a raw `codegen` draft could place and rewrite it correctly from `CLAUDE.md` alone, with no human explaining the project.

---

## Parallel-readiness review (validates SC-012)

A code review rather than a command, because nothing enables parallelism yet (the clarified decision was parallel-ready, not parallel-enabled):

- Every fixture in `tests/conftest.py` is function-scoped, except the frozen `Settings` fixture — justified in [data-model.md](./data-model.md) §1.
- No artifact path is a fixed filename; each derives from the test's node ID.
- Allure result filenames are UUID-generated by the plugin.

Pass condition: enabling parallel execution would require no change to any fixture, test, or artifact path.

---

## Coverage summary

| User Story | Priority | Scenario |
|---|---|---|
| 1 — Clean-checkout bootstrap | P1 | 1, 6 |
| 2 — Real browser test | P2 | 2 |
| 3 — Secret-safe configuration | P2 | 3 |
| 4 — Explore and record | P3 | 4 |
| 5 — Shareable report | P3 | 5 |
| Cross-cutting: idempotence, upgrades, guidance | — | 6, 7, guidance review |

All twelve success criteria are exercised: SC-001 through SC-004, SC-007 and SC-011 in Scenario 1; SC-005, SC-006, SC-008 and SC-009 in Scenario 3; SC-010 by running Scenarios 1, 2 and 5 on a machine with no display; SC-012 by the review above.
