# Specification Quality Checklist: Prompt-Driven Test Generation

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- All 16 items pass. 30 functional requirements, 17 success criteria, 4 user stories, 15 edge cases. Ready for `/speckit.plan`.
- **All three clarifications resolved** on 2026-10-03:
  - **Q1 (FR-012)**: non-runnable **test skeleton** — real files, names, markers, docstrings, unimplemented bodies.
  - **Q2 (FR-013)**: **interactive assistant** authors the bodies; the platform owns the deterministic half (extract, retrieve, hand off, scaffold) and calls no language model.
  - **Q3 (FR-019)**: **refuse by default** on regeneration; overwrite only on explicit instruction.
- **Four requirements and four criteria were added as consequences**, not requested:
  - **FR-027, FR-028 / SC-014, SC-015, SC-016** exist because skeletons are the one deliverable that can *look* like coverage while proving nothing. A skeleton must report as skipped with a reason naming it unimplemented, must be incapable of reporting as passed, and must appear in a single listing of outstanding work. Without these, option B's main failure mode — a repository slowly filling with skipped tests nobody notices — is unaddressed.
  - **FR-029** exists because answering Q2 with "interactive" risks the whole feature becoming unusable without a human. Splitting the deterministic half out and requiring it to run unattended keeps extraction, retrieval and scaffolding usable in CI even though authoring is not.
  - **FR-030** exists because interactive authoring is only reproducible if the conventions live in the repository rather than in whoever is at the keyboard. It extends feature 001's FR-014 (`CLAUDE.md`) to cover skeleton conventions.
  - **SC-017** makes Q3's refusal measurable rather than aspirational.
- **One contradiction was found and fixed during integration.** SC-011 previously read "zero assistant connectors or external tooling are required at runtime" — which Q2's answer would have falsified, since generation now needs an assistant. It has been rewritten to draw the boundary precisely: the *deterministic path* requires no assistant and runs unattended; *authoring* requires one; and no part of the platform requires an MCP server or connector at any time. The no-MCP constraint from feature 002 is preserved exactly; the no-assistant claim is narrowed to where it is actually true.
- **The genericity requirement is the real subject** of the user's request. FR-009 to FR-011 and SC-002/SC-003 exist because the complaint was explicitly about "a one off integration where tests are created for a specific jira only". FR-009 is written as a prohibition on committed files so it can be verified by searching the repository rather than by reading intent.
- **FR-005 and SC-005 guard a non-obvious failure**: `COVID-19`, `ISO-8601`, `UTF-8` and dates all match the shape of a ticket key. A false positive is worse than a miss, because it silently resolves to the wrong thing or to nothing.
- **One honest limitation recorded in Assumptions**: a ticket describes behaviour, not markup, so no amount of ticket text yields real selectors. This is why option B (skeleton) is a more truthful deliverable than option C (runnable) would have been for UI tests — the skeleton's docstring states the behaviour, and the selectors come from the recorded-draft workflow in feature 001.

## Validation History

| Iteration | Date | Result |
|-----------|------|--------|
| 1 | 2026-10-03 | 14 of 16 items pass. 2 failures, both from the three open clarifications — the generation deliverable (Q1) and generator (Q2) were undefined, so FR-012 and FR-013 carried no acceptance criteria. |
| 2 | 2026-10-03 | 16 of 16 items pass. All three clarifications answered (B/C/A). Markers removed; FR-027 to FR-030 and SC-014 to SC-017 added as consequences; SC-011 rewritten to remove the contradiction with interactive generation. Final counts: 30 functional requirements, 17 success criteria, 4 user stories, 15 edge cases. Ready for planning. |
