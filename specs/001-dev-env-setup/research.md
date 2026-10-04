# Phase 0 Research: Development Environment Bootstrap

**Feature**: `001-dev-env-setup` | **Date**: 2026-10-03 | **Plan**: [plan.md](./plan.md)

Twelve decisions, each stated as Decision / Rationale / Alternatives considered. The eight questions already answered in the spec's Clarifications session (2026-10-03) are treated as settled input, not re-opened; R11 and R12 record the design consequences of the last three.

**Local toolchain probed on 2026-10-03** (informs R1, R5, R9):

| Tool | Result | Consequence |
|---|---|---|
| `python --version` | 3.14.7 | Wrong version — must not be used for this project |
| `py -3.12 --version` | No suitable runtime found | **No Python 3.12 on this machine** |
| `uv --version` | 0.12.22 | Present; can provision interpreters |
| `node --version` | v26.8.2 | Present but forbidden by FR-013 |
| `java -version` | 1.8.0_503 | Allure CLI would run if installed |
| `allure --version` | not found | Optional report renderer absent, as the spec anticipated |

---

## R1: Interpreter provisioning

**Decision**: Commit `.python-version` containing `3.12` and set `requires-python = "==3.12.*"` in `pyproject.toml`. `uv sync` downloads and pins CPython 3.12 automatically. `uv` becomes the single external prerequisite.

**Rationale**: The machine this project starts on has no Python 3.12 at all — only 3.14.7. Treating the interpreter as a manual prerequisite would make the very first documented command fail on the very first machine, and would make SC-002 ("100% of setup commands succeed on a machine with no prior project state") depend on an engineer correctly installing a specific minor version by hand. Letting `uv` own the interpreter makes the pinned version a property of the repository rather than of the machine, which is what FR-005 and SC-003 are really asking for. The exact pin `==3.12.*` rather than `>=3.12` matters: a range would let `uv` satisfy the constraint with the locally installed 3.14.7 and silently defeat FR-002.

**Alternatives considered**:
- *Document installing Python 3.12 manually* — rejected: two prerequisites instead of one, and the common failure (engineer has 3.11 or 3.13) produces a confusing resolution error rather than a clear one.
- *`requires-python = ">=3.12"`* — rejected: would resolve against system 3.14.7 here, violating FR-002 while appearing to work.
- *pyenv / asdf* — rejected: a third tool to install, and FR-013 restricts the toolchain to Python and `uv`.

## R2: Dependency declaration and locking

**Decision**: `uv add` for each of the eight packages, writing `[project.dependencies]` in `pyproject.toml` and a committed `uv.lock`. Clean-checkout installs use `uv sync --locked`, which fails rather than re-resolving if the lock is stale.

**Rationale**: `--locked` is the difference between "reproducible" and "probably the same". A plain `uv sync` will silently update the lock when `pyproject.toml` has drifted, which would let two checkouts diverge and quietly break SC-003. Failing loudly is the correct behaviour for a setup step whose entire purpose is reproducibility. Committing the lock satisfies FR-005 directly.

**Alternatives considered**:
- *`requirements.txt` + `uv pip install`* — rejected: no lock semantics, no dependency groups, and FR-001 wants configuration in `pyproject.toml`.
- *Hand-pinned exact versions in `pyproject.toml`* — rejected: pins direct dependencies only, leaving transitive versions free, so checkouts still diverge.
- *`uv sync` without `--locked`* — rejected for the reason above.

## R3: Configuration validation without adding a dependency

**Decision**: Load `.env` with `python-dotenv`, then validate into a `pydantic.BaseModel` subclass. Do **not** add `pydantic-settings`.

**Rationale**: This is the one place the plan nearly added a package by reflex. In pydantic v2, `BaseSettings` was moved out of `pydantic` into the separate `pydantic-settings` distribution, so the idiomatic "settings model" import is not available from the mandated dependency. But FR-023 only requires that configuration be validated at startup and that a missing or malformed setting fail immediately naming the offending setting — which `BaseModel` plus explicit `os.environ` reads does completely, since pydantic's `ValidationError` already names the offending field. FR-004 permits additions only where a requirement cannot otherwise be met; this one can, so adding the package would violate the clarified dependency rule.

**Alternatives considered**:
- *Add `pydantic-settings`* — rejected: more ergonomic, but FR-004 forbids convenience additions and the clarification was explicit that each addition must name a requirement it alone satisfies.
- *Plain `os.environ` with manual checks* — rejected: `pydantic` is already mandated and gives typed coercion and field-naming error messages for free; hand-rolling that is more code and worse messages.

## R4: Browser installation

**Decision**: `uv run playwright install chromium firefox webkit` as an explicit, separately documented setup step. On Linux, document `uv run playwright install-deps` as an additional root-requiring step.

**Rationale**: Browser binaries are not Python packages and are not covered by `uv sync`, which is precisely why FR-008 demands an explicit documented step — skipping it is the single most common setup failure and produces a launch error that names nothing useful. Installing all three browsers matches the spec's stated assumption even though only Chromium is verified, because the marginal download cost is paid once and a later cross-browser test then needs no new setup. `install-deps` is the one genuinely platform-divergent command and needs elevation on Linux, so FR-029 must document it separately rather than folding it into a shared command list.

**Alternatives considered**:
- *Chromium only* — rejected: contradicts the spec's browser-coverage assumption and forces a setup change the first time a cross-browser test is written.
- *`--with-deps` always* — rejected: unnecessary on Windows and prompts for elevation, making the primary platform's happy path worse.

## R5: Playwright CLI resolution

**Decision**: Invoke the CLI as `uv run playwright ...` in documentation, and in the health-check test invoke it as a subprocess using `sys.executable -m playwright --version`.

**Rationale**: FR-012 requires the tool to resolve to the project-pinned version, and the spec's own edge case calls out the failure where a global copy at a different version answers instead. `shutil.which("playwright")` would find whatever is first on `PATH` — exactly the wrong answer. Going through `sys.executable` guarantees the interpreter running the test is the interpreter providing the CLI, which makes the check structurally incapable of passing against a foreign copy. Node 26.8.2 is present on this machine, which makes the `npx playwright` route tempting and is precisely why FR-013's prohibition needs to be enforced by construction rather than by discipline.

**Alternatives considered**:
- *`shutil.which("playwright")`* — rejected: verifies something is on `PATH`, not that it is the project's version.
- *Import `playwright` and read `__version__`* — rejected: proves the library is importable, not that the command-line entry point works, which is what Story 4 depends on.

## R6: Parallel-safe fixtures and artifact paths

**Decision**: All fixtures function-scoped. `pytest-playwright`'s own `page`/`context` fixtures are already function-scoped and are used as-is. Artifact paths derive from the test's node ID, sanitised, under `reports/artifacts/`. Serial execution remains the default; no parallel-execution plugin is added.

**Rationale**: The clarified answer was parallel-ready, not parallel-enabled, and the cost of readiness is entirely in these two choices — both made now, for free. The failure mode being designed out is a session-scoped browser or a fixed artifact filename, either of which forces a rewrite of shared fixture code the moment workers are added. Node-ID-derived paths are collision-free by construction because pytest node IDs are unique within a run.

**Alternatives considered**:
- *Session-scoped browser fixture for speed* — rejected: the standard parallel-safety trap, and SC-007's 60-second budget is met comfortably without it.
- *Add `pytest-xdist` now* — rejected: FR-004 forbids anticipatory additions, and a five-test suite cannot demonstrate a benefit.

## R7: Allure result output

**Decision**: Default `--alluredir=reports/allure-results` via `addopts` in `[tool.pytest.ini_options]`. Document `allure serve reports/allure-results` as an optional rendering step requiring the separately installed Allure CLI and a Java runtime.

**Rationale**: Putting `--alluredir` in `addopts` satisfies FR-016's requirement that a bare run behave identically to a fully specified one, and FR-024's collision-freedom needs no work because `allure-pytest` names each result file with a generated UUID. Keeping the renderer optional matches the spec's assumption and keeps SC-004 passable on a machine without Java — though Java 1.8.0_503 is in fact present here, so an engineer on this machine only needs the Allure CLI itself.

**Alternatives considered**:
- *Require the Allure CLI in setup* — rejected: adds a Java prerequisite, contradicting SC-011's minimal-prerequisite intent for a step the spec marks optional.
- *Pass `--alluredir` manually per run* — rejected: violates FR-016 and means a forgotten flag silently produces no results.

## R8: pytest configuration location and markers

**Decision**: `[tool.pytest.ini_options]` in `pyproject.toml`. `testpaths = ["tests"]`, strict markers, and registered markers `healthcheck`, `ui`, `api`, `smoke`. Default `addopts` fix `--alluredir`, artifact output, and tracing/screenshot-on-failure.

**Rationale**: One configuration file rather than two keeps FR-001 honest. `--strict-markers` turns a typo'd marker into an immediate error instead of a silently-selects-nothing run, which matters because FR-019 makes `-m healthcheck` the documented verification command — a typo there would report success by running zero tests, the worst possible failure for a verification gate.

**Alternatives considered**:
- *Separate `pytest.ini`* — rejected: a second configuration file for no benefit; `pyproject.toml` is already mandated by FR-001.
- *Unregistered markers* — rejected: silent no-op runs, as above.

## R9: Cross-platform command set

**Decision**: Document every command in `uv run` form. No virtual-environment activation step. One shared command list, with Linux-only `install-deps` called out separately.

**Rationale**: Activation is the main source of per-platform divergence in Python documentation (`.venv\Scripts\activate` versus `source .venv/bin/activate`), and `uv run` eliminates it by resolving the environment itself. This reduces FR-029's per-platform variants to the single genuine case in R4, rather than duplicating every command for two shells. Windows is the primary platform per the spec, and this keeps its path identical to Linux CI's.

**Alternatives considered**:
- *Document activation per platform* — rejected: doubles every command block and introduces the "forgot to activate" failure class.
- *Makefile or task runner* — rejected: a Makefile is not portable to stock Windows, and a task runner is a dependency FR-004 forbids.

## R10: Health-check test composition

**Decision**: Five independent tests in `tests/health/test_environment.py`, marked `healthcheck`: (1) every mandated dependency imports and reports a version, (2) a Chromium browser launches and loads a `data:` URL, (3) `allure-pytest` is registered with the plugin manager, (4) the Playwright CLI reports its version via subprocess, (5) settings load and validate from the environment. Each asserts with a message naming the missing prerequisite.

**Rationale**: The clarified answer made these tests the verification mechanism, so they must fail *diagnostically*, not just fail. Independence matters more than it looks: a single combined test would stop at the first failure and report one problem when three are present, which defeats SC-009's requirement that each missing prerequisite be named. Test 2 uses a `data:` URL rather than a real site so the browser check does not depend on network reachability or on the not-yet-known application under test — otherwise an offline machine would report a broken environment when the environment is fine.

**Alternatives considered**:
- *One combined smoke test* — rejected: masks simultaneous failures, violating SC-009.
- *Load a real URL in the browser check* — rejected: couples environment verification to network and to an external site's uptime.
- *A shell script instead of tests* — rejected by the spec's clarification; a script is also not run by CI's test step and so drifts.

## R11: Dependency upgrade procedure

**Decision**: Upgrades are a documented manual procedure in `README.md`: `uv lock --upgrade` to refresh the lock, then `uv run playwright install chromium firefox webkit` to re-match browser binaries, then commit the refreshed `uv.lock` as its own change. No automated update tooling.

**Rationale**: FR-005 says versions hold "until the lock file is deliberately updated", and the clarification of 2026-10-03 made *deliberately* mean this procedure. The design point worth stating is that the refresh command is deliberately **not** the setup command: `uv sync --locked` fails on a stale lock rather than rewriting it (R2), so the only way to change versions is to run `uv lock --upgrade` on purpose. That separation is what makes FR-005 enforceable instead of aspirational — there is no command in the documented happy path that can silently move a version.

Pairing the browser re-install into the same written procedure addresses the spec's "stale browser binaries after a dependency upgrade" edge case at its actual cause: the binaries are version-matched to the `playwright` package, and an engineer who bumps the package without re-installing gets a launch failure whose message does not mention the upgrade they just did. Requiring the lock to be committed separately keeps a version bump reviewable rather than buried in an unrelated diff.

**Alternatives considered**:
- *Automated update bot* — rejected: requires a CI pipeline, which this feature's assumptions place out of scope. Revisit when CI exists.
- *No documented procedure* — rejected: the likeliest source of the "works on my machine" divergence SC-003 exists to prevent, and it leaves the browser re-install to memory.
- *Pin exact versions in `pyproject.toml` and skip the lock* — rejected in R2; also makes every upgrade a manual edit of eight version strings.

## R12: Platform support scope

**Decision**: Windows and Linux are supported and both are SC-002 verification targets. macOS is unsupported and `README.md` must say so explicitly.

**Rationale**: Settled by the 2026-10-03 clarification rather than by research, recorded here because it constrains the design. Nothing in this plan is platform-specific — `uv run` removes the activation divergence (R9) and the only per-platform command is Linux's `install-deps` (R4) — so macOS would very probably work. But SC-002 demands verified success on every supported platform, and a platform nobody runs cannot be verified. Declaring it unsupported keeps the criterion honest; the alternative is a claim that fails the first time someone on a Mac trusts it.

**Alternatives considered**:
- *Claim macOS support untested* — rejected: this is what the spec said before the clarification, and it made SC-002 unverifiable by construction.
- *Add macOS as a verification target* — rejected: would block feature completion on access to hardware the project does not have.

---

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain. For the record, these were resolved rather than deferred:

| Unknown from Technical Context | Resolved by |
|---|---|
| How is Python 3.12 obtained when absent? | R1 — `uv` provisions it |
| How is FR-023 met without `pydantic-settings`? | R3 — `BaseModel` + `python-dotenv` |
| How does the CLI check avoid a global copy? | R5 — `sys.executable -m playwright` |
| What makes artifact paths collision-free? | R6 — node-ID-derived paths |
| Where does pytest configuration live? | R8 — `pyproject.toml` |
| How many per-platform command variants are needed? | R9 — one (Linux `install-deps`) |
| What does "deliberately updated" mean for the lock file? | R11 — `uv lock --upgrade`, browser re-install, separate commit |
| Is macOS in scope? | R12 — no; Windows and Linux only |
