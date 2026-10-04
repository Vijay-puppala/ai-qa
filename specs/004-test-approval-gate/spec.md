# Feature Specification: Test Approval Gate

**Feature Branch**: `004-test-approval-gate` *(no branch created — `main` is the only branch and nothing is committed yet)*

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "once tests are created that these are manually reviewed and approved by user then only automation scripts needs to be created these needs approvals needs to be recorded and incase of ci-cd we can consider only existing test scripts are executed rather than any new tests are added as part of ci cd"

## Clarifications

### Session 2026-10-04

- Q: Where are approval records stored? -> A: **Committed files in the repository**, one per decision - diffable, reviewable in the same change, and verifiable with no network access.
- Q: May the author approve their own test design? -> A: **Configurable, defaulting to requiring a second person.** The policy in force must be recorded on each decision.
- Q: What does the pipeline do with an unapproved test script? -> A: **Fail the run.** Non-zero exit, naming every offending script and its remedy.
- Correction applied 2026-10-04 (cross-feature analysis finding X1, CRITICAL): FR-017 and FR-035 originally tied an approval to a digest of the **whole** file, so writing the test bodies - the very act the approval authorises - would have voided that approval and deadlocked the workflow. Both now scope the digest to the **design portion** (names, markers, docstrings). Changing a docstring, renaming a test, or adding or removing one still voids the approval; filling in a body does not.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review a generated test design before anyone automates it (Priority: P1)

A QA lead is shown what was generated for a ticket — the test names and the behaviour each one claims it will prove — and decides whether that is the right set of tests. They approve it, reject it, or ask for changes. This happens *before* anyone spends time writing automation, because reviewing intent is cheap and rewriting automation is not.

**Why this priority**: This is the point of the feature. Reviewing a test design costs minutes; discovering after automation that the tests prove the wrong thing costs days. Without this story there is no gate.

**Independent Test**: Generate a test design for a ticket, review it, record an approval, and confirm the approval is visible afterwards. Fully testable alone.

**Acceptance Scenarios**:

1. **Given** a generated test design awaiting review, **When** the reviewer lists what is pending, **Then** it appears with its source ticket and the behaviour each test claims to prove.
2. **Given** a test design under review, **When** the reviewer approves it, **Then** the approval is recorded and the design is no longer pending.
3. **Given** a test design under review, **When** the reviewer rejects it, **Then** the rejection is recorded with the reviewer's reason and the design does not become approved.
4. **Given** a reviewer has neither approved nor rejected, **When** the state is inspected, **Then** the design is reported as pending rather than as implicitly approved.

---

### User Story 2 - Automation cannot be written before approval (Priority: P1)

An engineer, or an AI assistant, tries to turn an unapproved test design into working automation. The platform refuses and says the design needs approval first. Approval is a precondition that holds whoever attempts it and whatever route they take.

**Why this priority**: An approval step that can be bypassed is documentation, not a gate. This story is what makes Story 1 mean something.

**Independent Test**: Attempt to implement an unapproved test design and confirm it is refused, naming the missing approval; then approve it and confirm the same attempt proceeds.

**Acceptance Scenarios**:

1. **Given** a test design with no approval, **When** automation is attempted for it, **Then** it is refused, naming the design and the approval that is missing.
2. **Given** a test design that was rejected, **When** automation is attempted, **Then** it is refused and the recorded rejection reason is shown.
3. **Given** an approved test design, **When** automation is attempted, **Then** it proceeds.
4. **Given** an approved design, **When** automation is written, **Then** the resulting scripts record which approval authorised them.

---

### User Story 3 - Every approval decision is recorded and auditable (Priority: P2)

Months later, someone asks who approved a particular set of tests and when. The answer is available without relying on anyone's memory, and it covers rejections as well as approvals.

**Why this priority**: The user asked specifically that approvals "need to be recorded". An unrecorded approval cannot be audited, cannot be checked by automation, and cannot answer the question that gets asked during an incident.

**Independent Test**: Approve one design and reject another, then confirm both decisions are retrievable with who, what, and when.

**Acceptance Scenarios**:

1. **Given** any recorded decision, **When** it is inspected, **Then** it states the decision, the approver's identity, the time, the source ticket, and exactly what was approved.
2. **Given** a rejection, **When** it is inspected, **Then** the reason is present.
3. **Given** a history of decisions on the same design, **When** it is inspected, **Then** earlier decisions remain visible rather than being overwritten by the latest.
4. **Given** an approval record, **When** someone asks what content it covered, **Then** that is answerable precisely rather than by inference from timestamps.

---

### User Story 4 - An approval stops applying when what was approved changes (Priority: P2)

Someone edits an approved test design. The approval no longer applies, and the platform says so rather than letting a stale approval authorise content nobody reviewed.

**Why this priority**: This is the failure that makes approval gates worthless in practice. An approval that survives arbitrary edits to the thing it approved is a rubber stamp, and the drift is silent.

**Independent Test**: Approve a design, modify it, then confirm the platform reports the approval as no longer applying and refuses automation until it is re-approved.

**Acceptance Scenarios**:

1. **Given** an approved design that is then modified, **When** its state is inspected, **Then** the approval is reported as no longer applying to the current content.
2. **Given** a stale approval, **When** automation is attempted, **Then** it is refused and re-approval is required.
3. **Given** a stale approval, **When** the record is inspected, **Then** the original decision remains in the history rather than being deleted.
4. **Given** an approved design whose source ticket has since changed, **When** its state is inspected, **Then** that is surfaced so the reviewer can decide whether re-approval is needed.

---

### User Story 5 - CI/CD runs existing scripts and never creates tests (Priority: P1)

A pipeline runs the committed test suite. It does not generate tests, does not reach for a ticket to invent new ones, and does not run anything that has not been approved. What it executes is exactly what is in the repository and approved — nothing appears for the first time during a pipeline run.

**Why this priority**: Equal to the gate itself. A pipeline that can generate and run new tests makes approval optional in practice, because the thing that actually runs never passed through review.

**Independent Test**: Run the pipeline's command set in an unattended environment with no generation capability available, and confirm it executes existing approved scripts and fails or refuses if unapproved ones are present.

**Acceptance Scenarios**:

1. **Given** a pipeline run, **When** it executes, **Then** it runs only test scripts already committed to the repository.
2. **Given** a pipeline run, **When** it executes, **Then** no test generation occurs and no ticket is consulted to produce new tests.
3. **Given** a repository containing an unapproved test script, **When** the pipeline runs, **Then** the run fails with a non-zero outcome, naming every offending script, rather than executing or silently skipping it.
4. **Given** a pipeline run in an environment with no network access to the ticket system, **When** it executes, **Then** approved scripts still run normally.

---

### Edge Cases

- **No approval exists**: Automation attempt must be refused naming the missing approval, not fail obscurely.
- **Design was rejected**: Must be refused with the recorded reason shown, distinctly from "never reviewed".
- **Approved content subsequently edited**: Approval must stop applying (US4). This is the central failure mode of approval systems.
- **Approver is also the author**: Refused under the default policy, naming the policy. Permitted only where self-approval has been explicitly configured, and then recorded as such.
- **Approval record deleted or hand-edited**: Must be detectable rather than being treated as a valid absence of approval or a valid approval.
- **Two reviewers decide concurrently**: Must not produce a record where the outcome depends on write order without being visible.
- **Approved design deleted**: The record must not point at nothing silently; the orphaned approval must be reportable.
- **Approved file renamed or moved**: Must not silently void the approval, nor silently carry it to unrelated content.
- **Partially implemented design**: Some tests in an approved design automated, others not. Must be reportable rather than appearing complete.
- **Hand-written test that never came from a design**: Must have defined treatment — not every test originates from generation.
- **Source ticket changed after approval**: Must be surfaced; the approval covered the design as reviewed against the ticket as it then was.
- **Pipeline encounters an unapproved script**: Must be detected and reported (US5).
- **Pipeline runs with no ticket-system access**: Approved scripts must still run; approval checking must not require the network.
- **Approval for a design whose tests are all still unimplemented**: Approving the design is not the same as the automation existing; the two states must be distinguishable.
- **Approver identity cannot be determined**: Recording must be refused rather than writing an anonymous or placeholder approver, which would produce a record that answers nothing.
- **A stale approval blocks an unrelated deploy**: An operational consequence of failing the run. The same check must be reproducible locally so the failure is never first discovered in the pipeline.
- **Approver policy changed after a decision**: A past decision must remain interpretable against the policy that was in force when it was made, not the current one.

## Requirements *(mandatory)*

### Functional Requirements

**The review step**

- **FR-001**: The platform MUST let a reviewer see every test design awaiting review, with its source ticket and the behaviour each test claims to prove.
- **FR-002**: The platform MUST let a reviewer record an explicit **approval** or **rejection** of a test design.
- **FR-003**: A rejection MUST capture the reviewer's reason.
- **FR-004**: Absence of a decision MUST be reported as **pending**. The platform MUST NOT treat silence, time elapsed, or any other condition as approval.
- **FR-005**: Review MUST be possible without network access to the ticket system, so reviewing is never blocked by an external outage.

**The gate**

- **FR-006**: Creating automation for a test design MUST be refused unless a currently-applicable approval exists for it.
- **FR-007**: A refusal MUST name the design and state whether it is pending, rejected, or covered by an approval that no longer applies — these three MUST be distinguishable.
- **FR-008**: A rejection refusal MUST show the recorded reason.
- **FR-009**: The gate MUST apply regardless of who or what attempts automation — human or AI assistant — and regardless of which entry point is used. No route may bypass it.
- **FR-010**: Automation produced for an approved design MUST record which approval authorised it.

**Recording decisions**

- **FR-011**: Every decision MUST be recorded with: the decision, the approver's identity, the time, the source ticket, and a precise identification of the content decided upon.
- **FR-012**: Decision records MUST be stored as committed files in the repository, one file per decision, in a defined location, in a format a human can read and a reviewer can diff. Verification MUST require no network access and no external service.
- **FR-013**: The decision history for a design MUST be append-only in effect: a later decision MUST NOT erase an earlier one.
- **FR-014**: A decision record MUST identify the approved content precisely enough that "what exactly was approved?" is answerable without inference.
- **FR-015**: Tampering with or deletion of a decision record MUST be detectable, and MUST NOT be interpretable as either a valid approval or a clean absence of one.
- **FR-016**: The approver's identity MUST be recorded in a form that is meaningful to a later auditor, not an anonymous or shared marker.

**Approval validity**

- **FR-017**: An approval MUST apply only to the **design portion** of the content it was recorded against - the test names, the markers, and the docstrings stating the behaviour each test must prove. Any change to that design portion MUST cause the approval to stop applying. Writing or changing a test **body** MUST NOT void the approval, because implementing the approved behaviour is the act the approval authorises (FR-030).
- **FR-018**: A no-longer-applicable approval MUST be reported as such, distinctly from "never approved" and from "rejected".
- **FR-019**: When an approval stops applying, the original record MUST remain in the history rather than being deleted.
- **FR-020**: Where the source ticket has changed since approval, the platform MUST surface that so the reviewer can judge whether re-approval is needed. It MUST NOT invalidate the approval automatically on that basis alone, because a ticket may change in ways irrelevant to the tests.
- **FR-021**: Renaming or moving approved content MUST NOT silently void the approval, and MUST NOT silently transfer it to different content.

**Who may approve**

- **FR-022**: The platform MUST enforce a configurable approver policy. The default MUST require that the approver is **not** the author of the design under review. Where the policy is relaxed to permit self-approval, that MUST be an explicit configuration choice, never a default or a silent fallback.

**Pipeline behaviour**

- **FR-023**: A pipeline run MUST execute only test scripts already present in the repository.
- **FR-024**: A pipeline run MUST NOT generate tests, and MUST NOT consult the ticket system to produce new ones. No test may appear for the first time during a pipeline run.
- **FR-025**: A pipeline MUST be able to verify that every test script it would execute is covered by a currently-applicable approval, without network access.
- **FR-026**: On encountering a test script with no applicable approval, the pipeline MUST **fail the run** with a non-zero outcome. It MUST NOT execute the script, and MUST NOT skip it and pass - a silently skipped test is indistinguishable from coverage that never existed.
- **FR-027**: Pipeline execution of approved scripts MUST NOT depend on the ticket system being reachable.
- **FR-028**: The platform MUST provide a single command that reports pipeline-relevant approval state, so a pipeline's enforcement does not depend on reimplementing the rules.

**Scope of the gate**

- **FR-029**: Test scripts that did not originate from a generated design MUST have defined treatment, stated explicitly rather than left to interpretation.
- **FR-030**: Approving a design MUST be distinguishable from its automation existing. Approval authorises automation; it does not assert that automation has been written.
- **FR-031**: Partial implementation of an approved design MUST be reportable, so a design is not treated as done when only some of its tests exist.

**Inherited constraints**

- **FR-032**: This feature MUST add no new third-party dependency, consistent with the dependency floor established in feature 001.
- **FR-033**: No MCP server, assistant connector, or other external tooling may be required at runtime for review, recording, gate enforcement, or pipeline verification.
- **FR-034**: Credentials MUST NOT appear in any decision record, report, or error message.

**Consequences of the recorded decisions**

- **FR-035**: A decision record MUST identify the content it covers by a digest of the **design portion** defined in FR-017 - not of the whole file - so FR-017's validity check and FR-015's tamper detection need nothing beyond the repository itself. Digesting the whole file would void every approval the moment its automation was written, making the gate self-defeating.
- **FR-036**: Every decision record MUST state which approver policy was in force when it was made, so a later auditor can interpret it without reconstructing historical configuration.
- **FR-037**: Where the approver's identity cannot be determined, recording a decision MUST be refused. The platform MUST NOT record an anonymous, placeholder, or shared approver.
- **FR-038**: A pipeline failure under FR-026 MUST name every script lacking an applicable approval, state for each whether it is pending, rejected, or stale, and state the remedy. A failure reporting only a count is insufficient.
- **FR-039**: The approval check MUST be runnable locally and MUST produce results identical to the pipeline's for the same repository state, so a pipeline failure is reproducible before pushing rather than discovered during a deploy.

### Key Entities

- **Test Design**: The reviewable artifact produced for a ticket — test names plus the behaviour each claims to prove. The thing under review. Supplied by the generation feature.
- **Decision**: One recorded approval or rejection: outcome, approver identity, time, source ticket, precise identification of the content decided upon, and a reason when rejected.
- **Decision History**: The ordered set of decisions for a design. Append-only in effect, so earlier decisions survive later ones.
- **Approval Validity**: Whether a recorded approval still applies to the current content. The four states that must be distinguishable: pending, approved-and-applicable, approved-but-stale, rejected.
- **Automation Script**: The runnable test produced after approval, carrying a reference to the approval that authorised it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can see every pending test design, with its source ticket and claimed behaviour, in one listing.
- **SC-002**: 100% of automation attempts against a design that is pending, rejected, or covered by a stale approval are refused; zero proceed.
- **SC-003**: The four states — pending, approved-and-applicable, approved-but-stale, rejected — are distinguishable in 100% of cases; zero are reported as another.
- **SC-004**: 100% of recorded decisions carry the decision, approver identity, time, source ticket, and a precise identification of what was decided.
- **SC-005**: Zero decisions are lost or overwritten by a later decision on the same design.
- **SC-006**: Any modification to approved content causes the approval to stop applying in 100% of cases; zero modified designs remain reported as approved.
- **SC-007**: "Who approved this, when, and what exactly did they approve?" is answerable for any approved design with zero reliance on memory or inference.
- **SC-008**: Tampering with or deletion of a decision record is detected in 100% of cases; zero such cases are reported as a valid approval or a clean absence.
- **SC-009**: Zero tests appear for the first time during a pipeline run.
- **SC-010**: Zero ticket-system requests are made during a pipeline run.
- **SC-011**: A pipeline run in an environment with no network access to the ticket system executes all approved scripts normally, with zero failures attributable to that absence.
- **SC-012**: 100% of test scripts without an applicable approval are detected by the pipeline before execution; zero are executed silently.
- **SC-013**: Approval state for an entire repository is reportable by one command in under 10 seconds for a suite of up to 1,000 tests.
- **SC-014**: Zero new third-party dependencies are added by this feature.
- **SC-015**: Zero assistant connectors or external tooling are required for review, recording, gate enforcement, or pipeline verification.
- **SC-016**: A design whose automation is partially written is reported as partial in 100% of cases; zero are reported as complete.
- **SC-017**: 100% of decision records are committed, human-readable files verifiable with zero network requests and zero external services.
- **SC-018**: Under the default policy, zero self-approvals are accepted. Where self-approval is explicitly configured, 100% of such decisions are recorded as self-approved with the policy named.
- **SC-019**: A pipeline encountering any script without an applicable approval exits non-zero in 100% of cases, naming every offending script with its state and remedy.
- **SC-020**: The local check and the pipeline check return identical results for the same repository state, with zero divergence.

## Assumptions

Reasonable defaults chosen where the description did not specify a detail. Each is a candidate for revision during `/speckit.clarify` or `/speckit.plan`.

- **Builds on feature 003**: The reviewable test design is the skeleton produced by prompt-driven generation, and "creating automation scripts" means implementing those skeleton bodies into working tests. Feature 003 must exist first; feature 003 in turn depends on feature 002.
- **One gate, not two**: Approval is of the test *design*, before automation is written. The automation itself is assumed to go through the team's normal code review rather than a second gate inside this platform. If the automation needs its own recorded approval, that is a change to this feature's scope.
- **Approval is per design, not per individual test**: A reviewer approves the set of tests generated for a ticket. Approving some and rejecting others within one design is treated as a rejection with a reason, not a partial approval, so that "approved" always means the whole reviewed artifact.
- **Identity comes from the environment, not a new account system**: The approver's identity is taken from the development environment rather than from authentication this platform implements. Building a user directory would be a far larger feature than the gate itself. Where identity cannot be determined, FR-037 requires refusing to record rather than recording an anonymous approval - a record naming nobody answers none of the questions the record exists to answer.
- **Failing the pipeline is a deliberate trade** *(resolved: Clarifications, 2026-10-04)*: an unapproved or stale script fails the run rather than being skipped. The cost is real - one stale approval can block a deploy that has nothing to do with it, and that pressure is how gates get weakened. FR-038 and FR-039 are the mitigation: the failure says exactly which script and what to do, and the identical check runs locally, so the failure is foreseeable rather than a surprise during a release. The alternative, skipping silently, trades a visible inconvenience for invisible coverage loss, which is the worse failure for a QA platform.
- **Pipeline enforcement is cooperative, not adversarial**: The gate stops mistakes and omissions, not a determined engineer with repository write access. Anyone able to commit can commit an approval record. Making the gate tamper-proof against its own operators would need signing and an external authority, which is a different and much larger feature.
- **"CI/CD" means a pipeline running the committed suite**: No specific pipeline product is assumed. What matters is the two prohibitions — execute only what is committed, generate nothing — which hold for any pipeline.
- **No pipeline configuration is delivered here**: This feature defines the behaviour a pipeline must have and the command that makes it checkable. Authoring the pipeline itself remains out of scope, as it was in feature 001.
- **Supported platforms carry over**: Windows and Linux. macOS remains unsupported.
- **Features 001 to 003 rules remain in force**: dependency floor, `.env`/`.gitignore` with no secret scanning, configuration through the validated settings model, no MCP at runtime, parallel-safe fixtures and artifact paths, and the skeleton conventions of feature 003.
- **Canonical terms** *(normalised 2026-10-04, finding X4)*: a **test design** is the reviewable artifact for a ticket - test names, markers, and the docstrings stating the behaviour each test must prove. A **skeleton** is a test design in its unimplemented state, before bodies exist. **Completed automation** is a test design whose bodies have been written. The three terms name three states of one artifact, not three artifacts.
- **No project constitution in force**: `.specify/memory/constitution.md` is still the unfilled template. This is the fourth feature specified without governance gates — and it is the one most obviously about governance, which makes the omission harder to justify.
