"""``devague evidence`` — file, list, or adjudicate an evidence record.

Bvts t5: the CLI twin of ``Delivery.add_evidence`` / ``EvidenceRecord`` (bvts
t3, :mod:`devague.delivery`). Structurally this is two things stitched
together: it clones :mod:`devague.cli._commands.oblige`'s file/list/confirm/
reject argument shape (the record-mode discriminator is a required flag
rather than a positional, since an evidence record has no single natural
positional identifier — ``--obligation`` plays that role), and it clones
:mod:`devague.cli._commands.deviate`'s plan resolution: the record files into
the current/named plan's delivery ledger via :mod:`devague.delivery_store`,
exactly like a deviation does.

Recording is deterministic: no LLM calls, no shelling out to run a test.
Filing an evidence record only *describes* a test that was run elsewhere, it
never runs one (mirrors the devague-wide rule that the CLI never executes
tests or picks a backend, #20). Origin drives the initial status exactly like every other
ledger move in this codebase: ``--origin llm`` lands ``proposed`` and needs an
explicit user ``--confirm``; a user-authored record (the default) auto-
approves. ``--confirm``/``--reject`` are therefore the only way a proposed
evidence record is resolved — there is no amend and no delete, the same
append-only asymmetry as obligations and lapses.

Run-reference validation (c21/h17): ``devague.delivery.Delivery.add_evidence``
already refuses a record at ``execution``/``sensitivity`` strength with no run
reference at all. This module adds the *shape* check on top: when a run
reference is given, ``--run-commit`` must look like a commit SHA (7-40 hex
chars) and ``--run-timestamp`` must parse as an ISO-8601 timestamp
(``datetime.fromisoformat``) — a malformed reference is exactly as unusable to
a reviewer as a missing one, so it is refused before anything is persisted.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime

from devague import delivery_store
from devague.cli._deliveries import resolve_delivery
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._output import emit_result
from devague.cli._plans import resolve_plan
from devague.delivery import (
    EVIDENCE_OUTCOMES,
    EVIDENCE_TYPES,
    ORIGINS,
    RUN_REQUIRED_STRENGTHS,
    STRENGTH_LEVELS,
    RunReference,
)

# A commit SHA (abbreviated or full): 7-40 lowercase hex chars — the same
# shape `git rev-parse --short`..`git rev-parse` produces.
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _record_dict(rec) -> dict:
    return {
        "id": rec.id,
        "obligation_ref": rec.obligation_ref,
        "test_ref": rec.test_ref,
        "behavior_text": rec.behavior_text,
        "contract_text": rec.contract_text,
        "evidence_type": rec.evidence_type,
        "strength": rec.strength,
        "strength_basis": rec.strength_basis,
        "outcome": rec.outcome,
        "run": {"timestamp": rec.run.timestamp, "commit": rec.run.commit} if rec.run else None,
        "origin": rec.origin,
        "status": rec.status,
    }


def _plan_slug(args: argparse.Namespace) -> str:
    return resolve_plan(args.plan).slug


def _validate_run_shape(commit: str, timestamp: str) -> None:
    if not _COMMIT_RE.match(commit):
        raise DevagueError(
            EXIT_USER_ERROR,
            f"--run-commit {commit!r} is not a commit SHA (7-40 hex chars)",
            "pass the short or full commit SHA the test actually ran against",
        )
    try:
        datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"--run-timestamp {timestamp!r} is not a parseable ISO-8601 timestamp",
            "pass a timestamp like 2026-08-31T10:00:00Z",
        ) from exc


def _build_run(args: argparse.Namespace) -> RunReference | None:
    commit = args.run_commit
    timestamp = args.run_timestamp
    if commit is None and timestamp is None:
        return None
    if commit is None or timestamp is None:
        missing = "--run-commit" if commit is None else "--run-timestamp"
        raise DevagueError(
            EXIT_USER_ERROR,
            f"missing {missing}",
            "a run reference needs both --run-commit and --run-timestamp, or neither",
        )
    _validate_run_shape(commit, timestamp)
    return RunReference(timestamp=timestamp, commit=commit)


def _record(args: argparse.Namespace) -> int:
    missing = []
    if not args.test:
        missing.append("--test")
    if not args.behavior:
        missing.append("--behavior")
    if not args.contract:
        missing.append("--contract")
    if not args.type:
        missing.append("--type")
    if not args.strength:
        missing.append("--strength")
    if not args.basis:
        missing.append("--basis")
    if not args.outcome:
        missing.append("--outcome")
    if missing:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"missing {', '.join(missing)}",
            'pass --test "<test ref>" --behavior "<asserted behavior>" '
            '--contract "<claim/criterion text>" --type <type> --strength '
            '<level> --basis "<why>" --outcome pass|fail',
        )
    run = _build_run(args)
    if run is None and args.strength in RUN_REQUIRED_STRENGTHS:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"strength {args.strength!r} requires a run reference",
            "pass --run-commit <sha> --run-timestamp <ISO-8601> "
            "(execution/sensitivity strength asserts something about an actual run)",
        )
    plan = resolve_plan(args.plan)
    delivery = resolve_delivery(plan.slug)
    try:
        rec = delivery.add_evidence(
            args.obligation,
            args.test,
            args.behavior,
            args.contract,
            args.type,
            args.strength,
            args.basis,
            args.outcome,
            run=run,
            origin=args.origin or "user",
        )
    except ValueError as exc:
        raise DevagueError(EXIT_USER_ERROR, str(exc), "check the evidence fields") from exc
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result(_record_dict(rec), json_mode=True)
    else:
        emit_result(f"filed {rec.id} ({rec.status})", json_mode=False)
    return 0


def _resolve_status(args: argparse.Namespace, eid: str, status: str) -> int:
    slug = _plan_slug(args)
    delivery = resolve_delivery(slug)
    rec = delivery.find_evidence(eid)
    if rec is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such evidence: {eid}",
            "run 'devague evidence --list' to see filed evidence ids",
        )
    if rec.status != "proposed":
        raise DevagueError(
            EXIT_USER_ERROR,
            f"evidence {eid} is already {rec.status}",
            f"only a 'proposed' evidence record can be confirmed/rejected — "
            f"{eid} is already {rec.status}",
        )
    delivery.set_evidence_status(eid, status)
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result({"id": eid, "status": status}, json_mode=True)
    else:
        emit_result(f"{eid} -> {status}", json_mode=False)
    return 0


def _list(args: argparse.Namespace) -> int:
    slug = _plan_slug(args)
    delivery = resolve_delivery(slug)
    records = delivery.evidence
    if getattr(args, "json", False):
        emit_result(
            {"plan": slug, "evidence": [_record_dict(r) for r in records]},
            json_mode=True,
        )
    elif not records:
        emit_result("no evidence filed yet", json_mode=False)
    else:
        lines = []
        for r in records:
            lines.append(
                f"{r.id}: {r.obligation_ref} <- {r.test_ref} "
                f"[{r.strength}/{r.outcome}] ({r.status})"
            )
        emit_result("\n".join(lines), json_mode=False)
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    if (args.confirm or args.reject) and args.obligation:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --confirm/--reject with record flags",
            "resolve and record are separate moves: run "
            "'devague evidence --confirm <id>' (or --reject), then "
            "'devague evidence --obligation <oN> --test <ref> --behavior ...'",
        )
    if args.list and args.obligation:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --list with record flags",
            "list and record are separate moves: run 'devague evidence --list' "
            "or 'devague evidence --obligation <oN> --test <ref> --behavior ...'",
        )
    # Record-only flags with no --obligation given must never fall through to
    # listing (the lapse/obligation-ledger precedent, PR #101) — a silent
    # no-op is the worst failure available for a ledger whose premise is that
    # filing is cheap enough to do mid-flight.
    if not args.obligation:
        given = [
            flag
            for flag, value in (
                ("--test", args.test),
                ("--behavior", args.behavior),
                ("--contract", args.contract),
                ("--type", args.type),
                ("--strength", args.strength),
                ("--basis", args.basis),
                ("--outcome", args.outcome),
                ("--run-commit", args.run_commit),
                ("--run-timestamp", args.run_timestamp),
                ("--origin", args.origin),
            )
            if value
        ]
        if given:
            raise DevagueError(
                EXIT_USER_ERROR,
                f"{', '.join(given)} given without --obligation to file",
                "file the evidence in one move: devague evidence --obligation "
                "<oN> --test <ref> --behavior ... , or drop the flags to list",
            )
    if args.confirm:
        return _resolve_status(args, args.confirm, "approved")
    if args.reject:
        return _resolve_status(args, args.reject, "rejected")
    if args.obligation:
        return _record(args)
    return _list(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("evidence", help="File, list, or adjudicate an evidence record.")
    p.add_argument("--obligation", help="Obligation ref this evidence satisfies (e.g. o1).")
    p.add_argument("--test", help="Test ref that asserts the behavior (e.g. a test node id).")
    p.add_argument("--behavior", help="The behavior the named test actually asserts, quoted.")
    p.add_argument(
        "--contract",
        help="Snapshot of the claim/acceptance-criterion text at filing time.",
    )
    p.add_argument("--type", choices=EVIDENCE_TYPES, help="What kind of evidence this is.")
    p.add_argument("--strength", choices=STRENGTH_LEVELS, help="The evidence strength level.")
    p.add_argument("--basis", help="Why this strength level was earned, recorded verbatim.")
    p.add_argument("--outcome", choices=EVIDENCE_OUTCOMES, help="pass or fail, recorded verbatim.")
    p.add_argument("--run-commit", help="Commit SHA the test last ran against (7-40 hex chars).")
    p.add_argument("--run-timestamp", help="ISO-8601 timestamp of that run.")
    # default=None (not "user") so an explicitly-passed --origin is
    # distinguishable from the default — cmd_evidence needs that to tell
    # record intent from a bare list, mirroring oblige.py.
    p.add_argument("--origin", choices=ORIGINS, default=None, help="Who proposed it.")
    resolution = p.add_mutually_exclusive_group()
    resolution.add_argument(
        "--confirm", metavar="ID", help="Approve a proposed evidence id (user-only)."
    )
    resolution.add_argument("--reject", metavar="ID", help="Reject an evidence id (user-only).")
    resolution.add_argument("--list", action="store_true", help="List filed evidence (default).")
    p.add_argument("--plan", help="Plan slug (default: current plan).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_evidence)
