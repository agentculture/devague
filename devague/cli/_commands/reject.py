"""``devague reject`` — reject one or more claims / honesty conditions."""

from __future__ import annotations

import argparse

from devague.cli._commands.confirm import cmd_reject


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("reject", help="Reject one or more claims / honesty conditions.")
    p.add_argument("ids", nargs="+", help="One or more claim ids (c*) or honesty ids (h*).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_reject)
