"""``devague scope`` — record an explored surface + finding as first-class state.

The pre-frame exploration leg (`/scope`, #53 t3). Recording is deterministic:
no LLM calls, no subprocess, no filesystem exploration — the move only
RECORDS what the operator already explored read-only. Optional ``--seeds``
links the entry to claim ids it went on to seed; an unknown seed id is
refused with a hint rather than silently accepted (see
``Frame.add_scope_entry``).

``--amend <sN> --finding <text>`` (issue #84) replaces an existing entry's
finding in place — same id, same ``surface``, same ``seeds`` — instead of
recording a second entry that says "supersedes sN" (the old, only recourse).
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result


def _entry_dict(entry) -> dict:
    return {
        "id": entry.id,
        "surface": entry.surface,
        "finding": entry.finding,
        "seeds": entry.seeds,
    }


def _record(args: argparse.Namespace, frame) -> int:
    if not args.finding:
        raise DevagueError(
            EXIT_USER_ERROR,
            "missing --finding",
            'pass --finding "<text>" describing what was learned about the surface',
        )
    try:
        entry = frame.add_scope_entry(args.surface, args.finding, seeds=args.seeds)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "run 'devague show' to see valid claim ids",
        ) from exc
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(_entry_dict(entry), json_mode=True)
    else:
        emit_result(f"recorded {entry.id} ({entry.surface})", json_mode=False)
    return 0


def _amend(args: argparse.Namespace, frame) -> int:
    if not args.finding:
        raise DevagueError(
            EXIT_USER_ERROR,
            "missing --finding",
            'pass --finding "<corrected text>" to replace the entry\'s finding',
        )
    try:
        entry = frame.amend_scope_entry(args.amend, args.finding)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "run 'devague scope' to see current scope entry ids",
        ) from exc
    store.save(frame)
    if getattr(args, "json", False):
        emit_result(_entry_dict(entry), json_mode=True)
    else:
        emit_result(f"amended {entry.id} ({entry.surface})", json_mode=False)
    return 0


def _list(args: argparse.Namespace, frame) -> int:
    entries = frame.scope_entries
    if getattr(args, "json", False):
        emit_result(
            {"frame": frame.slug, "scope_entries": [_entry_dict(e) for e in entries]},
            json_mode=True,
        )
    elif not entries:
        emit_result("no scope entries yet", json_mode=False)
    else:
        lines = []
        for e in entries:
            line = f"{e.id}: {e.surface} -> {e.finding}"
            if e.seeds:
                line += f" [seeds: {', '.join(e.seeds)}]"
            lines.append(line)
        emit_result("\n".join(lines), json_mode=False)
    return 0


def cmd_scope(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    if args.amend:
        if args.surface:
            raise DevagueError(
                EXIT_USER_ERROR,
                "pass a surface or --amend, not both",
                "drop the positional surface when amending an existing entry",
            )
        return _amend(args, frame)
    if args.surface:
        return _record(args, frame)
    return _list(args, frame)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("scope", help="Record an explored surface + finding (pre-frame scoping).")
    p.add_argument("surface", nargs="?", help="The surface explored (omit to list).")
    p.add_argument("--finding", help="What was learned about the surface (or the amend text).")
    p.add_argument(
        "--seeds",
        nargs="*",
        default=None,
        metavar="CLAIM_ID",
        help="Claim ids this finding seeded (must already exist).",
    )
    p.add_argument(
        "--amend",
        metavar="SID",
        help="Replace scope entry SID's finding in place (pairs with --finding).",
    )
    p.add_argument("--list", action="store_true", help="List recorded scope entries (default).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_scope)
