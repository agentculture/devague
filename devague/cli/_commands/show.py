"""``devague show`` — render the current frame (markdown, or --json for raw state)."""

from __future__ import annotations

import argparse

from devague import render
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import to_dict


def cmd_show(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    if getattr(args, "json", False):
        emit_result(to_dict(frame), json_mode=True)
        return 0
    emit_result(render.render(frame, args.format), json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("show", help="Render the current frame.")
    p.add_argument("--format", default="frame-md", help="Renderer format (default: frame-md).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit the raw frame as JSON.")
    p.set_defaults(func=cmd_show)
