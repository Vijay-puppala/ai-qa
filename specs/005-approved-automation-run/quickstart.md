# Quickstart Validation: Approved Automation Run & Reporting

**Feature**: `005-approved-automation-run` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

How to prove this feature works. Not `README.md` — that is an implementation deliverable for people *using* the platform.

Commands and exit codes: [contracts/commands.md](./contracts/commands.md). Report content: [contracts/report-format.md](./contracts/report-format.md).

**Scenarios 1–5 need no Jira, no approval records, and no network.** The classifier, the assertion digest, the report generator and the ticket-attribution hook are all verifiable against fixtures — which is deliberate, because this feature sits on three unbuilt features and everything that *can* be validated independently should be.

---

## Prerequisite

Feature 001's environment. Nothing new to install — this feature adds no dependency and no prerequisite (SC-017).

```bash
uv run pytest -m healthcheck    # expect 14 passed, unchanged
```

---

## Scenario 1 — The ticket label actually appears (validates SC-008, FR-021)

Do this **first**. It is the design's quietest failure mode: without the conftest hook, everything renders correctly with every test unattributed.

```bash
uv run pytest tests/report/test_read.py -k ticket_label -v
```

Then prove it end to end on a real marked test:

```bash
uv run pytest -k "<a test marked with @pytest.mark.ticket>" -q
uv run python -m ai_qa.automation report
# open reports/report.html - the test must appear under its ticket group,
# NOT under "Unattributed"
```

**Expected**: the test is grouped under its ticket.

**Why this is scenario 1**: a bare marker becomes a `tag` label automatically, so it is natural to assume a marker with an argument does too. It does not — verified during research. If this scenario fails, the report is still valid-looking and completely untraceable.

---

## Scenario 2 — Repair never touches an assertion (validates SC-022, SC-023)

The most important scenario in this feature. All offline.

```bash
uv run pytest tests/report/test_classify.py -v
uv run pytest tests/report/test_digest.py -v
```

**Expected** from the classifier tests, each asserting a negative:

| Failure | Verdict |
|---|---|
| Import / collection error | `ELIGIBLE` |
| `SyntaxError` | `ELIGIBLE` |
| Fixture lookup error | `ELIGIBLE` |
| Unregistered marker | `ELIGIBLE` |
| Framework API misuse | `ELIGIBLE` |
| `AssertionError` | `ESCALATE` |
| Element not found | `ESCALATE` |
| Timeout | `ESCALATE` |
| HTTP status mismatch | `ESCALATE` |
| **An exception type the classifier has never seen** | `ESCALATE` |

That last row is the one to check deliberately — FR-038 requires ambiguity to fail closed, so an unrecognised failure must escalate without anyone having classified it.

**Expected** from the digest tests: reformatting, renaming a non-asserted variable, adding a comment, or changing setup code all leave the digest unchanged; altering, weakening or removing any assertion changes it, and the repair is refused with `refused_assertion_changed`.

---

## Scenario 3 — An empty run is a failure (validates SC-009, FR-011)

```bash
uv run python -m ai_qa.automation run --ticket NOSUCH-99999; echo "exit=$?"
```

**Expected**: exit **5**, reported as a failure.

A mistyped ticket key must not produce a confident green run. Most callers treat any non-1 exit as success, which is precisely why this needs its own check.

---

## Scenario 4 — Report is self-contained and honest (validates SC-018, SC-021, FR-032)

```bash
uv run pytest -q
uv run python -m ai_qa.automation report
```

Then confirm, by opening `reports/report.html` and by inspection:

| Check | Expected |
|---|---|
| External requests | **Zero.** No CDN, font, or analytics reference in the file |
| Renders offline | Yes, with networking disabled |
| Scope header | Present, first on the page, naming ticket or full suite |
| Provenance line | States it is a project-generated summary, not an Allure report |
| `collected` | Shown; zero would render as a failure |
| Evidence note | States that `reports/artifacts/` must accompany the report |

```bash
grep -ciE 'https?://(cdn|fonts|unpkg|jsdelivr)' reports/report.html   # expect 0
```

---

## Scenario 5 — No credential in the report (validates SC-011, FR-019)

```bash
JIRA_API_TOKEN=SENTINEL-abc123 uv run pytest -q 2>&1 | grep -c "SENTINEL-abc123"
uv run python -m ai_qa.automation report
grep -rc "SENTINEL-abc123" reports/ 2>/dev/null
```

**Expected**: `0` from both. The report is the artifact most likely to leave the team, and a traceback is where a credential actually surfaces.

---

## Scenario 6 — The approval gate holds (validates SC-001, FR-002)

Needs feature 004. Attempt completion in each state:

```bash
uv run python -m ai_qa.automation complete TC-345   # design pending  -> exit 3
uv run python -m ai_qa.automation complete TC-345   # design rejected -> exit 3, reason shown
uv run python -m ai_qa.automation complete TC-345   # approval stale  -> exit 3, named as stale
uv run python -m ai_qa.automation complete TC-345   # approved        -> proceeds
```

**Expected**: the three refusals are distinguishable from each other (FR-003), and only the approved case proceeds. Then confirm the completed tests record the ticket and the authorising approval (FR-005, SC-004), and that no pre-existing body was overwritten (FR-004, SC-002).

---

## Scenario 7 — Nothing runs in a pipeline (validates SC-013, SC-025)

```bash
CI=true uv run python -m ai_qa.automation complete TC-345; echo "exit=$?"
CI=true uv run python -m ai_qa.automation repair TC-345;   echo "exit=$?"
```

**Expected**: exit **4** from both, naming the CI environment as the reason.

The two layers from research R10: a pipeline would not call these, *and* they refuse anyway. The second layer is the one that holds when someone adds a convenient step to a workflow file.

---

## Scenario 8 — Fast feedback, then explicit regression (validates SC-020, FR-010)

```bash
uv run python -m ai_qa.automation run --ticket TC-345
```

**Expected**: only `TC-345`'s tests execute; the full suite is **offered** as a next step and does not start. The report states the narrow scope (Scenario 4).

Then the deliberate follow-up:

```bash
uv run python -m ai_qa.automation run --full-suite
```

---

## Scenario 9 — A repaired pass is disclosed (validates SC-024, FR-041)

Introduce a mechanical fault into a passing test — misname a fixture — then:

```bash
uv run python -m ai_qa.automation repair TC-345
uv run python -m ai_qa.automation report
```

**Expected**: the fixture fault is repaired; `reports/repair-log.jsonl` records the attempt with the digests either side; and the report marks that test as **repaired**, visually distinct from an ordinary pass.

A test passing because a tool modified it is a different claim from a test passing as authored, and a reader skimming for green must not miss the difference.

---

## Coverage summary

| User Story | Priority | Scenario |
|---|---|---|
| 1 — Complete an approved design | P1 | 6, 7 |
| 2 — Run and get a report | P1 | 3, 4 |
| 3 — Trace back to ticket and approval | P2 | 1, 6 |
| 4 — Product bug vs broken test | P2 | 2, 9 |
| 5 — Run only what is relevant | P3 | 8 |

Scenarios 1–5 are independent of features 002, 003 and 004 and can be validated as soon as this feature is built. Scenarios 6–9 need the upstream chain, so they are the ones that will move if those features' interfaces change — see the Integration Points table in [plan.md](./plan.md).
