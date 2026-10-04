"""Run summary, with a mandatory scope (FR-035, SC-021, FR-011).

``scope`` is **not optional**. SC-021 requires every report to state what the
run covered, and the only way to guarantee that is to make the field
impossible to omit - a ticket-scoped green must never read as suite-wide
confidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import NamedTuple

from ai_qa.report.read import TestResult

UNATTRIBUTED = "Unattributed"


class RunSummary(NamedTuple):
    scope: str  # required - see module docstring
    results: tuple[TestResult, ...]
    counts: dict[str, int]
    by_ticket: dict[str, tuple[TestResult, ...]]
    repaired: frozenset[str]

    @property
    def collected(self) -> int:
        return len(self.results)

    @property
    def empty(self) -> bool:
        """A run that tested nothing is a failure, not a pass (FR-011)."""
        return self.collected == 0

    @property
    def failed(self) -> int:
        return self.counts.get("failed", 0) + self.counts.get("broken", 0)

    @property
    def started(self) -> int:
        return min((r.start for r in self.results), default=0)

    @property
    def finished(self) -> int:
        return max((r.stop for r in self.results), default=0)


def build(
    results: list[TestResult], *, scope: str, repaired: set[str] | None = None
) -> RunSummary:
    """Group results by ticket, with unattributed ones kept visible.

    The ``Unattributed`` group is deliberately shown rather than hidden: a test
    that should carry a ticket but does not is a traceability gap, and a large
    group here is the first symptom of the conftest ticket hook being broken.
    """
    grouped: dict[str, list[TestResult]] = defaultdict(list)
    for result in results:
        grouped[result.ticket or UNATTRIBUTED].append(result)

    ordered = {
        key: tuple(grouped[key])
        for key in sorted(grouped, key=lambda k: (k == UNATTRIBUTED, k))
    }
    return RunSummary(
        scope=scope,
        results=tuple(results),
        counts=dict(Counter(r.status for r in results)),
        by_ticket=ordered,
        repaired=frozenset(repaired or ()),
    )
