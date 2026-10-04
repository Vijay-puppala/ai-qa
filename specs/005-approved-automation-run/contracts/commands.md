# Command Contract: Approved Automation Run & Reporting

**Feature**: `005-approved-automation-run` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Five subcommands. Names, arguments, and exit-code meanings are what callers and pipelines depend on, so changing them is a breaking change.

All commands run through `uv run`, per feature 001. None requires an AI assistant to *run*; the authoring inside `complete` and `repair` does (FR-029, SC-015).

---

## `complete` — turn an approved design into runnable automation

```bash
uv run python -m ai_qa.automation complete <TICKET-KEY>
```

| | |
|---|---|
| **Does** | Checks the approval gate, finds the ticket's unimplemented skeletons, retrieves ticket content for context, and hands off for authoring |
| **Refuses when** | The design is pending, rejected, or covered by a stale approval (FR-002, FR-003); or a CI environment is detected (FR-008) |
| **Never** | Overwrites an existing test body (FR-004). Only unimplemented skeletons are touched |
| **Records** | The source ticket and the authorising approval on the completed automation (FR-005) |
| **Satisfies** | FR-001 to FR-008 |

The approval check is delegated to feature 004's gate rather than reimplemented here — FR-002 requires that, and a second implementation would be a second thing to drift.

**CI guard**: refuses when `CI` or a known vendor variable is set, naming the reason. Two layers, because relying on "the pipeline does not call this" puts the guarantee in a file this repository does not control (R10).

## `run` — execute tests and emit result data

```bash
uv run python -m ai_qa.automation run --ticket <TICKET-KEY>
uv run python -m ai_qa.automation run --full-suite
```

| | |
|---|---|
| **Does** | Runs the selected tests, emitting Allure result data via the existing configuration |
| **Default scope** | The named ticket's tests only. A full-suite run is **never** started automatically (FR-010) |
| **Selection** | By the `ticket` marker's argument, filtered at collection — not by `-m`, which cannot discriminate by key (R4) |
| **Zero collected** | **Failure.** Exit code 5 from the underlying runner is treated as failure, never as a pass (FR-011, R8) |
| **Unreachable application** | Reported distinctly from a test failure (FR-012) |
| **Satisfies** | FR-009 to FR-013 |

After a ticket-scoped run the command **offers** the full-suite follow-up and does not run it (FR-010). This is the explicit half of the Q2 decision: fast feedback first, regression deliberate rather than forgotten.

## `report` — generate the readable report

```bash
uv run python -m ai_qa.automation report
```

| | |
|---|---|
| **Does** | Reads `reports/allure-results/`, joins the repair log, writes `reports/report.html` |
| **Requires** | Nothing beyond the project's existing toolchain — no Java, no Node, no network (FR-031, SC-017) |
| **Produces** | One self-contained HTML file, readable in any browser (FR-015, SC-018) |
| **States** | The scope of the run it covers (FR-035), and that it is a project-generated summary rather than an Allure report (FR-032) |
| **Empty input** | Reported as empty, never as a clean run (FR-017) |
| **Satisfies** | FR-014 to FR-020, FR-031 to FR-035 |

Format details: [report-format.md](./report-format.md).

The Allure CLI remains an optional alternative for anyone who wants the full Allure report from the same result data (FR-033). No success criterion depends on it being installed (SC-019).

## `repair` — fix mechanical test faults only

```bash
uv run python -m ai_qa.automation repair <TICKET-KEY> [--max-attempts N] [--dry-run]
```

| | |
|---|---|
| **Does** | For each failing test: classifies the failure, and for eligible classes only, hands off for repair under the assertion-digest guard |
| **Eligible** | Collection/import errors, `SyntaxError`, fixture lookup errors, unregistered markers, test-framework API misuse (FR-036) |
| **Never repairs** | Assertion failures, element-not-found, timeouts, status mismatches — or any unrecognised failure (FR-037, FR-038) |
| **Refuses** | Any repair whose assertion digest changed (FR-039). Recorded as `refused_assertion_changed` and escalated |
| **Bounded** | By `--max-attempts`; exhaustion stops and reports what was attempted (FR-040) |
| **Records** | Every attempt, with what changed and the digests either side (FR-040) |
| **Refuses when** | A CI environment is detected (FR-042) |
| **Satisfies** | FR-024 to FR-027, FR-036 to FR-042 |

**The two properties that matter**, and which the tests assert as negatives:

- Eligibility is a pure function of the failure's **exception type** — never its message, never the test's content. SC-022 asserts zero repairs on ineligible classes, and a negative is only verifiable if the decision is deterministic.
- A repair may not change what a test asserts. The digest is compared before and after; a change means refusal, not a warning (SC-023).

`--dry-run` reports what would be attempted and changes nothing.

## `skeletons` — list unimplemented work

```bash
uv run python -m ai_qa.automation skeletons
```

Lists every unimplemented skeleton with its source ticket, using feature 003's sentinel and listing (R5). Read-only; safe in any environment. Satisfies FR-007's verification side.

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. Includes a dry run, and a run where tests failed but the command did its job — see below |
| 1 | Tests failed (from `run`) |
| 2 | Configuration error |
| 3 | Refused by the approval gate — design pending, rejected, or stale |
| 4 | Refused because a CI environment was detected |
| 5 | **Zero tests collected** — always a failure (FR-011) |
| 6 | Repair refused: assertion digest changed |
| 7 | Repair budget exhausted with the test still failing |
| 8 | Report generation failed, or result data was empty (FR-017) |

### The distinction worth preserving

Exit **1** means tests failed. Exit **0** from `complete` or `repair` means the command completed its job, which may include leaving tests failing.

FR-026 requires that test failures are run outcomes, not errors in the completion step. Conflating them would mean a first run with failures — the normal case for new automation — reads as a broken tool, and the pressure would be to make the tool "succeed" by making tests pass. That is exactly the failure mode FR-036 to FR-042 exist to prevent.

Code **6** is likewise not a malfunction: it means the digest guard fired and refused to let a repair change an assertion. It is the guarantee working.

---

## Compatibility notes

Breaking changes that need a deliberate decision:

- Adding a failure class to the `ELIGIBLE` list, or removing the escalate-by-default behaviour. Either widens what the tool may edit.
- Removing or weakening the assertion digest check.
- Making a ticket-scoped `run` fall through to the full suite, or vice versa.
- Treating exit 5 as success.
- Dropping the scope statement from the report, or the "not an Allure report" statement.
- Removing the CI guard from `complete` or `repair`.
- Adding any dependency or external prerequisite (FR-031).
