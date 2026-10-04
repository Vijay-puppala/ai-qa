# Phase 1 Data Model: Test Approval Gate

**Feature**: `004-test-approval-gate` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Four structures: the decision record, the design digest, the computed state, and the policy inputs. Records are committed JSON files; nothing else is persisted.

---

## 1. Decision record

One file per decision at `approvals/<TICKET>/<utc-timestamp>-<decision>.json`. External format: [contracts/record-format.md](./contracts/record-format.md).

### `DecisionRecord`

| Field | Type | Required | Notes |
|---|---|---|---|
| `decision` | `Literal["approved", "rejected"]` | Yes | FR-002 |
| `ticket` | `str` | Yes | Source ticket key |
| `design_path` | `str` | Yes | Path at decision time — **for humans only**, never used for matching (R9) |
| `design_digest` | `str` | Yes | The design-portion digest — see §2. This is the matching key |
| `approver` | `str` | Yes | Git `user.email`. Never empty, never a placeholder (FR-016, FR-037) |
| `author` | `str \| None` | Yes | From feature 003's `generated-by-identity`. `None` means unknown |
| `policy_require_second_person` | `bool` | Yes | The policy **in force at decision time** (FR-036) |
| `timestamp` | `str` | Yes | UTC, ISO 8601 |
| `reason` | `str \| None` | Conditional | **Required when `decision == "rejected"`** (FR-003) |
| `test_names` | `tuple[str, ...]` | Yes | The test names covered, so "what exactly was approved?" is answerable without re-deriving the digest (FR-014) |

### Why `policy_require_second_person` is stored

Because the policy is configurable, a record without it becomes uninterpretable the moment someone changes the setting. An auditor reading a self-approval cannot tell whether it was permitted at the time or a violation — and the current setting says nothing about the past. One boolean removes that ambiguity permanently.

### Append-only by construction

FR-013 requires that a later decision never erases an earlier one. One file per decision makes that **structural**: a new decision is a new filename, so there is no code path that rewrites a record. This is a stronger guarantee than code that merely does not overwrite, because it cannot regress.

### Field constraints, verbatim

- `approver` must be non-empty. Where git `user.email` is unset, recording is **refused** rather than written with a placeholder (FR-037).
- `reason` must be non-empty when `decision == "rejected"` (FR-003).
- `design_digest` must be the design-portion digest of §2, never a whole-file hash.
- No field may contain a credential; every string is written through feature 002's `redact()` (FR-034).

---

## 2. Design digest

`src/ai_qa/approval/digest.py`. A pure function over a test file.

**Definition**: parse the file's AST and collect, in source order, for each test function:

1. the function name
2. its markers (name and arguments)
3. its docstring

Normalise — strip comments, collapse whitespace — then hash.

**Test bodies are excluded.**

### Why bodies are excluded

This is the X1 correction in concrete form, and the reason matters enough to restate. A digest over the whole file would void every approval the instant its automation was written — and writing that automation is the **act the approval authorises**. The gate would refuse the work it had just permitted, deadlocking the entire workflow across features 003, 004 and 005.

Excluding bodies gives exactly the sensitivity a reviewer would expect:

| Change | Approval |
|---|---|
| Write or edit a test body | **Preserved** — this is the authorised act (FR-030) |
| Reformat, add a comment | Preserved — normalisation removes both |
| Edit a docstring | **Voided** — the docstring states the behaviour under review |
| Rename a test | **Voided** — the name is part of the design |
| Add or remove a test | **Voided** — the reviewed set changed |
| Add or change a marker | **Voided** — markers determine where and how a test runs |
| Move or rename the file | Preserved — matching is by digest, not path (R9, FR-021) |

### Naming

This is the **design digest**. Feature 005 has a separate **assertion digest** covering assertion statements, for a different purpose (preventing a repair from changing what a test asserts). The names are kept distinct deliberately; the cross-feature analysis flagged the collision before either was built.

---

## 3. Computed state

`src/ai_qa/approval/state.py`. **Derived on every call, never stored.**

```text
ApprovalState = PENDING | APPROVED | STALE | REJECTED
```

| State | Condition |
|---|---|
| `PENDING` | No decision records for this design |
| `REJECTED` | Latest record is `rejected` |
| `APPROVED` | Latest record is `approved` **and** its `design_digest` equals a fresh digest of the current file |
| `STALE` | Latest record is `approved` **and** the digests differ |

### Why nothing is stored

SC-003 requires all four states distinguishable in 100% of cases, with zero reported as another. A stored state field is a cache with no invalidation signal: the moment someone edits a docstring, the stored value is wrong, and **a wrong state looks exactly like a correct one**. Deriving it means there is nothing to keep in sync.

`STALE` is the state that makes the gate honest, and the one a cache would most often get wrong — it is precisely the "approved, then changed" case.

### Additional reported conditions

Not states, but reported by `status` and `verify`:

| Condition | Meaning |
|---|---|
| `unmanaged` | The file carries no `generated-by: ai-qa` marker, so the gate does not apply (R8, FR-029) |
| `orphaned` | A record whose digest matches no design in the repository (FR-015) |
| `partial` | An approved design where some tests still carry feature 003's sentinel (FR-031) |
| `unimplemented` | An approved design where **every** test still carries the sentinel — approved but not automated (FR-030) |

`unmanaged` is reported rather than omitted: if that count grows unexpectedly, somebody is bypassing generation, and that is worth seeing.

---

## 4. Policy inputs

`src/ai_qa/approval/policy.py`. Two settings on the existing `Settings` model (FR-022, R11):

| Setting | Type | Default | Notes |
|---|---|---|---|
| `approval_require_second_person` | `bool` | **`True`** | Default must require a second person |
| `approval_records_dir` | `Path` | `approvals/` | Committed; must not be git-ignored |

### Decision rule

```text
refuse if require_second_person and author is None          -> AUTHOR_UNKNOWN
refuse if require_second_person and author == approver       -> SELF_APPROVAL
otherwise record
```

### Why `AUTHOR_UNKNOWN` refuses

Under the default policy, an unknown author means the policy **cannot be checked**, and a policy that silently passes when it cannot be checked is decorative. This is the same fail-closed reasoning feature 005 applies to its repair classifier.

The consequence is deliberate: a design generated before the provenance field exists will refuse approval under the default policy. The escape hatches are explicit — set `approval_require_second_person = false`, or regenerate the design so it carries an author. Both are visible choices, and the chosen one is recorded on the decision.

---

## Entity mapping to spec

| Spec Key Entity | Where it lives |
|---|---|
| Test Design | A generated test file; its reviewable portion is defined by the digest — §2 |
| Decision | `DecisionRecord` — §1 |
| Decision History | The directory `approvals/<TICKET>/`, ordered by filename — §1 |
| Approval Validity | The four-state function — §3 |
| Automation Script | A completed test carrying the approval identifier stamped by feature 005 |
