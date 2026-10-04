"""Jira tooling entry point (FR-004, FR-019, research R12).

``argparse`` from the standard library: a CLI framework would be a new
dependency, which the floor forbids. Read-only, like the client.
"""

from __future__ import annotations

import argparse
import sys

from ai_qa.config import Settings
from ai_qa.jira import (
    JiraAuthError,
    JiraClient,
    JiraConfigError,
    JiraForbiddenError,
    JiraNotFoundError,
    JiraQueryError,
    JiraRateLimitError,
    JiraUnavailableError,
)

#: Exit codes are a contract - a script reacts to the cause, not the message.
#: Code 5 is deliberately unused: it meant "write refused locally" before
#: writes were deferred, and reserving it means a script written against the
#: earlier contract cannot silently misread a different failure.
EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_AUTH = 3
EXIT_NOT_FOUND = 4
EXIT_UNAVAILABLE = 6
EXIT_QUERY = 7


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ai_qa.jira",
        description="Read-only Jira access for the AI-QA platform.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify credentials; touches no issue")

    issue = sub.add_parser("issue", help="print one issue")
    issue.add_argument("key")

    search = sub.add_parser("search", help="print every issue matching a JQL query")
    search.add_argument("jql")
    search.add_argument("--limit", type=int, default=0, help="stop after N issues (0 = all)")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        settings = Settings.from_env()
    except Exception as exc:  # pydantic ValidationError and friends
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    try:
        with JiraClient(settings) as client:
            if args.command == "check":
                who = client.whoami()
                name = who.get("displayName") or who.get("emailAddress") or "<unknown>"
                print(f"Authenticated against {client.host} as {name}")
                return EXIT_OK

            if args.command == "issue":
                issue = client.get_issue(args.key)
                print(f"{issue.key}  [{issue.issue_type}/{issue.status}]  {issue.summary}")
                if issue.labels:
                    print("labels: " + ", ".join(issue.labels))
                if issue.description:
                    print()
                    print(issue.description)
                return EXIT_OK

            if args.command == "search":
                # Validate first: /search/jql returns 200 + empty list for an
                # unknown field, so without this a typo looks like "no matches".
                client.validate_jql(args.jql)
                shown = 0
                for issue in client.search(args.jql):
                    print(f"{issue.key}\t{issue.status}\t{issue.summary}")
                    shown += 1
                    if args.limit and shown >= args.limit:
                        break
                print(f"\n{shown} issue(s)", file=sys.stderr)
                return EXIT_OK

    except JiraConfigError as exc:
        print(f"{exc}", file=sys.stderr)
        return EXIT_CONFIG
    except (JiraAuthError, JiraForbiddenError) as exc:
        print(f"{exc}", file=sys.stderr)
        return EXIT_AUTH
    except JiraNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    except JiraQueryError as exc:
        print(f"{exc}", file=sys.stderr)
        return EXIT_QUERY
    except (JiraRateLimitError, JiraUnavailableError) as exc:
        print(f"{exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE

    return EXIT_OK  # pragma: no cover - argparse requires a subcommand


if __name__ == "__main__":
    raise SystemExit(main())
