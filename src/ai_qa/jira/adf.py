"""Atlassian Document Format to plain text (research R2).

On Jira Cloud REST API v3 an issue ``description`` is **ADF JSON**, not a
string. Code written against the obvious ``fields.description`` string shape
fails on the first call - which is why this module exists at all.

``from_text`` was deliberately **not** implemented: it was only needed for
comment bodies, and write operations were deferred out of feature 002 on
2026-10-04. Adding it back is one function when a feature needs to write.
"""

from __future__ import annotations

from typing import Any

#: Nodes whose children are joined with no separator (inline context).
_INLINE = {"paragraph", "heading", "listItem", "blockquote", "tableCell", "tableHeader"}

#: Nodes rendered as their own block, separated by a blank line.
_BLOCK_BREAK = {"paragraph", "heading", "codeBlock", "blockquote", "rule", "panel"}


def to_text(adf: Any) -> str:
    """Flatten an ADF document to readable plain text.

    Any **unrecognised node degrades to the concatenated text of its
    children** and never raises, so a node type Atlassian adds later loses
    formatting but never loses content. A plain string passes through
    unchanged, so a v2-shaped response or an already-flattened value is safe.
    """
    if adf is None:
        return ""
    if isinstance(adf, str):
        return adf
    if not isinstance(adf, dict):
        return ""

    parts: list[str] = []
    _walk(adf, parts, depth=0, ordered_index=None)
    text = "".join(parts)
    # Collapse runs of three or more newlines down to a paragraph break.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def _walk(node: Any, out: list[str], *, depth: int, ordered_index: int | None) -> None:
    if not isinstance(node, dict):
        return

    kind = node.get("type")

    if kind == "text":
        out.append(str(node.get("text", "")))
        return
    if kind == "hardBreak":
        out.append("\n")
        return
    if kind == "rule":
        out.append("\n---\n")
        return
    if kind in {"emoji", "status"}:
        attrs = node.get("attrs") or {}
        out.append(str(attrs.get("text") or attrs.get("shortName") or ""))
        return
    if kind == "mention":
        attrs = node.get("attrs") or {}
        out.append(str(attrs.get("text") or ""))
        return

    children = node.get("content") or []

    if kind == "codeBlock":
        inner: list[str] = []
        for child in children:
            _walk(child, inner, depth=depth, ordered_index=None)
        out.append("\n" + "".join(inner).rstrip() + "\n")
        return

    if kind in {"bulletList", "orderedList"}:
        for i, child in enumerate(children, start=1):
            marker = f"{i}. " if kind == "orderedList" else "- "
            out.append("\n" + ("  " * depth) + marker)
            _walk(child, out, depth=depth + 1, ordered_index=i)
        out.append("\n")
        return

    if kind == "heading":
        level = int((node.get("attrs") or {}).get("level", 1))
        out.append("\n" + "#" * max(1, min(level, 6)) + " ")
        for child in children:
            _walk(child, out, depth=depth, ordered_index=None)
        out.append("\n")
        return

    # paragraph, blockquote, doc, listItem, tables, and anything unrecognised:
    # emit children, adding a block break where the node is a block.
    for child in children:
        _walk(child, out, depth=depth, ordered_index=ordered_index)
    if kind in _BLOCK_BREAK:
        out.append("\n\n")
    elif kind in _INLINE:
        out.append("\n")
