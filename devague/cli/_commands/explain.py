"""``devague explain <move>`` — print docs for a single move."""

from __future__ import annotations

import argparse

from devague.cli._commands.learn import MOVES
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._output import emit_result


def cmd_explain(args: argparse.Namespace) -> int:
    desc = MOVES.get(args.move)
    if desc is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown move: {args.move}",
            f"available moves: {', '.join(MOVES)}",
        )
    if getattr(args, "json", False):
        emit_result({"move": args.move, "description": desc}, json_mode=True)
    else:
        emit_result(f"{args.move}: {desc}", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("explain", help="Explain a devague move.")
    p.add_argument("move", help="A move name (e.g. converge).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_explain)
