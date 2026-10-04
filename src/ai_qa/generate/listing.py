"""Finding unimplemented skeletons without running anything (FR-028, R6).

Static AST scan, not a test run: skips are evaluated at run time, so
``--collect-only`` would find nothing, and a run-derived listing would be only
as current as the last run and would need the application reachable. The scan
answers from the repository alone - which is what makes it usable by a
pipeline, and by features 004 and 005.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

from ai_qa.generate.sentinel import SKELETON_SENTINEL


class Skeleton(NamedTuple):
    path: Path
    test_name: str
    ticket: str | None


def find_skeletons(root: Path | str = "tests") -> list[Skeleton]:
    """Every unimplemented skeleton under ``root``, with its source ticket."""
    found: list[Skeleton] = []
    for path in sorted(Path(root).rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            # A broken file is reported by the collectability check, not here.
            continue
        module_ticket = _module_ticket(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_skeleton(node):
                found.append(
                    Skeleton(path, node.name, _function_ticket(node) or module_ticket)
                )
    return found


def _is_skeleton(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if not _is_pytest_skip(node.func):
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            if SKELETON_SENTINEL in _literal_text(arg):
                return True
    return False


def _is_pytest_skip(func: ast.expr) -> bool:
    return isinstance(func, ast.Attribute) and func.attr == "skip"


def _literal_text(node: ast.expr) -> str:
    """Text of a string literal or an f-string, including the sentinel name.

    A skeleton body is written as ``pytest.skip(skip_reason(...))`` or an
    f-string interpolating ``SKELETON_SENTINEL``, so both shapes must match.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append(_name_of(value.value))
        return "".join(parts)
    if isinstance(node, ast.Call):
        # skip_reason("...") - the helper always embeds the sentinel
        if _name_of(node.func).endswith("skip_reason"):
            return SKELETON_SENTINEL
    return _name_of(node)


def _name_of(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return SKELETON_SENTINEL if node.id == "SKELETON_SENTINEL" else node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _module_ticket(tree: ast.Module) -> str | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
            continue
        return _ticket_from_marks(node.value)
    return None


def _function_ticket(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for dec in func.decorator_list:
        ticket = _ticket_from_marks(dec)
        if ticket:
            return ticket
    return None


def _ticket_from_marks(node: ast.expr) -> str | None:
    candidates = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
    for item in candidates:
        if (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr == "ticket"
            and item.args
            and isinstance(item.args[0], ast.Constant)
        ):
            return str(item.args[0].value)
    return None
