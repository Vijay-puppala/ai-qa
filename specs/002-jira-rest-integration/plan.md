# Implementation Plan: Jira REST Integration

**Branch**: `002-jira-rest-integration` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-jira-rest-integration/spec.md`

## Summary

Add a **read-only** Jira client to the AI-QA platform that talks to Jira Cloud's REST API directly — reading issues and querying them — authenticated from `.env` through the existing validated settings model, with **no MCP or assistant connector in the runtime path** and **no new third-party dependencies**.

**Scope change, 2026-10-04**: write operations (comment, transition) were deferred out of this feature once it was confirmed that nothing needs them — feature 004 keeps its approval records in the repository, and feature 005 rules Jira reporting out of scope. The platform therefore has **no destructive capability**, and the eight safeguards that existed to contain one went with it. Research R3, R4 and R10 are retained as DEFERRED for whichever feature adds writes later.

Five decisions carry the design, each resolved in [research.md](./research.md):

1. **One client, two call paths.** `JiraClient` is constructed directly by tooling and injected into tests by a fixture. The clarified answer to "runtime or tooling?" was *both*, and the risk in that answer is two code paths whose error handling drifts apart. One class removes it (R9).
2. ~~All four write safeguards live inside the client.~~ **Deferred with the write scope** — see the scope change above.
3. **API v3 plus an in-project ADF flattener.** On v3 an issue description is a nested ADF document, not a string. v2 would hand back a plain string, which is the tempting shortcut — v3 is still chosen because it is the current Cloud API and the one Atlassian develops against, and because `from_text` will be needed unchanged when writes return (R2).
4. **`httpx.MockTransport` for offline tests.** The conventional answers (`respx`, `vcrpy`) are dependencies the floor forbids; `httpx` already ships what is needed (R5).
5. **`argparse` for the CLI, `SecretStr` plus explicit redaction for the token.** Both chosen to hold the zero-dependency line without weakening the requirement (R12, R8).

Net new dependencies: **zero**. Net new runtime services: **zero**.

## Technical Context

**Language/Version**: Python 3.12, unchanged from feature 001

**Primary Dependencies**: `httpx` (HTTP, already declared), `pydantic` (settings and models, already declared), `pytest` (fixtures, already declared). Standard library `argparse`, `hashlib`, `base64`. **Nothing added.**

**Storage**: N/A. No persistence, no caching — issues are fetched when requested.

**Testing**: pytest with `httpx.MockTransport`. New marker `jira` for the integration's own tests. No test contacts a live Jira site.

**Target Platform**: Windows and Linux, per feature 001. macOS remains unsupported.

**Project Type**: Library subpackage plus a CLI entry point inside the existing single project.

**Performance Goals**: Every request bounded by an explicit timeout, default 30 s (FR-013). At most three attempts on 429/5xx (R7).

**Constraints**: No MCP, assistant connector, or external tooling in the runtime path (FR-002, SC-003) — the Jira features must work with no AI assistant present. Zero new dependencies (FR-003, SC-002). Jira unavailability must not affect tests that make no Jira request (FR-016, SC-008). Full suite must pass with no network access to Jira (SC-009). Credential must appear in zero error messages, logs, tracebacks, or Allure artifacts (SC-006).

**Scale/Scope**: Two operations (read, query). One subpackage of six modules, one `Settings` extension of four fields, one CLI with three subcommands.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status: PASS — vacuously, and this is now the second feature affected.** `.specify/memory/constitution.md` remains the unmodified template: every principle is a `[PRINCIPLE_N_NAME]` placeholder and governance is `[GOVERNANCE_RULES]`. No ratified principle exists for this plan to comply with or violate.

Worth noting: this feature no longer writes to a live system of record, which removes the sharpest edge the empty gate would have left unguarded. It still handles a credential carrying the holder's full Jira permissions, so the redaction requirements remain the security-relevant surface here — and they are this plan's own discipline rather than a governance requirement.

Pre-Phase 0: no violations (no principles exist).
Post-Phase 1: unchanged — see [Post-Design Constitution Re-Check](#post-design-constitution-re-check).

## Project Structure

### Documentation (this feature)

```text
specs/002-jira-rest-integration/
├── plan.md              # This file
├── research.md          # Phase 0 — 12 decisions
├── data-model.md        # Phase 1 — settings, issue model, error taxonomy
├── quickstart.md        # Phase 1 — validation walkthrough
├── contracts/
│   ├── jira-client.md   # Client and CLI contract
│   └── configuration.md # Jira `.env` settings contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

New and changed files only; everything else from feature 001 is unchanged.

```text
src/ai_qa/
├── config.py                  # CHANGED: + 4 Jira fields, + cross-field validation (FR-008)
└── jira/                      # NEW subpackage
    ├── __init__.py            # Public surface: JiraClient, errors, models
    ├── client.py              # JiraClient: read + query, no write methods (FR-005/006/007)
    ├── models.py              # JiraIssue, IssueQueryPage (FR-005)
    ├── errors.py              # 7-way error taxonomy + redaction helper (FR-014, FR-010)
    ├── adf.py                 # ADF <-> plain text (R2)
    └── __main__.py            # argparse CLI: check / issue / search (FR-019, R12)

tests/
├── conftest.py                # CHANGED: + jira_client fixture, + mock_jira transport factory
├── jira/                      # NEW
│   ├── test_client_read.py    # Read + query, incl. pagination (US1, US4)
│   ├── test_no_write.py       # FR-007 is a prohibition, so it needs its own test
│   ├── test_errors.py         # 7 failure causes are distinct (FR-014, SC-005)
│   ├── test_redaction.py      # Token absent from all output (SC-006)
│   └── test_adf.py            # Flattener, incl. unknown node degradation (R2)
└── health/test_environment.py # CHANGED: + Jira settings validate when configured (FR-011)

.env.example                   # CHANGED: + 7 Jira settings with placeholders (FR-009)
README.md                      # CHANGED: + Jira setup, token creation, `check` step (FR-020)
CLAUDE.md                      # CHANGED: + "no MCP for Jira" rule (FR-021)
pyproject.toml                 # CHANGED: + `jira` marker only. No dependency change.
```

**Structure Decision**: A subpackage rather than flat modules, because the integration is six distinct concerns (transport, models, errors, ADF, CLI, public surface) and a flat layout would scatter them among general-purpose helpers.

Jira settings extend the **existing** `Settings` model rather than forming a parallel `JiraSettings`. Feature 001 established that configuration has exactly one validated source with every setting named in `.env.example`; a second settings object would reintroduce the invisible-configuration problem SC-010 forbids, and would mean two places to look when a value is wrong.

Test files are split by *concern under test* rather than by module, so the files a reviewer reads to check the safeguards (`test_safeguards.py`) and the credential handling (`test_redaction.py`) are named for the guarantee rather than for the code.

## Phase 0: Research

Complete — see [research.md](./research.md). Twelve decisions, zero `NEEDS CLARIFICATION` remaining.

The four findings most likely to be got wrong by assumption:

- **Issue descriptions are ADF JSON on v3**, not strings. Code written against the obvious `fields.description` string shape fails immediately.
- **`GET /rest/api/3/search` is deprecated** in favour of token-paginated `POST /search/jql`. Building on the offset form would require a migration within the year and carries offset-drift, which conflicts with SC-011.

## Phase 1: Design

Complete. Artifacts:

| Artifact | Contents |
|---|---|
| [data-model.md](./data-model.md) | The 7 new `Settings` fields with validation rules; `JiraIssue` and `IssueQueryPage`; the 7-way error taxonomy; the comment signature scheme |
| [contracts/jira-client.md](./contracts/jira-client.md) | Client method contracts — inputs, returns, which error each failure raises, which safeguard refuses what; the 5 CLI subcommands with exit codes |
| [contracts/configuration.md](./contracts/configuration.md) | The Jira `.env` contract: each setting, type, required/optional, default, placeholder |
| [quickstart.md](./quickstart.md) | Validation walkthrough mapped to the 17 success criteria, including the safeguard and redaction checks |

Contracts are included because this feature exposes two consumer-facing surfaces: a Python API that tests and tooling call, and a CLI. Both can break compatibly or incompatibly, which is what makes them worth pinning down.

### Post-Design Constitution Re-Check

Unchanged: **PASS, vacuously.** The design adds no dependency, no runtime service, and no second configuration source, and it concentrates the dangerous surface (writes) behind four guards in one auditable place. Had the usual Spec Kit default principles been ratified, this design would be expected to clear them — an inference, not a verified result, and not a substitute for ratifying the constitution.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations to justify — the gate is empty rather than passed. For the record, the two places this design is deliberately *more* complex than the minimum, and why:

| Added complexity | Why needed | Simpler alternative rejected because |
|---|---|---|
| ADF flattener (`adf.py`) | v3 returns descriptions as a document tree; FR-005 and the rich-text edge case need usable text | Using API v2 for reads returns plain strings, but splits the feature across two API versions since writes need ADF anyway |

## Risks

Stated plainly because the clarified scope is the widest option and the spec's own safeguards are the mitigation.

| Risk | Mitigation | Residual |
|---|---|---|
| ~~A flaky test transitions a real ticket~~ | **Eliminated 2026-10-04**: writes were deferred out of this feature, so the client has no method that modifies Jira | None - the capability does not exist to misuse |
| Token leaks into a shared Allure report | `SecretStr` plus explicit redaction on every error path (FR-010), verified by searching a failed run's full output (SC-006) | A token pasted inline into a test by hand. Feature 001 chose no secret scanning, so this stays a code-review concern. |
| Jira outage breaks the suite | Jira absent from the non-Jira path (FR-016), bounded timeouts (FR-013), offline-testable (FR-018) | A future test that calls Jira in a fixture used suite-wide would reintroduce the coupling. |
| Transition allow-list drifts from the real workflow | Per-issue transition lookup distinguishes policy refusal from workflow refusal (R3) | Allow-list is configuration; it can be wrong without failing anything until a transition is attempted. |

## Spec Deltas Discovered During Planning

None. Every requirement in the spec is satisfiable as written, and no requirement had to be reinterpreted to make the design work.

No outstanding observations. The write-audit note that stood here referred to FR-026, which was removed with the write scope on 2026-10-04.
