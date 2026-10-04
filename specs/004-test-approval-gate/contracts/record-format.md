# Record Format Contract: Test Approval Gate

**Feature**: `004-test-approval-gate` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

The committed decision record. A contract because three readers depend on it: this feature's `status` and `verify`, feature 005's completion gate, and a human auditor months later.

Field types and constraints: [data-model.md](../data-model.md) §1.

---

## Location

```text
approvals/<TICKET>/<utc-timestamp>-<decision>.json
```

Example: `approvals/TC-345/20261004T100511Z-approved.json`

**One file per decision.** This is what makes the append-only requirement structural rather than enforced — a later decision is a new filename, so no code path rewrites a record and the guarantee cannot regress.

Per-ticket directories keep a ticket's full history one listing away. There is deliberately **no index file**: an index is a second source of truth that drifts from the directory it describes.

### `approvals/` must be committed

Feature 001's `.gitignore` excludes generated output broadly. This directory must be explicitly **not** ignored, and a test asserts it is tracked.

A records directory that gets ignored makes every approval invisible to the pipeline and to review — and the failure is quiet: `verify` reports everything as unapproved, which reads as "nobody has reviewed anything yet" rather than "the records are being discarded".

---

## Format

```json
{
  "decision": "approved",
  "ticket": "TC-345",
  "design_path": "tests/ui/test_checkout_expired_card.py",
  "design_digest": "9c1f44ab7e2d08b5",
  "approver": "reviewer@example.com",
  "author": "someone@example.com",
  "policy_require_second_person": true,
  "timestamp": "2026-10-04T10:05:11Z",
  "test_names": [
    "test_expired_card_is_rejected_at_checkout",
    "test_expired_card_error_names_the_reason"
  ]
}
```

A rejection sets `decision` to `rejected` and adds a `reason`:

```json
{
  "decision": "rejected",
  "reason": "Missing the case where the card expires mid-session",
  "ticket": "TC-345",
  "design_path": "tests/ui/test_checkout_expired_card.py",
  "design_digest": "9c1f44ab7e2d08b5",
  "approver": "reviewer@example.com",
  "author": "someone@example.com",
  "policy_require_second_person": true,
  "timestamp": "2026-10-04T09:40:02Z",
  "test_names": ["test_expired_card_is_rejected_at_checkout"]
}
```

---

## The three fields most easily got wrong

**`design_digest` covers the design portion only** — test names, markers and docstrings, by AST, bodies excluded. A whole-file hash here would void every approval the moment its automation was written, which is the very act the approval authorises. This was analysis finding X1, and it is the single most important line in this contract.

**`policy_require_second_person` records the policy in force at decision time.** Because the policy is configurable, a record without it becomes uninterpretable as soon as the setting changes: an auditor reading a self-approval cannot tell whether it was permitted then or a violation. The current setting says nothing about the past.

**`author` may be `null`, and that is meaningful.** It means the design carried no `generated-by-identity` — hand-written, or generated before the field existed. Under the default policy an unknown author **refuses** the approval, because the policy cannot be checked, and a policy that passes when it cannot be verified is decorative.

---

## Matching and validity

- Records match designs by **`design_digest`**, never by `design_path`. A moved or renamed design still matches; different content at the old path does not (FR-021, R9).
- `design_path` is stored for human readability only. Treating it as the key would mean a rename voids the approval, which FR-021 forbids.
- Validity is **computed** from the latest record plus a fresh digest of the current file, never stored. See [data-model.md](../data-model.md) §3.

---

## Tamper and integrity checks

Three conditions, **reported rather than enforced** (FR-015):

| Condition | Detected by |
|---|---|
| Orphaned — digest matches no design in the repository | Digest comparison across `tests/` |
| Malformed — unparseable or missing a required field | Schema validation on read |
| Modified or deleted — differs from git history | Comparison against git |

Git history is what makes **deletion** detectable at all: a removed file leaves nothing on disk, but it leaves a trace in history.

### The limitation, stated plainly

The gate is **cooperative**. Anyone with repository write access can author a convincing record. These checks catch mistakes, accidents and drift — not an adversary. Closing that would need signing and an external authority, which is a far larger feature than the gate and is explicitly out of scope in the spec's assumptions.

That is not a defect to be tightened away later; it is the chosen scope, and anyone relying on this gate for an audit should know it.

---

## No credentials

Every string is written through feature 002's `redact()` (FR-034). A rejection reason is free text typed by a human, which is exactly where a token gets pasted by accident — and unlike a log line, this file is committed.
