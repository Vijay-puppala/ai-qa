"""The four states, computed and never stored (FR-018, SC-003, research R5).

A stored state field is a cache with no invalidation signal: the moment
someone edits a docstring the stored value is wrong, and **a wrong state looks
exactly like a correct one**. Deriving it means there is nothing to keep in
sync - and ``STALE`` is precisely the case a cache would get wrong.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import NamedTuple

from ai_qa.approval.digest import design_digest_for, covered_test_names
from ai_qa.approval.records import DecisionRecord, history_for, read_all
from ai_qa.generate.listing import find_skeletons
from ai_qa.generate.scaffold import GENERATED_MARKER, read_provenance


class State(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    STALE = "STALE"
    REJECTED = "REJECTED"
    UNMANAGED = "UNMANAGED"


class Completion(str, Enum):
    UNIMPLEMENTED = "unimplemented"
    PARTIAL = "partial"
    COMPLETE = "complete"


class DesignStatus(NamedTuple):
    path: Path
    state: State
    digest: str
    completion: Completion
    latest: DecisionRecord | None
    ticket: str | None

    @property
    def blocks_automation(self) -> bool:
        """PENDING, STALE and REJECTED all refuse - for different reasons."""
        return self.state in {State.PENDING, State.STALE, State.REJECTED}

    def refusal_reason(self) -> str:
        if self.state is State.PENDING:
            return (
                f"{self.path} has not been reviewed. Run "
                f"'python -m ai_qa.approval review' and approve the design first."
            )
        if self.state is State.REJECTED:
            why = (self.latest.reason if self.latest else None) or "no reason recorded"
            return f"{self.path} was rejected: {why}"
        if self.state is State.STALE:
            return (
                f"{self.path} was approved, but the design has changed since - a "
                f"test name, marker or docstring was edited. Re-approve it."
            )
        return ""


def is_managed(path: Path) -> bool:
    """The gate applies to generated designs only (FR-029, research R8).

    Requiring approval for every hand-written test would block one somebody
    wrote in two minutes, which is the fastest route to the gate being
    switched off. Unmanaged files are reported, never blocked.
    """
    try:
        return GENERATED_MARKER in Path(path).read_text(encoding="utf-8")
    except OSError:  # pragma: no cover
        return False


def approval_state(path: Path | str, *, records_dir: Path) -> DesignStatus:
    """Current state of one design.

    Part of the public API, not just a CLI internal: feature 005's completion
    step needs this in-process (analysis finding U1).
    """
    path = Path(path)
    if not is_managed(path):
        return DesignStatus(path, State.UNMANAGED, "", Completion.COMPLETE, None, None)

    digest = design_digest_for(path)
    all_records, _ = read_all(Path(records_dir))
    matching = history_for(digest, all_records)

    # A decision recorded against *earlier* content still matters: an approval
    # whose digest no longer matches is STALE, not absent. Matched on the
    # recorded path for that case only - digest is the primary key.
    wanted = str(path).replace("\\", "/")
    by_path = sorted(
        (r for r in all_records if r.design_path == wanted), key=lambda r: r.timestamp
    )

    latest = matching[-1] if matching else (by_path[-1] if by_path else None)

    if latest is None:
        state = State.PENDING
    elif latest.decision == "rejected":
        state = State.REJECTED
    elif latest.design_digest == digest:
        state = State.APPROVED
    else:
        state = State.STALE

    ticket = (latest.ticket if latest else None) or read_provenance(path).get("ticket")
    return DesignStatus(path, state, digest, _completion(path), latest, ticket)


def _completion(path: Path) -> Completion:
    """Approval is not the same as automation existing (FR-030, FR-031)."""
    total = len(covered_test_names(path.read_text(encoding="utf-8")))
    if total == 0:
        return Completion.COMPLETE
    remaining = len([s for s in find_skeletons(path.parent) if s.path == path])
    if remaining == 0:
        return Completion.COMPLETE
    if remaining >= total:
        return Completion.UNIMPLEMENTED
    return Completion.PARTIAL


def scan(root: Path | str = "tests", *, records_dir: Path) -> list[DesignStatus]:
    """State of every test file in the repository (SC-013)."""
    return [
        approval_state(p, records_dir=Path(records_dir))
        for p in sorted(Path(root).rglob("test_*.py"))
    ]
