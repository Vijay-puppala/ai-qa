# Command Contract: Test Approval Gate

**Feature**: `004-test-approval-gate` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Five subcommands under `uv run python -m ai_qa.approval`. Standard-library `argparse`. **No network anywhere in this feature** — every command works offline, which is what FR-025 and SC-011 require of pipeline verification.

Record format: [record-format.md](./record-format.md). States: [data-model.md](../data-model.md) §3.

---

## `review` — see what is waiting

```bash
uv run python -m ai_qa.approval review
uv run python -m ai_qa.approval review --ticket TC-345
```

| | |
|---|---|
| **Does** | Lists every design awaiting review with its source ticket and, per test, the behaviour its docstring claims |
| **Shows** | Only `PENDING` designs by default; `--all` includes every state |
| **Satisfies** | FR-001, SC-001 |

The docstrings are shown because they *are* the thing under review — the digest covers names, markers and docstrings, so a reviewer who has not read them has not reviewed the design.

## `approve` / `reject` — record a decision

```bash
uv run python -m ai_qa.approval approve <DESIGN_PATH>
uv run python -m ai_qa.approval reject <DESIGN_PATH> --reason "Missing the expired-card case"
```

| | |
|---|---|
| **Records** | decision, ticket, design path, design digest, approver, author, policy in force, timestamp, test names, and reason for a rejection |
| **Approver** | Git `user.email`. **Refused** if unset — a record naming nobody answers nothing (FR-037) |
| **Refuses** | Self-approval under the default policy; unknown author under the default policy; a rejection with no reason |
| **Never** | Overwrites an earlier record. A new decision is a new file |
| **Satisfies** | FR-002, FR-003, FR-011 to FR-016, FR-036, FR-037 |

**`reject` requires `--reason`.** A rejection without one tells the author nothing and makes the record useless to a later auditor.

## `status` — current state of everything

```bash
uv run python -m ai_qa.approval status
uv run python -m ai_qa.approval status --ticket TC-345
```

| | |
|---|---|
| **Reports** | Per design: `PENDING`, `APPROVED`, `STALE`, or `REJECTED`, plus the `unmanaged`, `partial`, `unimplemented` and `orphaned` conditions |
| **Performance** | Whole repository in under 10 s for 1,000 tests (SC-013) |
| **Satisfies** | FR-018, FR-030, FR-031, SC-003 |

`STALE` is reported distinctly from `PENDING`: "never reviewed" and "reviewed, then changed" need different remedies, and conflating them sends someone to the wrong one.

## `verify` — the pipeline gate

```bash
uv run python -m ai_qa.approval verify
```

| | |
|---|---|
| **Does** | Checks every test script the gate applies to, and **fails the run** if any lacks an applicable approval |
| **Prints** | Every offending script with its state and the remedy for each — not a count (FR-038) |
| **Exit** | Non-zero on any offender (FR-026) |
| **Network** | None (FR-025, SC-011) |
| **Satisfies** | FR-023 to FR-028, FR-038, FR-039 |

**This is the same command an engineer runs locally**, and it must produce identical results for the same repository state (FR-039, SC-020). One implementation, two callers — which is what makes a pipeline failure reproducible before pushing instead of discovered during a release.

Printing every offender rather than stopping at the first is deliberate: a pipeline run is expensive, and a failure reporting one of four problems costs four runs.

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — for `verify`, every applicable script is covered by an applicable approval |
| 2 | Configuration error |
| 3 | Refused: self-approval under the default policy |
| 4 | Refused: the design's author is unknown, so the policy cannot be checked |
| 5 | Refused: a rejection was attempted without a reason |
| 6 | **`verify` found scripts without an applicable approval** — the pipeline failure |
| 7 | Approver identity could not be determined (git `user.email` unset) |
| 8 | Tampering detected: an orphaned, malformed, or history-modified record |

Codes 3 and 4 are distinct because the remedies differ: 3 means ask a colleague, 4 means the design predates author recording or was hand-written. Code 7 is distinct from 2 because the fix is `git config user.email`, not project configuration.

---

## What the gate applies to

A test file is subject to the gate when it carries feature 003's `generated-by: ai-qa` provenance marker. Hand-written tests without it are reported as `unmanaged` and are **not** blocked (FR-029).

Requiring approval for every test would block a hand-written test somebody wrote in two minutes, which is the fastest route to the gate being switched off. Reporting the `unmanaged` count keeps a bypass visible.

---

## Compatibility notes

Breaking changes:

- Digesting anything other than the design portion — a whole-file digest deadlocks the workflow (this was analysis finding X1).
- Defaulting `approval_require_second_person` to `false` — removes the gate for anyone upgrading without reading a changelog.
- Allowing a record to be written with an empty or placeholder approver.
- Making `verify` exit zero with a warning.
- Matching records to designs by path instead of digest — a rename would void the approval, which FR-021 forbids.
- Storing state instead of computing it.
- Reporting only a count from `verify` instead of every offender.
