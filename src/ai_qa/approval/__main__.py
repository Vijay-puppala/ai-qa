"""Approval gate CLI (FR-001 to FR-003, FR-028, FR-038, FR-039).

No network anywhere in this feature: every command works offline, which is
what lets a pipeline verify approvals with no credentials and no connectivity.

``verify`` is the **same command** an engineer runs locally and that a pipeline
runs - one implementation, two callers, so a pipeline failure is reproducible
before pushing rather than met during a release (FR-039).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_qa.approval import policy, records
from ai_qa.approval.digest import design_digest_for, design_items, covered_test_names
from ai_qa.approval.state import Completion, State, approval_state, scan
from ai_qa.config import Settings

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_SELF_APPROVAL = 3
EXIT_AUTHOR_UNKNOWN = 4
EXIT_NO_REASON = 5
EXIT_UNAPPROVED = 6
EXIT_IDENTITY = 7
EXIT_TAMPERED = 8

_VERDICT_EXIT = {
    policy.Verdict.SELF_APPROVAL: EXIT_SELF_APPROVAL,
    policy.Verdict.AUTHOR_UNKNOWN: EXIT_AUTHOR_UNKNOWN,
    policy.Verdict.IDENTITY_UNKNOWN: EXIT_IDENTITY,
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m ai_qa.approval")
    sub = p.add_subparsers(dest="command", required=True)

    rv = sub.add_parser("review", help="list designs awaiting review")
    rv.add_argument("--ticket")
    rv.add_argument("--all", action="store_true")
    rv.add_argument("--root", default="tests")

    ap = sub.add_parser("approve", help="record an approval")
    ap.add_argument("design")

    rj = sub.add_parser("reject", help="record a rejection")
    rj.add_argument("design")
    rj.add_argument("--reason", required=True, help="why - required, and recorded")

    st = sub.add_parser("status", help="state of every design")
    st.add_argument("--ticket")
    st.add_argument("--root", default="tests")

    vf = sub.add_parser("verify", help="fail if any design lacks an applicable approval")
    vf.add_argument("--root", default="tests")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = Settings.from_env()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    root = Path(settings.approval_records_dir)

    if args.command == "review":
        return _review(args, root)
    if args.command == "status":
        return _status(args, root)
    if args.command == "verify":
        return _verify(args, root)
    return _decide(args, root, settings)


def _review(args, root: Path) -> int:
    shown = 0
    for status in scan(args.root, records_dir=root):
        if status.state is State.UNMANAGED:
            continue
        if args.ticket and status.ticket != args.ticket:
            continue
        if not args.all and status.state is not State.PENDING:
            continue
        shown += 1
        print(f"\n{status.path}  [{status.state.value}]  ticket {status.ticket or '?'}")
        # The docstrings *are* the thing under review - a reviewer who has not
        # read them has not reviewed the design.
        for item in design_items(status.path.read_text(encoding="utf-8")):
            print(f"  - {item.name}")
            print(f"      claims: {item.docstring or '(no docstring - cannot be reviewed)'}")
    print(f"\n{shown} design(s) awaiting review", file=sys.stderr)
    return EXIT_OK


def _status(args, root: Path) -> int:
    designs = [
        s
        for s in scan(args.root, records_dir=root)
        if not args.ticket or s.ticket == args.ticket
    ]
    unmanaged = sum(1 for s in designs if s.state is State.UNMANAGED)
    for s in designs:
        if s.state is State.UNMANAGED:
            continue
        extra = "" if s.completion is Completion.COMPLETE else f"  ({s.completion.value})"
        print(f"{s.state.value:<9} {s.path}  ticket {s.ticket or '?'}{extra}")

    known = {s.digest for s in designs if s.digest}
    integrity = records.check_integrity(root, known)
    for path in integrity.orphaned:
        print(f"ORPHANED  {path}  (digest matches no design)", file=sys.stderr)
    for path in integrity.malformed:
        print(f"MALFORMED {path}", file=sys.stderr)
    for gone in integrity.deleted:
        print(f"DELETED   {gone}  (present in git history, absent on disk)", file=sys.stderr)

    print(f"\n{unmanaged} unmanaged (hand-written) test file(s)", file=sys.stderr)
    return EXIT_TAMPERED if not integrity.clean else EXIT_OK


def _verify(args, root: Path) -> int:
    """The pipeline gate. Prints every offender, never a count (FR-038)."""
    offenders = [
        s for s in scan(args.root, records_dir=root) if s.blocks_automation
    ]
    if not offenders:
        print("All generated designs are covered by an applicable approval.")
        return EXIT_OK

    print("Unapproved test scripts found. This pipeline run fails.", file=sys.stderr)
    for s in offenders:
        print(f"\n  {s.path}", file=sys.stderr)
        print(f"    state:  {s.state.value}", file=sys.stderr)
        print(f"    remedy: {s.refusal_reason()}", file=sys.stderr)
    print(
        f"\n{len(offenders)} script(s) without an applicable approval. "
        "Run the same command locally to reproduce this before pushing.",
        file=sys.stderr,
    )
    return EXIT_UNAPPROVED


def _decide(args, root: Path, settings: Settings) -> int:
    design = Path(args.design)
    if not design.exists():
        print(f"{design} does not exist", file=sys.stderr)
        return EXIT_CONFIG

    decision = "approved" if args.command == "approve" else "rejected"
    reason = getattr(args, "reason", None)
    if decision == "rejected" and not (reason or "").strip():
        print("A rejection needs --reason: without one it tells the author "
              "nothing and is useless to a later auditor.", file=sys.stderr)
        return EXIT_NO_REASON

    check = policy.check(design, require_second_person=settings.approval_require_second_person)
    if not check.allowed:
        print(check.message(), file=sys.stderr)
        return _VERDICT_EXIT[check.verdict]

    status = approval_state(design, records_dir=root)
    source = design.read_text(encoding="utf-8")
    record = records.DecisionRecord(
        decision=decision,  # type: ignore[arg-type]
        ticket=status.ticket or "UNKNOWN",
        design_path=str(design).replace("\\", "/"),
        design_digest=design_digest_for(design),
        approver=check.approver or "",
        author=check.author,
        policy_require_second_person=settings.approval_require_second_person,
        timestamp=records.now_stamp(),
        test_names=covered_test_names(source),
        reason=reason,
    )
    path = records.write(record, root=root)
    print(f"Recorded {decision} by {record.approver} -> {path}")
    print(f"Covers {len(record.test_names)} test(s); design digest {record.design_digest}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
