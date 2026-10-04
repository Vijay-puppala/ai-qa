# Phase 0 Research: Prompt-Driven Test Generation

**Feature**: `003-prompt-driven-test-generation` | **Date**: 2026-10-04 | **Plan**: [plan.md](./plan.md)

Eleven decisions. The three clarifications in the spec (skeleton deliverable, interactive authoring, refuse-by-default regeneration) are settled input.

---

## R1: Extracting a key without matching things that merely look like one

**Decision**: Candidate extraction by pattern `\b[A-Za-z][A-Za-z0-9_]{1,9}-\d{1,6}\b`, normalised to upper case, then filtered through three structural rejections before any lookup:

1. **A denylist of standards prefixes**: `ISO`, `UTF`, `RFC`, `ANSI`, `IEEE`, `SHA`, `AES`, `COVID`, `EN`, `BS`, `SI`, `ASCII`, `HTTP`, `IPV`, `MD`, `CVE`.
2. **A year rule**: a four-digit numeric part in 1900–2199 is rejected, which removes `2026-10` and most date fragments.
3. **A length rule**: a numeric part longer than six digits is not an issue number.

Surviving candidates are resolved against Jira. A candidate that does not resolve is reported as *not found*, distinctly from *malformed*.

**Rationale**: This is the requirement most likely to be implemented naively and then quietly misbehave. A bare `[A-Z]+-\d+` regex matches `COVID-19`, `ISO-8601`, `UTF-8` and `CVE-2026-1234`, so every mention of a standard in ordinary prose would trigger a lookup — FR-005 forbids exactly that, and SC-005 measures it. The filters are deliberately **structural and local**, applied before the network, because a false positive that reaches Jira either resolves to the wrong ticket or wastes a request and produces a confusing "not found".

The split between *malformed* and *nonexistent* (FR-008) falls out naturally: a string the pattern rejects is malformed; one that passes the filters and fails to resolve does not exist or is not visible.

**Alternatives considered**:
- *Validate against a configured list of project keys* — rejected: FR-010 requires a new project to work with zero configuration changes.
- *Fetch the project list from Jira and validate against it* — rejected: adds a network round trip to every extraction, and FR-025 requires extraction to be verifiable offline.
- *Resolve every candidate and let Jira decide* — rejected: violates FR-005, and makes `ISO-8601` in a sentence cost a request.

## R2: Intent — a key being present must not trigger generation

**Decision**: Generation is an explicit command (`generate`). The platform never infers from free text whether the user wants tests. Extraction answers *which ticket*, never *what to do*.

**Rationale**: The spec's edge case requires that "why did TC-345 fail?" does not generate tests. Rather than classify intent — which would need judgement and would misfire — the design removes the question: generation happens only when someone runs the generate command, and the free-form text is parsed *only* for the key. This satisfies FR-006's "report and do not proceed" and the intent edge case with no inference at all.

**Alternatives considered**:
- *Intent classification over the prompt* — rejected: unreliable, untestable, and solves a problem the command structure removes.
- *Generate whenever a key appears* — rejected by the spec's edge case.

## R3: The deterministic/interactive split

**Decision**: The platform owns extraction, retrieval, **brief** production, and file scaffolding. An AI assistant authors the test functions. The hand-off is a committed-nowhere brief written to the scratch area and printed to stdout: ticket key, summary, flattened description, acceptance criteria, labels, and the conventions the assistant must follow.

**Rationale**: FR-013's clarified answer. The important design consequence is FR-029: the deterministic half must run unattended and offline-testable, so it cannot be entangled with authoring. Making the brief a concrete artifact rather than an in-memory hand-off is what lets the deterministic half be tested on its own — the test asserts the brief's content, with no assistant involved.

**Alternatives considered**:
- *Deterministic templates generating test names from acceptance criteria text* — rejected by the clarification, and acceptance criteria rarely map one-to-one to test names.
- *Call a language model from the platform* — rejected by the clarification; adds a dependency and a credential.

## R4: What the platform scaffolds versus what the assistant writes

**Decision**: The platform writes the file: module docstring with the provenance header (R8), imports, `pytestmark` with the `ticket` marker, and a single marker comment delimiting where test functions go. The assistant writes the test functions — names, docstrings stating claimed behaviour, and the skip body.

**Rationale**: Splitting at the file level rather than the function level keeps the deterministic output verifiable: the scaffold is byte-predictable from the ticket, so it can be asserted in a test, while the part requiring judgement is clearly delimited. It also guarantees the provenance header and the ticket marker exist even if authoring is interrupted — which matters because FR-017 requires provenance on every generated artifact, and a half-finished file with no provenance is the worst outcome.

**Alternatives considered**:
- *Assistant writes the whole file* — rejected: provenance and the ticket marker would depend on the assistant remembering, and FR-017/FR-021 would be unenforceable.
- *Platform generates placeholder test functions too* — rejected: it would have to invent names, which is the judgement the clarification assigned to the assistant.

## R5: The skip sentinel

**Decision**: A single shared constant, `SKELETON_SENTINEL = "ai-qa:unimplemented"`, used as the prefix of every skeleton's `pytest.skip(...)` reason and exported from `src/ai_qa/generate/sentinel.py`.

**Rationale**: FR-027 requires a skeleton to report as skipped with a reason identifying it as unimplemented, and to be incapable of reporting as passed. Feature 005 detects completion by the sentinel's absence, and feature 004 reports partial implementation by counting it. Three features depend on one string, so it must live in one place — a literal repeated across features is the kind of thing that drifts by one character and silently breaks detection in two of them.

**Alternatives considered**:
- *`pytest.mark.skip` decorator* — rejected: a decorator is harder to remove cleanly when the body is implemented, and `skip()` in the body makes the unimplemented state obvious at the point it matters.
- *`xfail`* — rejected: an unimplemented test is not an expected failure, and `xfail` can report as `xpass`, violating FR-027's "must not be capable of reporting as passed".

## R6: Listing unimplemented skeletons without running them

**Decision**: Static AST scan of `tests/` for calls to `pytest.skip` whose argument contains the sentinel, reading the ticket from the module's `ticket` marker.

**Rationale**: FR-028 requires a listing of outstanding generated work. Deriving it from a test run would mean the listing is only as current as the last run, and would need the application under test to be reachable. A static scan answers the question from the repository alone, which also makes it usable by feature 004's partial-implementation reporting and by a pipeline.

**Alternatives considered**:
- *Collect with `pytest --collect-only` and inspect skips* — rejected: skips are evaluated at run time, not collection, so this would not find them.
- *Maintain a manifest file* — rejected: a second source of truth that drifts from the code.

## R7: Regeneration refusal

**Decision**: Before writing, check whether the target file exists. If it does, refuse and name both the file and the explicit flag required to overwrite. Overwriting happens only on that flag.

**Rationale**: FR-019's clarified answer. The check is on file existence rather than on content comparison because the requirement is to protect *hand-made changes*, and the platform cannot tell a refined skeleton from an untouched one without the provenance comparison of R8 — which is available, but refusing unconditionally is the safer default and the one the clarification chose.

**Alternatives considered**:
- *Overwrite if unmodified since generation* — rejected by the clarification (that was option C); it also depends on the provenance digest being correct, so a bug there would destroy work.
- *Write to a timestamped new file* — rejected by the clarification (option B).

## R8: Provenance and staleness

**Decision**: A provenance block in the module docstring carrying: ticket key, ticket summary, the ticket's `updated` timestamp from Jira, a digest of the ticket's text content, the generation timestamp, the identity that generated it, and a `generated-by: ai-qa` marker.

**Rationale**: FR-017 requires key, summary and time; FR-018 requires generated artifacts to be distinguishable from hand-written ones; FR-020 requires ticket change to be discoverable **without rerunning generation** — which the stored content digest provides by comparison against a fresh fetch of the ticket alone.

The **identity** field is not required by this feature's own requirements. It is included because feature 004 needs to know who authored a design in order to enforce its author-may-not-approve policy, and that information exists only at generation time. Recording it here is cheap; reconstructing it later is impossible. Flagged as a spec delta in [plan.md](./plan.md).

**Alternatives considered**:
- *Store provenance in a sidecar file* — rejected: separable from the test, so the two drift and a moved test loses its provenance.
- *Store only the generation timestamp* — rejected: FR-020 needs ticket change detectable, which a timestamp alone cannot give.

## R9: Where the key is read from, and URL forms

**Decision**: Accept a bare key, a key anywhere in a sentence, any letter case, and a key inside a URL by matching the path segment after `/browse/` or the `selectedIssue` query parameter, falling back to the general pattern.

**Rationale**: FR-002 to FR-004 and SC-004 enumerate exactly these forms. The URL case is handled by looking at the recognised Jira URL shapes first, because a URL also contains digits and hyphens elsewhere (`/jira/software/c/projects/...`) and the general pattern alone can pick the wrong fragment.

**Alternatives considered**:
- *General pattern only* — rejected: risks matching a non-key fragment of a URL path.

## R10: Multiple keys

**Decision**: Report every key found and refuse to proceed. No fan-out, no silent selection of the first.

**Rationale**: FR-007 states it directly, and the spec's assumption records batch generation as a later feature. The failure this prevents is subtle: generating for the first of three keys looks like success and leaves two tickets silently uncovered.

**Alternatives considered**:
- *Generate for each key in turn* — rejected: not specified, and multiplies the regeneration-refusal cases.
- *Use the first key* — rejected by FR-007.

## R11: CLI surface

**Decision**: `python -m ai_qa.generate` with three subcommands: `extract` (show which key was found, no generation), `generate`, `skeletons`.

**Rationale**: `extract` satisfies FR-026 — extraction diagnosable independently of generation — and is the command the offline extraction tests exercise. `argparse` from the standard library keeps the dependency floor intact. `skeletons` surfaces R6's listing; feature 005's own `skeletons` command is expected to delegate here rather than reimplement the scan.

**Alternatives considered**:
- *One command with flags* — rejected: `extract` with a `--dry-run`-ish flag muddles two distinct outputs.

---

## Resolved unknowns

| Unknown | Resolved by |
|---|---|
| How is a key distinguished from `ISO-8601`? | R1 — structural filters before any lookup |
| How is "generate" told apart from "ask about"? | R2 — explicit command, no intent inference |
| What exactly does the platform produce versus the assistant? | R4 — file scaffold versus test functions |
| How does feature 005 know a skeleton is implemented? | R5 — one shared sentinel constant |
| How is outstanding work listed without a run? | R6 — static AST scan |
| How is ticket change detected without regenerating? | R8 — content digest in the provenance block |
