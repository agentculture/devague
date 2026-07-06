"""``devague interrogate`` — pressure-test a claim with honesty conditions / hard questions."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_diagnostic, emit_result


def cmd_interrogate(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    claim = frame.find_claim(args.claim_id)
    # For --instruction only, the target id may name a claim (c*) OR an
    # honesty condition (h*) — #53 t4, c10.
    honesty = None if claim is not None else frame.find_honesty(args.claim_id)
    if claim is None and honesty is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such claim or honesty condition: {args.claim_id}",
            "run 'devague show'",
        )

    claim_only_requested = args.honesty or args.risk or args.hard_question or args.contradicts
    if honesty is not None and claim_only_requested:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"{args.claim_id} is an honesty condition — "
            "--honesty/--hard-question/--risk/--contradicts require a claim id",
            "pass a claim id (e.g. c1), or drop those flags and keep --instruction",
        )

    added: list[dict] = []
    if args.honesty:
        h = frame.add_honesty(claim, args.honesty, origin=args.origin)
        added.append({"kind": "honesty", "id": h.id, "status": h.status})
    if args.risk:
        q = frame.add_hard_question(claim, f"risk: {args.risk}", blocking=False)
        added.append({"kind": "hard_question", "id": q.id, "status": "open"})
    if args.hard_question:
        q = frame.add_hard_question(claim, args.hard_question, blocking=args.blocking)
        added.append(
            {"kind": "hard_question", "id": q.id, "status": "blocking" if q.blocking else "open"}
        )
    if args.contradicts:
        q = frame.add_hard_question(claim, f"contradiction with {args.contradicts}?", blocking=True)
        added.append({"kind": "hard_question", "id": q.id, "status": "blocking"})

    flip_note = None
    if args.instruction is not None:
        # --instruction alongside --honesty targets the CLAIM (not the
        # freshly-added honesty condition) — the operator-pinned semantics.
        target = claim if claim is not None else honesty
        if target.status == "confirmed":
            target.status = "proposed"
            flip_note = (
                f"{target.id} was confirmed; the instruction change flips it back to "
                f"proposed — re-confirm with 'devague confirm {target.id}'"
            )
        target.instruction = args.instruction
        added.append({"kind": "instruction", "id": target.id, "status": target.status})

    if not added:
        raise DevagueError(
            EXIT_USER_ERROR,
            "nothing to interrogate",
            "pass --honesty / --hard-question / --risk / --contradicts / --instruction",
        )
    store.save(frame)
    if flip_note:
        emit_diagnostic(flip_note)
    if getattr(args, "json", False):
        emit_result({"claim": args.claim_id, "added": added}, json_mode=True)
    else:
        emit_result(
            f"interrogated {args.claim_id}: " + ", ".join(f"{a['kind']} {a['id']}" for a in added),
            json_mode=False,
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("interrogate", help="Attach honesty conditions / hard questions to a claim.")
    p.add_argument(
        "claim_id",
        help=(
            "Claim id (e.g. c1); with --instruction only, an honesty "
            "condition id (e.g. h1) also works."
        ),
    )
    p.add_argument("--honesty", help="An honesty condition (what must be true).")
    p.add_argument("--hard-question", dest="hard_question", help="A hard question.")
    p.add_argument("--risk", help="A risk (recorded as a non-blocking hard question).")
    p.add_argument("--contradicts", help="Claim id this contradicts (records a blocking question).")
    p.add_argument("--blocking", action="store_true", help="Mark the hard question blocking.")
    p.add_argument(
        "--instruction",
        help=(
            "Add or update a verbatim instruction on the target claim/honesty "
            "condition. Changing it on a confirmed item flips it back to proposed."
        ),
    )
    p.add_argument(
        "--origin",
        choices=("user", "llm"),
        default="llm",
        help="Who proposed the honesty condition.",
    )
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_interrogate)
