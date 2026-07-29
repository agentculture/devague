"""``devague lapse`` — file, list, or adjudicate a reasoning-degradation lapse.

The Reasoning Degradation Ledger's CLI move (issue #97 t2). The domain model
(``Frame.lapses`` / ``LapseRecord`` / ``Frame.add_lapse`` / ``find_lapse`` /
``set_lapse_status``) landed in t1 (:mod:`devague.frame`); this module is
its CLI twin.

This is a direct clone of :mod:`devague.cli._commands.deviate`'s argument
surface and confirm/reject/list shape, with two deliberate omissions:

- **No ``--task``** — a lapse is filed against the current *frame*, not a
  *plan*; there is no plan-item link to validate.
- **No id-ref validation** — a deviation's ``--affects`` must resolve to a
  known plan/frame id (:func:`deviate._validate_refs`); a lapse's ``--ref``
  stays free text, never checked against known ids (see
  :class:`devague.frame.LapseRecord`'s docstring for why: the ledger records
  what was skipped, and demanding a real id for that would let a filer dodge
  filing when they can't (or shouldn't) cite one precisely).

Recording is deterministic: no LLM calls, no subprocess. Origin drives the
initial status exactly like a claim, a task, or a deviation: ``--origin llm``
lands ``proposed`` and needs an explicit user ``--confirm``; a user-authored
record (the default) auto-approves (``Frame.add_lapse``). ``--confirm`` /
``--reject`` are therefore the only way a proposed lapse is resolved.
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import LAPSE_CODES, ORIGINS


def _record_dict(rec) -> dict:
    return {
        "id": rec.id,
        "code": rec.code,
        "what": rec.what,
        "skipped_check": rec.skipped_check,
        "refs": rec.refs,
        "origin": rec.origin,
        "status": rec.status,
    }


def _record(args: argparse.Namespace, frame) -> int:
    if not args.code:
        raise DevagueError(
            EXIT_USER_ERROR,
            "missing --code",
            f"pass --code <code>: {', '.join(LAPSE_CODES)}",
        )
    try:
        rec = frame.add_lapse(
            args.code,
            args.what,
            skipped_check=args.skipped_check or "",
            refs=args.refs,
            origin=args.origin or "user",
        )
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            f"valid lapse codes: {', '.join(LAPSE_CODES)}",
        ) from exc
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(_record_dict(rec), json_mode=True)
    else:
        emit_result(f"filed {rec.id} ({rec.status})", json_mode=False)
    return 0


def _resolve_status(args: argparse.Namespace, frame, lid: str, status: str) -> int:
    rec = frame.find_lapse(lid)
    if rec is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such lapse: {lid}",
            "run 'devague lapse --list' to see filed lapse ids",
        )
    if rec.status != "proposed":
        raise DevagueError(
            EXIT_USER_ERROR,
            f"lapse {lid} is already {rec.status}",
            f"only a 'proposed' lapse can be confirmed/rejected — "
            f"{lid} is already {rec.status}",
        )
    frame.set_lapse_status(lid, status)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": lid, "status": status}, json_mode=True)
    else:
        emit_result(f"{lid} -> {status}", json_mode=False)
    return 0


def _list(args: argparse.Namespace, frame) -> int:
    records = frame.lapses
    if getattr(args, "json", False):
        emit_result(
            {"frame": frame.slug, "lapses": [_record_dict(r) for r in records]},
            json_mode=True,
        )
    elif not records:
        emit_result("no lapses filed yet", json_mode=False)
    else:
        lines = [f"{r.id}: {r.what} ({r.code}, {r.status})" for r in records]
        emit_result("\n".join(lines), json_mode=False)
    return 0


def cmd_lapse(args: argparse.Namespace) -> int:
    if (args.confirm or args.reject) and args.what:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --confirm/--reject with a positional 'what' argument",
            "resolve and record are separate moves: run "
            "'devague lapse --confirm <id>' (or --reject), then "
            "'devague lapse \"<what>\" --code <code>'",
        )
    if args.list and args.what:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --list with a positional 'what' argument",
            "list and record are separate moves: run 'devague lapse --list' "
            "or 'devague lapse \"<what>\" --code <code>'",
        )
    # Record-only flags with no `what` used to fall through to listing, so
    # `devague lapse --code <code> --skipped "<check>"` exited 0 having filed
    # nothing (Qodo, PR #101). For a ledger whose premise is that filing is
    # cheap enough to do mid-flight, a silent no-op is the worst failure
    # available: the operator believes the degradation is recorded and it is
    # not. Fail closed, matching the flag/positional-ambiguity precedent (#72).
    if not args.what:
        given = [
            flag
            for flag, value in (
                ("--code", args.code),
                ("--skipped", args.skipped_check),
                ("--ref", args.refs),
                ("--origin", args.origin),
            )
            if value
        ]
        if given:
            raise DevagueError(
                EXIT_USER_ERROR,
                f"{', '.join(given)} given without a positional 'what' to file",
                'record the lapse in one move: devague lapse "<what>" '
                "--code <code>, or drop the flags to list",
            )
    frame = resolve(args.frame)
    if args.confirm:
        return _resolve_status(args, frame, args.confirm, "approved")
    if args.reject:
        return _resolve_status(args, frame, args.reject, "rejected")
    if args.what:
        return _record(args, frame)
    return _list(args, frame)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("lapse", help="File, list, or adjudicate a reasoning-degradation lapse.")
    p.add_argument("what", nargs="?", help="What lapsed (omit with --confirm/--reject/--list).")
    p.add_argument(
        "--code",
        choices=LAPSE_CODES,
        help="Which lapse code this instance is.",
    )
    p.add_argument(
        "--skipped",
        dest="skipped_check",
        default="",
        metavar="CHECK",
        help="What check should have caught this but didn't.",
    )
    p.add_argument(
        "--ref",
        dest="refs",
        action="append",
        default=None,
        metavar="REF",
        help="A free-text reference this lapse relates to (repeatable, never validated).",
    )
    # default=None (not "user") so an explicitly-passed --origin is
    # distinguishable from the default — cmd_lapse needs that to tell
    # record intent from a bare list. _record resolves None to "user".
    p.add_argument("--origin", choices=ORIGINS, default=None, help="Who proposed it.")
    resolution = p.add_mutually_exclusive_group()
    resolution.add_argument(
        "--confirm", metavar="ID", help="Approve a proposed lapse id (user-only)."
    )
    resolution.add_argument("--reject", metavar="ID", help="Reject a lapse id (user-only).")
    resolution.add_argument("--list", action="store_true", help="List filed lapses (default).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_lapse)
