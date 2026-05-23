"""``devague reject`` — reject a claim or honesty condition."""

from __future__ import annotations

import argparse

from devague.cli._commands.confirm import _transition


def cmd_reject(args: argparse.Namespace) -> int:
    return _transition(args, "rejected")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("reject", help="Reject a claim or honesty condition.")
    p.add_argument("id", help="Claim id (c*) or honesty id (h*).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_reject)
