# Skeleton Format Contract: Prompt-Driven Test Generation

**Feature**: `003-prompt-driven-test-generation` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

The shape of a generated skeleton. This is the most load-bearing contract in the project: **features 004 and 005 both read it**, so a change here breaks them silently rather than loudly.

| Consumer | Reads | For |
|---|---|---|
| 004 | provenance header, sentinel | design digest input; partial-implementation reporting |
| 005 | `ticket` marker, sentinel, provenance | attribution, run scoping, completion detection |

---

## File shape

```python
"""<Short description of what this module covers.>

generated-by: ai-qa
ticket: TC-345
ticket-summary: Checkout rejects an expired card
ticket-updated: 2026-10-04T09:12:33.000+0000
ticket-digest: 3f9a1c8e2b04
generated-at: 2026-10-04T10:05:11Z
generated-by-identity: someone@example.com
"""

import pytest

from ai_qa.generate.sentinel import SKELETON_SENTINEL

pytestmark = [pytest.mark.ui, pytest.mark.ticket("TC-345")]


# --- ai-qa: generated test functions below ---


def test_expired_card_is_rejected_at_checkout():
    """Checkout refuses an expired card and shows the user why.

    From TC-345 acceptance criterion 1.
    """
    pytest.skip(f"{SKELETON_SENTINEL}: body not implemented")
```

Everything above the delimiter comment is written by the platform and is byte-predictable from the ticket. Everything below it is authored.

---

## Provenance header

Seven fields in the module docstring, one per line, `key: value`.

| Field | Required | Consumer |
|---|---|---|
| `generated-by: ai-qa` | Yes | Marks the file as generated (FR-018) |
| `ticket` | Yes | 004, 005 |
| `ticket-summary` | Yes | FR-017 |
| `ticket-updated` | Yes | Human corroboration |
| `ticket-digest` | Yes | Staleness comparison (FR-020) |
| `generated-at` | Yes | FR-017 |
| `generated-by-identity` | Yes | **004's author-may-not-approve policy** |

**Staleness is determined by `ticket-digest`, not `ticket-updated`.** Jira bumps `updated` for changes that never touch the text — a label, a sprint, a watcher — so comparing timestamps would report staleness constantly and train people to ignore it. The digest compares the text that the tests were derived from.

**`generated-by-identity` is here for feature 004, not for this feature.** Its FR-022 needs the design's author, and that is only knowable at generation time. Added to FR-017 on 2026-10-04 (analysis finding X5), which is what made feature 004's approver policy enforceable.

---

## The sentinel

```python
pytest.skip(f"{SKELETON_SENTINEL}: <what is not implemented>")
```

Imported from `ai_qa.generate.sentinel` — **never written as a literal**. Three features depend on the string; a literal in three places drifts by one character and breaks detection in two of them with no error, because "no skeletons found" and "nothing to detect" are indistinguishable.

**Guarantees** (FR-027):

- A skeleton reports as **skipped**, with a reason naming it an unimplemented generated skeleton.
- A skeleton **cannot report as passed**. This is why `skip()` in the body is used rather than `xfail`, which can report `xpass`.

**Completion** (consumed by 005): a test is no longer a skeleton when the sentinel call is gone from its body. That is the whole detection mechanism — there is no second state file.

---

## Markers

| Marker | Required | Why |
|---|---|---|
| `ticket("<KEY>")` | Yes | Attribution and run scoping in 005. **Carries an argument**, which matters — see below |
| `ui` / `api` | One of | Test kind, per the repository's existing convention |
| `smoke` | Optional | Critical-path subset |

**The `ticket` marker carries an argument, and that has a consequence 005 had to design around**: `allure-pytest` maps *bare* markers to Allure `tag` labels but **drops markers carrying arguments**. Verified empirically. So the marker alone produces no ticket information in a report — feature 005 adds a conftest hook to turn it into a label. Generated files must still carry the marker, because it is also what the `--ticket` collection filter selects on.

---

## Naming conventions

- Module: `tests/<kind>/test_<feature_area>.py` — not named after the ticket, because a ticket is a unit of work and a test file is a unit of behaviour.
- Function: `test_<behaviour_being_proven>`, stating the behaviour rather than the mechanism.
- Docstring: states the behaviour the test must prove, and cites the acceptance criterion it derives from.

**The docstring is not decoration.** Feature 004 approves the *design*, which is names, markers and docstrings — so the docstring is part of the approved content and its digest. Feature 005's repair boundary rests on it too: an assertion may not be changed because it *implements the behaviour the docstring claims*. A vague docstring weakens both features.

---

## Compatibility notes

Changes that break a downstream feature:

- Renaming or reformatting a provenance field — 004's digest and 005's attribution read these keys.
- Changing `SKELETON_SENTINEL`'s value — breaks 005's completion detection and 004's partial-implementation count.
- Writing the sentinel as a literal instead of importing it — removes the single point of truth.
- Dropping the `ticket` marker — breaks 005's attribution and run scoping.
- Moving the provenance block out of the module docstring — changes where both consumers look.
- Using `xfail` instead of `skip` — a skeleton could then report as passed, violating FR-027.
