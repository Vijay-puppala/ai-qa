# Phase 1 Data Model: Approved Automation Run & Reporting

**Feature**: `005-approved-automation-run` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Four structures: the projection the report is built from, the repair log, the assertion digest, and the classifier's verdict. No persistence — everything lives in generated files under `reports/`.

---

## 1. Result projection

Built by `src/ai_qa/report/read.py` from `reports/allure-results/*-result.json`. The source schema was read off the installed `allure-pytest` 2.16.2 rather than assumed (see [research.md](./research.md)).

### `TestResult`

| Field | Source | Notes |
|---|---|---|
| `uuid` | `uuid` | Identity within the run |
| `name` | `name` | Display name |
| `full_name` | `fullName` | Module path plus test name; the join key to the repair log |
| `status` | `status` | `passed` \| `failed` \| `broken` \| `skipped` |
| `start` / `stop` | `start`, `stop` | Epoch milliseconds |
| `duration_ms` | derived | `stop - start` |
| `ticket` | `labels[name="ticket"]` | **Present only because of the conftest hook** — see §1.1 |
| `tags` | `labels[name="tag"]` | Bare pytest markers arrive here |
| `suite` | `labels[name="suite"]` | |
| `failure_message` | `statusDetails.message` | Verified present on failures |
| `failure_trace` | `statusDetails.trace` | Verified present on failures |
| `evidence_paths` | derived | Relative paths under `reports/artifacts/<sanitised-node-id>/` |
| `repairs` | repair log join | Empty tuple when none — drives FR-041 disclosure |
| `approval_id` | `labels[name="approval"]` | Written at completion (FR-005, FR-022) |

Frozen models. Absent optional fields degrade to `None` or an empty tuple; a missing `description` or label is normal and must not raise.

### 1.1 The `ticket` label does not exist by default

The single most important fact in this model. Verified empirically: `@pytest.mark.ticket("TC-345")` produces **no** label — `allure-pytest` maps bare markers to `tag` labels but drops markers carrying arguments.

So a conftest hook must read the marker and write the label:

```text
marker @pytest.mark.ticket("TC-345")  ->  label {name: "ticket", value: "TC-345"}
```

Without it, `TestResult.ticket` is `None` for every test, FR-021/FR-023 and SC-008 fail, and **nothing looks broken** — the report renders correctly with every test unattributed. This is the design's quietest failure mode, which is why `tests/report/` includes a test asserting the label is present on a marked test rather than only testing the projection.

Labels are written at **run time**, so a test that is marked but never executed produces no label. "Which tests claim ticket X" is therefore a question about a run, not about the repository; the static answer comes from the marker via the `--ticket` collection filter.

### `RunSummary`

| Field | Notes |
|---|---|
| `scope` | What this run covered — a ticket key, `full-suite`, or an explicit selection. **Required** (FR-035) |
| `counts` | Per status |
| `tickets` | Grouping of results by ticket, with unattributed results in their own group |
| `started` / `finished` | Run bounds |
| `collected` | Number of tests collected. **Zero is a failure, not a pass** (FR-011, SC-009) |
| `repaired_count` | How many tests were repaired during the run (FR-041) |

`scope` is mandatory rather than optional because SC-021 requires every report to state it: a ticket-scoped green must never be readable as suite-wide confidence, and the only way to guarantee that is to make the field impossible to omit.

---

## 2. Repair log

Append-only JSON Lines at `reports/repair-log.jsonl`, written by `src/ai_qa/automation/repairlog.py`, joined to results on `full_name`.

### `RepairAttempt`

| Field | Notes |
|---|---|
| `test_full_name` | Join key |
| `attempt` | 1-based; bounded by the limit in FR-040 |
| `timestamp` | When attempted |
| `verdict` | Classifier verdict — see §4 |
| `failure_type` | The exception type that drove the verdict |
| `changed` | Human-readable description of what was changed |
| `digest_before` / `digest_after` | Assertion digests — see §3 |
| `outcome` | `repaired` \| `refused_assertion_changed` \| `escalated` \| `budget_exhausted` \| `still_failing` |
| `notes` | Optional detail, redacted |

**Append-only in effect.** A later attempt never rewrites an earlier record, so the log answers "what did this tool do to my tests" completely. That is the point of FR-040: a repair mechanism without a record is indistinguishable from a tool quietly editing tests.

Every string is passed through feature 002's `redact()` before writing (FR-019).

`outcome = refused_assertion_changed` is recorded as a **first-class outcome, not an error**. It means the digest check fired and did its job; it is evidence the guarantee is working, and SC-023 is verified by its absence from the "repaired" set rather than by its absence from the log.

---

## 3. Assertion digest

`src/ai_qa/automation/digest.py`. A pure function, the mechanism behind FR-039.

**Definition**: parse the test file, locate the test function, and collect in source order:

- every `assert` statement's normalised source
- every call to a recognised assertion helper (`expect(...)` from Playwright, `pytest.raises(...)` context entries)

Normalisation strips comments and collapses whitespace, then the collected items are hashed into one digest.

**What may change freely**: formatting, comments, variable names not inside an assertion, imports, fixtures requested, setup code, helper calls that are not assertions.

**What may not change**: the text of any assertion. A repair whose `digest_after` differs from `digest_before` is refused (FR-039), recorded as `refused_assertion_changed`, and escalated.

### Known limitation, stated rather than buried

The digest compares assertion **text**. A repair could change what an assertion effectively checks by altering a value it depends on, without touching the assert line:

```text
expected = 5        ->   expected = 0
assert total == expected      # digest unchanged
```

This narrows the hole substantially — the obvious route to a green assertion, editing the assertion, is closed — but does not close it. Three things carry the remaining risk: repairs are bounded (FR-040), every attempt is logged with what changed (FR-040), and every repaired pass is disclosed in the report (FR-041). A reviewer seeing "this test was repaired and now passes" has what they need; a tool that silently fixed it would not.

Closing the hole entirely would require comparing the test's semantics, not its text, which is not a tractable addition here.

---

## 4. Classifier verdicts

`src/ai_qa/automation/classify.py`. A pure function from failure to verdict, keyed **only** on exception type — never on message text, which is version-dependent and partly application-controlled.

```text
Verdict = ELIGIBLE | ESCALATE
```

### `ELIGIBLE` — closed list (FR-036)

| Failure | Why mechanical |
|---|---|
| Collection / import error | The test cannot load; no behaviour was exercised |
| `SyntaxError` | Not runnable code |
| Fixture lookup error | A fixture name is wrong or missing |
| Unregistered marker error | A marker is not declared in configuration |
| `TypeError` / `AttributeError` from test-framework API misuse | Wrong call shape against pytest or the Playwright API |

None of these can encode a statement about the application, which is what makes them safe to repair: there is no product finding to erase.

### `ESCALATE` — named explicitly (FR-037)

| Failure | Why excluded |
|---|---|
| `AssertionError` | The test's verdict on the application. Repairing it is hiding a defect |
| Playwright timeout | Indistinguishable from a feature that is slow or missing |
| Element not found | Indistinguishable from a feature that was never built |
| HTTP status mismatch | A statement about the API's behaviour |
| **Anything not positively recognised** | FR-038 — ambiguity resolves towards escalation |

The default is `ESCALATE` and it is unconditional. A failure mode introduced by a future dependency upgrade lands on the safe side without anyone remembering to classify it.

**Element-not-found and timeout are excluded deliberately despite being the commonest test-side faults in browser automation.** That is the cost of Q3's answer, accepted knowingly: repairing one would sometimes erase a genuine "this feature does not exist" finding, and no classifier can tell the two apart from the exception alone.

---

## Entity mapping to spec

| Spec Key Entity | Where it lives |
|---|---|
| Approved Design | Feature 004's records plus feature 003's skeletons — not modelled here |
| Completed Automation | A test file carrying `ticket` and `approval` markers — §1 |
| Run | `RunSummary` — §1 |
| Result Data | `reports/allure-results/*.json`, already produced by feature 001 |
| Report | `reports/report.html`, rendered from `RunSummary` + `TestResult` |
| Failure Evidence | `failure_message`, `failure_trace`, `evidence_paths` — §1 |
