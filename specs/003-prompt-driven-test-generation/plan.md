# Implementation Plan: Prompt-Driven Test Generation

**Branch**: `003-prompt-driven-test-generation` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-prompt-driven-test-generation/spec.md`

## Summary

Read a ticket key out of ordinary language ("generate tests for TC-345"), fetch that ticket through the project's own Jira client, and produce a test skeleton — real test files with names, markers, docstrings and unimplemented bodies — with the authoring done by an AI assistant and everything around it deterministic.

Four decisions carry the design, each resolved in [research.md](./research.md):

1. **Key extraction filters before it fetches.** A bare `[A-Z]+-\d+` pattern matches `COVID-19`, `ISO-8601`, `UTF-8` and `CVE-2026-1234`. FR-005 forbids those producing a lookup and SC-005 measures it, so a denylist, a year rule and a length rule run locally before any network call (R1).
2. **Intent is never inferred.** Generation is an explicit command, so "why did TC-345 fail?" cannot trigger it. The free text is parsed for a key and nothing else — which resolves the intent edge case with no classification at all (R2).
3. **The platform scaffolds the file; the assistant writes the test functions.** Splitting at the file level keeps the deterministic output byte-predictable and therefore testable, and guarantees provenance exists even if authoring is interrupted (R4).
4. **One shared sentinel constant marks an unimplemented skeleton.** Features 004 and 005 both detect state from it, so three features depend on one string and it lives in one place (R5).

Net new dependencies: **zero**. Net new external prerequisites: **zero**.

## Technical Context

**Language/Version**: Python 3.12, unchanged.

**Primary Dependencies**: `httpx` and `pydantic` via feature 002's Jira client, `pytest` for the markers and sentinel. Standard library `re`, `ast`, `argparse`, `hashlib`. **Nothing added.**

**Storage**: None. Generated skeletons are committed test files; the brief is a scratch artifact.

**Testing**: pytest. Extraction and the AST scan are pure functions with unit tests and need no network (FR-025). A new marker is not required — this feature *writes* the `ticket` marker that feature 005 registers and consumes.

**Target Platform**: Windows and Linux. macOS unsupported.

**Project Type**: Library modules plus a CLI inside the existing single project.

**Performance Goals**: Extraction is local and immediate. One Jira fetch per generation.

**Constraints**: Zero new dependencies. No MCP or connector in the runtime path (FR-021, SC-011) — the deterministic half must complete with no assistant present (FR-029). Extraction verifiable offline (FR-025, SC-012). No committed file may *limit* behaviour to a particular ticket, though provenance keys are required (FR-009, as corrected 2026-10-04).

**Scale/Scope**: One package of five modules, one CLI with three subcommands, one shared constant that two other features depend on.

**Upstream dependency**: feature 002 (Jira retrieval), specified and planned but **not implemented**. Only the retrieval call site depends on it; extraction, scaffolding, the sentinel and the listing are all independent of it.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status: PASS — vacuously.** `.specify/memory/constitution.md` is still the unmodified template; every principle is a placeholder. No ratified principle exists to comply with or violate.

Pre-Phase 0: no violations. Post-Phase 1: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/003-prompt-driven-test-generation/
├── plan.md              # This file
├── research.md          # Phase 0 — 11 decisions
├── data-model.md        # Phase 1 — key, brief, provenance, sentinel
├── quickstart.md        # Phase 1 — validation walkthrough
├── contracts/
│   ├── commands.md      # extract / generate / skeletons
│   └── skeleton-format.md  # The contract features 004 and 005 depend on
├── checklists/
│   └── requirements.md  # 16/16
└── tasks.md             # Phase 2 output (NOT created here)
```

### Source Code (repository root)

```text
src/ai_qa/
├── generate/                   # NEW
│   ├── __init__.py
│   ├── keys.py                 # Extraction, filters, normalisation (R1, R9, R10)
│   ├── sentinel.py             # SKELETON_SENTINEL — the shared constant (R5)
│   ├── brief.py                # Deterministic hand-off artifact (R3)
│   ├── scaffold.py             # File scaffold + provenance header (R4, R8)
│   ├── listing.py              # Static AST scan for unimplemented skeletons (R6)
│   └── __main__.py             # argparse CLI: extract / generate / skeletons (R11)
└── jira/                       # EXISTING (feature 002) — one call site

tests/
└── generate/                   # NEW
    ├── test_keys.py            # Every input form + every non-key pattern (SC-004, SC-005)
    ├── test_scaffold.py        # Scaffold is byte-predictable; provenance present
    ├── test_listing.py         # AST scan finds skeletons, ignores implemented tests
    └── test_brief.py           # Brief content, offline

CLAUDE.md                       # CHANGED: + skeleton conventions (FR-030)
README.md                       # CHANGED: + generate workflow
```

**Structure Decision**: A `generate/` package rather than modules scattered under `src/ai_qa/`, because five of the six files are only meaningful together. `sentinel.py` is deliberately a module of its own holding one constant — it is imported by features 004 and 005, and giving it a trivial home makes the cross-feature dependency explicit rather than buried in whichever module happened to define it first.

`keys.py` and `listing.py` are pure and network-free. SC-004 and SC-005 are stated as percentages and zeros over input sets, which is only testable if extraction is a function of its input.

## Integration Points

| This feature needs or provides | Direction | Counterpart | Spec reference |
|---|---|---|---|
| Ticket retrieval by key | needs | 002 `JiraClient.get_issue` | FR-021 |
| ADF-flattened description for the brief | needs | 002 `adf.to_text` | FR-015 |
| `SKELETON_SENTINEL` | **provides** | 004 (partial-implementation reporting), 005 (completion detection) | FR-027 |
| Provenance header format | **provides** | 004 (design digest input), 005 (ticket attribution) | FR-017 |
| `ticket` marker on generated files | **provides** | 005 (attribution and run scoping) | FR-021 of 005 |
| Skeleton listing | **provides** | 005 `skeletons` subcommand | FR-028 |

This feature is the one the other two read *from*, which is why `contracts/skeleton-format.md` exists as a separate contract.

## Phase 0: Research

Complete — see [research.md](./research.md). Eleven decisions, zero `NEEDS CLARIFICATION` remaining.

The decision most likely to be got wrong by assumption is **R1**. The obvious implementation of FR-002 is a regex, and the obvious regex violates FR-005 on the first sentence containing a standards identifier. The filters are structural and run before the network, so a false positive never costs a request and never resolves to something unintended.

**R2** is worth noting as a design simplification rather than a technical choice: making generation an explicit command removes the need to classify intent at all, which is why no part of this plan contains natural-language understanding.

## Phase 1: Design

Complete.

| Artifact | Contents |
|---|---|
| [data-model.md](./data-model.md) | Extraction result and rejection reasons; brief structure; provenance header fields; sentinel definition |
| [contracts/commands.md](./contracts/commands.md) | `extract`, `generate`, `skeletons` with exit codes |
| [contracts/skeleton-format.md](./contracts/skeleton-format.md) | Provenance header, sentinel usage, naming and marker conventions — the contract 004 and 005 build on |
| [quickstart.md](./quickstart.md) | Validation walkthrough; extraction scenarios need no network |

### Post-Design Constitution Re-Check

Unchanged: **PASS, vacuously.** No dependency added, no second configuration source, and the one cross-feature coupling (`sentinel.py`) is a single constant in a named place.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations. One place where the design is deliberately more complex than the minimum:

| Added complexity | Why needed | Simpler alternative rejected because |
|---|---|---|
| Three structural filters before lookup (`keys.py`) | FR-005 forbids a lookup for key-like non-keys; SC-005 requires zero false positives | A plain regex matches `ISO-8601` and `COVID-19`, so every mention of a standard would fetch |

## Spec Deltas Discovered During Planning

| Spec text | What the design does | Recommended resolution |
|---|---|---|
| ~~**FR-017** requires provenance to record ticket key, summary and generation time~~ | The provenance header also records **the identity that generated the design** and the ticket's content digest | **Resolved 2026-10-04.** Both were added to FR-017. The identity is not needed by this feature at all — it exists so feature 004 can enforce its author-may-not-approve policy, and that information is only available at generation time. |

**No outstanding deltas.** `/speckit.analyze` surfaced this as finding X5 once both features had tasks, and it was applied with approval on 2026-10-04. It was the one blocking item between these two plans.
