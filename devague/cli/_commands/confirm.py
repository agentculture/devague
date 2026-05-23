"""``devague confirm`` — confirm claims/honesty conditions (user-only transition).

Accepts one or more ids in a single call, or a reviewed decision set via
``--from-review <file>`` (apply the confirm/reject markers a human edited into a
``devague review`` artifact). Either way the batch is **transactional**: every
id is validated first, and if any is unknown nothing is changed. Confirmation
stays a user-only action, and ``--from-review`` applies only what the file
explicitly marks — ``pending`` lines are never auto-confirmed. See issue #17.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.render.review_md import parse_decisions


def _exists(frame, item_id: str) -> bool:
    return frame.find_claim(item_id) is not None or frame.find_honesty(item_id) is not None


def _run(args: argparse.Namespace, confirm_ids: list[str], reject_ids: list[str]) -> int:
    frame = resolve(args.frame)
    all_ids = confirm_ids + reject_ids
    if not all_ids:
        raise DevagueError(EXIT_USER_ERROR, "no ids to resolve", "pass at least one id")
    unknown = [i for i in all_ids if not _exists(frame, i)]
    if unknown:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such claim or honesty condition: {', '.join(unknown)}",
            "run 'devague show'; the batch is transactional — nothing was changed",
        )
    for item_id in confirm_ids:
        frame.set_status(item_id, "confirmed")
    for item_id in reject_ids:
        frame.set_status(item_id, "rejected")
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"confirmed": confirm_ids, "rejected": reject_ids}, json_mode=True)
    else:
        lines = [f"{i} -> confirmed" for i in confirm_ids]
        lines += [f"{i} -> rejected" for i in reject_ids]
        emit_result("\n".join(lines), json_mode=False)
    return 0


def _from_review(path: str) -> tuple[list[str], list[str]]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as err:
        raise DevagueError(EXIT_USER_ERROR, f"cannot read review file: {path}", str(err))
    try:
        decisions = parse_decisions(text)
    except ValueError as err:
        raise DevagueError(EXIT_USER_ERROR, str(err), "fix the conflicting decision and retry")
    confirm_ids = [i for i, d in decisions.items() if d == "confirm"]
    reject_ids = [i for i, d in decisions.items() if d == "reject"]
    if not confirm_ids and not reject_ids:
        raise DevagueError(
            EXIT_USER_ERROR,
            "no decisions found in review file",
            "change a line's 'pending' to 'confirm' or 'reject' first",
        )
    return confirm_ids, reject_ids


def cmd_confirm(args: argparse.Namespace) -> int:
    if args.from_review:
        if args.ids:
            raise DevagueError(
                EXIT_USER_ERROR,
                "pass ids or --from-review, not both",
                "drop the positional ids when applying a review file",
            )
        confirm_ids, reject_ids = _from_review(args.from_review)
        return _run(args, confirm_ids, reject_ids)
    return _run(args, list(args.ids), [])


def cmd_reject(args: argparse.Namespace) -> int:
    return _run(args, [], list(args.ids))


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("confirm", help="Confirm claims/honesty conditions, or apply a review file.")
    p.add_argument("ids", nargs="*", help="One or more claim ids (c*) or honesty ids (h*).")
    p.add_argument("--from-review", help="Apply confirm/reject decisions from a review file.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_confirm)
