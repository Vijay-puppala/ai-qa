# Implementation Plan: Approved Automation Run & Reporting

**Branch**: `005-approved-automation-run` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-approved-automation-run/spec.md`

## Summary

Close the loop from an approved test design to a readable report: complete the approved skeletons into runnable tests, run the ticket's tests, generate a self-contained report from the project's own result data, and allow repair of mechanical test faults only — never of a failing assertion.

Five decisions carry the design, each resolved in [research.md](./research.md):

1. **Ticket attribution needs an explicit hook.** Verified empirically: `@pytest.mark.ticket("TC-345")` produces **no** Allure label at all, because markers carrying arguments are not mapped to tags. Without the hook, FR-021/FR-023/SC-008 are unachievable and the failure is silent — reports would render perfectly with every test unattributed (R2).
2. **The report is a projection, not a parse.** The result schema was read off the installed plugin, and `statusDetails.message`/`trace` are present on failures, so failure evidence needs no new capture mechanism (R1, R3).
3. **Repair eligibility is a pure function of exception type**, with an allowlist and an unconditional escalate-by-default. A negative success criterion (SC-022: zero repairs on ineligible failures) is only verifiable if the decision is deterministic (R6).
4. **"Must not change what a test asserts" is enforced by an AST assertion digest**, compared before and after a repair. FR-039 is otherwise an instruction given to the component most able to breach it (R7).
5. **Completion and repair are kept out of pipelines by two layers** — commands a pipeline never calls, plus a CI guard inside them — so the guarantee does not live in a YAML file this repository does not control (R10).

Net new dependencies: **zero**. Net new external prerequisites: **zero**.

## Technical Context

**Language/Version**: Python 3.12, unchanged.

**Primary Dependencies**: `pytest`, `allure-pytest`, `pytest-playwright` (already declared). Standard library `json`, `ast`, `html`, `pathlib`, `hashlib`. **Nothing added** — FR-031 forbids it, which is what rules out a templating engine for the report.

**Storage**: None. Result data, the repair log, and the report are all generated files under `reports/`, git-ignored per feature 001.

**Testing**: pytest. New marker `ticket`. The classifier (R6) and the assertion digest (R7) are pure functions with unit tests; the generator is tested against fixture result data; no test contacts a live application or Jira.

**Target Platform**: Windows and Linux. macOS unsupported.

**Project Type**: Library modules plus CLI subcommands inside the existing single project.

**Performance Goals**: Report generation under 60 s for 1,000 tests with zero truncation (SC-014). Repair attempts bounded by an explicit limit (FR-040).

**Constraints**: Zero new dependencies and zero new external prerequisites (FR-031, SC-017). No MCP or assistant connector required to run tests or emit result data (FR-029, SC-015). No completion or repair during a pipeline run (FR-008, FR-042). No repair of an assertion failure, ever (FR-037, FR-039). A run collecting zero tests is a failure (FR-011). No credential in any report or evidence (FR-019).

**Scale/Scope**: Two library packages, one conftest hook pair, five CLI subcommands, one HTML generator.

**Upstream dependency risk — stated plainly**: this feature sits on features 002, 003 and 004, **none of which is implemented and two of which have no plan**. The interfaces it builds against — the approval gate's state query, the skeleton sentinel, the ticket retrieval client — are specified but not designed. This plan names each touchpoint explicitly in the Integration Points table so the rework is bounded and locatable when those features land, but the risk is real and is not reduced by planning further ahead.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status: PASS — vacuously, for the fifth consecutive feature.** `.specify/memory/constitution.md` remains the unmodified template; every principle is a `[PRINCIPLE_N_NAME]` placeholder.

This is the feature where the empty gate costs the most. The spec's Question 3 settled whether an automated tool may modify a test until it passes — a project principle if anything is, and one that will recur in every future feature touching test code. It has now been answered inside a feature spec, which means the next feature is free to answer it differently. FR-036 to FR-042 are this plan's own discipline, not a governance constraint, and nothing but review prevents their removal.

Pre-Phase 0: no violations (no principles exist).
Post-Phase 1: unchanged — see [Post-Design Constitution Re-Check](#post-design-constitution-re-check).

## Project Structure

### Documentation (this feature)

```text
specs/005-approved-automation-run/
├── plan.md              # This file
├── research.md          # Phase 0 — 12 decisions, 4 empirical findings
├── data-model.md        # Phase 1 — result projection, repair log, digest, classifier verdicts
├── quickstart.md        # Phase 1 — validation walkthrough
├── contracts/
│   ├── commands.md      # complete / run / report / repair / skeletons - exit codes
│   └── report-format.md # What the report contains and guarantees
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

New and changed files only.

```text
src/ai_qa/
├── report/                     # NEW — the in-project report generator
│   ├── __init__.py
│   ├── read.py                 # Parse allure-results into the projection (R1)
│   ├── render.py               # Single self-contained HTML file, stdlib only (R9)
│   └── summary.py              # Scope statement, counts, per-ticket grouping (FR-035)
├── automation/                 # NEW — completion and repair
│   ├── __init__.py
│   ├── complete.py             # Gate check, skeleton hand-off, CI guard (FR-001..FR-008)
│   ├── classify.py             # Pure failure classifier, escalate-by-default (R6)
│   ├── digest.py               # AST assertion digest (R7)
│   └── repairlog.py            # Append-only attempt record (R11)
└── jira/                       # EXISTING (feature 002) — reused, unchanged

tests/
├── conftest.py                 # CHANGED: + ticket marker -> allure label hook (R2),
│                               #           + --ticket collection filter (R4)
└── report/                     # NEW
    ├── test_read.py            # Projection against fixture result data
    ├── test_render.py          # Self-containment, scope statement, no credentials
    ├── test_classify.py        # Every eligible and escalate class, incl. unknown (SC-022)
    ├── test_digest.py          # Assertion digest detects change, ignores formatting (SC-023)
    └── fixtures/               # Canned allure-results, including a failed record

pyproject.toml                  # CHANGED: + `ticket` marker. No dependency change.
README.md                       # CHANGED: + complete/run/report commands, report limitations
CLAUDE.md                       # CHANGED: + repair boundary, ticket marker convention
```

**Structure Decision**: Two packages split by concern rather than one `automation` package, because the report generator is a pure read-side projection with no authority, while `automation/` holds the two components that can *change things* — completion and repair. Keeping them apart means the dangerous surface is three small files (`complete.py`, `classify.py`, `digest.py`) that a reviewer can read end to end, which matters because FR-036 to FR-042 are enforced there.

`classify.py` and `digest.py` are deliberately pure and dependency-free. SC-022 and SC-023 assert negatives — zero repairs on ineligible failures, zero repairs changing assertions — and a negative is only testable if the decision is a function of its inputs.

## Integration Points with Unbuilt Features

Every place this design reaches into a feature that does not yet exist. Each is a single call site, so the rework when those features land is locatable rather than diffuse.

| This feature needs | From | Spec reference | If it changes |
|---|---|---|---|
| Approval state for a design (pending / approved / stale / rejected) | 004 | FR-006, FR-007 | One call in `complete.py` |
| Approval identifier to record on completed automation | 004 | FR-005, FR-022 | One field written by `complete.py` |
| CI prohibition semantics | 004 | FR-024 | Shared with the guard in `complete.py` |
| Unimplemented-skeleton sentinel and listing | 003 | FR-027, FR-028 | `complete.py` detection, `skeletons` subcommand |
| Skeleton conventions for authoring | 003 | FR-030 | `CLAUDE.md` content |
| Ticket content for context during completion | 002 | FR-005 | One call via the existing client |
| Credential redaction helper | 002 | FR-010 | Imported by `report/render.py` and `repairlog.py` |

## Phase 0: Research

Complete — see [research.md](./research.md). Twelve decisions, four empirical findings, zero `NEEDS CLARIFICATION` remaining.

The two findings that changed the design:

- **A marker with arguments produces no Allure label.** Probed directly: `@pytest.mark.ticket("TC-345")` yielded `parentSuite, suite, host, thread, framework, language, package` and nothing else. Bare markers do become `tag` labels, which makes the wrong conclusion very easy to reach. Ticket attribution therefore needs a conftest hook, and the failure mode without it is silent.
- **`statusDetails` carries `message` and `trace` on failure.** So FR-016's "failure reason reachable from the report" needs no additional capture — it is already in the result data the project emits today.

One item is carried forward **unverified**: whether browser-failure artifacts appear as `attachments` in the result JSON. The probe was a non-browser test, so it proves nothing either way. It does not block the design — the generator can reconstruct paths from the node ID — but the generator should prefer real attachment entries if they exist, and that is a confirmation for implementation rather than an assumption now.

## Phase 1: Design

Complete. Artifacts:

| Artifact | Contents |
|---|---|
| [data-model.md](./data-model.md) | The result projection and its field mapping; repair log record; assertion digest definition; classifier verdicts and the closed eligibility lists |
| [contracts/commands.md](./contracts/commands.md) | Five subcommands with inputs, exit codes, and which requirement each satisfies |
| [contracts/report-format.md](./contracts/report-format.md) | What the report contains, what it guarantees, and what it explicitly is not |
| [quickstart.md](./quickstart.md) | Validation walkthrough mapped to the 25 success criteria |

### Post-Design Constitution Re-Check

Unchanged: **PASS, vacuously.** The design adds no dependency, no prerequisite, and no second configuration source, and it concentrates the authority to modify tests behind two pure, unit-testable functions. Under typical default principles this would be expected to clear — an inference, not a verified result.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations to justify — the gate is empty rather than passed. Two places where this design is deliberately more complex than the minimum:

| Added complexity | Why needed | Simpler alternative rejected because |
|---|---|---|
| AST assertion digest (`digest.py`) | FR-039 forbids a repair changing what a test asserts, and needs a mechanism | Trusting the instruction places the safety property in the component most able to breach it |
| Hand-written HTML generator (`report/render.py`) | FR-031 permits no templating dependency | A templating engine is a dependency the floor forbids; Markdown cannot link evidence or collapse a traceback |

## Risks

| Risk | Mitigation | Residual |
|---|---|---|
| A repair weakens an assertion and hides a defect | Closed eligibility list (FR-036), explicit exclusions (FR-037), escalate-by-default (FR-038), AST digest (FR-039), disclosure in the report (FR-041) | The digest compares assertion text, so changing a variable an assertion depends on without touching the assert line would pass. Narrowed, not closed — see R7 |
| Ticket attribution silently absent | The conftest hook, plus a test asserting the label exists on a marked test | A test marked but never run produces no label, because labels are emitted at run time |
| A mistyped `--ticket` produces a confident empty run | Exit code 5 treated as failure (FR-011, R8) | None material |
| Completion or repair runs in a pipeline | Separate commands plus CI-environment guard (R10) | A pipeline that unsets `CI` and calls the command directly |
| Report shared with a credential in it | Redaction on every string entering the report (R12, FR-019) | A credential pasted inline into a test, per feature 001's no-scanning decision |
| Upstream features change shape | Integration Points table above confines each touchpoint to one call site | Real and unavoidable while 002–004 are unbuilt |

## Spec Deltas Discovered During Planning

None. Every requirement is satisfiable as written.

Two observations that are not deltas:

- **FR-015's "self-contained"** is implemented as one HTML file with **relative links** to evidence, not an embedded bundle. FR-034 already requires the report to state what must accompany it, so this is compliant — but if you intended a single file that survives being emailed on its own, that is a different requirement (embed evidence as data URIs) and worth saying now rather than at review.
- **FR-039's enforcement is strong but not absolute** (R7). The spec requires that a repair must not change what a test asserts; the digest enforces that at the level of assertion statements. A repair that changes an input the assertion depends on would evade it. Recorded here, and in the Risks table, rather than left for someone to discover.
