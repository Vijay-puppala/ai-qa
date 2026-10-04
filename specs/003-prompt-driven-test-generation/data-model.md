# Phase 1 Data Model: Prompt-Driven Test Generation

**Feature**: `003-prompt-driven-test-generation` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Four structures: the extraction result, the brief, the provenance header, and the sentinel. No persistence — generated skeletons are ordinary committed test files.

---

## 1. Extraction result

Produced by `src/ai_qa/generate/keys.py`. A pure function of its input string, which is what makes SC-004 and SC-005 testable.

### `ExtractionResult`

| Field | Type | Notes |
|---|---|---|
| `keys` | `tuple[str, ...]` | Accepted keys, normalised to upper case |
| `rejected` | `tuple[Rejection, ...]` | Candidates that matched the pattern but failed a filter, each with its reason |
| `outcome` | enum | `ONE` \| `NONE` \| `MANY` |

`outcome` is explicit rather than derived from `len(keys)` because each value maps to different required behaviour: `ONE` proceeds, `NONE` reports the expected form and stops (FR-006), `MANY` reports every key found and stops (FR-007).

### `Rejection`

| Field | Notes |
|---|---|
| `candidate` | The text that matched the pattern |
| `reason` | `DENYLISTED_PREFIX` \| `YEAR_LIKE` \| `NUMBER_TOO_LONG` |

Rejections are **returned, not discarded**. `extract` prints them so an engineer whose real key was filtered can see why, which is the difference between a diagnosable tool and a silent one.

### Acceptance rules, verbatim

Candidate pattern: `\b[A-Za-z][A-Za-z0-9_]{1,9}-\d{1,6}\b`, matched case-insensitively, normalised to upper case.

Rejected before any network call:

1. **Denylisted prefix** — `ISO`, `UTF`, `RFC`, `ANSI`, `IEEE`, `SHA`, `AES`, `COVID`, `EN`, `BS`, `SI`, `ASCII`, `HTTP`, `IPV`, `MD`, `CVE`
2. **Year-like** — numeric part is four digits in the range 1900–2199
3. **Number too long** — numeric part exceeds six digits

URL forms are checked first: the path segment following `/browse/`, then a `selectedIssue` query parameter, then the general pattern. A URL contains other digit-hyphen fragments, so the general pattern alone can select the wrong one.

**Malformed versus nonexistent** (FR-008): a string the pattern or filters reject is *malformed* and never reaches Jira. A key that passes and fails to resolve is *not found or not visible*, reusing feature 002's wording.

---

## 2. Brief

The deterministic hand-off from the platform to the authoring assistant (R3). Written to the scratch area and printed to stdout; **not committed**.

| Field | Source |
|---|---|
| `key` | Extraction |
| `summary` | Ticket |
| `description` | Ticket, ADF-flattened via feature 002 |
| `acceptance_criteria` | Ticket text, read broadly — teams put these in the description, a custom field, or comments, so no single field is assumed |
| `labels`, `issue_type`, `status` | Ticket |
| `content_digest` | Digest of the ticket's text content, carried into provenance |
| `conventions` | A pointer to `CLAUDE.md`, not a copy of it |
| `warnings` | e.g. "description is empty; non-text content present" |

Two warning cases are required rather than optional:

- **Little usable requirement text** (FR-014): stated plainly, so the assistant does not invent requirements to fill the gap.
- **Non-text requirement content** (FR-015): where the description is empty but attachments or images exist, the brief says the text was empty *and* that non-text content was present — reporting an empty requirement would be wrong.

`conventions` is a pointer because duplicating `CLAUDE.md` into every brief guarantees the two diverge.

---

## 3. Provenance header

A block in the generated module's docstring, written by the platform (R4, R8). This is the structure features 004 and 005 read; the external contract is [contracts/skeleton-format.md](./contracts/skeleton-format.md).

| Field | Purpose | Required by |
|---|---|---|
| `generated-by: ai-qa` | Distinguishes a generated artifact from a hand-written one | FR-018 |
| `ticket` | Source key | FR-017 |
| `ticket-summary` | Summary as at generation | FR-017 |
| `ticket-updated` | The ticket's `updated` timestamp at generation | FR-020 |
| `ticket-digest` | Digest of the ticket's text content at generation | FR-020 |
| `generated-at` | Generation timestamp | FR-017 |
| `generated-by-identity` | **Who ran generation** | FR-017 — added 2026-10-04 for feature 004's FR-022 |

**On `generated-by-identity`**: this feature has no use for it. Feature 004's FR-022 requires enforcing that an author may not approve their own design, and the author is only knowable at generation time. Recording it here costs one line; reconstructing it afterwards is impossible. It is logged as a spec delta in [plan.md](./plan.md) rather than quietly added, because adding a field to one feature's requirement to serve another's is a cross-feature decision.

**Staleness** (FR-020): compare `ticket-digest` against a fresh digest of the ticket's current text. Unequal means the ticket has moved on since generation — answerable without rerunning generation, which is exactly what FR-020 asks. `ticket-updated` is kept as a human-readable corroboration, not as the comparison, because Jira bumps `updated` for changes that do not touch the text.

---

## 4. Skeleton sentinel

```python
SKELETON_SENTINEL = "ai-qa:unimplemented"
```

One constant in `src/ai_qa/generate/sentinel.py`. Every skeleton body is `pytest.skip(f"{SKELETON_SENTINEL}: <behaviour>")`.

**Why a module holding one constant.** Three features depend on this string: this one writes it, feature 004 counts it to report partial implementation (its FR-031), feature 005 detects completion by its absence (its FR-007). A literal repeated in three places drifts by one character and silently breaks detection in two of them — with no error, because "no skeletons found" and "nothing to detect" look identical.

**Why `skip` in the body rather than a `skip` marker or `xfail`**: FR-027 requires a skeleton to be *incapable of reporting as passed*. `xfail` can report `xpass`. A decorator is also harder to remove cleanly than a body statement when the test is implemented, and the body is where the unimplemented state matters.

### Unimplemented listing

`src/ai_qa/generate/listing.py` performs a static AST scan over `tests/`, finding calls to `pytest.skip` whose argument contains the sentinel, and reads the ticket from the module's `ticket` marker.

Static rather than run-based because skips are evaluated at run time: `--collect-only` would find nothing, and a run-derived listing would be only as current as the last run and would need the application reachable. The scan answers from the repository alone, which is what makes it usable by a pipeline and by feature 004.

---

## Entity mapping to spec

| Spec Key Entity | Where it lives |
|---|---|
| Generation Request | `ExtractionResult` plus the explicit command — §1, R2 |
| Ticket Key | Accepted, normalised keys in `ExtractionResult.keys` — §1 |
| Resolved Ticket | Feature 002's `JiraIssue`, projected into the brief — §2 |
| Generated Artifact | A test file carrying the provenance header and the sentinel — §3, §4 |
