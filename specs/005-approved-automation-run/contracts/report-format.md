# Report Format Contract: Approved Automation Run & Reporting

**Feature**: `005-approved-automation-run` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

What `reports/report.html` contains, what it guarantees, and what it deliberately is not. This is a contract because people will read this report to make decisions, and a reader who misjudges what it covers draws the wrong conclusion from a correct document.

Field sources: [data-model.md](./data-model.md) §1.

---

## Guarantees

| Guarantee | Requirement |
|---|---|
| Readable with nothing but a browser or text viewer — no Java, no Node, no network, no install | FR-015, FR-031, SC-017, SC-018 |
| Every executed test appears | FR-014, SC-005 |
| Every failure's message and traceback are present | FR-016, SC-006 |
| The scope of the run is stated | FR-035, SC-021 |
| Results are groupable by ticket | FR-021, FR-023, SC-008 |
| The authorising approval is identifiable | FR-022 |
| Every repaired test discloses that it was repaired | FR-041, SC-024 |
| No credential appears anywhere in it | FR-019, SC-011 |
| Nothing is truncated for a large run | FR-018, SC-014 |

---

## Required content

### 1. Scope header — first thing on the page

States exactly what the run covered, in words a reader cannot misread:

- `Scope: ticket TC-345 only (4 tests)` — or
- `Scope: full suite (312 tests)`

**Why this is first and mandatory.** A ticket-scoped run that is all green says nothing about the rest of the suite. Without the scope stated up front, a green report is read as "the product is fine" when it means "these four tests passed". FR-035 makes the field impossible to omit, and SC-021 verifies it.

### 2. Provenance line

Immediately after the scope: that this is a project-generated summary, **not** an Allure report (FR-032).

It must name what it does not offer — no run timeline, no historical trend, no attachment browser — and point at the optional Allure CLI path for anyone who wants those (FR-033). A reader who assumes Allure parity goes looking for history that does not exist and concludes the report is broken.

### 3. Counts

Passed, failed, broken, skipped, and **collected**.

`collected = 0` is rendered as a **failure**, never as a clean run (FR-017, SC-009). An empty report is the one case where a document that looks reassuring is most misleading.

### 4. Results grouped by ticket

One group per ticket, with tests carrying no ticket label in their own `Unattributed` group.

The `Unattributed` group is deliberately visible rather than hidden. A test that should carry a ticket but does not is a traceability gap, and the only way anyone notices is if the report shows it. Note that the ticket label exists only because of the conftest hook — see [data-model.md](./data-model.md) §1.1 — so a large `Unattributed` group is the first symptom of that hook being broken.

### 5. Per-test detail

| Shown | Notes |
|---|---|
| Name, status, duration | |
| Approval identifier | Where present (FR-022) |
| Failure message | From `statusDetails.message` |
| Traceback | From `statusDetails.trace`, collapsed by default |
| Evidence links | Relative paths into `reports/artifacts/` (FR-034) |
| **Repair disclosure** | Where the test was repaired: what changed, how many attempts (FR-041) |

**Repair disclosure is not optional and not a footnote.** A test that passes because a tool modified it is a materially different claim from a test that passed as authored. SC-024 requires 100% disclosure. The display must make a repaired pass visually distinct from an ordinary pass — a reader skimming for green must not miss it.

### 6. Evidence note

A statement of what must accompany the report for evidence links to resolve: the `reports/artifacts/` directory (FR-034).

Honest consequence of linking rather than embedding — the HTML file alone is readable but its evidence links will not resolve if it is sent on its own. Stated in the artifact rather than in documentation nobody reads alongside it.

---

## What this report is not

Recorded so expectations are set by the contract rather than by the word "Allure" in the original request:

| Not provided | Where to get it |
|---|---|
| Run timeline / Gantt view | Allure CLI against the same result data |
| Historical trends across runs | Allure CLI with history, or a future feature |
| Attachment browser | Evidence links, or the Allure CLI |
| Flakiness analysis | Not available from one run's data |
| Retries view | Not in scope |

The same `reports/allure-results/` directory feeds both, so installing the Allure CLI later adds these without changing anything this feature produces.

---

## Self-containment

One file, inline CSS, **no external requests** — no CDN, no web font, no analytics. It must render identically offline and on a locked-down machine.

Evidence is linked relatively, not embedded. Embedding screenshots as data URIs would make a single truly portable file at the cost of size; FR-018 forbids truncating results to compensate, so the trade was made in favour of linking plus the FR-034 statement. If a genuinely standalone file is wanted, that is a change to FR-015, not an implementation detail.

---

## Redaction

Every string entering the report passes through feature 002's redaction helper (FR-019, SC-011).

This matters more here than anywhere else in the project: the report is the artifact most likely to be shared outside the team, and a traceback is where a credential actually surfaces. Verification is by searching a failed run's complete output and the rendered report for a sentinel token — SC-011's method, not an inspection of the code.
