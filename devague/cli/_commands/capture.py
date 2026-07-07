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
    if args.instruction is not None:
        # A freshly-captured claim has no prior confirmed status to protect —
        # the re-confirm rule only fires on *changing* an existing item
        # (see interrogate.py).
        claim.instruction = args.instruction
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(
            {
                "id": claim.id,
                "kind": claim.kind,
                "origin": claim.origin,
                "status": claim.status,
                "instruction": claim.instruction,
            },
            json_mode=True,
        )
    else:
        emit_result(f"captured {claim.id} ({claim.kind}, {claim.status})", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("capture", help="Record and classify a claim.")
    p.add_argument("text", help="The claim text.")
    p.add_argument("--kind", required=True, choices=CLAIM_KINDS, help="Claim kind.")
    p.add_argument("--origin", choices=("user", "llm"), default="user", help="Who proposed it.")
    p.add_argument(
        "--instruction",
        help="Optional verbatim instruction: how to verify or implement this claim.",
    )
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_capture)
