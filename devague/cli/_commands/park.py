"""``devague park`` — move uncertainty into first-class open vagueness."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import VAGUENESS_KINDS


def cmd_park(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    v = frame.add_vagueness(args.text, args.kind, claim_id=args.claim)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": v.id, "kind": v.kind}, json_mode=True)
    else:
        emit_result(f"parked {v.id} ({v.kind})", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("park", help="Record open vagueness instead of forcing an answer.")
    p.add_argument("text", help="The uncertainty.")
    p.add_argument("--kind", required=True, choices=VAGUENESS_KINDS, help="Vagueness kind.")
    p.add_argument("--claim", help="Link to a claim id.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_park)
