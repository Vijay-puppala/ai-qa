"""Repair eligibility: a pure function of the failure's exception type.

The platform may fix a test that **cannot run**. It may not make a failing
test **pass**. These two lists are what keep that line sharp, because the
easiest way to turn a red assertion green is to weaken it - which would turn
this platform into a way of hiding defects.

Keyed on exception type and nothing else: never the message, which is
version-dependent and partly application-controlled. SC-022 asserts a negative
("zero repair attempts on ineligible failures"), and a negative is only
verifiable if the decision is a function of its input.
"""

from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ESCALATE = "ESCALATE"


#: Mechanical, test-side faults (FR-036). None of these can encode a statement
#: about the application, which is what makes them safe to repair: there is no
#: product finding to erase.
ELIGIBLE_TYPES: frozenset[str] = frozenset(
    {
        "SyntaxError",
        "IndentationError",
        "TabError",
        "ImportError",
        "ModuleNotFoundError",
        "CollectError",
        "CollectionError",
        "FixtureLookupError",
        "FixtureLookupErrorRepr",
        "MarkerError",
        "UsageError",
        "TypeError",
        "AttributeError",
        "NameError",
    }
)

#: Named explicitly so the exclusion is visible rather than implied (FR-037).
#: ``TimeoutError`` and element-not-found are the commonest test-side faults in
#: browser automation, which is exactly why they are tempting - and they are
#: indistinguishable from a feature that was never built, so repairing one
#: would sometimes erase a genuine finding.
ESCALATE_TYPES: frozenset[str] = frozenset(
    {
        "AssertionError",
        "TimeoutError",
        "TimeoutException",
        "PlaywrightTimeoutError",
        "ElementNotFoundError",
        "ElementHandleError",
        "HTTPStatusError",
        "ConnectError",
        "Failed",
        "XFailed",
    }
)


def classify(exception_type: str | None) -> Verdict:
    """Decide whether a failure may be repaired automatically.

    **The default is ESCALATE, unconditionally** (FR-038). A failure mode
    introduced by a future dependency upgrade lands on the safe side without
    anyone remembering to classify it, and an unrecognised type is ambiguity -
    which resolves towards escalation, never towards editing the test.
    """
    if not exception_type:
        return Verdict.ESCALATE
    name = exception_type.rsplit(".", 1)[-1].strip()
    if name in ESCALATE_TYPES:
        return Verdict.ESCALATE
    if name in ELIGIBLE_TYPES:
        return Verdict.ELIGIBLE
    return Verdict.ESCALATE


def explain(exception_type: str | None) -> str:
    """Why a failure was escalated, for the operator and the report."""
    verdict = classify(exception_type)
    if verdict is Verdict.ELIGIBLE:
        return f"{exception_type} is a mechanical test-side fault and may be repaired."
    name = (exception_type or "<unknown>").rsplit(".", 1)[-1]
    if name in ESCALATE_TYPES:
        return (
            f"{name} is excluded from automated repair: it may be a statement "
            f"about the application, and repairing it could erase a real "
            f"finding. A human must judge this one."
        )
    return (
        f"{name} is not a recognised mechanical fault. Ambiguity resolves "
        f"towards escalation, never towards editing the test."
    )
