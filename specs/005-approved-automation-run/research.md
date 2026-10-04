# Phase 0 Research: Approved Automation Run & Reporting

**Feature**: `005-approved-automation-run` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Twelve decisions. The three clarifications in the spec (in-project report, ticket-scoped run, mechanical-only repair) are settled input.

## Empirical findings

Checked against the installed toolchain on 2026-10-04 rather than assumed. Two of these overturn the obvious design.

| Probe | Result | Consequence |
|---|---|---|
| Result JSON keys from `allure-pytest` 2.16.2 | `description, fullName, historyId, labels, name, parameters, start, status, stop, testCaseId, titlePath, uuid` | The generator reads this exact shape (R1) |
| Labels on a normal test | `parentSuite, suite, host, thread, framework, language, package` — and `tag` for bare markers | No ticket information is present by default |
| `@pytest.mark.ticket("TC-345")` | **No label produced at all.** A marker *with arguments* is not mapped to a `tag` | **Ticket attribution needs an explicit hook** (R2) |
| Failed test record | `statusDetails` present with `message` **and** `trace` | Failure reason and traceback are available from result data (R3) |

---

## R1: Report generation from result data

**Decision**: A generator in the project reads `reports/allure-results/*-result.json` and emits one self-contained HTML file. Standard library only — `json`, `html.escape`, `pathlib`, string templating. No templating engine, no new dependency.

**Rationale**: FR-031 permits nothing else: zero new dependencies, zero external prerequisites. HTML rather than Markdown because FR-016 requires failure evidence to be *reachable* from the report, which means links, and because a browser is the one viewer every machine already has. The verified schema above means the generator is a straightforward projection — status, name, timing, labels, `statusDetails` — not a parsing problem.

**Alternatives considered**:
- *Allure CLI* — rejected by the Q1 clarification; needs Java, and remains available as the optional path (FR-033).
- *Allure 3* — rejected during clarification: npm-only, requires Node.js, which features 001 and 002 excluded deliberately.
- *A templating dependency (Jinja2)* — rejected: FR-031 forbids it, and the report has one layout.
- *Markdown output* — rejected: no reliable link-to-evidence or collapsible traceback in a plain Markdown viewer.

## R2: Ticket attribution needs an explicit hook

**Decision**: Tests declare their ticket with `@pytest.mark.ticket("TC-345")`. A `conftest.py` hook reads that marker at test setup and writes an Allure label named `ticket` with the key as its value. The generator then groups by that label.

**Rationale**: This is the finding most likely to have been got wrong by assumption. `allure-pytest` maps bare markers to `tag` labels, so it is natural to expect `@pytest.mark.ticket("TC-345")` to arrive as a tag — it does not. The probe produced **no label whatsoever** for a marker carrying an argument. Without the hook, FR-021, FR-023 and SC-008 are simply unachievable from result data, and the failure would be silent: reports would render correctly with every test unattributed.

Writing a real Allure label rather than stuffing the key into the test name keeps the report's grouping independent of naming conventions, and keeps the key machine-readable for the run-scoping filter in R4.

**Alternatives considered**:
- *Rely on marker-to-tag mapping* — rejected: verified not to work.
- *Encode the ticket in the test name* — rejected: couples grouping to naming, and breaks the moment someone renames a test.
- *A separate committed index mapping tests to tickets* — rejected: a second source of truth that drifts, and feature 003's FR-009 forbids committed files that scope behaviour to particular tickets.

## R3: Failure evidence

**Decision**: Take the failure message and traceback from `statusDetails.message` and `statusDetails.trace`. Reference per-test evidence files (screenshot, trace, video) from feature 001's `reports/artifacts/<sanitised-node-id>/` by relative path.

**Rationale**: Verified present on a failing record, so FR-016 needs no extra capture mechanism. Linking evidence by relative path rather than embedding it keeps the report small; FR-034 then requires the report to state that the artifacts directory must accompany it, which is the honest consequence of that choice.

**Not yet verified**: whether `allure-pytest` also records those artifacts as `attachments` entries in the result JSON. The probe produced none, but it was a non-browser test. If attachments do appear for browser failures, the generator should prefer them over path reconstruction. Flagged for confirmation at implementation rather than assumed either way.

**Alternatives considered**:
- *Embed screenshots as data URIs* — rejected for now: makes a single truly portable file, but inflates the report and FR-018 forbids truncation as the escape hatch. Worth revisiting if portability beats size.

## R4: Scoping a run to one ticket

**Decision**: A `--ticket` option registered in `conftest.py`, filtering at collection by the `ticket` marker's argument. Not `-m`.

**Rationale**: `-m` evaluates marker *names*, not their arguments — `-m "ticket"` selects every ticketed test regardless of key. `-k` matches against names, which would make scoping depend on the naming convention R2 deliberately avoided. A collection-time filter reads the same marker the label hook reads, so the two cannot disagree.

**Alternatives considered**:
- *`-m "ticket"`* — rejected: cannot discriminate by key.
- *`-k TC-345`* — rejected: matches names, so it both misses correctly-marked tests and matches unrelated ones.

## R5: Detecting that a skeleton is now implemented

**Decision**: Reuse feature 003's skip sentinel. A test is an unimplemented skeleton while its body skips with that sentinel reason; completion removes it. The listing from feature 003's FR-028 is the single source for "what is still unimplemented".

**Rationale**: FR-007 requires completed tests to stop being reported as skeletons, and feature 003 already defined the marker that makes that detectable. Inventing a second mechanism here would create two answers to the same question.

**Alternatives considered**:
- *Track completion state in a separate file* — rejected: drifts from the code it describes.
- *Infer from whether a test has assertions* — rejected: a legitimately implemented test may assert indirectly through a helper.

## R6: Classifying failures for repair eligibility

**Decision**: A deterministic classifier mapping the failure's exception type to one of `ELIGIBLE` or `ESCALATE`, with an explicit allowlist and an unconditional `ESCALATE` default.

`ELIGIBLE`: collection and import errors, `SyntaxError`, pytest fixture lookup errors, unregistered-marker errors, and `TypeError`/`AttributeError` arising from misuse of the test framework's own API.

`ESCALATE` (named explicitly, per FR-037): `AssertionError`, Playwright timeout and element-not-found errors, HTTP status mismatches — and, per FR-038, **anything the classifier does not positively recognise**.

**Rationale**: Q3's middle option is only safe if the boundary is mechanical rather than judgemental, so the classifier keys off the exception type and nothing else — no message heuristics, no inference from the test's content. Defaulting to `ESCALATE` means a new failure mode introduced by a future dependency upgrade lands on the safe side without anyone remembering to classify it.

The classifier must be pure and unit-testable, because SC-022 asserts a negative — zero repair attempts on ineligible classes — and a negative is only verifiable if the decision is a function of its input.

**Alternatives considered**:
- *Classify from the failure message* — rejected: brittle across versions, and a message is attacker- and app-controlled text.
- *Let the assistant judge eligibility* — rejected: makes SC-022 unverifiable and puts the safety boundary in the least deterministic component.
- *Treat element-not-found as eligible* — rejected by FR-037. It is the commonest test-side fault in browser automation, which is exactly why it is tempting; it is also indistinguishable from a feature that was never built, so repairing it would erase a genuine finding.

## R7: Enforcing "a repair must not change what a test asserts"

**Decision**: Before a repair, parse the test's source and extract an **assertion digest** — the normalised text of every `assert` statement and every `expect(...)` call within the test function. Re-extract after the repair and refuse the repair if the digest changed.

**Rationale**: FR-039 is the single most important requirement in this feature, and without a mechanism it is just an instruction that the component most able to violate it is asked to obey. An AST-level digest makes it enforceable: whitespace, comments and surrounding code may change freely; the asserted conditions may not. This is what keeps the repair path from becoming the shortest route to a green assertion.

Deliberate limitation, stated rather than hidden: the digest compares assertion *text*, so a repair could change an assertion's meaning by altering a variable it depends on without touching the assert line itself. The digest narrows the hole substantially but does not close it, which is why FR-041 still requires every repaired pass to be disclosed in the report, and why repairs remain bounded and recorded.

**Alternatives considered**:
- *Trust the instruction* — rejected: puts the safety property in the hands of the component most likely to breach it.
- *Forbid any edit to the test file and regenerate instead* — rejected: regeneration would discard the authored body, which is the thing being repaired.
- *Compare full-file digests* — rejected: any legitimate repair changes the file, so the check would refuse everything.

## R8: A run that collects nothing is a failure

**Decision**: Treat pytest exit code 5 (no tests collected) as failure in every command this feature adds, and report it as such.

**Rationale**: FR-011 and SC-009. Exit 5 is pytest's "nothing to do", and most callers treat non-1 as success — so a mistyped `--ticket` would produce a confident green run that tested nothing. For a platform whose output is confidence, that is the worst available failure mode. Feature 001's command contract already flagged exit 5 as a failure for pipelines; this makes it explicit for the new commands too.

**Alternatives considered**:
- *Treat exit 5 as success with a warning* — rejected: the warning is exactly what gets ignored.

## R9: Report self-containment and evidence

**Decision**: One HTML file at `reports/report.html`, with inline CSS and no external asset requests. Evidence linked by relative path into `reports/artifacts/`. The report states that the artifacts directory must travel with it for evidence links to resolve.

**Rationale**: FR-015 requires readability with nothing but a browser, and no external request means it works offline and in a locked-down environment. FR-034 requires the report to say what must accompany it — so the limitation is disclosed in the artifact itself rather than in documentation nobody reads alongside it.

**Alternatives considered**:
- *A directory of linked HTML pages* — rejected: harder to share, and "self-contained" in FR-015 reads against it.
- *CDN-hosted CSS* — rejected: breaks offline viewing, and adds a network dependency to reading a report.

## R10: Keeping completion and repair out of pipelines

**Decision**: Two layers. Completion and repair live in commands a pipeline never invokes, and each refuses to run when a CI environment is detected, naming the reason.

**Rationale**: FR-008 and FR-042 forbid both in a pipeline, and feature 004's FR-024 forbids tests appearing for the first time during a pipeline run. Relying only on "the pipeline does not call it" would make the guarantee a property of a YAML file nobody in this repository controls. The environment check is the layer that holds when someone adds a convenient step.

Detection is by the conventional `CI` environment variable plus the common vendor variables, treated as advisory-but-sufficient: a misconfigured local shell claiming to be CI loses access to completion, which is a safe failure.

**Alternatives considered**:
- *Rely on pipeline configuration alone* — rejected: the guarantee leaves the repository.
- *Detect absence of a TTY* — rejected: false-positives on perfectly ordinary local invocations.

## R11: Repair audit record

**Decision**: An append-only log keyed by test node ID recording each attempt: the classifier's verdict, what changed, the assertion digest before and after, the outcome, and the attempt number. Written to the generated-output location; read by the report generator to satisfy FR-041.

**Rationale**: FR-040 requires recording what changed and why, and FR-041 requires the report to disclose repairs per test. Keying by node ID is what lets the generator join the log to result data without a second lookup table.

**Alternatives considered**:
- *Log to stdout only* — rejected: the report cannot read it, so FR-041 fails.
- *Store in the decision records of feature 004* — rejected: those are approvals, and conflating a repair with an approval would misrepresent both.

## R12: Credential redaction

**Decision**: Reuse feature 002's `redact()` helper for every string entering the report, the repair log, and any error message.

**Rationale**: FR-019 and SC-011 forbid credentials anywhere in a report or evidence, and the report is the artifact most likely to be shared outside the team. Feature 002 already built redaction for exactly this hazard; a second implementation would be a second thing to get wrong.

**Alternatives considered**:
- *Rely on `SecretStr` masking* — rejected: does not cover tracebacks or captured output, which is where a credential actually surfaces.

---

## Resolved unknowns

| Unknown | Resolved by |
|---|---|
| What shape is the result data? | Verified empirically — R1 |
| Does a ticket marker reach the report? | **No.** Needs an explicit hook — R2 |
| Is failure detail available without extra capture? | Yes — `statusDetails` — R3 |
| How is a run scoped to one ticket? | `--ticket` collection filter, not `-m` — R4 |
| How is "still a skeleton" detected? | Feature 003's skip sentinel — R5 |
| How is repair eligibility decided deterministically? | Exception-type allowlist, default escalate — R6 |
| How is "must not change assertions" enforced? | AST assertion digest, compared across the repair — R7 |
| How is an empty run prevented from passing? | Exit code 5 treated as failure — R8 |
| How do completion and repair stay out of pipelines? | Separate commands plus a CI guard — R10 |

**Carried forward unverified**: whether browser-failure artifacts appear as `attachments` in the result JSON (R3). Does not block design; confirm at implementation.
