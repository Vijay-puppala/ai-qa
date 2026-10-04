# Phase 0 Research: Test Approval Gate

**Feature**: `004-test-approval-gate` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Eleven decisions. The three clarifications in the spec (repository records, configurable approver policy defaulting to a second person, pipeline fails the run) are settled input, as is the X1 correction of 2026-10-04 scoping the approval digest to the design portion.

---

## R1: Record storage and layout

**Decision**: One JSON file per decision, at `approvals/<TICKET>/<utc-timestamp>-<decision>.json`. Committed. Human-readable, one object per file, no index.

**Rationale**: FR-012's clarified answer requires committed, offline-verifiable records. One file per decision makes FR-013's append-only property **structural rather than enforced**: a later decision is a new file, so it cannot overwrite an earlier one. There is no code path that rewrites a record, which is a stronger guarantee than "the code does not do that".

Per-ticket directories keep the listing readable as the project grows and make a ticket's full decision history one `ls` away. No index file, because an index is a second source of truth that drifts from the directory it describes.

**Alternatives considered**:
- *One append-only file per ticket* — rejected: concurrent decisions would conflict in the same file, and a bad merge could lose a record.
- *A single global log file* — rejected: every decision contends on one file, and FR-013 becomes a property of careful editing.
- *Jira comments* — rejected by the clarification; also breaks SC-010/SC-011 offline pipeline verification.

## R2: The design digest — what it covers, and what it must not

**Decision**: Parse the test file's AST and extract, in source order: each test function's name, its markers, and its docstring. Normalise (strip comments, collapse whitespace), then hash. **Test bodies are excluded.**

**Rationale**: This is the X1 fix made concrete. Digesting the whole file would void every approval the instant its automation was written — the approved act itself would invalidate the approval, deadlocking the workflow. Scoping to names, markers and docstrings matches exactly what feature 003's FR-012 defines as the reviewable design, so the digest covers what the reviewer actually read.

The consequence is a precise and desirable sensitivity: changing a docstring, renaming a test, or adding or removing one **does** void the approval, because each changes what was reviewed. Filling in or editing a body does not.

**Naming note**: this is the **design digest**. Feature 005 has a separate **assertion digest** over assertion statements. Different scope, different purpose; the names are kept distinct deliberately, because the analysis flagged the collision.

**Alternatives considered**:
- *Whole-file digest* — rejected: this was the X1 defect.
- *Digest of the file with bodies stripped textually* — rejected: fragile to formatting; AST extraction is exact.
- *Digest names only* — rejected: a docstring states the behaviour under review, so changing it silently would change the approved claim.

## R3: Approver identity

**Decision**: Read `user.email` from git configuration. If absent or empty, **refuse to record** the decision.

**Rationale**: FR-016 requires an identity meaningful to a later auditor, and FR-037 requires refusal rather than an anonymous record. Git config is the identity every contributor already has in a repository-based workflow, so this adds no account system — which the spec's assumption explicitly rules out as a far larger feature.

Refusing is the right failure: a record naming nobody answers none of the questions a record exists to answer, and writing a placeholder would be worse than writing nothing because it looks like an audit trail.

**Alternatives considered**:
- *OS username* — rejected: not meaningful to an auditor and collides across machines.
- *An environment variable* — rejected: trivially set to anything, so it records intent rather than identity.
- *Build a user directory* — rejected by the spec's assumption; dwarfs the gate itself.

## R4: Author determination for the approver policy

**Decision**: Read the design's author from feature 003's `generated-by-identity` provenance field. Where it is absent — a hand-written test, or a file generated before the field existed — treat the author as **unknown** and, under the default policy, **refuse** the approval, naming the reason.

**Rationale**: FR-022's clarified answer requires the approver not to be the author by default, which is unenforceable without knowing the author. The author is only knowable at generation time, which is why feature 003's plan records it — flagged there as a spec delta, and it is this decision that needs it.

Refusing on unknown authorship is the fail-closed choice consistent with FR-038's spirit elsewhere in the project: an unknown author means the policy cannot be checked, and a policy that silently passes when it cannot be checked is not a policy. The escape hatch is the explicit configuration that permits self-approval.

**Alternatives considered**:
- *Infer the author from git blame* — rejected: blame reports who committed the file, which for a generated file is often whoever ran generation, but may be a merge or a reformatting commit. Plausible-looking and wrong.
- *Pass the author on the command line* — rejected: self-asserted, so it defeats the policy.
- *Allow the approval when the author is unknown* — rejected: fails open on the one check the policy exists for.

## R5: The four states

**Decision**: A single `approval_state(design) -> State` function returning `PENDING`, `APPROVED`, `STALE`, or `REJECTED`, computed from the decision directory plus a fresh design digest. No stored state.

**Rationale**: SC-003 requires all four to be distinguishable in 100% of cases and zero reported as another. Computing state from the records and the current file means there is nothing to keep in sync — a stored state field would be a cache that goes stale, and the bug would be invisible because a wrong state looks like a correct one.

`STALE` is specifically "a latest decision of approved, whose digest does not match the current design". That is the state that makes the gate honest, and it is the one a stored field would most likely get wrong.

**Alternatives considered**:
- *Store the current state in a file* — rejected: a cache with no invalidation signal.
- *Three states, folding stale into pending* — rejected: SC-003 requires four, and "never reviewed" and "reviewed then changed" need different remedies.

## R6: Tamper detection

**Decision**: Three checks, reported rather than enforced: a record whose digest matches no design in the repository (orphaned); a record that is unparseable or missing required fields (malformed); and any difference between the records on disk and those in git history (modified or deleted).

**Rationale**: FR-015 requires tampering or deletion to be **detectable** and never interpretable as a valid approval or a clean absence. Git history is what makes deletion detectable at all — a removed file leaves no trace on disk, but it leaves one in the history.

**The honest limitation**, already recorded in the spec's assumptions: the gate is **cooperative**. Anyone with repository write access can author a record, and a determined insider can commit a convincing one. These checks catch mistakes, accidents and drift, not an adversary. Closing that would need signing and an external authority — a much larger feature than the gate.

**Alternatives considered**:
- *Cryptographic signing* — rejected for this feature: needs key distribution and an authority, and the spec's assumption scopes the gate as cooperative.
- *Refusing to run when tampering is detected* — rejected: makes a false positive block all work; reporting is the proportionate response.

## R7: Pipeline verification

**Decision**: One command, `approvals verify`, exiting non-zero when any test script lacks an applicable approval, printing each offending script with its state and remedy. The same command is what an engineer runs locally.

**Rationale**: FR-026's clarified answer (fail the run), FR-028 (one command so a pipeline never reimplements the rules), FR-038 (name every script and its remedy) and FR-039 (identical local results). One implementation, two callers — which is what keeps a pipeline failure reproducible before pushing rather than discovered during a release.

Printing *every* offender rather than failing on the first matters: a pipeline run is expensive, and a failure reporting one of four problems costs four runs.

**Alternatives considered**:
- *A pipeline-only script* — rejected: diverges from what engineers run, so failures surprise.
- *Fail on the first offender* — rejected: turns one fix cycle into several.
- *Exit zero with a warning* — rejected by the clarification; a warning is what gets ignored.

## R8: Which scripts require approval

**Decision**: A test file requires approval if it carries feature 003's `generated-by: ai-qa` provenance marker. Hand-written tests without it are **out of scope for the gate** and are reported as `unmanaged` in the verify output.

**Rationale**: FR-029 requires defined treatment for tests that did not originate from a generated design. Keying on the provenance marker is the only signal that is both reliable and already present — and the alternative, requiring approval for every test, would mean the gate blocks a hand-written test somebody wrote in two minutes, which is how a gate gets disabled.

Reporting them as `unmanaged` rather than omitting them keeps the count visible: if that number grows unexpectedly, someone is bypassing generation, and that is worth seeing.

**Alternatives considered**:
- *Every test requires approval* — rejected: scope the spec does not claim, and the fastest route to the gate being switched off.
- *Silently ignore unmanaged tests* — rejected: hides a bypass.

## R9: Rename and move safety

**Decision**: Records are matched to designs by **digest**, not by path. A record stores the design's path at decision time for human readability only.

**Rationale**: FR-021 requires that renaming or moving approved content neither silently voids the approval nor silently transfers it to different content. A content digest gives both properties for free: the same design at a new path still matches, and different content at the old path does not.

**Alternatives considered**:
- *Match by path* — rejected: a rename would void the approval, which FR-021 forbids.
- *Match by path with a rename-tracking table* — rejected: a second source of truth, and git already tracks renames.

## R10: Partial implementation reporting

**Decision**: Count feature 003's sentinel occurrences within an approved design. All present means approved-but-unimplemented; none means fully implemented; some means partial.

**Rationale**: FR-030 and FR-031 require approval to be distinguishable from automation existing, and partial implementation to be reportable. The sentinel is already the project's single marker for "unimplemented", so this needs no new mechanism — and reusing it means the three features agree on the state of a test by construction rather than by convention.

**Alternatives considered**:
- *Track implementation state in the record* — rejected: a record describes a decision, not the current code, and would need updating on every edit.

## R11: Configuration

**Decision**: Two settings on the existing `Settings` model: `approval_require_second_person: bool` (default **`True`**) and `approval_records_dir: Path` (default `approvals/`). Each decision records the policy that was in force (FR-036).

**Rationale**: FR-022's clarified answer is "configurable, defaulting to requiring a second person". Recording the policy on the decision is what keeps a past record interpretable — without it, an auditor reading a self-approval cannot tell whether it was permitted at the time or a violation, and the current setting says nothing about the past.

Settings go on the existing model rather than a new one, consistent with feature 001's single-validated-source rule and feature 002's precedent.

**Alternatives considered**:
- *A dedicated config file for approvals* — rejected: a second configuration source, which feature 001's SC-010 exists to prevent.
- *Not recording the policy* — rejected: makes every historical record ambiguous the moment the setting changes.

---

## Resolved unknowns

| Unknown | Resolved by |
|---|---|
| How is a record stored so a pipeline can verify it offline? | R1 — one committed JSON file per decision |
| What exactly does an approval cover? | R2 — AST digest of names, markers, docstrings; bodies excluded |
| Where does the approver's identity come from? | R3 — git `user.email`, refuse if absent |
| How is the *author* known, to enforce the policy? | R4 — feature 003's provenance field; refuse if unknown |
| How are the four states computed without drifting? | R5 — derived, never stored |
| How is deletion of a record detected? | R6 — git history comparison |
| How does a pipeline check without reimplementing the rules? | R7 — one `verify` command, same locally |
| Which tests does the gate apply to? | R8 — those carrying the generated marker |
| Does a rename void an approval? | R9 — no; digest-matched, not path-matched |
