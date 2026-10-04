# Command Contract: Prompt-Driven Test Generation

**Feature**: `003-prompt-driven-test-generation` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Three subcommands under `uv run python -m ai_qa.generate`. Standard-library `argparse`; a CLI framework would be a new dependency.

Skeleton shape: [skeleton-format.md](./skeleton-format.md).

---

## `extract` — show which key was found, generate nothing

```bash
uv run python -m ai_qa.generate extract "generate tests for TC-345"
uv run python -m ai_qa.generate extract "https://site.atlassian.net/browse/TC-345"
```

| | |
|---|---|
| **Does** | Runs extraction and prints accepted keys plus every rejected candidate with its reason |
| **Network** | **None.** Pure local function — this is what makes FR-025 and SC-012 verifiable offline |
| **Satisfies** | FR-026 |

Rejections are printed, not swallowed. An engineer whose real key was filtered needs to see which rule fired; a tool that silently finds nothing is undiagnosable.

## `generate` — produce a skeleton for one ticket

```bash
uv run python -m ai_qa.generate generate "generate tests for TC-345"
uv run python -m ai_qa.generate generate "TC-345" --force
```

| | |
|---|---|
| **Does** | Extracts the key, fetches the ticket via feature 002, writes the brief, scaffolds the file, hands off for authoring |
| **Refuses** | No key found (FR-006); several keys found (FR-007); target file exists without `--force` (FR-019) |
| **Never** | Infers intent. Generation happens because this command was run, never because a key appeared in some text (R2) |
| **Satisfies** | FR-001 to FR-019 |

**`--force` is the only route to overwriting.** Refusal names the existing file and the flag, so overwriting is always a deliberate act.

## `skeletons` — list unimplemented work

```bash
uv run python -m ai_qa.generate skeletons
```

| | |
|---|---|
| **Does** | Static AST scan of `tests/` for the sentinel; prints each unimplemented test with its source ticket |
| **Network** | None. Repository-only, so a pipeline can run it |
| **Satisfies** | FR-028 |

Static rather than run-derived: skips are evaluated at run time, so `--collect-only` finds nothing, and a run-based listing would be stale and would need the application reachable. Feature 005's `skeletons` command delegates here rather than reimplementing the scan.

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 2 | Configuration error — Jira settings missing or incomplete |
| 3 | No ticket key found in the input |
| 4 | Several ticket keys found — every key is named, nothing is generated |
| 5 | Ticket not found or not visible to this account |
| 6 | Target file already exists; `--force` required |
| 7 | Jira unavailable, rejected the credentials, or rate-limited |

Codes 3 and 5 are deliberately distinct: 3 means the input had no recognisable key (malformed or absent), 5 means a well-formed key did not resolve. FR-008 requires exactly that distinction, and conflating them sends an engineer to fix the wrong thing.

Code 4 exists because acting on one of several keys looks like success and leaves the others silently uncovered.

---

## Compatibility notes

Breaking changes:

- Making `generate` act on the first of several keys instead of refusing — reintroduces the silent-omission failure FR-007 prevents.
- Making `extract` perform a lookup — breaks FR-025 and SC-012 offline verification.
- Making `generate` overwrite without `--force`.
- Adding intent inference so a key in arbitrary text triggers generation.
- Deriving `skeletons` from a test run instead of a static scan.
