"""Who may record a decision (FR-022, FR-036, FR-037, research R3/R4).

Two deliberate fail-closed choices:

* **Identity undeterminable -> refuse.** A record naming nobody answers none of
  the questions a record exists to answer, and writing a placeholder would be
  worse because it looks like an audit trail.
* **Author unknown -> refuse** under the default policy. The policy cannot be
  checked, and a policy that silently passes when unverifiable is decorative.
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from ai_qa.generate.scaffold import read_provenance


class Verdict(str, Enum):
    ALLOWED = "ALLOWED"
    SELF_APPROVAL = "SELF_APPROVAL"
    AUTHOR_UNKNOWN = "AUTHOR_UNKNOWN"
    IDENTITY_UNKNOWN = "IDENTITY_UNKNOWN"


class PolicyCheck(NamedTuple):
    verdict: Verdict
    approver: str | None
    author: str | None

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOWED

    def message(self) -> str:
        if self.verdict is Verdict.ALLOWED:
            return ""
        if self.verdict is Verdict.IDENTITY_UNKNOWN:
            return (
                "Cannot determine who you are: git user.email is not set. "
                "Run 'git config user.email you@example.com'. Refusing to "
                "write a record that names nobody."
            )
        if self.verdict is Verdict.SELF_APPROVAL:
            return (
                f"{self.approver} authored this design, and the policy requires "
                f"a second person. Ask a colleague to review it, or set "
                f"APPROVAL_REQUIRE_SECOND_PERSON=false to permit self-approval "
                f"deliberately - the choice is recorded on the decision."
            )
        return (
            "This design records no author, so the author-may-not-approve "
            "policy cannot be checked. It was either hand-written or generated "
            "before provenance recorded an identity. Regenerate it, or set "
            "APPROVAL_REQUIRE_SECOND_PERSON=false deliberately."
        )


def approver_identity() -> str | None:
    """Who is recording the decision, from git config (research R3)."""
    try:
        out = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        return None
    return out.stdout.strip() or None


def design_author(path: Path | str) -> str | None:
    """The design's author, from feature 003's provenance (research R4).

    Deliberately **not** inferred from git blame: blame reports who committed
    the file, which for a generated file is often whoever ran generation but
    may equally be a merge or a reformatting commit. Plausible-looking and
    wrong is worse than absent.
    """
    author = read_provenance(Path(path)).get("generated-by-identity")
    if not author or author == "unknown":
        return None
    return author


def check(path: Path | str, *, require_second_person: bool) -> PolicyCheck:
    """Decide whether this person may record a decision on this design."""
    approver = approver_identity()
    author = design_author(path)

    if approver is None:
        return PolicyCheck(Verdict.IDENTITY_UNKNOWN, None, author)
    if not require_second_person:
        return PolicyCheck(Verdict.ALLOWED, approver, author)
    if author is None:
        return PolicyCheck(Verdict.AUTHOR_UNKNOWN, approver, None)
    if author == approver:
        return PolicyCheck(Verdict.SELF_APPROVAL, approver, author)
    return PolicyCheck(Verdict.ALLOWED, approver, author)
