"""The assertion digest: what stops a repair changing what a test proves.

FR-039 forbids a repair altering, weakening or removing an assertion. Without
a mechanism that is just an instruction handed to the component most able to
breach it, so the digest makes it enforceable: whitespace, comments and
surrounding code may change freely; the asserted conditions may not.

Not to be confused with feature 004's **design digest**, which covers test
names, markers and docstrings for a different purpose.

**Known limitation, stated rather than hidden**: this compares assertion
*text*. A repair could change what an assertion effectively checks by altering
a value it depends on without touching the assert line::

    expected = 5      ->   expected = 0
    assert total == expected      # digest unchanged

That narrows the hole substantially - the obvious route to a green assertion,
editing the assertion, is closed - but does not close it. The remaining risk is
carried by bounded attempts, the logged digests either side, and the report
disclosing every repaired pass.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

_WS = re.compile(r"\s+")

#: Calls treated as assertions even though they are not ``assert`` statements.
_ASSERTION_CALLS = {"expect", "raises", "assert_that", "approx"}


def assertion_texts(source: str, test_name: str | None = None) -> tuple[str, ...]:
    """Normalised source of every assertion, in order.

    When ``test_name`` is given, only that function is examined - a repair to
    one test must not be blocked by an unrelated one.
    """
    tree = ast.parse(source)
    nodes: list[ast.AST] = []

    if test_name is None:
        nodes = [tree]
    else:
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == test_name
            ):
                nodes.append(node)
        if not nodes:
            return ()

    found: list[str] = []
    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Assert):
                found.append(_norm(ast.unparse(node)))
            elif isinstance(node, ast.Expr) and _roots_at_assertion(node.value):
                # The WHOLE chained expression, not the inner call. For
                # `expect(x).to_have_text("hello")` the inner `expect(x)` is
                # identical however the matcher is weakened, so capturing it
                # alone would let `to_have_text` become `to_be_visible`
                # without changing the digest.
                found.append(_norm(ast.unparse(node.value)))
    return tuple(found)


def assertion_digest(source: str, test_name: str | None = None) -> str:
    """Digest every assertion in the source (or in one test)."""
    return hashlib.sha256(
        "\x00".join(assertion_texts(source, test_name)).encode("utf-8")
    ).hexdigest()[:16]


def assertion_digest_for(path: Path | str, test_name: str | None = None) -> str:
    return assertion_digest(Path(path).read_text(encoding="utf-8"), test_name)


def repair_changed_assertions(before: str, after: str, test_name: str | None = None) -> bool:
    """True when a repair altered what the test asserts - so refuse it."""
    return assertion_digest(before, test_name) != assertion_digest(after, test_name)


def _roots_at_assertion(node: ast.expr) -> bool:
    """True when an expression statement is an assertion in disguise.

    Covers both ``expect(locator).to_have_text(...)`` - whose base callee is
    ``expect`` - and ``self.assertEqual(...)`` style calls.
    """
    if not isinstance(node, ast.Call):
        return False

    # self.assertEqual(...) / obj.assert_something(...)
    if isinstance(node.func, ast.Attribute) and (
        node.func.attr in _ASSERTION_CALLS or node.func.attr.startswith("assert")
    ):
        return True

    # Descend the attribute/call chain to its base name.
    current: ast.expr = node
    while True:
        if isinstance(current, ast.Call):
            current = current.func
        elif isinstance(current, ast.Attribute):
            current = current.value
        else:
            break
    return isinstance(current, ast.Name) and current.id in _ASSERTION_CALLS


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip()
