# Project context — handoff

Everything a new contributor (human or AI) needs before touching this
repository. Read this, then `docs/decisions.md`, then `CLAUDE.md`.

**Last updated**: 2026-10-04 · Committed and pushed: 151 files on `main` at
`github.com/Vijay-puppala/ai-qa` (public). `.env` and `reports/` are
git-ignored and were verified absent from the remote.

---

## 1. Constitution principles — ⚠ NOT RATIFIED

`.specify/memory/constitution.md` **is still the unfilled Spec Kit template.**
Every principle is a `[PLACEHOLDER]`. Eight `/speckit.analyze` and
`/speckit.converge` passes recorded this; the constitution gate has never been
genuinely evaluated for any feature.

The cost is concrete and measurable: the no-MCP rule is restated in **four**
specs, the dependency floor in **three**, and feature 004 had to invent its own
approver policy because there was nothing to defer to.

These are the principles that have actually been governing the project. They
are **de facto, not ratified** — ready to paste into
`/speckit.constitution`:

1. **Dependency floor.** The eight declared packages are a minimum. A new
   dependency requires naming the requirement that cannot otherwise be met.
   Convenience is not a reason.
2. **One external prerequisite.** `uv` only. No second package manager, no
   additional language runtime, no Node.js.
3. **No assistant in the runtime path.** No MCP server or connector may be
   required for anything to run. Interactive authoring steps are the sole,
   explicit exception.
4. **Offline-testable.** The full suite passes with no network. Optional
   integrations skip, never fail.
5. **A tool may fix what cannot run; it may never make a failure pass.** No
   automated change may alter what a test asserts.
6. **Approval covers reviewed intent, not implementation.** Implementing
   approved work never voids its approval; changing what was reviewed does.
7. **Fail closed.** Ambiguity resolves towards refusal: unrecognised failure
   classes escalate, unknown authorship refuses approval, missing identity
   refuses to record.
8. **Configuration has one validated source**, and every setting is named in
   the committed example.

**Until ratified, nothing stops a future feature contradicting any of these.**

---

## 2. Status

| Feature | Spec | Plan | Tasks | Built | Remaining |
|---|---|---|---|---|---|
| 001 dev-env-setup | ✓ | ✓ | 45 | **44/45** | Needs a 2nd machine (SC-003) |
| 002 jira-rest-integration | ✓ | ✓ | 55 | **54/55** | Document the public surface (T055) |
| 003 prompt-driven-test-generation | ✓ | ✓ | 41 | **37/41** | 4 need multi-project live runs |
| 004 test-approval-gate | ✓ | ✓ | 49 | **46/49** | 2 need 005; 1 needs a 1000-test suite |
| 005 approved-automation-run | ✓ | ✓ | 56 | **26/56** | **CLI + repair log (~30 tasks)** |

- **183 tests passing**, identically with and without Jira credentials
- **8 dependencies**, unchanged across all five features
- Requirements: **205** across 002–005 (132 FR + 73 SC), 92% cited by a task

**005 is the real remaining work**: its safety layer (classifier, assertion
digest, ticket hook) and report pipeline are built and tested; its
`complete` / `run` / `repair` / `skeletons` CLI and the repair log are not.

---

## 3. Live environment

| | |
|---|---|
| Jira | `<your-site>.atlassian.net` — working, read-only. Real value in `.env` (git-ignored) |
| App under test | `<app-under-test>` — a Clinical Trials Management System. Real value in `.env` |
| `BASE_URL` | points at the app above. **Deliberately not recorded here** - this repository is public, and publishing a live host alongside the login findings below would point the internet at them |
| Approval policy | `APPROVAL_REQUIRE_SECOND_PERSON=false` (single-person project; recorded on every decision) |

**Two different identities are in play**, intentionally:
one address authenticates to Jira (`JIRA_EMAIL`); the git `user.email` is
stamped into generated tests as `generated-by-identity` and recorded as the
approver. The git one ends up in **committed** files, so choose it with that
in mind.

---

## 4. Known bugs and issues

### In the application under test (DC-11) — real findings, not test defects

`tests/ui/test_login_screen.py`: **5 pass, 4 fail.** The failures should stay
red until the app changes.

| Failing test | Evidence |
|---|---|
| Required-controls, and Forgot-Password navigation | Page has exactly two links: `/` (logo) and `Sign up`. **No Forgot Password link** |
| Visibility toggle reveals/re-masks | One button on the page: `Login`. No `show`/`hide`/`toggle`/`eye` affordance |
| Duplicate submission prevented | **2 POST requests** sent for one login attempt |

Lead worth chasing: **`"forgot"` appears in the raw HTML but in no visible text
or link** — possibly a built-but-unrouted component.

Judgement call for a reviewer: the app uses **native HTML5 validation**
(`"Please fill out this field."`) rather than custom message elements. That
satisfies "client-side validation messages" as written; you may disagree.

### In this project

| Issue | Severity | Where |
|---|---|---|
| 002 public surface undocumented in its contract (`validate_jql`, `whoami`, `close`, `sleep` param) | MEDIUM | Open as **T055** |
| `scaffold.target_path` names files after the *summary*, so names can still be long | LOW | Fixed to word boundaries; DC-11 needed a manual rename to `test_login_screen.py` |
| 005's completion step cannot run — no `complete` command yet | — | By design; ~30 tasks outstanding |

### Resolved, recorded so they are not reintroduced

`redact()` masked only the first word of an `Authorization` header · pytest
collected a production function named `test_names` · the assertion digest
missed weakened Playwright matchers (`to_have_text` → `to_be_visible`) because
it captured the inner `expect(...)` call · a CLI test passed only because no
credentials existed · `NUMBER_TOO_LONG` was unreachable dead code.

---

## 5. Open questions

1. **Ratify the constitution?** Eight passes have flagged it. The principles in
   §1 are ready.
2. **Build out 005, or stop?** The safety layer is the valuable half and it is
   done. The CLI is mechanical.
3. **DC-11's three gaps** — unfinished work, descoped requirements, or a stale
   ticket? The tests state the evidence and deliberately do not assert a cause.
4. **SC-003 and SC-002 (Linux/second machine)** need hardware this project has
   not had. Descope, or provision a runner?
5. **Should 005 report results back to Jira?** Currently out of scope, and
   impossible — 002 has no write capability. Re-adding writes is a new feature,
   not a config change.
6. **macOS**: declared unsupported. Promote it only by verifying it.

---

## 6. Important files

| Path | Purpose |
|---|---|
| `CLAUDE.md` | **Read first.** Conventions an AI assistant must follow: layout, markers, fixture rules, the repair boundary, the no-MCP rule |
| `docs/decisions.md` | Every decision + the 10 that must not change without discussion |
| `docs/architecture.md` | The pipeline, module layout, cross-feature couplings |
| `src/ai_qa/config.py` | **The** settings model. All 14 settings. Never read `os.environ` elsewhere |
| `src/ai_qa/generate/sentinel.py` | One constant, three features depend on it. Import, never retype |
| `src/ai_qa/approval/digest.py` | The design digest. Changing its scope deadlocks the workflow |
| `src/ai_qa/approval/gate.py` | The single enforcement point. No caller may carry its own check |
| `src/ai_qa/automation/classify.py` | Repair eligibility. The default must stay `ESCALATE` |
| `src/ai_qa/automation/digest.py` | Assertion digest. The guardrail against hiding defects |
| `tests/conftest.py` | The `ticket` → Allure-label hook. **Without it every report is unattributed and nothing looks broken** |
| `.env` (git-ignored) | Real credentials. `.env.example` is the committed contract |
| `approvals/` | Committed decision records. **Must never be git-ignored** |
| `specs/00*/` | spec + plan + research + data-model + contracts + tasks per feature |
| `.specify/memory/constitution.md` | **Unfilled template** |

---

## 7. How to run things

```bash
uv sync --locked                                  # setup (provisions Python 3.12)
uv run playwright install chromium firefox webkit # Linux: add --with-deps, needs root
cp .env.example .env                              # then set BASE_URL

uv run pytest -m healthcheck                      # verify the environment (14 tests)
uv run pytest --ignore=tests/ui                   # 183 tests, no app needed
uv run pytest -m jira                             # Jira suite, no network needed

uv run python -m ai_qa.jira check                 # verify Jira credentials
uv run python -m ai_qa.generate generate "tests for DC-11"
uv run python -m ai_qa.approval review            # what awaits review
uv run python -m ai_qa.approval verify            # the pipeline gate
```

**Only `BASE_URL` is required.** Everything else has a working default.

---

## 8. Process notes

The Spec Kit workflow was followed throughout: `specify` → `clarify` → `plan` →
`tasks` → `analyze` → `implement` → `converge`. Worth knowing:

- **Cross-feature `analyze` earned its keep.** It found X1 (the digest deadlock)
  and X2 (a requirement that made 003 and 005 mutually unsatisfiable) before
  either was built.
- **`converge` converged.** Three passes on 002 found 3 → 3 → 1 findings, and
  each later finding traced to the *previous fix* rather than the original
  build.
- **Going live found what offline testing could not**: a test that passed only
  because no credentials existed, and a Jira endpoint that answers 200 for an
  invalid query instead of 400.
- Several specs were **narrowed** after the fact (Jira writes, SC-011). Scope
  reduction was repeatedly the right call.
