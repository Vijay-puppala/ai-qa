# AI-QA — project conventions

Guidance for an AI assistant working in this repository. Human setup
instructions live in [README.md](./README.md); this file is about *where code
goes and what it must look like*.

---

## Toolchain constraint (hard)

**Python and `uv` only.** No Node.js, no second package manager, no additional
language runtime — even though Node may be installed on the machine. The
Playwright CLI used here is the one shipped with the Python `playwright`
package, not `npx playwright`.

Every command goes through `uv run`. Never instruct anyone to activate a
virtual environment.

## Dependencies

The dependency set is a **minimum floor, not an open invitation**. Adding a
package requires naming the specific requirement that cannot be satisfied
without it. Convenience, preference, and "we'll probably need it" are not
reasons.

Notably: use `pydantic.BaseModel` plus `python-dotenv` for configuration.
Do **not** add `pydantic-settings` — in pydantic v2 it is a separate
distribution, and `BaseModel` already does the job here.

---

## Where things go

| What | Where |
|---|---|
| Browser-driven tests | `tests/ui/test_*.py` |
| Service/API tests (use `httpx`) | `tests/api/test_*.py` |
| Environment health checks | `tests/health/test_environment.py` |
| Shared fixtures | `tests/conftest.py` |
| Page objects | `src/ai_qa/pages/` |
| YAML test data | `tests/data/*.yaml` |
| Reusable helpers | `src/ai_qa/` |
| Generated output | `reports/` (git-ignored, never commit) |

Support code belongs in `src/ai_qa/`, not in `tests/`. The `src/` layout is
deliberate: it stops tests importing the package from the working directory and
masking a packaging error that would only show up on a clean checkout.

## Markers

Registered in `pyproject.toml`: `healthcheck`, `ui`, `api`, `smoke`.

`--strict-markers` is on, so an unregistered marker is an error rather than a
silent no-op. Register a new marker in `pyproject.toml` before using it.

---

## Fixture rules (these are load-bearing)

**Every fixture is function-scoped**, with exactly two documented exceptions:
`settings` and `base_url`. Both are safe only because they are immutable values
derived from the process environment, and under parallel execution each worker
is a separate process.

Do not introduce a session- or module-scoped fixture holding mutable state — a
shared browser or a reusable logged-in context being the classic temptation.
The suite runs serially today but **must stay parallel-ready**: enabling
parallel execution has to remain a configuration change, never a refactor of
fixture code.

**Never hard-code an artifact filename.** Derive every generated path from the
test's node ID (see the `artifact_dir` fixture), so concurrent tests cannot
overwrite each other's evidence.

`base_url` deliberately overrides the fixture from `pytest-base-url`, which is
what wires `BASE_URL` from `.env` into `page.goto("/relative")`. It must stay
**session**-scoped — `pytest-base-url` has a session-scoped autouse fixture
that requests it, and a function-scoped override raises `ScopeMismatch` for
every test in the suite.

## Configuration

All configuration comes from `.env`, validated through the `Settings` model in
`src/ai_qa/config.py`. YAML is for test data only — never configuration.

Reading `os.environ` anywhere outside `Settings` is a contract violation: the
setting becomes invisible to `.env.example`, and the next person has to read
code to discover it. Adding a setting means three edits — the model, the
`_ENV_PREFIXES` tuple, and `.env.example` (with a placeholder, never a real
value).

## The approval gate (feature 004)

**Generated designs are not optional to approve.** Do not write automation for
a design that is `PENDING`, `REJECTED` or `STALE` - call
`ai_qa.approval.require_approval(path, records_dir=...)` and let it refuse.

**Never carry your own approval check at a call site.** The enforcement point
is `src/ai_qa/approval/gate.py` and every route funnels through it. A guard
duplicated per entry point is one somebody eventually forgets, and features
003 and 005 each add an entry point.

**The digest covers the design portion only** - names, markers, docstrings.
Never digest the whole file: writing a body is the act the approval authorises,
so a whole-file digest would void every approval the moment its automation was
written and deadlock the whole workflow.

Hand-written tests without `generated-by: ai-qa` are **unmanaged** and are
reported, never blocked.

## Generated test skeletons (feature 003)

A skeleton is a **test design**: real test functions with names, markers and
docstrings, and a body that does not yet assert anything. The three states of
one artifact are *test design* -> *skeleton* (unimplemented) -> *completed
automation*.

### Where things go

| What | Where |
|---|---|
| Browser-driven tests | `tests/ui/test_<behaviour_area>.py` |
| Service/API tests | `tests/api/test_<behaviour_area>.py` |
| Generated skeletons | the same places - named for behaviour, never for the ticket |

A ticket is a unit of work; a test file is a unit of behaviour. Do not name a
file after a ticket key.

### The unimplemented marker

```python
from ai_qa.generate.sentinel import skip_reason

def test_expired_card_is_rejected():
    """Checkout refuses an expired card and shows the user why."""
    pytest.skip(skip_reason())
```

**Import `skip_reason` / `SKELETON_SENTINEL`; never type the literal.** Three
features depend on that string - 003 writes it, 004 counts it to report partial
implementation, 005 detects completion by its absence. A copy drifts by one
character and silently breaks detection in two of them.

Use `pytest.skip` in the body, not `@pytest.mark.skip` and never `xfail`: a
skeleton must be **incapable of reporting as passed**, and `xfail` can report
`xpass`.

### Required markers

`pytest.mark.ticket("<KEY>")` plus one of `ui` / `api`. The ticket marker
carries an argument, which matters: `allure-pytest` drops markers with
arguments, so feature 005 adds a conftest hook to turn it into a label. The
marker is still required - it is what `--ticket` selects on.

### Docstrings are not decoration

Feature 004 approves the **design**: names, markers and docstrings, and its
digest covers exactly those. The docstring states the behaviour the test must
prove, so it is part of the approved content. Feature 005's repair boundary
rests on it too - an assertion may not be changed because it *implements the
behaviour the docstring claims*. A vague docstring weakens both features.

### Refactoring a recorded `codegen` draft

1. Move it to `tests/ui/test_<behaviour>.py`
2. Replace positional selectors with role- or label-based locators
3. Extract interactions into a page object under `src/ai_qa/pages/`
4. Replace the hard-coded URL with a relative path - `base_url` supplies the host
5. Move literal inputs into `tests/data/*.yaml`
6. Add the `ui` marker and a docstring naming the behaviour protected
7. Delete `codegen`'s explicit waits - Playwright assertions auto-wait

### Provenance

Every generated file carries seven provenance fields in its module docstring,
including `generated-by-identity`. That field is not used by feature 003 at
all - feature 004 needs it to enforce "the approver may not be the author", and
authorship is only knowable at generation time.

## Jira access (feature 002)

**All Jira access goes through `src/ai_qa/jira/`, over REST, from this
project.** Never use an MCP server, an assistant connector, or any external
tooling for Jira at runtime - no Jira capability may require an AI assistant to
be present. This is FR-002 of feature 002 and it is measured by SC-003.

**The client is read-only.** It has no method that modifies Jira, and that is a
property of the type rather than a setting: write operations were deferred on
2026-10-04 because nothing in the project needed them. Adding one back is a
specification change for the feature that needs it, not a method addition -
`tests/jira/test_no_write.py` will fail if a write method or a mutating HTTP
verb appears.

Reach for `JiraClient` via a fixture or construct it directly; both paths share
one client so their behaviour and error handling cannot diverge.

## Secrets

Real values live in `.env` only, which is git-ignored. `.env.example` is
committed and carries placeholders.

There is **no secret-scanning tooling** in this repo. The ignore rule protects
the configuration *file*; it does nothing about a credential pasted inline into
a test, a fixture, or a doc. Do not write one, and flag it if you see one.

---

## Refactoring a recorded `codegen` draft

`uv run playwright codegen` produces a working draft with brittle output. Before
it is committed:

1. **Move it** to `tests/ui/test_<feature>.py`.
2. **Replace positional selectors** with role- or label-based locators —
   `page.get_by_role("button", name="Submit")`, not `page.locator("div:nth-child(3) > button")`.
3. **Extract page interactions** into a page object under `src/ai_qa/pages/`,
   subclassing `BasePage`. Name methods for intent (`submit_login`), not
   mechanics (`click_button`).
4. **Replace the hard-coded URL** with a relative path — `base_url` supplies
   the host from `.env`.
5. **Move literal inputs** into `tests/data/*.yaml` and load them with
   `ai_qa.data.load`, especially where the same values appear in several tests.
6. **Add the `ui` marker** and a docstring saying what user-visible behaviour
   the test protects.
7. **Drop `codegen`'s waits.** Playwright's assertions auto-wait; explicit
   `wait_for_timeout` calls are flake waiting to happen.

A recorded draft is a starting point, not a test.
