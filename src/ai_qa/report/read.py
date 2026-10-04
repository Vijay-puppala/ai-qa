"""Project Allure result data into a reportable shape (FR-014, FR-016).

The source schema was read off the installed ``allure-pytest`` rather than
assumed. Verified keys: ``description, fullName, historyId, labels, name,
parameters, start, status, stop, testCaseId, titlePath, uuid`` - and
``statusDetails`` with ``message`` and ``trace`` on a failure, which is why
failure evidence needs no additional capture mechanism.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, NamedTuple

_UNSAFE = re.compile(r"[^A-Za-z0-9]+")


class TestResult(NamedTuple):
    uuid: str
    name: str
    full_name: str
    status: str
    start: int
    stop: int
    ticket: str | None
    tags: tuple[str, ...]
    suite: str | None
    failure_message: str | None
    failure_trace: str | None
    approval: str | None

    @property
    def duration_ms(self) -> int:
        return max(0, self.stop - self.start)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def evidence_dir(self, artifacts_root: Path) -> Path:
        """Where pytest-playwright puts this test's evidence (FR-034)."""
        return Path(artifacts_root) / _UNSAFE.sub("-", self.full_name).strip("-")


def _label(labels: list[dict[str, Any]], name: str) -> str | None:
    for item in labels:
        if item.get("name") == name:
            value = item.get("value")
            return str(value) if value is not None else None
    return None


def read_results(results_dir: Path | str) -> list[TestResult]:
    """Every test result in a run's output directory."""
    out: list[TestResult] = []
    root = Path(results_dir)
    if not root.exists():
        return out
    for path in sorted(root.glob("*result.json")):
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(body, dict) or "status" not in body:
            continue
        labels = body.get("labels") or []
        details = body.get("statusDetails") or {}
        out.append(
            TestResult(
                uuid=str(body.get("uuid", "")),
                name=str(body.get("name", "")),
                full_name=str(body.get("fullName") or body.get("name") or ""),
                status=str(body["status"]),
                start=int(body.get("start") or 0),
                stop=int(body.get("stop") or 0),
                # Present only because of the conftest hook - a marker with an
                # argument produces no label on its own.
                ticket=_label(labels, "ticket"),
                tags=tuple(
                    str(item.get("value"))
                    for item in labels
                    if item.get("name") == "tag" and item.get("value")
                ),
                suite=_label(labels, "suite"),
                failure_message=details.get("message"),
                failure_trace=details.get("trace"),
                approval=_label(labels, "approval"),
            )
        )
    return out
