# Quickstart Validation: Test Approval Gate

**Feature**: `004-test-approval-gate` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

How to prove the gate works. Commands: [contracts/commands.md](./contracts/commands.md). Record format: [contracts/record-format.md](./contracts/record-format.md).

**Everything here is offline.** This feature makes no network request at all, which is what lets a pipeline verify approvals with no credentials and no connectivity (FR-025, SC-011).

---

## Prerequisites

Feature 001's environment, plus a git identity — the gate refuses to record a decision without one:

```bash
uv run pytest -m healthcheck    # expect 14 passed
git config user.email           # must print something
```

Feature 003 must have generated at least one design for the gate to act on.

---

## Scenario 1 — The X1 property: completion must not void an approval (validates FR-017 as corrected)

**Do this first.** It is the defect the cross-feature analysis found, and the one that would deadlock the whole workflow.

```bash
uv run python -m ai_qa.approval approve tests/ui/test_checkout_expired_card.py
uv run python -m ai_qa.approval status --ticket TC-345     # expect APPROVED
```

Now write a test body — the act the approval authorises — and re-check:

```bash
# implement one test body by hand, then:
uv run python -m ai_qa.approval status --ticket TC-345     # must STILL be APPROVED
```

**Expected**: still `APPROVED`. Writing a body does not void the approval.

Then confirm the sensitivity is real in the other direction:

```bash
# edit a docstring, then:
uv run python -m ai_qa.approval status --ticket TC-345     # expect STALE
```

**Expected**: `STALE`. The docstring states the behaviour under review, so changing it voids the approval.

```bash
uv run pytest tests/approval/test_digest.py -v
```

If body edits void the approval here, the digest is covering the whole file and the workflow is deadlocked — approve, complete, refused.

---

## Scenario 2 — All four states are distinguishable (validates SC-003)

```bash
uv run python -m ai_qa.approval status --all
uv run pytest tests/approval/test_state.py -v
```

**Expected**, each reported as itself and never as another:

| State | How to produce it |
|---|---|
| `PENDING` | A freshly generated design, no decision yet |
| `APPROVED` | Approve it; leave the design portion alone |
| `STALE` | Approve, then rename a test or edit a docstring |
| `REJECTED` | Reject it with a reason |

`PENDING` and `STALE` must not be conflated: "never reviewed" and "reviewed, then changed" need different remedies.

---

## Scenario 3 — The approver policy (validates SC-018, FR-022)

Default policy requires a second person.

```bash
# As the design's author:
uv run python -m ai_qa.approval approve tests/ui/test_checkout_expired_card.py; echo "exit=$?"
```

**Expected**: exit **3**, refused as self-approval, naming the policy.

```bash
# A design with no generated-by-identity (hand-written or pre-dating the field):
uv run python -m ai_qa.approval approve tests/ui/test_handwritten.py; echo "exit=$?"
```

**Expected**: exit **4** — author unknown, so the policy cannot be checked. This fails closed deliberately: a policy that passes when it cannot be verified is decorative.

Then the explicit escape hatch:

```bash
# .env: APPROVAL_REQUIRE_SECOND_PERSON=false
uv run python -m ai_qa.approval approve tests/ui/test_checkout_expired_card.py
```

**Expected**: proceeds, and the record carries `"policy_require_second_person": false` — so an auditor can tell this was permitted rather than a violation.

```bash
git config --unset user.email
uv run python -m ai_qa.approval approve tests/ui/test_checkout_expired_card.py; echo "exit=$?"
```

**Expected**: exit **7**. No record is written. A record naming nobody answers none of the questions it exists to answer.

---

## Scenario 4 — The gate cannot be bypassed (validates FR-009, SC-002)

```bash
uv run pytest tests/approval/test_gate.py -v
```

**Expected**: 100% of automation attempts against a `PENDING`, `REJECTED` or `STALE` design are refused, with the state named — and **zero** proceed.

Then through the real entry point, once feature 005 exists:

```bash
uv run python -m ai_qa.automation complete TC-345; echo "exit=$?"
```

**Expected**: refused with the state named. Both routes — this feature's own and feature 005's — must funnel through the same enforcement point. A guard duplicated per call site is one someone eventually forgets.

---

## Scenario 5 — Records are append-only and tamper-evident (validates SC-005, SC-008)

```bash
uv run python -m ai_qa.approval reject tests/ui/test_x.py --reason "first pass"
uv run python -m ai_qa.approval approve tests/ui/test_x.py
ls approvals/TC-345/
```

**Expected**: **two** files. The rejection is still there — a later decision never erases an earlier one, because each is its own file.

```bash
rm approvals/TC-345/*-rejected.json
uv run python -m ai_qa.approval status --ticket TC-345
```

**Expected**: the deletion is **reported**, detected against git history. A removed file leaves nothing on disk, so history is the only way to see it.

```bash
# Hand-edit a record's digest, then:
uv run python -m ai_qa.approval status; echo "exit=$?"
```

**Expected**: exit **8**, reported as orphaned or modified — and **never** interpreted as a valid approval or a clean absence.

**Known limit, by design**: the gate is cooperative. Anyone with write access can commit a convincing record. These checks catch mistakes and drift, not an adversary.

---

## Scenario 6 — `approvals/` is actually committed (validates the quiet failure)

```bash
git check-ignore -v approvals/ ; echo "ignored=$?"
git ls-files approvals/ | head
```

**Expected**: `approvals/` is **not** ignored (non-zero from `check-ignore`), and records appear in `git ls-files`.

Worth its own scenario because the failure is silent: if feature 001's broad ignore rules swallow this directory, `verify` reports everything as unapproved, which reads as "nothing reviewed yet" rather than "records are being discarded".

---

## Scenario 7 — The pipeline gate (validates SC-012, SC-019, SC-020, FR-026)

```bash
uv run python -m ai_qa.approval verify; echo "exit=$?"
```

**Expected** with an unapproved generated test present: exit **6**, listing **every** offending script with its state and remedy — not a count (FR-038).

**Expected** with everything approved: exit 0.

Then the property that keeps the gate survivable:

```bash
uv run python -m ai_qa.approval verify > local.txt
# run the same command in the pipeline
diff local.txt pipeline.txt
```

**Expected**: identical (SC-020, FR-039). A pipeline failure must be reproducible before pushing, or the first time anyone meets it is during a release — which is how a gate gets disabled.

Finally, confirm no network is needed:

```bash
# with networking disabled:
uv run python -m ai_qa.approval verify
```

**Expected**: works normally (SC-011).

---

## Scenario 8 — Approval is not the same as automation existing (validates SC-016, FR-030, FR-031)

```bash
uv run python -m ai_qa.approval status --ticket TC-345
```

**Expected**, by counting feature 003's sentinel:

| Condition | Meaning |
|---|---|
| `unimplemented` | Approved, every test still a skeleton |
| `partial` | Approved, some tests implemented |
| (neither) | Approved and fully implemented |

A design whose automation is partially written must report as `partial` in 100% of cases and **zero** as complete. Conflating approval with implementation would let an approved-but-unwritten design read as finished work.

---

## Coverage summary

| User Story | Priority | Scenario |
|---|---|---|
| 1 — Review before anyone automates | P1 | 2, 3 |
| 2 — Automation cannot precede approval | P1 | 1, 4 |
| 3 — Decisions recorded and auditable | P2 | 3, 5, 6 |
| 4 — Approval stops applying when content changes | P2 | 1, 2 |
| 5 — Pipeline runs existing, approved scripts only | P1 | 7 |

Scenarios 1–3 and 5–8 need only feature 003. Scenario 4's second half needs feature 005.
