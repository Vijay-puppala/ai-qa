"""Read-side projection of a run: result data in, readable report out.

No authority to change anything - that lives in ``ai_qa.automation``.
"""

from ai_qa.report.read import TestResult, read_results
from ai_qa.report.render import render, write
from ai_qa.report.summary import UNATTRIBUTED, RunSummary, build

__all__ = [
    "RunSummary",
    "TestResult",
    "UNATTRIBUTED",
    "build",
    "read_results",
    "render",
    "write",
]
