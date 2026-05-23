"""``devague confirm`` — confirm claims/honesty conditions (user-only transition).

Accepts one or more ids in a single call. The batch is **transactional**: every
id is validated first, and if any is unknown nothing is changed (no half-applied
batch). Confirmation stays a user-only action — see issue #17.
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result


def _exists(frame, item_id: str) -> bool:
    return frame.find_claim(item_id) is not None or frame.find_honesty(item_id) is not None


def _transition(args: argparse.Namespace, status: str) -> int:
    frame = resolve(args.frame)
    ids: list[str] = args.ids
    unknown = [i for i in ids if not _exists(frame, i)]
    if unknown:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such claim or honesty condition: {', '.join(unknown)}",
            "run 'devague show'; the batch is transactional — nothing was changed",
        )
    for item_id in ids:
        frame.set_status(item_id, status)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"ids": ids, "status": status}, json_mode=True)
    else:
        emit_result("\n".join(f"{i} -> {status}" for i in ids), json_mode=False)
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    return _transition(args, "confirmed")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("confirm", help="Confirm one or more claims / honesty conditions.")
    p.add_argument("ids", nargs="+", help="One or more claim ids (c*) or honesty ids (h*).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_confirm)
