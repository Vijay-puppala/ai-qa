"""Completion, repair and the boundary between them (feature 005).

The platform may fix a test that cannot run. It may not make a failing test
pass. ``classify`` and ``digest`` are where that line is enforced, and both
are pure so the negative criteria over them are testable.
"""

from ai_qa.automation.classify import (
    ELIGIBLE_TYPES,
    ESCALATE_TYPES,
    Verdict,
    classify,
    explain,
)
from ai_qa.automation.digest import (
    assertion_digest,
    assertion_digest_for,
    assertion_texts,
    repair_changed_assertions,
)

__all__ = [
    "ELIGIBLE_TYPES",
    "ESCALATE_TYPES",
    "Verdict",
    "assertion_digest",
    "assertion_digest_for",
    "assertion_texts",
    "classify",
    "explain",
    "repair_changed_assertions",
]
