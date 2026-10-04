"""Generation tooling entry point (FR-026, R11, R12).

Generation happens because **this command was run**, never because a key
appeared in some text. That is how the intent requirement is met with no
natural-language classification at all: there is no code path from "a key is
present" to "tests were created".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_qa.config import Settings
from ai_qa.generate import brief as brief_mod
from ai_qa.generate import scaffold
from ai_qa.generate.keys import Outcome, expected_form, extract
from ai_qa.generate.listing import find_skeletons
from ai_qa.jira import JiraClient, JiraError, JiraNotFoundError

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_NO_KEY = 3
EXIT_MANY_KEYS = 4
EXIT_NOT_FOUND = 5
EXIT_FILE_EXISTS = 6
EXIT_JIRA = 7


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m ai_qa.generate")
    sub = p.add_subparsers(dest="command", required=True)

    ex = sub.add_parser("extract", help="show which ticket key was found; generates nothing")
    ex.add_argument("text", nargs="+")

    gen = sub.add_parser("generate", help="produce a test skeleton for one ticket")
    gen.add_argument("text", nargs="+")
    gen.add_argument("--kind", choices=["ui", "api"], default="ui")
    gen.add_argument("--force", action="store_true", help="overwrite an existing file")

    sk = sub.add_parser("skeletons", help="list unimplemented generated skeletons")
    sk.add_argument("--root", default="tests")
    sk.add_argument("--check-stale", action="store_true", help="compare against the live ticket")

    return p


def _resolve_one(text: str) -> tuple[str | None, int]:
    result = extract(text)
    if result.outcome is Outcome.NONE:
        print("No ticket key found in that input.", file=sys.stderr)
        print(expected_form(), file=sys.stderr)
        for r in result.rejected:
            print(f"  rejected {r.candidate}: {r.reason.value}", file=sys.stderr)
        return None, EXIT_NO_KEY
    if result.outcome is Outcome.MANY:
        print(
            "Several ticket keys found: " + ", ".join(result.keys),
            file=sys.stderr,
        )
        print("Generate for one at a time - acting on one of several would "
              "look like success and leave the rest uncovered.", file=sys.stderr)
        return None, EXIT_MANY_KEYS
    return result.keys[0], EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    text = " ".join(getattr(args, "text", []) or [])

    if args.command == "extract":
        result = extract(text)
        for key in result.keys:
            print(key)
        for r in result.rejected:
            print(f"rejected {r.candidate}: {r.reason.value}", file=sys.stderr)
        if result.outcome is Outcome.NONE:
            print(expected_form(), file=sys.stderr)
            return EXIT_NO_KEY
        if result.outcome is Outcome.MANY:
            return EXIT_MANY_KEYS
        return EXIT_OK

    if args.command == "skeletons":
        skeletons = find_skeletons(args.root)
        for s in skeletons:
            print(f"{s.path}::{s.test_name}\t{s.ticket or '<no ticket>'}")
        print(f"\n{len(skeletons)} unimplemented skeleton(s)", file=sys.stderr)
        if args.check_stale:
            return _check_stale(skeletons)
        return EXIT_OK

    # generate
    key, code = _resolve_one(text)
    if key is None:
        return code

    try:
        settings = Settings.from_env()
        with JiraClient(settings) as client:
            issue = client.get_issue(key)
    except JiraNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_NOT_FOUND
    except JiraError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG if "not configured" in str(exc) else EXIT_JIRA
    except Exception as exc:  # configuration/validation
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    bf = brief_mod.build(issue)
    target = scaffold.target_path(bf, kind=args.kind)

    if target.exists() and not args.force:
        print(
            f"{target} already exists. Refusing to overwrite - pass --force if "
            "you intend to discard what is there.",
            file=sys.stderr,
        )
        return EXIT_FILE_EXISTS

    print(bf.render())

    target.parent.mkdir(parents=True, exist_ok=True)
    updated = str((issue.raw.get("fields") or {}).get("updated") or "")
    target.write_text(scaffold.render(bf, kind=args.kind, ticket_updated=updated), encoding="utf-8")
    print(f"Scaffolded {target}", file=sys.stderr)
    print("Now author the test functions below the delimiter, per CLAUDE.md.", file=sys.stderr)
    return EXIT_OK


def _check_stale(skeletons: list[object]) -> int:
    """Compare stored ticket digests against the live ticket (FR-020)."""
    paths = sorted({s.path for s in skeletons})  # type: ignore[attr-defined]
    try:
        settings = Settings.from_env()
        client = JiraClient(settings)
    except Exception as exc:
        print(f"Cannot check staleness: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    stale = 0
    with client:
        for path in paths:
            fields = scaffold.read_provenance(Path(path))
            key, stored = fields.get("ticket"), fields.get("ticket-digest")
            if not key or not stored:
                continue
            current = brief_mod.content_digest(client.get_issue(key).text_content())
            if current != stored:
                stale += 1
                print(f"STALE {path}  ticket {key} changed since generation")
    print(f"\n{stale} stale file(s)", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
