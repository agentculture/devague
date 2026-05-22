"""``devague new`` — start a frame from an announcement (the first move)."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._output import emit_result
from devague.frame import Frame


def cmd_new(args: argparse.Namespace) -> int:
    title = args.title or args.announcement
    frame = Frame(slug=store.slugify(title), title=title)
    frame.add_claim("announcement", args.announcement, origin="user")
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"slug": frame.slug, "title": title, "claims": 1}, json_mode=True)
    else:
        emit_result(f"created frame '{frame.slug}' (announcement = c1)", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("new", help="Start a frame from an announcement.")
    p.add_argument("announcement", help="Pretend it shipped: what would you announce?")
    p.add_argument("--title", help="Frame title (defaults to the announcement).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_new)
