# Decisions

Every decision below was made deliberately, with an alternative rejected. The
`⛔` ones must not be changed without discussion — each exists because the
obvious alternative was tried, reasoned about, or actively caused a bug.

**Last updated**: 2026-10-04

---

## ⛔ Must not change without discussion

### 1. The approval digest covers the design portion only, never whole files

`approval/digest.py` hashes test **names, markers and docstrings**. Bodies are
excluded.

A whole-file digest voids every approval the moment its automation is written —
and writing automation is the act the approval authorises. The gate would
refuse the work it had just permitted, **deadlocking 003 → 004 → 005
together**. This was found by cross-feature analysis as finding X1 before any
code existed, and `tests/approval/test_digest.py` is the regression guard.

### 2. Repair may never change an assertion

`automation/digest.py` compares an assertion digest before and after a repair
and refuses any change. `automation/classify.py` permits repair only for a
closed list of mechanical faults and **escalates by default**.

The shortest path from a red assertion to a green one is to weaken the
assertion. Without these, the platform becomes a machine for hiding defects.
Element-not-found and timeouts are excluded *deliberately* despite being the
commonest test-side faults in browser automation — they are indistinguishable
from a feature that was never built.

**Known limitation, documented not hidden**: the digest compares assertion
*text*, so changing a value an assertion depends on (`expected = 5` → `0`) is
not caught. `tests/report/test_safety.py` asserts this limitation so nobody
mistakes it for a guarantee. The residual risk is carried by bounded attempts,
logged digests, and the report disclosing every repaired pass.

### 3. `SKELETON_SENTINEL` is imported, never retyped

`generate/sentinel.py` holds one constant. Three features depend on it. A
literal copied into a second place drifts by one character and silently breaks
detection in two features — with no error, because "no skeletons found" and
"nothing to detect" are indistinguishable.

### 4. The gate has exactly one enforcement point

`approval/gate.py`. Features 003 and 005 each add an entry point; a guard
duplicated per call site is one somebody eventually forgets.

### 5. Approval state is computed, never stored

A stored state is a cache with no invalidation signal. The moment a docstring
is edited the stored value is wrong, and **a wrong state looks exactly like a
correct one**. `STALE` is the case a cache would get wrong most often.

### 6. Zero new third-party dependencies

Held across five features. Each refusal has a named substitute:
`httpx.MockTransport` (not `respx`), `argparse` (not `click`), hand-written
HTML (not Jinja2), hand-written ADF flattener (not a converter).

`pydantic-settings` is the specific near-miss: in pydantic v2 `BaseSettings`
moved to a separate distribution, so the idiomatic import would have breached
the floor. `BaseModel` + `python-dotenv` covers the requirement exactly.

### 7. No MCP, connector or external tooling in any runtime path

The platform must work with no AI assistant present. This is why **Allure
Report 3 was rejected**: it removes the Java requirement but is npm-only and
needs Node.js, which 002's Question 1 had already excluded. It would have
swapped one forbidden prerequisite for another.

### 8. The Jira client is read-only by construction

Not a configuration flag — there is no write code. Write support was specified
first, then deferred once it was established that nothing needs it (004 keeps
records in git, 005 rules Jira reporting out of scope). FR-007 is now a
*prohibition*, and `tests/jira/test_no_write.py` enforces it by asserting every
`POST` targets one of two named read-only endpoints.

### 9. A run that collects zero tests is a failure

pytest exits 5 for "nothing collected" and most callers treat non-1 as success.
A mistyped `--ticket` would otherwise produce a confident green run that tested
nothing — the worst failure available to a platform whose product is confidence.

### 10. The report says it is *not* an Allure report

`report/render.py` states this in the output. A reader who assumes parity goes
looking for a timeline and history that do not exist and concludes the report
is broken.

---

## Other settled decisions

| Decision | Why | Rejected |
|---|---|---|
| `uv` provisions Python 3.12 via exact pin `==3.12.*` | This machine has only 3.14.7; `>=3.12` would resolve against it and silently defeat the pin | Manual Python install |
| Jira API **v3** + in-project ADF flattener | v3 descriptions are ADF JSON, not strings. v2 returns plain text but splits the feature across API versions | v2 for reads |
| `POST /search/jql` with token pagination | `GET /search` is deprecated and carries offset drift | Offset pagination |
| Retry only 429/5xx, max 3, honour `Retry-After` | Retrying a 401 cannot succeed and only turns a clear error slow | Retry everything |
| Key extraction filters **before** the network | A bare regex accepts `ISO-8601`, `COVID-19`, `UTF-8`, `CVE-2026-1234` | Validate by lookup |
| Generation is an explicit command | Removes intent classification entirely: no path from "a key appeared" to "tests created" | NLP intent detection |
| Regeneration refuses by default | Protects hand-made refinements; `--force` is the only route | Overwrite silently |
| Staleness compares the ticket **digest**, not `updated` | Jira bumps `updated` for labels and sprints that never touch the text | Timestamp comparison |
| Approval records: one committed file per decision | Makes append-only *structural* — no code path rewrites a record | One file per ticket |
| Records match designs by **digest**, not path | A rename keeps its approval; different content at the old path does not inherit it | Path matching |
| Approver identity from `git config user.email`; refuse if unset | A record naming nobody answers none of the questions it exists for | OS username, env var |
| Author from 003's provenance, **not** git blame | Blame reports who committed, which may be a merge or reformat — plausible-looking and wrong | git blame |
| Pipeline **fails** on an unapproved script | A silently skipped test is indistinguishable from coverage that never existed | Skip and warn |
| `verify` is the same command locally and in CI | Makes a pipeline failure reproducible before pushing | Separate CI script |
| Secrets: `.env` + `.gitignore` only, no scanning tooling | Accepted for a small team; protects the *file*, not an inline-pasted token | Pre-commit scanner |
| Report generated in-project, Allure CLI optional | Keeps the one-prerequisite property; every machine gets a readable report | Install Allure CLI |
| macOS unsupported | SC-002 demands verified success per platform; an unverified platform cannot be claimed | "Expected to work" |

---

## Decisions reversed during the project

Recorded so the reasoning is not re-derived:

| Was | Now | Why |
|---|---|---|
| Jira writes in scope (read + comment + transition) | **Read-only** | Nothing needed them; 8 safeguards existed to contain a risk nobody had asked to take |
| SC-011: "exactly two prerequisites" | "exactly one" | `uv` provisions the interpreter — the number predated the mechanism |
| Approval digest over the whole file | Design portion only | Deadlocked the workflow (finding X1) |
| `test_names()` as a public function name | `covered_test_names()` | pytest collected it as a test wherever it was imported |
| `NUMBER_TOO_LONG` unreachable (`\d{1,6}`) | Pattern widened to `\d{1,12}` | The rule was dead code; over-long numbers failed silently instead of being reported |
