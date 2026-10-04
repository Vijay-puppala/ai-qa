# Implementation Plan: Test Approval Gate

**Branch**: `004-test-approval-gate` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-test-approval-gate/spec.md`

## Summary

Put a reviewable gate between a generated test design and the automation written from it: a reviewer approves or rejects the design, the decision is recorded as a committed file, automation is refused without a currently-applicable approval, and a pipeline fails rather than running anything unapproved.

Five decisions carry the design, each resolved in [research.md](./research.md):

1. **The approval covers the design portion only** — test names, markers and docstrings, extracted by AST, bodies excluded. This is the X1 correction made concrete: a whole-file digest would void every approval the moment its automation was written, which is the approved act itself (R2).
2. **One file per decision** makes the append-only requirement structural rather than enforced. There is no code path that rewrites a record (R1).
3. **The four states are computed, never stored.** A stored state field is a cache with no invalidation signal, and a wrong state looks exactly like a correct one (R5).
4. **Author identity comes from feature 003's provenance**, and an unknown author refuses the approval under the default policy. The policy is unenforceable otherwise, and failing open on the one check the policy exists for would make it decorative (R4).
5. **One `verify` command serves both the pipeline and the engineer**, so a pipeline failure is reproducible before pushing rather than discovered during a release (R7).

Net new dependencies: **zero**. Net new external prerequisites: **zero**.

## Technical Context

**Language/Version**: Python 3.12, unchanged.

**Primary Dependencies**: `pydantic` for the record model, `pytest` for test discovery. Standard library `ast`, `json`, `hashlib`, `argparse`, `subprocess` (git). **Nothing added.**

**Storage**: Committed JSON files under `approvals/`. No database, no index.

**Testing**: pytest. The digest, the state function and the record reader are pure and unit-tested. Git-dependent checks are tested against a temporary repository fixture. No network anywhere in this feature.

**Target Platform**: Windows and Linux. macOS unsupported.

**Project Type**: Library modules plus a CLI inside the existing single project.

**Performance Goals**: Whole-repository approval state reportable in under 10 seconds for 1,000 tests (SC-013). The AST scan is the dominant cost; records are small.

**Constraints**: Zero new dependencies (FR-032). No MCP or connector required for review, recording, gate enforcement or pipeline verification (FR-033, SC-015). Verification must work with no network (FR-025, SC-011). No credential in any record or report (FR-034). No route may bypass the gate, human or assistant (FR-009).

**Scale/Scope**: One package of six modules, two settings, one CLI with five subcommands, one record format that two features read.

**Upstream dependency**: feature 003 (provenance marker, `generated-by-identity`, the skeleton sentinel). Specified and planned, **not implemented**. One of its fields does not yet exist in its spec — see Spec Deltas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status: PASS — vacuously, and this is the feature where that is least defensible.** `.specify/memory/constitution.md` is still the unmodified template.

This feature *is* governance. "Who may approve" (FR-022) and "what the pipeline must enforce" (FR-023, FR-026) are precisely what a project constitution states once for every feature, and here they are being decided inside one feature's spec and one feature's settings. A later feature is free to answer them differently, and nothing would flag the contradiction.

Pre-Phase 0: no violations (none exist to violate). Post-Phase 1: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/004-test-approval-gate/
├── plan.md              # This file
├── research.md          # Phase 0 — 11 decisions
├── data-model.md        # Phase 1 — record, digest, state, policy
├── quickstart.md        # Phase 1 — validation walkthrough
├── contracts/
│   ├── commands.md      # review / approve / reject / status / verify
│   └── record-format.md # The committed record format
├── checklists/
│   └── requirements.md  # 16/16
└── tasks.md             # Phase 2 output (NOT created here)
```

### Source Code (repository root)

```text
src/ai_qa/
├── approval/                   # NEW
│   ├── __init__.py
│   ├── digest.py               # AST design digest: names, markers, docstrings (R2)
│   ├── records.py              # Read/write decision files; git-history checks (R1, R6)
│   ├── state.py                # PENDING | APPROVED | STALE | REJECTED, computed (R5)
│   ├── policy.py               # Approver policy; author from provenance (R3, R4, R11)
│   ├── gate.py                 # The single enforcement point (FR-006, FR-009)
│   └── __main__.py             # argparse CLI (R7)
├── config.py                   # CHANGED: + 2 approval settings
└── generate/                   # EXISTING (feature 003) — provenance + sentinel read

approvals/                      # NEW, committed: <TICKET>/<timestamp>-<decision>.json

tests/approval/                 # NEW
├── test_digest.py              # Body edits do not change it; docstring edits do
├── test_state.py               # All four states, incl. stale
├── test_policy.py              # Self-approval refused by default; unknown author refused
├── test_records.py             # Append-only; tamper and orphan detection
├── test_gate.py                # No route bypasses it
└── test_verify.py              # Exit codes; every offender named

.gitignore                      # CHANGED: approvals/ must NOT be ignored
README.md                       # CHANGED: + review workflow, enabling self-approval
CLAUDE.md                       # CHANGED: + the gate is not optional for generated tests
```

**Structure Decision**: `gate.py` exists as a separate module holding the single enforcement point, because FR-009 requires that no route bypasses the gate — human or AI assistant, any entry point. Features 003 and 005 each introduce an entry point, so the check has to be somewhere both funnel through rather than duplicated at each call site, where one would eventually be forgotten.

`digest.py`, `state.py` and `policy.py` are pure. SC-002, SC-003, SC-006 and SC-018 are all negative or exhaustive criteria ("zero proceed", "100% distinguishable", "zero self-approvals accepted"), which are only testable if the decisions are functions of their inputs.

**`approvals/` must be explicitly excluded from `.gitignore`.** Feature 001's ignore rules exclude generated output broadly; a records directory that gets ignored would make every approval invisible to the pipeline and to review, and the failure would look like "nothing is approved yet".

## Integration Points

| This feature needs or provides | Direction | Counterpart | Reference |
|---|---|---|---|
| `generated-by: ai-qa` marker — which tests the gate applies to | needs | 003 provenance | R8, FR-029 |
| `generated-by-identity` — the design's author | needs | 003 provenance | R4; **added to 003's FR-017 on 2026-10-04** |
| `SKELETON_SENTINEL` — partial-implementation counting | needs | 003 `generate/sentinel.py` | R10, FR-031 |
| Design digest input (names, markers, docstrings) | needs | 003 skeleton format | R2 |
| `approval_state(design)` — programmatic query | **provides** | 005 `complete.py` | Closes analysis finding U1 |
| Approval identifier to stamp on automation | **provides** | 005 FR-005 | FR-010 |
| `verify` command and exit codes | **provides** | pipeline | FR-028, FR-038 |

The `approval_state` function is deliberately part of the public surface, not just a CLI internal. Analysis finding U1 noted that feature 004 exposed state only as a command while feature 005 needs it in-process; exporting the function closes that.

## Phase 0: Research

Complete — see [research.md](./research.md). Eleven decisions, zero `NEEDS CLARIFICATION` remaining.

The two decisions most worth reading before implementation:

- **R2** is the X1 fix in concrete form. Digesting the whole file was the defect; the digest covers the AST-extracted design portion, so filling a body preserves the approval while changing a docstring, renaming a test or adding one voids it. The sensitivity is exactly what a reviewer would expect, which is the point.
- **R4** is where this feature depends on a field feature 003 records: the author's identity, only knowable at generation time. It was added to 003's FR-017 on 2026-10-04, which unblocked FR-022. Designs predating the field have `author = None` and refuse under the default policy, which is the intended fail-closed behaviour rather than a gap.

## Phase 1: Design

Complete.

| Artifact | Contents |
|---|---|
| [data-model.md](./data-model.md) | Decision record fields and verbatim constraints; design digest definition; the four-state function; policy inputs |
| [contracts/commands.md](./contracts/commands.md) | `review`, `approve`, `reject`, `status`, `verify` with exit codes |
| [contracts/record-format.md](./contracts/record-format.md) | The committed record format, which two features and a pipeline read |
| [quickstart.md](./quickstart.md) | Validation walkthrough, all of it offline |

### Post-Design Constitution Re-Check

Unchanged: **PASS, vacuously.** No dependency, no network, no second configuration source. The enforcement point is one module; the decisions that matter are three pure functions.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations. Two places the design is deliberately more complex than the minimum:

| Added complexity | Why needed | Simpler alternative rejected because |
|---|---|---|
| AST design digest (`digest.py`) | FR-017 as corrected needs a digest over names, markers and docstrings only | A whole-file digest was the X1 defect; a textual body-stripping heuristic is fragile to formatting |
| Git-history comparison in `records.py` | FR-015 requires *deletion* to be detectable | A deleted file leaves no trace on disk; only history shows it |

## Risks

| Risk | Mitigation | Residual |
|---|---|---|
| Someone commits a fabricated approval | Identity recorded, policy recorded, history auditable (R3, R6, R11) | **Real and accepted.** The gate is cooperative — it stops mistakes, not a determined insider. Signing would need an external authority |
| `approvals/` accidentally git-ignored | Explicit negation in `.gitignore`, plus a test asserting the directory is tracked | A later broad ignore rule could re-shadow it |
| Stale approvals block an unrelated deploy | Every offender named with its remedy; identical check runs locally (R7, FR-038, FR-039) | The pressure to weaken the gate after a blocked release is organisational, not technical |
| Author unknown, so the policy cannot be checked | Refuse under the default policy (R4) | A repository of pre-existing hand-written tests would all refuse; mitigated by R8 scoping the gate to generated tests only |
| ~~Upstream provenance field never added~~ | **Resolved 2026-10-04** — added to 003's FR-017 | Designs generated before the field refuse under the default policy; regenerate or relax the policy deliberately |

## Spec Deltas Discovered During Planning

| Spec text | What the design needs | Recommended resolution |
|---|---|---|
| ~~**FR-022** requires enforcing that the approver is not the author~~ | The author's identity, which only exists at generation time | **Resolved 2026-10-04.** `generated-by-identity` was added to feature 003's FR-017, so FR-022 is now enforceable. This was the only item blocking this feature from being built. |

**No outstanding deltas.** The one blocking dependency between features 003 and 004 was closed on 2026-10-04.
