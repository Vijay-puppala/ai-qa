# Quickstart Validation: Prompt-Driven Test Generation

**Feature**: `003-prompt-driven-test-generation` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

How to prove this feature works. Commands: [contracts/commands.md](./contracts/commands.md). Skeleton shape: [contracts/skeleton-format.md](./contracts/skeleton-format.md).

**Scenarios 1–3 need no Jira and no network.** Extraction and the skeleton listing are pure, which is what FR-025 and SC-012 require — and it means most of this feature is verifiable before feature 002 exists.

---

## Prerequisite

Feature 001's environment. Nothing new installed (zero new dependencies).

```bash
uv run pytest -m healthcheck    # expect 14 passed
```

---

## Scenario 1 — Key extraction across every input form (validates SC-004)

```bash
uv run python -m ai_qa.generate extract "generate tests for TC-345"
uv run python -m ai_qa.generate extract "for TC-345 generate tests"
uv run python -m ai_qa.generate extract "TC-345: write tests"
uv run python -m ai_qa.generate extract "tc-345"
uv run python -m ai_qa.generate extract "https://site.atlassian.net/browse/TC-345"
```

**Expected**: every one reports `TC-345`, normalised to upper case. Five forms, one answer — that is SC-004's 100%.

---

## Scenario 2 — Things that look like keys but are not (validates SC-005, FR-005)

The scenario that catches the naive implementation.

```bash
uv run python -m ai_qa.generate extract "we follow ISO-8601 for dates"
uv run python -m ai_qa.generate extract "COVID-19 regression suite"
uv run python -m ai_qa.generate extract "encoding is UTF-8"
uv run python -m ai_qa.generate extract "see CVE-2026-1234"
uv run python -m ai_qa.generate extract "sprint ending 2026-10"
```

**Expected**: **zero** accepted keys from all five, each reporting the rejected candidate and which rule fired (`DENYLISTED_PREFIX`, `YEAR_LIKE`, `NUMBER_TOO_LONG`). Zero network requests made.

A bare `[A-Z]+-\d+` pattern accepts all five. If this scenario passes, the filters are doing their job; if it fails, every mention of a standard in a prompt will fetch a ticket.

```bash
uv run pytest tests/generate/test_keys.py -v
```

---

## Scenario 3 — Unimplemented listing works from the repository alone (validates FR-028)

```bash
uv run python -m ai_qa.generate skeletons
uv run pytest tests/generate/test_listing.py -v
```

**Expected**: every test whose body calls `pytest.skip` with the sentinel is listed with its source ticket. Implemented tests are absent. No network, no test run required.

Confirm the scan is static, not run-derived:

```bash
uv run python -m ai_qa.generate skeletons   # works with the application under test unreachable
```

---

## Scenario 4 — No key, several keys (validates SC-006, FR-006, FR-007)

```bash
uv run python -m ai_qa.generate generate "please write some tests"; echo "exit=$?"
uv run python -m ai_qa.generate generate "tests for TC-345 and TC-346"; echo "exit=$?"
```

**Expected**: the first exits **3**, saying no key was found and showing the expected form. The second exits **4**, naming **both** keys and generating nothing.

The second case matters more than it looks: acting on `TC-345` alone would look like success and leave `TC-346` silently uncovered.

---

## Scenario 5 — Intent is never inferred (validates the intent edge case)

```bash
uv run python -m ai_qa.generate extract "why did TC-345 fail last night?"
```

**Expected**: reports `TC-345` and **generates nothing** — `extract` does not generate, and `generate` only runs when invoked. There is no code path from "a key appeared in some text" to "tests were created", which is how this requirement is met with no intent classification at all.

---

## Scenario 6 — Generate a skeleton (validates US1, SC-001, SC-007)

Needs feature 002 configured.

```bash
uv run python -m ai_qa.generate generate "generate tests for TC-345"
```

**Expected**: a brief is printed; a test file is created under `tests/ui/` or `tests/api/`; the file carries the provenance header and the `ticket` marker; each test function has a docstring and a sentinel skip body.

Then confirm the skeleton behaves as FR-027 requires:

```bash
uv run pytest --ticket TC-345 -v
```

**Expected**: every generated test reports as **skipped**, with a reason naming it an unimplemented generated skeleton. **Zero report as passed** — that is the guarantee, and it is why the body uses `skip()` rather than `xfail`.

---

## Scenario 7 — Genericity (validates SC-002, SC-003)

The requirement behind the original request: this must not be a one-off.

```bash
uv run python -m ai_qa.generate generate "tests for TC-345"
uv run python -m ai_qa.generate generate "tests for PLATFORM-12"
uv run python -m ai_qa.generate generate "tests for NEWPROJ-1"
```

**Expected**: three different projects, zero changes to any committed file between them, zero configuration changes.

Then the static check:

```bash
grep -rnE '\b[A-Z]{2,9}-[0-9]{1,6}\b' src/ | grep -v test
```

**Expected**: no ticket key in `src/` that *limits* behaviour — no lookup table, no special case, no conditional keyed on a ticket. Provenance keys in generated test files are expected and required; FR-009 was corrected on 2026-10-04 to make that distinction explicit.

---

## Scenario 8 — Regeneration refuses by default (validates SC-009, FR-019)

```bash
uv run python -m ai_qa.generate generate "tests for TC-345"; echo "exit=$?"   # second time
```

**Expected**: exit **6**, naming the existing file and the `--force` flag. Any hand-made refinement in that file survives.

```bash
uv run python -m ai_qa.generate generate "tests for TC-345" --force
```

**Expected**: proceeds, because overwriting was explicit.

---

## Scenario 9 — Ticket change is discoverable without regenerating (validates SC-010, FR-020)

Change the ticket's description in Jira, then:

```bash
uv run python -m ai_qa.generate skeletons --check-stale
```

**Expected**: the generated file is reported as stale, by comparing the stored `ticket-digest` against a fresh digest of the ticket's text — with zero regenerations needed to find out.

Note the deliberate choice: staleness compares the **digest**, not `ticket-updated`. Jira bumps `updated` for a label or sprint change that never touches the text, so a timestamp comparison would cry stale constantly and teach everyone to ignore it.

---

## Coverage summary

| User Story | Priority | Scenario |
|---|---|---|
| 1 — Ask for tests by naming a ticket | P1 | 1, 5, 6 |
| 2 — Works for any ticket, no code changes | P1 | 7 |
| 3 — Understand an unclear request | P2 | 2, 4 |
| 4 — Trace an artifact to its ticket | P2 | 6, 9 |

Scenarios 1–5 are independent of feature 002 and can be validated as soon as this feature is built. Scenarios 6–9 need ticket retrieval.
