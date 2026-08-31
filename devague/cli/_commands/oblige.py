"""``devague oblige`` — file, list, or adjudicate a claim obligation (frame side).

Bvts t4: the CLI twin of ``Frame.add_obligation`` / ``Obligation`` (bvts t1,
:mod:`devague.frame`). This is a direct clone of
:mod:`devague.cli._commands.lapse`'s argument surface and
confirm/reject/list shape, with the record-mode arguments swapped: a lapse's
free-text ``code`` positional becomes a required claim id positional (the
structural link an obligation files against) plus ``--seam``/``--behavior`` —
both required to record, and both checked here in the handler rather than by
argparse, mirroring how ``lapse`` requires ``--code`` in the handler so the
same missing-flag error path also covers ``--confirm``/``--reject``/``--list``
calls that never reach it.

Unlike a lapse's free-text ``--ref`` (never validated — see
:class:`devague.frame.LapseRecord`'s docstring), an obligation's ``claim_id``
IS validated, at the filing path (:meth:`devague.frame.Frame.add_obligation`):
an obligation names a real seam on a real claim, so an unknown claim id is
refused with an actionable hint rather than silently filed against nothing.

Recording is deterministic: no LLM calls, no subprocess. Origin drives the
initial status exactly like a claim, a task, a deviation, or a lapse:
``--origin llm`` lands ``proposed`` and needs an explicit user ``--confirm``;
a user-authored record (the default) auto-approves
(:meth:`Frame.add_obligation`). ``--confirm``/``--reject`` are therefore the
only way a proposed obligation is resolved — there is no amend and no delete
(the same c20-style asymmetry as the Reasoning Degradation Ledger).
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.frame import ORIGINS, obligation_drift


def _record_dict(rec) -> dict:
    return {
        "id": rec.id,
        "claim_id": rec.claim_id,
        "seam": rec.seam,
        "behavior": rec.behavior,
        "source_text": rec.source_text,
        "origin": rec.origin,
        "status": rec.status,
    }


def _drift_for(frame, rec):
    """The obligation's live drift message, or ``None`` — computed purely via
    :func:`devague.frame.obligation_drift`, never re-derived here. ``None``
    when the source claim itself is gone (a defensive fallback; claims are
    never deleted today, only rejected, so this path is currently unreached)."""
    claim = frame.find_claim(rec.claim_id)
    if claim is None:
        return None
    return obligation_drift(rec, claim)


def _record(args: argparse.Namespace, frame) -> int:
    missing = []
    if not args.seam:
        missing.append("--seam")
    if not args.behavior:
        missing.append("--behavior")
    if missing:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"missing {', '.join(missing)}",
            'pass --seam "<boundary>" --behavior "<what is owed>"',
        )
    try:
        rec = frame.add_obligation(
            args.claim_id,
            args.seam,
            args.behavior,
            origin=args.origin or "user",
        )
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "run 'devague show' to see current claim ids",
        ) from exc
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(_record_dict(rec), json_mode=True)
    else:
        emit_result(f"filed {rec.id} ({rec.status})", json_mode=False)
    return 0


def _resolve_status(args: argparse.Namespace, frame, oid: str, status: str) -> int:
    rec = frame.find_obligation(oid)
    if rec is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such obligation: {oid}",
            "run 'devague oblige --list' to see filed obligation ids",
        )
    if rec.status != "proposed":
        raise DevagueError(
            EXIT_USER_ERROR,
            f"obligation {oid} is already {rec.status}",
            f"only a 'proposed' obligation can be confirmed/rejected — "
            f"{oid} is already {rec.status}",
        )
    frame.set_obligation_status(oid, status)
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"id": oid, "status": status}, json_mode=True)
    else:
        emit_result(f"{oid} -> {status}", json_mode=False)
    return 0


def _list(args: argparse.Namespace, frame) -> int:
    records = frame.obligations
    if getattr(args, "json", False):
        payload = []
        for r in records:
            d = _record_dict(r)
            d["drift"] = _drift_for(frame, r)
            payload.append(d)
        emit_result({"frame": frame.slug, "obligations": payload}, json_mode=True)
    elif not records:
        emit_result("no obligations filed yet", json_mode=False)
    else:
        lines = []
        for r in records:
            marker = " — drifted" if _drift_for(frame, r) else ""
            lines.append(f"{r.id}: {r.claim_id} [{r.seam}] {r.behavior} ({r.status}){marker}")
        emit_result("\n".join(lines), json_mode=False)
    return 0


def cmd_oblige(args: argparse.Namespace) -> int:
    if (args.confirm or args.reject) and args.claim_id:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --confirm/--reject with a positional claim id",
            "resolve and record are separate moves: run "
            "'devague oblige --confirm <id>' (or --reject), then "
            '\'devague oblige <cN> --seam "<seam>" --behavior "<behavior>"\'',
        )
    if args.list and args.claim_id:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --list with a positional claim id",
            "list and record are separate moves: run 'devague oblige --list' "
            'or \'devague oblige <cN> --seam "<seam>" --behavior "<behavior>"\'',
        )
    # Record-only flags with no claim id given must never fall through to
    # listing (Qodo, PR #101, the lapse-ledger precedent) — a silent no-op is
    # the worst failure available for a ledger whose premise is that filing is
    # cheap enough to do mid-flight.
    if not args.claim_id:
        given = [
            flag
            for flag, value in (
                ("--seam", args.seam),
                ("--behavior", args.behavior),
                ("--origin", args.origin),
            )
            if value
        ]
        if given:
            raise DevagueError(
                EXIT_USER_ERROR,
                f"{', '.join(given)} given without a positional claim id to file",
                "file the obligation in one move: devague oblige <cN> --seam "
                '"<seam>" --behavior "<behavior>", or drop the flags to list',
            )
    frame = resolve(args.frame)
    if args.confirm:
        return _resolve_status(args, frame, args.confirm, "approved")
    if args.reject:
        return _resolve_status(args, frame, args.reject, "rejected")
    if args.claim_id:
        return _record(args, frame)
    return _list(args, frame)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("oblige", help="File, list, or adjudicate a claim obligation.")
    p.add_argument(
        "claim_id",
        nargs="?",
        help="Claim id to obligate (e.g. c1); omit with --confirm/--reject/--list.",
    )
    p.add_argument("--seam", help="The boundary/interface this obligation applies to.")
    p.add_argument("--behavior", help="What behavior is owed at that seam.")
    # default=None (not "user") so an explicitly-passed --origin is
    # distinguishable from the default — cmd_oblige needs that to tell record
    # intent from a bare list, mirroring lapse.py.
    p.add_argument("--origin", choices=ORIGINS, default=None, help="Who proposed it.")
    resolution = p.add_mutually_exclusive_group()
    resolution.add_argument(
        "--confirm", metavar="ID", help="Approve a proposed obligation id (user-only)."
    )
    resolution.add_argument("--reject", metavar="ID", help="Reject an obligation id (user-only).")
    resolution.add_argument("--list", action="store_true", help="List filed obligations (default).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_oblige)
