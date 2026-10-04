# AI-QA

AI-assisted QA automation platform: pytest + Playwright, with Allure reporting
and YAML-driven test data.

---

## Prerequisites

| Prerequisite | Version | Install |
|---|---|---|
| [`uv`](https://docs.astral.sh/uv/getting-started/installation/) | ≥ 0.5 | See link |

**That is the whole list.** Python is *not* a prerequisite — `uv` downloads and
pins CPython 3.12 for this project (`.python-version`), so you do not need a
system Python, and a newer system Python will not be used by accident.

Setup needs network access for three downloads: the interpreter, the Python
packages, and the browser binaries.

### Supported platforms

| Platform | Status |
|---|---|
| Windows | Supported, verified |
| Linux | Supported, verified |
| macOS | **Untested and unsupported.** Nothing here is platform-specific so it will probably work, but nobody has run it. Do not rely on it. |

---

## Setup

Run from the repository root, in order.

### 1. Install dependencies

```bash
uv sync --locked
```

Provisions Python 3.12 if absent, creates `.venv/`, and installs the exact
versions in `uv.lock`. `--locked` **fails** rather than silently re-resolving
if the lock is stale — that failure is what keeps two checkouts identical.

### 2. Install browser binaries

**Windows:**

```bash
uv run playwright install chromium firefox webkit
```

**Linux** (needs root — installs the system libraries browsers link against):

```bash
sudo uv run playwright install --with-deps chromium firefox webkit
```

Browsers are not Python packages, so `uv sync` does not cover them. Re-run this
after upgrading the `playwright` package — the binaries are version-matched.

On Linux, prefer the single `--with-deps` form over installing browsers and
then running `install-deps` separately. Installing browsers first on a bare
machine emits a missing-system-libraries warning before the libraries are
there, which is noise at best and confusing at worst; `--with-deps` orders it
correctly in one step.

### 3. Create your local configuration

```bash
cp .env.example .env          # bash
Copy-Item .env.example .env   # PowerShell
```

Then edit `.env` and set `BASE_URL`. It is the only required setting;
everything else has a working default.

`.env` is git-ignored. **Never put a real credential in `.env.example`** — that
file is committed.

---

## Verify the setup

```bash
uv run pytest -m healthcheck
```

This is the verification gate. It asserts each capability independently —
dependencies import, the pinned interpreter is 3.12, a browser launches,
configuration validates, the Playwright CLI resolves to this project's copy,
and Allure reporting is registered. Expect 14 passing tests in under a minute.

A failure names the missing prerequisite or the setup step that was skipped,
rather than just the symptom.

---

## Running tests

| Command | What it does |
|---|---|
| `uv run pytest` | Full suite. Allure results and artifact paths are already configured, so this behaves exactly like a fully-flagged invocation |
| `uv run pytest -m healthcheck` | Environment checks only |
| `uv run pytest -m ui` | Browser-driven tests only |
| `uv run pytest -m api` | Service/API tests only |
| `uv run pytest --headed` | Run with a **visible** browser window (needs a display) |
| `uv run pytest --browser firefox` | Override the configured browser |

Tests run **serially** by default and headless by default.

Failure evidence — screenshot, trace, video — is written to
`reports/artifacts/<test-node-id>/`, one directory per test. All of `reports/`
is git-ignored.

---

## Exploring an app and recording a draft test

Point the Playwright CLI at a page, click through the flow, and it emits
runnable Python:

```bash
uv run playwright codegen https://example.com
uv run playwright codegen https://example.com --output tests/ui/test_draft.py
```

**Requires an attached display, so this is a workstation-only workflow** — it
is interactive by nature and cannot run on a headless CI machine.

Treat the generated code as a *draft*: it uses brittle, position-dependent
selectors. Refactor it against the conventions in [CLAUDE.md](./CLAUDE.md)
before committing — that file tells an AI assistant (or a new teammate) where
tests live and what they must look like.

Check the CLI is available:

```bash
uv run playwright --version
```

Running it through `uv run` guarantees you get this project's pinned Playwright
rather than any globally installed copy.

---

## Reports

A plain `uv run pytest` writes Allure result data to `reports/allure-results/`
with no extra flag.

To view it as a browsable report:

```bash
allure serve reports/allure-results
```

**Optional.** This needs the [Allure
CLI](https://allurereport.org/docs/install/) installed separately, plus a Java
runtime (8+). Neither is required for the test suite or the health checks — a
missing Allure CLI does not fail a run.

---

## Upgrading dependencies

A deliberate procedure, not something a setup command does by accident. Run all
three steps together.

```bash
# 1. Refresh the lock to the newest compatible versions
uv lock --upgrade

# 2. MANDATORY: re-match browser binaries to the upgraded playwright package
uv run playwright install chromium firefox webkit

# 3. Re-verify before trusting the environment
uv run pytest -m healthcheck
```

Then **commit `uv.lock` as its own change**, so a version bump is reviewable
rather than buried in an unrelated diff.

Step 2 is not optional. Browser binaries are version-locked to the `playwright`
package, and skipping it produces a launch error that gives no hint the upgrade
caused it.

Note that `uv lock --upgrade` is the *only* command here that rewrites
`uv.lock`. `uv sync --locked` deliberately fails on a stale lock instead of
updating it, which is what makes versions impossible to move by accident.

---

## Approving a design before it is automated

Generated designs must be reviewed before anyone writes the automation.
Reviewing intent costs minutes; discovering after automation that the tests
prove the wrong thing costs days.

```bash
uv run python -m ai_qa.approval review                        # what is waiting
uv run python -m ai_qa.approval approve tests/ui/test_x.py
uv run python -m ai_qa.approval reject  tests/ui/test_x.py --reason "Missing the expired case"
uv run python -m ai_qa.approval status                        # state of everything
uv run python -m ai_qa.approval verify                        # the pipeline gate
```

No network anywhere - a pipeline verifies approvals with no credentials.

### What an approval covers

**Test names, markers and docstrings** - the design, not the bodies. So:

| Change | Approval |
|---|---|
| Write or edit a test body | **Preserved** - this is the act approval authorises |
| Reformat, add a comment | Preserved |
| Edit a docstring | **Voided** - the docstring states the reviewed behaviour |
| Rename, add or remove a test | **Voided** |
| Move or rename the file | Preserved - records match by digest, not path |

### Who may approve

By default the approver must **not** be the design's author. To permit
self-approval, set `APPROVAL_REQUIRE_SECOND_PERSON=false` - the choice is
recorded on every decision so an auditor can tell it was deliberate.

Decisions are committed files under `approvals/`, one per decision, so a later
decision never erases an earlier one.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Configuration error |
| 3 | Refused: self-approval under the current policy |
| 4 | Refused: the design records no author, so the policy cannot be checked |
| 5 | Refused: a rejection needs `--reason` |
| 6 | **`verify` found scripts without an applicable approval** |
| 7 | `git config user.email` is not set |
| 8 | Tampering detected in the records |

### A limitation worth knowing

The gate is **cooperative**. Anyone who can commit can commit an approval
record. It stops mistakes, omissions and drift - not a determined insider.
Making it tamper-proof would need signing and an external authority.

## Generating test skeletons from a ticket

Name a ticket however you like - the key is read out of the text:

```bash
uv run python -m ai_qa.generate extract "generate tests for TC-345"   # no network
uv run python -m ai_qa.generate generate "generate tests for TC-345"
uv run python -m ai_qa.generate skeletons                             # outstanding work
uv run python -m ai_qa.generate skeletons --check-stale               # tickets that moved on
```

`generate` fetches the ticket, prints a brief, and scaffolds a test file with
provenance and markers. **You (or an AI assistant) then write the test
functions** below the delimiter, following the conventions in
[CLAUDE.md](./CLAUDE.md).

Generated tests start as **skipped skeletons** and report as such - they can
never report as passed. `skeletons` lists everything still unimplemented, so
outstanding work cannot accumulate unnoticed.

### Why `extract` is separate

So you can see which key was found without generating anything, and so
extraction is diagnosable on its own. It needs no network.

Text that merely looks like a key is rejected locally and never fetched:

```bash
uv run python -m ai_qa.generate extract "we follow ISO-8601"
# rejected ISO-8601: DENYLISTED_PREFIX
```

`COVID-19`, `UTF-8`, `CVE-2026-1234` and `SPRINT-2026` are all rejected the
same way. A bare regex accepts all of them.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Configuration error |
| 3 | No ticket key found |
| 4 | Several keys found - every key is named, nothing is generated |
| 5 | Ticket not found or not visible |
| 6 | Target file exists; pass `--force` |
| 7 | Jira unavailable |

Regeneration **refuses by default** so hand-made refinements are never lost.

## Jira (optional)

Read-only access to Jira Cloud, straight from this project over REST. No MCP
server, no connector, no AI assistant required at runtime.

### Setup

1. Create an API token: <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Add to `.env` (never `.env.example` - that file is committed):

```dotenv
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your-token
JIRA_TIMEOUT_S=30
```

Set all three credentials together or none - partial configuration is rejected
at load, because setting two of three otherwise surfaces as an authentication
failure against Jira when the problem is local.

**A read-scoped token is sufficient.** This client never writes to Jira, so it
needs no permission to comment or transition. Jira tokens carry the holder's
full permissions and cannot be narrowed, so this is advice rather than a
guarantee - but a token leaked from this project cannot be used *through this
project* to change anything.

### Commands

```bash
uv run python -m ai_qa.jira check                        # verify credentials
uv run python -m ai_qa.jira issue TC-345                 # print one issue
uv run python -m ai_qa.jira search "project = TC"        # every match, all pages
```

`check` verifies authentication and reports the account without touching an
issue - run it first when setting up.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Configuration error - settings missing or incomplete |
| 3 | Jira rejected the credentials, or denied access |
| 4 | Not found, or not visible to this account |
| 6 | Jira unavailable, timed out, or rate-limited |
| 7 | Query rejected |

Code 5 is reserved: it meant "write refused" before write support was deferred.

### Running without Jira

The suite runs with no Jira configuration at all. Jira tests skip, everything
else is unaffected - an optional integration must never become a precondition
for running the tests.

```bash
uv run pytest -m jira          # the Jira suite (no network needed)
```

## Project layout

```text
src/ai_qa/              Importable support package
├── config.py           Settings model, loaded from .env and validated
├── data.py             YAML test-data loader
└── pages/base.py       Page-object base class

tests/
├── conftest.py         Shared fixtures
├── health/             Environment health checks
├── ui/                 Browser-driven tests
├── api/                Service tests
└── data/               YAML test data

reports/                Generated output (git-ignored)
```

Conventions, fixture rules, and what a recorded draft must be refactored to
meet: [CLAUDE.md](./CLAUDE.md).
