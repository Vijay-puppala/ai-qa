"""The design digest (FR-017 as corrected, research R2).

**This is the X1 fix made concrete, and it is the most important function in
the feature.** A digest over the whole file would void every approval the
instant its automation was written - and writing that automation is the very
act the approval authorises. The gate would refuse the work it had just
permitted, deadlocking features 003, 004 and 005 together.

So the digest covers the *design portion* only: test names, markers and
docstrings. Bodies are excluded.

Not to be confused with feature 005's **assertion digest**, which covers
assertion statements for a different purpose.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import NamedTuple

_WS = re.compile(r"\s+")


class DesignItem(NamedTuple):
    name: str
    markers: tuple[str, ...]
    docstring: str


def design_items(source: str) -> tuple[DesignItem, ...]:
    """Extract the reviewable design from a test module's source."""
    tree = ast.parse(source)
    module_marks = _module_marks(tree)
    items: list[DesignItem] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            marks = tuple(sorted(set(module_marks) | set(_decorator_marks(node))))
            items.append(DesignItem(node.name, marks, _norm(ast.get_docstring(node) or "")))
    return tuple(items)


def design_digest(source: str) -> str:
    """Digest the design portion. Formatting and bodies do not affect it."""
    parts: list[str] = []
    for item in design_items(source):
        parts.append(item.name)
        parts.extend(item.markers)
        parts.append(item.docstring)
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def design_digest_for(path: Path | str) -> str:
    return design_digest(Path(path).read_text(encoding="utf-8"))


def covered_test_names(source: str) -> tuple[str, ...]:
    """The test names covered, so "what was approved?" needs no inference."""
    return tuple(item.name for item in design_items(source))


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _module_marks(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            return _marks_from(node.value)
    return []


def _decorator_marks(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    marks: list[str] = []
    for dec in func.decorator_list:
        marks.extend(_marks_from(dec))
    return marks


def _marks_from(node: ast.expr) -> list[str]:
    candidates = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
    marks: list[str] = []
    for item in candidates:
        if isinstance(item, ast.Call):
            name = _mark_name(item.func)
            args = ",".join(
                str(a.value) for a in item.args if isinstance(a, ast.Constant)
            )
            if name:
                marks.append(f"{name}({args})" if args else name)
        else:
            name = _mark_name(item)
            if name:
                marks.append(name)
    return marks


def _mark_name(node: ast.expr) -> str | None:
    """``pytest.mark.ui`` -> ``ui``; ``pytest.mark.ticket`` -> ``ticket``."""
    if isinstance(node, ast.Attribute):
        return node.attr
    return None
