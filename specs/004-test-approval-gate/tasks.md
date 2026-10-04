---

description: "Task list for Test Approval Gate"
---

# Tasks: Test Approval Gate

**Input**: Design documents from `/specs/004-test-approval-gate/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Required, not optional. SC-002, SC-003, SC-006, SC-008 and SC-018 are exhaustive or negative criteria ("zero proceed", "100% distinguishable", "zero self-approvals accepted") — only demonstrable by test.

**⛔ Upstream**: feature **003** provides the provenance marker, `generated-by-identity`, and the skeleton sentinel. **One field does not yet exist in 003's spec** — see the blocking delta below.

**✅ Blocking spec delta resolved 2026-10-04**: feature 003's FR-017 now requires `generated-by-identity`, so FR-022 is enforceable. Designs generated before the field existed will still have `author = None` and refuse under the default policy - correct behaviour, handled by T011.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 from [spec.md](./spec.md)

---

## Phase 1: Setup

- [X] T001 [P] Create `src/ai_qa/approval/__init__.py` exporting the public surface, including **`approval_state`** — feature 005 needs it in-process, not only as a CLI (closes analysis finding U1)
- [X] T002 Add two settings to the `Settings` model in `src/ai_qa/config.py`, constraints verbatim from `data-model.md` §4: `approval_require_second_person: bool` (default **`True`**) and `approval_records_dir: Path` (default `approvals/`). Extend `_ENV_PREFIXES` so both stay visible to the `.env.example` cross-check
- [X] T003 Add the two variables to `.env.example` with placeholders and a comment explaining that relaxing the policy permits self-approval
- [X] T004 Add an explicit **negation** to `.gitignore` so `approvals/` is never ignored, and add a test asserting the directory is tracked by git. Feature 001's rules exclude generated output broadly, and a swallowed records directory fails **quietly**: `verify` would report everything as unapproved, reading as "nothing reviewed yet" rather than "records are being discarded"

**Checkpoint**: settings load; `approvals/` is committable.

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites. The four pure functions here are the feature's correctness.

- [X] T005 Implement the **design digest** in `src/ai_qa/approval/digest.py`: parse the AST and collect, in source order, each test function's name, its markers (name and arguments), and its docstring; normalise (strip comments, collapse whitespace); hash. **Test bodies are excluded.** A whole-file digest was analysis finding X1 — it would void every approval the moment its automation was written, which is the act the approval authorises, deadlocking features 003–005 — FR-017 as corrected, R2
- [X] T006 [P] Implement record read/write in `src/ai_qa/approval/records.py` at `approvals/<TICKET>/<utc-timestamp>-<decision>.json`, with the fields in `data-model.md` §1. **One file per decision** makes FR-013's append-only property structural — there must be no code path that rewrites a record
- [X] T007 Implement the three tamper checks in `src/ai_qa/approval/records.py`: **orphaned** (digest matches no design), **malformed** (unparseable or missing a required field), **modified or deleted** (differs from git history). Git history is the only way deletion is detectable — a removed file leaves nothing on disk — FR-015
- [X] T008 [P] Implement `approval_state(design)` in `src/ai_qa/approval/state.py` returning `PENDING` \| `APPROVED` \| `STALE` \| `REJECTED`, **computed on every call, never stored**. A stored state is a cache with no invalidation signal, and a wrong state looks exactly like a correct one — `STALE` is the case it would most often get wrong — FR-018, SC-003, R5
- [X] T009 Implement the additional reported conditions in `state.py`: `unmanaged` (no `generated-by: ai-qa` marker, so the gate does not apply), `orphaned`, `partial` and `unimplemented` (by counting feature 003's sentinel) — FR-029, FR-030, FR-031
- [X] T010 Implement approver identity in `src/ai_qa/approval/policy.py` from git `user.email`, **refusing to record** when unset — a record naming nobody answers none of the questions a record exists to answer, and a placeholder would be worse because it looks like an audit trail — FR-016, FR-037, R3
- [X] T011 Implement the policy decision in `policy.py`, verbatim from `data-model.md` §4: refuse `AUTHOR_UNKNOWN` when the policy requires a second person and the author is `None`; refuse `SELF_APPROVAL` when author equals approver; otherwise record. **Unknown author fails closed** — the policy cannot be checked, and a policy that passes when unverifiable is decorative — FR-022, R4
- [X] T012 Implement the single enforcement point in `src/ai_qa/approval/gate.py`. FR-009 requires that **no route** bypasses the gate — human or AI assistant, any entry point — and features 003 and 005 each introduce one, so the check lives where both funnel through rather than duplicated per call site where one is eventually forgotten
- [X] T013 [P] Add `tests/approval/test_digest.py` asserting a **body edit leaves the digest unchanged** while a docstring edit, a rename, an added or removed test, and a marker change each change it — the X1 property, and the first thing to verify
- [X] T014 [P] Add `tests/approval/test_state.py` covering all four states, including `STALE` produced by editing a docstring after approval — SC-003
- [X] T015 [P] Add `tests/approval/test_policy.py` asserting self-approval is refused under the default policy, unknown authorship is refused, and an unset git identity refuses to record — SC-018
- [X] T016 [P] Add `tests/approval/test_records.py` asserting a later decision never erases an earlier one, and that each of the three tamper conditions is detected and **never** read as a valid approval or a clean absence — SC-005, SC-008
- [X] T017 [P] Add `tests/approval/test_gate.py` asserting 100% of attempts against `PENDING`, `REJECTED` and `STALE` are refused with the state named, and **zero** proceed — SC-002

**Checkpoint**: the gate's correctness is built and tested, with no network anywhere.

---

## Phase 3: User Story 1 - Review before anyone automates (Priority: P1) 🎯 MVP

**Goal**: A reviewer sees pending designs and records a decision.

**Independent Test**: List pending designs, approve one, confirm the record and the state change.

- [X] T018 [US1] Implement the `review` subcommand in `src/ai_qa/approval/__main__.py` listing pending designs with their ticket and, **per test, the behaviour its docstring claims** — the docstrings are what is under review, so a reviewer who has not read them has not reviewed the design — FR-001, SC-001
- [X] T019 [US1] Implement `approve`, writing a record with every field from `data-model.md` §1 including `policy_require_second_person` — the policy **in force at decision time**, without which a record becomes uninterpretable the moment the setting changes — FR-002, FR-036
- [X] T020 [US1] Implement `reject`, **requiring** `--reason` and refusing with exit 5 without one. A rejection with no reason tells the author nothing and is useless to a later auditor — FR-003
- [X] T021 [US1] Ensure absence of a decision reports as `PENDING` and that **no condition** — silence, elapsed time, anything — is ever treated as approval — FR-004
- [X] T022 [P] [US1] Add a test asserting review works with no network, so an external outage never blocks reviewing — FR-005

**Checkpoint**: MVP — designs can be reviewed and decisions recorded.

---

## Phase 4: User Story 2 - Automation cannot precede approval (Priority: P1)

**Goal**: The gate holds, whoever attempts it.

**Independent Test**: Attempt automation in each non-approved state; confirm refusal naming the state; approve, confirm it proceeds.

- [X] T023 [US2] Make refusals distinguish `PENDING`, `REJECTED` and `STALE` from one another, naming which applies — three states, three different remedies — FR-007, SC-003
- [X] T024 [US2] Show the recorded rejection reason on a `REJECTED` refusal — FR-008
- [ ] T025 ⛔BLOCKED (needs **005**) [US2] Verify feature 005's `complete` command funnels through `gate.py` rather than carrying its own check — the property FR-009 actually requires
- [X] T026 [US2] Expose the approval identifier for feature 005 to stamp on completed automation — FR-010, and consumed by 005's FR-005

**Checkpoint**: approval is a precondition, not a convention.

---

## Phase 5: User Story 3 - Decisions recorded and auditable (Priority: P2)

**Goal**: Who approved what, when, and under which policy — answerable months later.

**Independent Test**: Approve one design and reject another; confirm both are retrievable with full detail.

- [X] T027 [US3] Ensure every record carries decision, ticket, design path, design digest, approver, author, policy, timestamp and test names — and that `design_path` is **human-readable metadata only**, never the matching key — FR-011, FR-014, SC-004
- [X] T028 [US3] Match records to designs by **digest, not path**, so a moved or renamed design keeps its approval and different content at the old path does not inherit it — FR-021, R9
- [X] T029 [US3] Pass every record string through feature 002's `redact()`. A rejection reason is free text typed by a human — exactly where a token gets pasted by accident — and unlike a log line, this file is **committed** — FR-034
- [X] T030 [P] [US3] Add a test asserting a design renamed after approval retains it, and that unrelated content at the old path does not — FR-021

**Checkpoint**: the audit trail answers the questions it exists for.

---

## Phase 6: User Story 4 - Approval stops applying when content changes (Priority: P2)

**Goal**: No stale approval authorises unreviewed content.

**Independent Test**: Approve, edit a docstring, confirm `STALE` and that automation is refused.

- [X] T031 [US4] Ensure a `STALE` approval refuses automation and requires re-approval, while the original record **remains in the history** rather than being deleted — FR-018, FR-019, SC-006
- [ ] T032 ⛔BLOCKED (needs **003**) [US4] Surface ticket change since approval by comparing feature 003's stored `ticket-digest` against the ticket's current text. **Do not auto-invalidate on this basis** — tickets change in ways irrelevant to the tests, and auto-invalidating would train reviewers to re-approve reflexively — FR-020
- [X] T033 [P] [US4] Add a test asserting a body edit does **not** void an approval while a docstring edit does — the same property as T013, asserted through the state function rather than the digest

**Checkpoint**: the gate is honest about what it covers.

---

## Phase 7: User Story 5 - Pipeline runs existing, approved scripts only (Priority: P1)

**Goal**: A pipeline fails rather than running anything unapproved, and never generates.

**Independent Test**: Run `verify` with an unapproved generated test present; confirm non-zero exit naming every offender.

- [X] T034 [US5] Implement `verify` in `src/ai_qa/approval/__main__.py`, exiting **non-zero (6)** on any script lacking an applicable approval. It must not execute the script and must not skip it and pass — a silently skipped test is indistinguishable from coverage that never existed — FR-026, SC-012
- [X] T035 [US5] Make `verify` print **every** offending script with its state and remedy, never a count. A pipeline run is expensive, and a failure reporting one of four problems costs four runs — FR-038
- [X] T036 [US5] Ensure `verify` is the **same** command an engineer runs locally and returns identical results for the same repository state — one implementation, two callers, so a pipeline failure is reproducible before pushing rather than met during a release — FR-028, FR-039, SC-020
- [X] T037 [US5] Ensure `verify` makes **zero** network requests and works with connectivity disabled — FR-025, FR-027, SC-011
- [X] T038 [P] [US5] Add `tests/approval/test_verify.py` asserting exit 6 with offenders named, exit 0 when all covered, and identical output from two invocations over the same state
- [X] T039 [P] [US5] Add a test asserting `unmanaged` tests (no generated marker) are **reported but not blocked** — requiring approval for every hand-written test is the fastest route to the gate being switched off — FR-029, R8

**Checkpoint**: all five stories functional.

---

## Phase 8: Polish & Cross-Cutting

- [X] T040 Implement `status` reporting every design's state plus the `unmanaged`, `partial`, `unimplemented` and `orphaned` conditions — FR-018, FR-030, FR-031
- [X] T041 Implement the exit-code mapping from `contracts/commands.md`: 0, 2 config, 3 self-approval, 4 author unknown, 5 missing reason, 6 verify found offenders, 7 identity undeterminable, 8 tampering
- [X] T042 [P] Document the review workflow in `README.md`: `review`, `approve`, `reject`, `status`, `verify`, and how to relax the approver policy deliberately
- [X] T043 [P] Add to `CLAUDE.md` that the gate is **not optional** for generated tests, that no entry point may carry its own approval check, and that the digest covers the design portion only
- [ ] T044 [P] Verify SC-013: whole-repository status in under 10 seconds for 1,000 tests
- [X] T045 [P] Verify SC-014 and SC-015: zero new dependencies, and zero assistant connectors required for review, recording, enforcement or verification
- [X] T046 [P] Verify SC-017: no credential appears in any record, report or error message

- [X] T047 [P] Add a test over a half-implemented approved design asserting it reports as **`partial`** in 100% of cases and **zero** report as complete. T009 implements partial detection but nothing currently tests it, and conflating partial with complete would let approved-but-unwritten work read as finished — SC-016, FR-031
- [X] T048 Make `verify` assert the two pipeline prohibitions this feature owns: that it executes only test scripts already present in the repository, and that no test appears for the first time during a pipeline run. The enforcing CI guards live in feature 005's tasks, so **state explicitly in the verify output which prohibition is delegated and which is checked here** - a requirement owned in one feature and enforced in another is how both end up assuming the other did it — FR-023, FR-024, SC-009, SC-010
- [X] T049 [P] Close the traceability gap for the requirements no single task owns, verifying each by inspection: **FR-006** (automation refused without an applicable approval, enforced by T012 and tested by T017), **FR-012** (records are committed files in a defined location, T006), **FR-032** (zero new dependencies), **FR-033** (no MCP or connector required for review, recording, enforcement or verification), **SC-019** (`verify` exits non-zero naming every offender)

---

## Dependencies & Execution Order

- **Phase 1** → no dependencies. T002 → T003 in order. **T004 is easy to skip and expensive to miss**
- **Phase 2** depends on Phase 1. **Blocks every user story.** T005 → T008 → T009 (state needs the digest); T010 → T011 (policy needs identity); T012 depends on T008 and T011
- **Phase 3 (US1)** depends on Phase 2. **MVP**
- **Phase 4 (US2)** depends on T012; T025 blocked on 005
- **Phase 5 (US3)** depends on T006 and T007
- **Phase 6 (US4)** depends on T005 and T008; T032 blocked on 003
- **Phase 7 (US5)** depends on T008 and T009 — and is **P1**, so it lands early despite being the last story phase
- **Phase 8** depends on the phases it exposes

### Shared write points (not parallelizable)

`src/ai_qa/approval/__main__.py` — T018, T019, T020, T034, T035, T040, T041. `src/ai_qa/config.py` — T002. `records.py` — T006, T007. `policy.py` — T010, T011. None carry `[P]` against each other.

---

## Parallel Execution Examples

- **Phase 2**: T006 and T008 run parallel to each other once T005 lands; then T013–T017 as five independent test files
- **Phase 7**: T038, T039 together
- **Phase 8**: T042–T046 together

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (T001–T022)**: a working, tested gate with review and recording. Needs feature 003 only for the provenance marker.

**Then Phase 7 (US5), not Phase 4.** It is the other P1 story and the one that gives the gate teeth where it matters; the pipeline check is also independent of feature 005.

**Four traps worth naming:**

1. **T005 is where X1 was.** If the digest covers test bodies, approving then completing a design voids the approval that permitted the completion, and the whole 003→004→005 workflow deadlocks. T013 exists to catch it.
2. **T004 is the quiet one.** If `approvals/` lands in `.gitignore`, every approval becomes invisible and `verify` reports a clean repository as entirely unapproved.
3. **T011 must fail closed on unknown authorship.** A policy that passes when it cannot be checked is decorative — and until feature 003 records `generated-by-identity`, this means the default policy refuses everything. That is correct behaviour and the reason the spec delta is blocking.
4. **T008 must compute, never store.** A cached state is wrong the moment a docstring is edited, and a wrong state is indistinguishable from a right one.
