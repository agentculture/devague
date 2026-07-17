"""``devague park`` — move uncertainty into first-class open vagueness, and
resolve it later without routing it through confirm/reject.

Two mutually exclusive paths share one parser (mirrors ``question.py``):
parking new vagueness (positional ``text`` + ``--kind``) and resolving a
previously parked item (``--resolve VID --decision TEXT``, optionally
``--claim CN`` to link the deciding claim). ``--resolve`` fails closed on an
unknown id, an already-resolved id, and an unknown ``--claim`` id — never a
silent no-op (issue #57, decision c21).
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import VAGUENESS_KINDS


def _create(args: argparse.Namespace, frame) -> int:
    if not args.text:
        raise DevagueError(
            EXIT_USER_ERROR,
            "no text to park",
            "pass vagueness text, or --resolve VID --decision TEXT to resolve an existing one",
        )
    if not args.kind:
        raise DevagueError(
            EXIT_USER_ERROR,
            "--kind is required to park new vagueness",
            f"choose one of: {', '.join(VAGUENESS_KINDS)}",
        )
    v = frame.add_vagueness(args.text, args.kind, claim_id=args.claim)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": v.id, "kind": v.kind}, json_mode=True)
    else:
        emit_result(f"parked {v.id} ({v.kind})", json_mode=False)
    return 0


def _resolve_vagueness(args: argparse.Namespace, frame) -> int:
    if args.text:
        raise DevagueError(
            EXIT_USER_ERROR,
            "pass positional text or --resolve, not both",
            "drop the positional text when resolving an existing id",
        )
    if not args.decision:
        raise DevagueError(
            EXIT_USER_ERROR,
            "--resolve requires --decision",
            'pass --decision "<text>" with the resolving decision',
        )
    try:
        v = frame.resolve_vagueness(args.resolve, args.decision, claim_id=args.claim)
    except ValueError as err:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(err),
            "run 'devague show' to see current vagueness ids and claim ids",
        ) from err
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(
            {
                "id": v.id,
                "resolved": True,
                "resolution": v.resolution,
                "resolution_claim_id": v.resolution_claim_id,
            },
            json_mode=True,
        )
    else:
        emit_result(f"{v.id} -> resolved", json_mode=False)
    return 0


def cmd_park(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    if args.resolve:
        return _resolve_vagueness(args, frame)
    return _create(args, frame)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("park", help="Record open vagueness instead of forcing an answer.")
    p.add_argument("text", nargs="?", help="The uncertainty (omit when using --resolve).")
    p.add_argument(
        "--kind", choices=VAGUENESS_KINDS, help="Vagueness kind (required to park new vagueness)."
    )
    p.add_argument(
        "--claim",
        help="Link to a claim id: the owning claim when parking, "
        "the deciding claim when --resolve.",
    )
    p.add_argument("--resolve", metavar="VID", help="Mark a parked vagueness id resolved.")
    p.add_argument("--decision", help="The resolution note recorded with --resolve.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_park)
