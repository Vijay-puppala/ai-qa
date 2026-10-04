"""The single enforcement point (FR-006, FR-007, FR-009).

FR-009 requires that **no route** bypasses the gate - human or AI assistant,
any entry point. Features 003 and 005 each introduce an entry point, so the
check lives where both funnel through rather than duplicated at each call
site, where one would eventually be forgotten.

Feature 005's completion step calls :func:`require_approval`.
"""

from __future__ import annotations

from pathlib import Path

from ai_qa.approval.state import DesignStatus, State, approval_state


class ApprovalRequired(Exception):
    """Automation was attempted without a currently-applicable approval.

    Carries the status so a caller can distinguish PENDING from REJECTED from
    STALE - three states with three different remedies, and conflating them
    sends someone to fix the wrong thing (FR-007).
    """

    def __init__(self, status: DesignStatus) -> None:
        self.status = status
        super().__init__(status.refusal_reason())

    @property
    def state(self) -> State:
        return self.status.state


def require_approval(path: Path | str, *, records_dir: Path) -> DesignStatus:
    """Raise unless this design carries a currently-applicable approval.

    Returns the status on success so the caller can stamp the approving
    record's identifier onto the automation it writes (FR-010).
    """
    status = approval_state(path, records_dir=Path(records_dir))
    if status.blocks_automation:
        raise ApprovalRequired(status)
    return status


def approval_identifier(status: DesignStatus) -> str | None:
    """The record that authorised automation, for stamping (FR-010).

    Consumed by feature 005's FR-005.
    """
    if status.latest is None or status.state is not State.APPROVED:
        return None
    return f"{status.latest.ticket}/{status.latest.timestamp}-{status.latest.decision}"
