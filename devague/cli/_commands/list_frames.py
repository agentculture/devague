"""``devague list`` — list frames and mark the current one."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._output import emit_result


def cmd_list(args: argparse.Namespace) -> int:
    slugs = store.list_slugs()
    current = store.current_slug()
    if getattr(args, "json", False):
        emit_result({"frames": slugs, "current": current}, json_mode=True)
        return 0
    if not slugs:
        emit_result("no frames yet", json_mode=False)
        return 0
    lines = [("* " if s == current else "  ") + s for s in slugs]
    emit_result("\n".join(lines), json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("list", help="List frames.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_list)
