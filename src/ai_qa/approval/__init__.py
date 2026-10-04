"""The approval gate between a generated test design and its automation.

``approval_state`` is part of the public surface, not just a CLI internal:
feature 005's completion step needs it in-process.
"""

from ai_qa.approval.digest import design_digest, design_digest_for, covered_test_names
from ai_qa.approval.gate import ApprovalRequired, approval_identifier, require_approval
from ai_qa.approval.policy import PolicyCheck, Verdict, check as check_policy
from ai_qa.approval.records import DecisionRecord
from ai_qa.approval.state import Completion, DesignStatus, State, approval_state, scan

__all__ = [
    "ApprovalRequired",
    "Completion",
    "DecisionRecord",
    "DesignStatus",
    "PolicyCheck",
    "State",
    "Verdict",
    "approval_identifier",
    "approval_state",
    "check_policy",
    "design_digest",
    "design_digest_for",
    "require_approval",
    "scan",
    "test_names",
]
