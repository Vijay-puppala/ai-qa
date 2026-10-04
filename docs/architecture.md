# Architecture

AI-QA: a test-automation platform that turns a Jira ticket into reviewed,
approved, runnable tests and a readable report.

**Last updated**: 2026-10-04

---

## The pipeline

```
Jira ticket
   │  002  read-only REST client
   ▼
Test design (skeleton)          003  key extraction → brief → scaffold
   │                                 names + markers + docstrings,
   │                                 bodies skip as "unimplemented"
   ▼
Human review                    004  approve / reject, recorded in git
   │  gate: no automation without an applicable approval
   ▼
Completed automation            005  bodies written, then run
   │
   ▼
Self-contained HTML report      005  generated in-project, no Allure CLI
```

Each stage is a separate feature with its own spec, plan and tasks under
`specs/`. The stages are coupled by three artifacts and nothing else:

| Coupling | Produced by | Consumed by |
|---|---|---|
| `SKELETON_SENTINEL` constant | 003 `generate/sentinel.py` | 004 (partial-implementation count), 005 (completion detection) |
| Provenance header (7 fields) | 003 `generate/scaffold.py` | 004 (design digest, author), 005 (ticket attribution) |
| `ticket` pytest marker | 003 | 005 (Allure label, `--ticket` filter) |

## Source layout

```
src/ai_qa/
├── config.py          ONE validated settings model, all 14 settings
├── jira/              002 - read-only Jira REST client
│   ├── client.py      get_issue, search, search_page, validate_jql, whoami
│   ├── errors.py      7-way failure taxonomy + redact()
│   ├── adf.py         Atlassian Document Format → plain text
│   ├── models.py      JiraIssue, IssueQueryPage (frozen)
│   └── __main__.py    CLI: check / issue / search
├── generate/          003 - ticket → test design
│   ├── sentinel.py    ONE constant, three features depend on it
│   ├── keys.py        key extraction + 3 rejection filters (pure)
│   ├── brief.py       deterministic hand-off to the authoring assistant
│   ├── scaffold.py    file scaffold + provenance header
│   ├── listing.py     static AST scan for unimplemented skeletons
│   └── __main__.py    CLI: extract / generate / skeletons
├── approval/          004 - the gate
│   ├── digest.py      DESIGN digest: names+markers+docstrings, NOT bodies
│   ├── records.py     one committed JSON file per decision
│   ├── state.py       PENDING | APPROVED | STALE | REJECTED (computed)
│   ├── policy.py      approver identity + author-may-not-approve
│   ├── gate.py        THE single enforcement point
│   └── __main__.py    CLI: review / approve / reject / status / verify
├── automation/        005 - completion & repair boundary (partial)
│   ├── classify.py    repair eligibility, pure, escalate-by-default
│   └── digest.py      ASSERTION digest: stops a repair changing a claim
├── report/            005 - read-side projection
│   ├── read.py        Allure result JSON → TestResult
│   ├── summary.py     RunSummary, scope MANDATORY
│   └── render.py      one self-contained HTML file, zero external requests
└── pages/             page objects (base + login)
```

## Design properties that hold across the whole system

- **Zero third-party dependencies beyond the original 8.** Every feature was
  specified with a dependency floor and none breached it. Consequences:
  `httpx.MockTransport` instead of `respx`, `argparse` instead of `click`, a
  hand-written HTML generator instead of a templating engine, a hand-written
  ADF flattener instead of a converter library.
- **One external prerequisite**: `uv`. It provisions the pinned Python 3.12,
  so no interpreter is installed by hand.
- **No MCP server, assistant connector or external tooling in any runtime
  path.** The platform works with no AI assistant present, except for the two
  authoring steps (writing skeleton bodies, writing repairs), which are
  interactive by design.
- **Offline-testable throughout.** The whole suite passes with no network and
  no Jira configuration. Jira tests skip rather than fail.
- **Serial by default, parallel-safe by construction.** Function-scoped
  fixtures (two documented exceptions) and node-ID-derived artifact paths, so
  enabling parallelism is a configuration change, not a refactor.
- **Two different digests, deliberately named apart**: 004's *design digest*
  (what was approved) and 005's *assertion digest* (what a test claims).

## Data flow for one ticket

1. `generate "tests for DC-11"` → `keys.extract` filters locally, never
   fetching for `ISO-8601`-shaped text → `JiraClient.get_issue` → `brief` →
   `scaffold` writes the file with provenance and the `ticket` marker.
2. An assistant authors test functions below the delimiter; bodies call
   `pytest.skip(skip_reason())` until implemented.
3. `approval approve <file>` digests the design portion, checks the approver
   policy, writes `approvals/<TICKET>/<timestamp>-approved.json`.
4. `approval verify` fails any pipeline where a generated design lacks an
   applicable approval.
5. Bodies are implemented; a run emits Allure result JSON; `report/` projects
   it into `reports/report.html`.
