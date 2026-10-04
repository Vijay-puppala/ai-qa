"""Decision records: committed files, one per decision (FR-012, FR-013, R1).

One file per decision makes the append-only requirement **structural rather
than enforced** - a later decision is a new filename, so there is no code path
that rewrites a record and the guarantee cannot regress.
"""

from __future__ import annotations

import datetime as _dt
import json
import subprocess
from pathlib import Path
from typing import Any, Literal, NamedTuple

from ai_qa.jira.errors import redact

Decision = Literal["approved", "rejected"]

REQUIRED_FIELDS = (
    "decision",
    "ticket",
    "design_path",
    "design_digest",
    "approver",
    "policy_require_second_person",
    "timestamp",
    "test_names",
)


class DecisionRecord(NamedTuple):
    decision: Decision
    ticket: str
    design_path: str
    design_digest: str
    approver: str
    author: str | None
    policy_require_second_person: bool
    timestamp: str
    test_names: tuple[str, ...]
    reason: str | None = None
    source: Path | None = None

    def to_json(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "decision": self.decision,
            "ticket": self.ticket,
            "design_path": self.design_path,
            "design_digest": self.design_digest,
            "approver": self.approver,
            "author": self.author,
            "policy_require_second_person": self.policy_require_second_person,
            "timestamp": self.timestamp,
            "test_names": list(self.test_names),
        }
        if self.reason is not None:
            # A rejection reason is free text typed by a human - exactly where
            # a token gets pasted by accident, and unlike a log line this file
            # is committed (FR-034).
            body["reason"] = redact(self.reason)
        return body


class Integrity(NamedTuple):
    orphaned: tuple[Path, ...]
    malformed: tuple[Path, ...]
    deleted: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not (self.orphaned or self.malformed or self.deleted)


def now_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write(record: DecisionRecord, *, root: Path) -> Path:
    """Write one decision as its own file. Never overwrites an earlier one."""
    directory = root / record.ticket
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record.timestamp}-{record.decision}.json"
    suffix = 1
    while path.exists():  # two decisions in the same second must not collide
        path = directory / f"{record.timestamp}-{record.decision}-{suffix}.json"
        suffix += 1
    path.write_text(json.dumps(record.to_json(), indent=2) + "\n", encoding="utf-8")
    return path


def read_all(root: Path) -> tuple[list[DecisionRecord], list[Path]]:
    """Every record, plus the paths that could not be parsed (FR-015)."""
    records: list[DecisionRecord] = []
    malformed: list[Path] = []
    if not Path(root).exists():
        return records, malformed
    for path in sorted(Path(root).rglob("*.json")):
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            malformed.append(path)
            continue
        if not isinstance(body, dict) or any(f not in body for f in REQUIRED_FIELDS):
            malformed.append(path)
            continue
        records.append(
            DecisionRecord(
                decision=body["decision"],
                ticket=body["ticket"],
                design_path=body["design_path"],
                design_digest=body["design_digest"],
                approver=body["approver"],
                author=body.get("author"),
                policy_require_second_person=bool(body["policy_require_second_person"]),
                timestamp=body["timestamp"],
                test_names=tuple(body["test_names"]),
                reason=body.get("reason"),
                source=path,
            )
        )
    return records, malformed


def history_for(digest: str, records: list[DecisionRecord]) -> list[DecisionRecord]:
    """Decisions covering a design, oldest first. Matched by digest, not path.

    Digest-matching is what makes FR-021 work: a moved or renamed design keeps
    its approval, and different content at the old path does not inherit it.
    """
    return sorted((r for r in records if r.design_digest == digest), key=lambda r: r.timestamp)


def deleted_records(root: Path) -> tuple[str, ...]:
    """Records present in git history but absent from disk (FR-015).

    A removed file leaves nothing on disk, so history is the only way deletion
    is detectable at all.
    """
    try:
        out = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=D",
                "--name-only",
                "--pretty=format:",
                "--",
                str(root),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        return ()
    gone = {line.strip() for line in out.stdout.splitlines() if line.strip().endswith(".json")}
    return tuple(sorted(p for p in gone if not Path(p).exists()))


def check_integrity(root: Path, known_digests: set[str]) -> Integrity:
    """Orphaned, malformed and deleted records - reported, not enforced.

    The gate is **cooperative**: anyone with repository write access can author
    a convincing record. These checks catch mistakes, accidents and drift, not
    an adversary. Closing that would need signing and an external authority,
    which the spec puts out of scope.
    """
    records, malformed = read_all(root)
    orphaned = tuple(r.source for r in records if r.design_digest not in known_digests and r.source)
    return Integrity(
        orphaned=orphaned, malformed=tuple(malformed), deleted=deleted_records(Path(root))
    )
