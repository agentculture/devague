"""``devague capture`` — record and classify a claim."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import CLAIM_KINDS


def cmd_capture(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    claim = frame.add_claim(args.kind, args.text, origin=args.origin)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": claim.id, "kind": claim.kind, "status": claim.status}, json_mode=True)
    else:
        emit_result(f"captured {claim.id} ({claim.kind}, {claim.status})", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("capture", help="Record and classify a claim.")
    p.add_argument("text", help="The claim text.")
    p.add_argument("--kind", required=True, choices=CLAIM_KINDS, help="Claim kind.")
    p.add_argument("--origin", choices=("user", "llm"), default="user", help="Who proposed it.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_capture)
