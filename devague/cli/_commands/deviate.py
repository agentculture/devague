"""``devague deviate`` — record an execution-time deviation from a confirmed plan.

The execution-seam move (#53 esd t3): while `assign-to-workforce` fans out a
converged plan's tasks, reality sometimes departs from what the plan said. This
move records that departure as a first-class, append-only ledger entry instead
of silently rewriting the plan the user confirmed — the plan itself is never
touched (see `devague/delivery_store.py`).

Recording is deterministic: no LLM calls, no subprocess. Origin drives the
initial status exactly like a claim or a task: ``--origin llm`` lands
``proposed`` and needs an explicit user ``--confirm``; a user-authored record
(the default) auto-approves. ``--confirm`` / ``--reject`` are therefore the
only way a proposed deviation is resolved, mirroring the frame/plan
anti-fabrication rule that LLM proposals never self-confirm.
"""

from __future__ import annotations

import argparse

from devague import delivery_store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._output import emit_result
from devague.cli._plans import resolve_plan
from devague.delivery import CLASSIFICATIONS, ORIGINS


def _record_dict(rec) -> dict:
    return {
        "id": rec.id,
        "what": rec.what,
        "task": rec.task_ref,
        "reason": rec.reason,
        "affects": rec.affects,
        "origin": rec.origin,
        "status": rec.status,
        "classification": rec.classification,
    }


def _plan_slug(args: argparse.Namespace) -> str:
    return resolve_plan(args.plan).slug


def _record(args: argparse.Namespace) -> int:
    if not args.reason:
        raise DevagueError(
            EXIT_USER_ERROR,
            "missing --reason",
            'pass --reason "<text>" explaining why the deviation happened',
        )
    if not args.task:
        raise DevagueError(
            EXIT_USER_ERROR,
            "missing --task",
            "pass --task <tN> naming the plan item this deviation relates to",
        )
    slug = _plan_slug(args)
    delivery = delivery_store.load_or_new(slug)
    rec = delivery.add_deviation(
        args.what,
        args.task,
        args.reason,
        affects=args.affects,
        origin=args.origin,
        classification=args.classification,
    )
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result(_record_dict(rec), json_mode=True)
    else:
        emit_result(f"recorded {rec.id} ({rec.status})", json_mode=False)
    return 0


def _resolve_status(args: argparse.Namespace, did: str, status: str) -> int:
    slug = _plan_slug(args)
    delivery = delivery_store.load_or_new(slug)
    if not delivery.set_status(did, status):
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such deviation: {did}",
            "run 'devague deviate --list' to see recorded deviation ids",
        )
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result({"id": did, "status": status}, json_mode=True)
    else:
        emit_result(f"{did} -> {status}", json_mode=False)
    return 0


def _list(args: argparse.Namespace) -> int:
    slug = _plan_slug(args)
    delivery = delivery_store.load_or_new(slug)
    records = delivery.deviations
    if getattr(args, "json", False):
        emit_result(
            {"plan": slug, "deviations": [_record_dict(r) for r in records]},
            json_mode=True,
        )
    elif not records:
        emit_result("no deviations recorded yet", json_mode=False)
    else:
        lines = []
        for r in records:
            line = f"{r.id}: {r.what} (task {r.task_ref}, {r.status})"
            if r.classification:
                line += f" [{r.classification}]"
            lines.append(line)
        emit_result("\n".join(lines), json_mode=False)
    return 0


def cmd_deviate(args: argparse.Namespace) -> int:
    if args.confirm:
        return _resolve_status(args, args.confirm, "approved")
    if args.reject:
        return _resolve_status(args, args.reject, "rejected")
    if args.what:
        return _record(args)
    return _list(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("deviate", help="Record an execution-time deviation from a confirmed plan.")
    p.add_argument("what", nargs="?", help="What deviated (omit with --confirm/--reject/--list).")
    p.add_argument("--task", help="Plan item ref this deviation relates to (e.g. t3).")
    p.add_argument("--reason", help="Why the deviation happened.")
    p.add_argument(
        "--affects",
        action="append",
        default=None,
        metavar="REF",
        help="A plan item ref this deviation affects (repeatable).",
    )
    p.add_argument(
        "--classification",
        choices=CLASSIFICATIONS,
        help="Optional risk classification (feeds the drift-entry contract).",
    )
    p.add_argument("--origin", choices=ORIGINS, default="user", help="Who proposed it.")
    p.add_argument("--confirm", metavar="ID", help="Approve a proposed deviation id (user-only).")
    p.add_argument("--reject", metavar="ID", help="Reject a deviation id (user-only).")
    p.add_argument("--list", action="store_true", help="List recorded deviations (default).")
    p.add_argument("--plan", help="Plan slug (default: current plan).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_deviate)
