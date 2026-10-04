"""Extracting a ticket key from ordinary language (FR-001 to FR-008).

The obvious implementation of FR-002 is a regex, and the obvious regex matches
``COVID-19``, ``ISO-8601``, ``UTF-8`` and ``CVE-2026-1234``. FR-005 forbids
those producing a lookup and SC-005 measures it at zero, so three structural
filters run **locally, before any network call** - a false positive must never
cost a request, and must never resolve to something unintended.

Pure and network-free, which is what makes SC-004 and SC-005 testable at all.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import NamedTuple

#: Project code, separator, issue number. Case-insensitive; normalised later.
#:
#: The number is matched generously (up to 12 digits) so an over-long one is
#: *reported* as rejected rather than silently failing to match. With a
#: ``\d{1,6}`` pattern the NUMBER_TOO_LONG rule was unreachable dead code, and
#: an engineer who typed a wrong number got no explanation at all.
_CANDIDATE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]{1,9})-(\d{1,12})\b")

#: Jira URL shapes, checked first: a URL contains other digit-hyphen fragments
#: and the general pattern alone can select the wrong one.
_URL_BROWSE = re.compile(r"/browse/([A-Za-z][A-Za-z0-9_]{1,9}-\d{1,6})\b")
_URL_SELECTED = re.compile(r"[?&]selectedIssue=([A-Za-z][A-Za-z0-9_]{1,9}-\d{1,6})\b")

#: Standards and identifier prefixes that are never project keys.
DENYLISTED_PREFIXES = frozenset(
    {
        "ISO", "UTF", "RFC", "ANSI", "IEEE", "SHA", "AES", "COVID",
        "EN", "BS", "SI", "ASCII", "HTTP", "IPV", "MD", "CVE",
    }
)


class Reason(str, Enum):
    DENYLISTED_PREFIX = "DENYLISTED_PREFIX"
    YEAR_LIKE = "YEAR_LIKE"
    NUMBER_TOO_LONG = "NUMBER_TOO_LONG"


class Outcome(str, Enum):
    ONE = "ONE"
    NONE = "NONE"
    MANY = "MANY"


class Rejection(NamedTuple):
    candidate: str
    reason: Reason


class ExtractionResult(NamedTuple):
    keys: tuple[str, ...]
    rejected: tuple[Rejection, ...]
    outcome: Outcome


def extract(text: str) -> ExtractionResult:
    """Find every ticket key in free-form text.

    Rejections are **returned, not discarded**: an engineer whose real key was
    filtered needs to see which rule fired, or the tool is undiagnosable.
    """
    if not text:
        return ExtractionResult((), (), Outcome.NONE)

    accepted: list[str] = []
    rejected: list[Rejection] = []

    # URL forms first - they are unambiguous where they match.
    for pattern in (_URL_BROWSE, _URL_SELECTED):
        for raw in pattern.findall(text):
            key = raw.upper()
            if key not in accepted:
                accepted.append(key)

    for prefix, number in _CANDIDATE.findall(text):
        key = f"{prefix.upper()}-{number}"
        if key in accepted:
            continue
        reason = _reject(prefix.upper(), number)
        if reason is not None:
            if not any(r.candidate == key for r in rejected):
                rejected.append(Rejection(key, reason))
            continue
        accepted.append(key)

    outcome = (
        Outcome.NONE if not accepted else Outcome.ONE if len(accepted) == 1 else Outcome.MANY
    )
    return ExtractionResult(tuple(accepted), tuple(rejected), outcome)


def _reject(prefix: str, number: str) -> Reason | None:
    if prefix in DENYLISTED_PREFIXES:
        return Reason.DENYLISTED_PREFIX
    if len(number) == 4 and 1900 <= int(number) <= 2199:
        return Reason.YEAR_LIKE
    if len(number) > 6:
        return Reason.NUMBER_TOO_LONG
    return None


def expected_form() -> str:
    """What to tell someone whose input had no key (FR-006)."""
    return (
        "Expected a ticket key like TC-345 - a project code, a hyphen and an "
        "issue number. A full Jira URL works too."
    )
