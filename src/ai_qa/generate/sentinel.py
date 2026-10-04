"""The one marker that says a test is an unimplemented skeleton.

**Three features depend on this string.** Feature 003 writes it, feature 004
counts it to report partial implementation, feature 005 detects completion by
its absence. A literal repeated in three places drifts by one character and
silently breaks detection in two of them - with no error, because "no
skeletons found" and "nothing to detect" look identical.

So it lives here, alone, and is imported rather than retyped.
"""

from __future__ import annotations

#: Prefix of every generated skeleton's ``pytest.skip`` reason (FR-027).
SKELETON_SENTINEL = "ai-qa:unimplemented"


def skip_reason(detail: str = "body not implemented") -> str:
    """Build the skip reason for a generated skeleton."""
    return f"{SKELETON_SENTINEL}: {detail}"


def is_skeleton_reason(reason: str | None) -> bool:
    """True when a skip reason marks an unimplemented generated skeleton."""
    return bool(reason) and SKELETON_SENTINEL in str(reason)
