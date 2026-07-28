"""``devague amend`` — correct a claim's text and/or kind without churning its id.

The `amend` move (issue #84): the only prior way to fix a typo or a wrong
number in a claim was `reject` + `capture` (a new id) + re-authoring every
honesty condition / instruction the old id carried, and any inbound
`scope --seeds` reference to the rejected claim was left dangling. `amend`
edits the claim in place — same id, same honesty conditions, same
instruction, same inbound seed references — so correcting one number is one
move, not five.

Amending a CONFIRMED claim flips it back to `proposed` and echoes that, the
same re-confirm rule `interrogate --instruction` already applies (see
`interrogate.py`'s `_apply_instruction` — the precedent this mirrors).
`origin` is never touched: there is no flag that can reach it, on purpose.
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_diagnostic, emit_result
from devague.frame import CLAIM_KINDS


def cmd_amend(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    try:
        claim, flipped = frame.amend_claim(
            args.claim_id,
            text=args.text,
            kind=args.kind,
            reason=args.reason or "",
        )
    except ValueError as err:
        message = str(err)
        if message.startswith("unknown claim id"):
            raise DevagueError(
                EXIT_USER_ERROR,
                message,
                "run 'devague show' to see current claim ids",
            ) from err
        raise DevagueError(
            EXIT_USER_ERROR,
            message,
            "pass --text and/or --kind with the corrected value",
        ) from err
    store.save(frame)
    flip_note = None
    if flipped:
        flip_note = (
            f"{claim.id} was confirmed; the amend flips it back to proposed — "
            f"re-confirm with 'devague confirm {claim.id}'"
        )
        emit_diagnostic(flip_note)
    if getattr(args, "json", False):
        emit_result(
            {
                "id": claim.id,
                "kind": claim.kind,
                "text": claim.text,
                "origin": claim.origin,
                "status": claim.status,
                "flipped": flipped,
            },
            json_mode=True,
        )
    else:
        emit_result(f"amended {claim.id} ({claim.kind}, {claim.status})", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "amend", help="Correct a claim's text and/or kind in place (keeps id and attachments)."
    )
    p.add_argument("claim_id", help="Claim id to amend (e.g. c1).")
    p.add_argument("--text", help="Corrected claim text.")
    p.add_argument("--kind", choices=CLAIM_KINDS, help="Corrected claim kind.")
    p.add_argument(
        "--reason",
        help="Optional note recorded alongside the superseded text/kind (why it was amended).",
    )
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_amend)
