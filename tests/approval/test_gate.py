"""States, the gate, the policy and partial reporting.

SC-002 ("zero proceed"), SC-003 ("100% distinguishable") and SC-018 ("zero
self-approvals accepted") are all negative or exhaustive claims, which is why
the decisions they rest on are pure functions.
"""

from __future__ import annotations

import pytest

from ai_qa.approval import records
from ai_qa.approval.digest import design_digest_for, covered_test_names
from ai_qa.approval.gate import ApprovalRequired, approval_identifier, require_approval
from ai_qa.approval.policy import Verdict, check
from ai_qa.approval.state import Completion, State, approval_state

from approval_fixtures import implement_one


def _record(design, records_dir, decision="approved", *, digest=None, reason=None, author="author@example.com"):
    rec = records.DecisionRecord(
        decision=decision,
        ticket="TC-345",
        design_path=str(design).replace("\\", "/"),
        design_digest=digest or design_digest_for(design),
        approver="reviewer@example.com",
        author=author,
        policy_require_second_person=True,
        timestamp=records.now_stamp(),
        test_names=covered_test_names(design.read_text(encoding="utf-8")),
        reason=reason,
    )
    return records.write(rec, root=records_dir)


# ------------------------------------------------------------------ the states


def test_a_fresh_design_is_pending(design, records_dir) -> None:
    assert approval_state(design, records_dir=records_dir).state is State.PENDING


def test_an_approved_design_is_approved(design, records_dir) -> None:
    _record(design, records_dir)
    assert approval_state(design, records_dir=records_dir).state is State.APPROVED


def test_editing_the_design_after_approval_makes_it_stale(design, records_dir) -> None:
    """The state a cached field would get wrong."""
    _record(design, records_dir)
    source = design.read_text(encoding="utf-8")
    design.write_text(source.replace("shows the user why", "shows the reason"), encoding="utf-8")

    assert approval_state(design, records_dir=records_dir).state is State.STALE


def test_a_rejected_design_is_rejected(design, records_dir) -> None:
    _record(design, records_dir, "rejected", reason="Missing the mid-session case")
    status = approval_state(design, records_dir=records_dir)

    assert status.state is State.REJECTED
    assert "mid-session" in status.refusal_reason()


def test_pending_and_stale_are_never_conflated(design, records_dir) -> None:
    """Never reviewed and reviewed-then-changed need different remedies."""
    pending = approval_state(design, records_dir=records_dir)
    _record(design, records_dir, digest="a-digest-from-earlier-content")
    stale = approval_state(design, records_dir=records_dir)

    assert pending.state is State.PENDING
    assert stale.state is State.STALE
    assert pending.refusal_reason() != stale.refusal_reason()


def test_a_handwritten_test_is_unmanaged_not_blocked(handwritten, records_dir) -> None:
    """FR-029: requiring approval for every test is how a gate gets disabled."""
    status = approval_state(handwritten, records_dir=records_dir)

    assert status.state is State.UNMANAGED
    assert not status.blocks_automation


# -------------------------------------------------------------------- the gate


@pytest.mark.parametrize("decision", ["pending", "rejected", "stale"])
def test_every_non_approved_state_refuses_automation(design, records_dir, decision) -> None:
    """SC-002: 100% refused, zero proceed."""
    if decision == "rejected":
        _record(design, records_dir, "rejected", reason="no")
    elif decision == "stale":
        _record(design, records_dir, digest="older-content-digest")

    with pytest.raises(ApprovalRequired) as caught:
        require_approval(design, records_dir=records_dir)

    assert caught.value.state is not State.APPROVED
    assert str(caught.value)


def test_an_approved_design_proceeds_and_yields_an_identifier(design, records_dir) -> None:
    _record(design, records_dir)
    status = require_approval(design, records_dir=records_dir)

    assert status.state is State.APPROVED
    assert approval_identifier(status), "nothing to stamp onto the automation (FR-010)"


def test_implementing_after_approval_still_passes_the_gate(design, records_dir) -> None:
    """The X1 property, seen through the gate rather than the digest."""
    _record(design, records_dir)
    implement_one(design)

    assert require_approval(design, records_dir=records_dir).state is State.APPROVED


# ------------------------------------------------------------------ the policy


def test_the_author_may_not_approve_their_own_design(design, as_author) -> None:
    result = check(design, require_second_person=True)

    assert result.verdict is Verdict.SELF_APPROVAL
    assert not result.allowed
    assert "second person" in result.message()


def test_someone_else_may_approve(design, as_reviewer) -> None:
    assert check(design, require_second_person=True).allowed


def test_unknown_author_fails_closed(handwritten, as_reviewer) -> None:
    """A policy that passes when it cannot be checked is decorative."""
    result = check(handwritten, require_second_person=True)

    assert result.verdict is Verdict.AUTHOR_UNKNOWN
    assert not result.allowed


def test_relaxing_the_policy_permits_self_approval(design, as_author) -> None:
    assert check(design, require_second_person=False).allowed


def test_no_identity_refuses_to_record(design, monkeypatch) -> None:
    """A record naming nobody answers none of the questions it exists for."""
    from ai_qa.approval import policy

    monkeypatch.setattr(policy, "approver_identity", lambda: None)
    result = check(design, require_second_person=True)

    assert result.verdict is Verdict.IDENTITY_UNKNOWN
    assert "git config user.email" in result.message()


# ------------------------------------------------- records, partial, integrity


def test_a_later_decision_never_erases_an_earlier_one(design, records_dir) -> None:
    """Append-only is structural: one file per decision."""
    _record(design, records_dir, "rejected", reason="first pass")
    _record(design, records_dir, "approved")

    found, malformed = records.read_all(records_dir)
    assert len(found) == 2, "a decision was overwritten"
    assert {r.decision for r in found} == {"approved", "rejected"}
    assert malformed == []


def test_the_policy_in_force_is_recorded(design, records_dir) -> None:
    """FR-036: without it, a past self-approval is uninterpretable."""
    _record(design, records_dir)
    found, _ = records.read_all(records_dir)

    assert found[0].policy_require_second_person is True


def test_a_rejection_reason_is_redacted(design, records_dir) -> None:
    """Free text typed by a human, in a committed file (FR-034)."""
    _record(design, records_dir, "rejected", reason="token Authorization: Bearer abc123xyz")
    found, _ = records.read_all(records_dir)

    assert "abc123xyz" not in (found[0].reason or "")


def test_partial_implementation_is_reported_as_partial(design, records_dir) -> None:
    """SC-016: zero reported as complete when only some tests exist."""
    _record(design, records_dir)
    assert approval_state(design, records_dir=records_dir).completion is Completion.UNIMPLEMENTED

    implement_one(design)

    assert approval_state(design, records_dir=records_dir).completion is Completion.PARTIAL


def test_a_malformed_record_is_detected_not_trusted(design, records_dir) -> None:
    """SC-008: never read as a valid approval nor as a clean absence."""
    (records_dir / "TC-345").mkdir(parents=True, exist_ok=True)
    (records_dir / "TC-345" / "broken.json").write_text("{not json", encoding="utf-8")

    found, malformed = records.read_all(records_dir)

    assert found == []
    assert len(malformed) == 1
    assert approval_state(design, records_dir=records_dir).state is State.PENDING


def test_an_orphaned_record_is_detected(design, records_dir) -> None:
    _record(design, records_dir, digest="matches-no-design-at-all")
    integrity = records.check_integrity(records_dir, {design_digest_for(design)})

    assert integrity.orphaned
    assert not integrity.clean


def test_a_renamed_design_keeps_its_approval(design, records_dir) -> None:
    """FR-021: matched by digest, not path."""
    _record(design, records_dir)
    moved = design.parent / "test_renamed_area.py"
    design.rename(moved)

    assert approval_state(moved, records_dir=records_dir).state is State.APPROVED
