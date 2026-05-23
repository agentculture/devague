"""``devague confirm`` — confirm a claim or honesty condition (user-only transition)."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result


def _transition(args: argparse.Namespace, status: str) -> int:
    frame = resolve(args.frame)
    if not frame.set_status(args.id, status):
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such claim or honesty condition: {args.id}",
            "run 'devague show'",
        )
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": args.id, "status": status}, json_mode=True)
    else:
        emit_result(f"{args.id} -> {status}", json_mode=False)
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    return _transition(args, "confirmed")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("confirm", help="Confirm a claim or honesty condition.")
    p.add_argument("id", help="Claim id (c*) or honesty id (h*).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_confirm)
