"""``devague delta`` — file, list, supersede, retract, or adjudicate a
behavioral delta.

Bvts t6: the CLI twin of ``Delivery.add_delta`` / ``DeltaRecord`` and
``Delivery.supersede`` / ``Delivery.retract_supersession`` (bvts t3,
:mod:`devague.delivery`). Structurally it clones
:mod:`devague.cli._commands.evidence`'s file/list/confirm/reject shape
(``--kind`` plays the "record trigger" role ``--obligation`` plays there) and
:mod:`devague.cli._commands.deviate`'s plan resolution and ref-validation
pattern — the ``ID_SHAPED_RE`` / ``refuse_unless_known`` helpers now live in
:mod:`devague.cli._refs` precisely so this module reuses them rather than
re-deriving them (the dep on t5/evidence is registration adjacency only; the
dep on deviate is the shared ref-validation helper).

Recording is deterministic: no LLM calls, nothing runs a test or touches the
frame/plan beyond reading ids to validate against. Origin drives the initial
status exactly like every other ledger move: ``--origin llm`` lands
``proposed`` and needs an explicit user ``--confirm``; a user-authored record
(the default) auto-approves.

Append-only, on the same terms as ``evidence``/``deviate``/``lapse``: there is
no amend and no delete for a filed delta. The only mutations after filing are
adjudication (``--confirm``/``--reject``) and the ``superseded`` flag, and the
flag is *never* touched directly — it only moves via a first-class,
append-only :class:`~devague.delivery.SupersessionEvent`
(``--supersede``/``--retract``), pinned by
``tests/test_cli_delta.py::test_supersede_and_retract_never_edit_record_content``.

Ref validation (acceptance criterion 1): ``--caused-by`` is required at
filing (mirrors ``Delivery.add_delta``'s own guard) and each ref is checked
by shape — a claim-shaped ref (``c14``) must resolve against the plan's live
source frame's claims; a deviation-shaped ref (``d2``) must resolve against
an *approved* deviation in this plan's delivery ledger (today.py's lineage
walk treats a delta's ``caused_by`` as real provenance, so an unresolvable
one is refused the same way ``deviate --affects`` refuses a typo); a
delta-shaped ref (``b7``) must resolve against an existing delta in this
ledger (a delta can cite an earlier delta as its predecessor — the lineage
link ``devague/today.py`` walks). A *qualified* ref (``<plan-slug>:b7``)
points across ledgers, which this CLI has no view of at filing time (only
``devague today``'s fail-open walk resolves those) — it is accepted without
validation, exactly like free-form prose that is not id-shaped at all.
``--evidence`` refs are stored verbatim and never validated here, mirroring
``Delivery.add_delta``'s own choice not to resolve them at filing (evidence
often lands after the delta).
"""

from __future__ import annotations

import argparse

from devague import delivery_store
from devague.cli._deliveries import resolve_delivery
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._output import emit_result
from devague.cli._plans import resolve_plan
from devague.cli._refs import load_source_frame, refuse_unless_known
from devague.delivery import DELTA_KINDS, ORIGINS


def _record_dict(rec) -> dict:
    return {
        "id": rec.id,
        "kind": rec.kind,
        "behavior_text": rec.behavior_text,
        "caused_by": rec.caused_by,
        "evidence_refs": rec.evidence_refs,
        "origin": rec.origin,
        "status": rec.status,
        "superseded": rec.superseded,
    }


def _event_dict(event) -> dict:
    return {
        "id": event.id,
        "action": event.action,
        "target_ref": event.target_ref,
        "replacement_ref": event.replacement_ref,
        "origin": event.origin,
    }


def _plan_slug(args: argparse.Namespace) -> str:
    return resolve_plan(args.plan).slug


def _validate_caused_by(plan, delivery, refs: list[str]) -> None:
    """Refuse a ``--caused-by`` ref that looks like an id but isn't one.

    A qualified ref (``slug:b7``) is a cross-ledger pointer this CLI has no
    view of at filing time — it is always allowed, exactly like free-form
    prose. A bare id-shaped ref is checked by prefix against the one family
    it could plausibly name.
    """
    frame = load_source_frame(plan.frame_slug)
    known_claims = {c.id for c in frame.claims} if frame is not None else set()
    known_deviations = {d.id for d in delivery.deviations if d.status == "approved"}
    known_deltas = {b.id for b in delivery.deltas}
    for ref in refs:
        if ":" in ref:
            continue
        if ref[:1] == "c" and ref[1:].isdigit():
            refuse_unless_known(
                ref,
                known_claims,
                flag="--caused-by",
                what="a claim id on the plan's live source frame",
                hint="run 'devague show' to see the frame's claim ids",
            )
        elif ref[:1] == "d" and ref[1:].isdigit():
            refuse_unless_known(
                ref,
                known_deviations,
                flag="--caused-by",
                what="an approved deviation id on this plan's delivery ledger",
                hint="run 'devague deviate --list' to see recorded deviation ids "
                "(only an approved deviation is real provenance)",
            )
        elif ref[:1] == "b" and ref[1:].isdigit():
            refuse_unless_known(
                ref,
                known_deltas,
                flag="--caused-by",
                what="an existing delta id on this plan's delivery ledger",
                hint="run 'devague delta --list' to see filed delta ids",
            )
        # Any other id-shaped ref (t3, h5, r1, ...) is left alone: caused_by
        # only names claims, approved deviations, or prior deltas, so nothing
        # else claims a specific known-ids family to be checked against.


def _record(args: argparse.Namespace) -> int:
    missing = []
    if not args.behavior:
        missing.append("--behavior")
    if not args.caused_by:
        missing.append("--caused-by")
    if missing:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"missing {', '.join(missing)}",
            'pass --kind added|amended|removed --behavior "<text>" '
            "--caused-by <ref> [--caused-by <ref> ...]",
        )
    plan = resolve_plan(args.plan)
    delivery = resolve_delivery(plan.slug)
    _validate_caused_by(plan, delivery, args.caused_by)
    try:
        rec = delivery.add_delta(
            args.kind,
            args.behavior,
            caused_by=args.caused_by,
            evidence_refs=args.evidence,
            origin=args.origin or "user",
        )
    except ValueError as exc:
        raise DevagueError(EXIT_USER_ERROR, str(exc), "check the delta fields") from exc
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result(_record_dict(rec), json_mode=True)
    else:
        emit_result(f"filed {rec.id} ({rec.status})", json_mode=False)
    return 0


def _supersede(args: argparse.Namespace) -> int:
    slug = _plan_slug(args)
    delivery = resolve_delivery(slug)
    try:
        event = delivery.supersede(
            args.supersede, replacement_ref=args.replacement, origin=args.origin or "user"
        )
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "run 'devague delta --list' to see filed evidence/delta ids",
        ) from exc
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result(_event_dict(event), json_mode=True)
    else:
        emit_result(f"{event.id}: {args.supersede} superseded", json_mode=False)
    return 0


def _retract(args: argparse.Namespace) -> int:
    slug = _plan_slug(args)
    delivery = resolve_delivery(slug)
    try:
        event = delivery.retract_supersession(args.retract, origin=args.origin or "user")
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "run 'devague delta --list' to see filed evidence/delta ids",
        ) from exc
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result(_event_dict(event), json_mode=True)
    else:
        emit_result(f"{event.id}: {args.retract} supersession retracted", json_mode=False)
    return 0


def _resolve_status(args: argparse.Namespace, bid: str, status: str) -> int:
    slug = _plan_slug(args)
    delivery = resolve_delivery(slug)
    rec = delivery.find_delta(bid)
    if rec is None:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"no such delta: {bid}",
            "run 'devague delta --list' to see filed delta ids",
        )
    if rec.status != "proposed":
        raise DevagueError(
            EXIT_USER_ERROR,
            f"delta {bid} is already {rec.status}",
            f"only a 'proposed' delta can be confirmed/rejected — {bid} is already {rec.status}",
        )
    delivery.set_delta_status(bid, status)
    delivery_store.save(delivery)
    if getattr(args, "json", False):
        emit_result({"id": bid, "status": status}, json_mode=True)
    else:
        emit_result(f"{bid} -> {status}", json_mode=False)
    return 0


def _list(args: argparse.Namespace) -> int:
    slug = _plan_slug(args)
    delivery = resolve_delivery(slug)
    records = delivery.deltas
    events = delivery.supersessions
    if getattr(args, "json", False):
        emit_result(
            {
                "plan": slug,
                "deltas": [_record_dict(r) for r in records],
                "supersessions": [_event_dict(e) for e in events],
            },
            json_mode=True,
        )
        return 0
    if not records and not events:
        emit_result("no deltas filed yet", json_mode=False)
        return 0
    lines = []
    for r in records:
        state = "superseded" if r.superseded else "live"
        lines.append(f"{r.id}: {r.kind} {r.behavior_text!r} ({r.status}) [{state}]")
    if events:
        lines.append("--- supersession events ---")
        for e in events:
            if e.action == "supersede":
                target = (
                    f"{e.target_ref} -> {e.replacement_ref}" if e.replacement_ref else e.target_ref
                )
                lines.append(f"{e.id}: supersede {target} ({e.origin})")
            else:
                lines.append(f"{e.id}: retract {e.target_ref} ({e.origin})")
    emit_result("\n".join(lines), json_mode=False)
    return 0


def cmd_delta(args: argparse.Namespace) -> int:
    exclusive = [
        name
        for name, value in (
            ("--confirm", args.confirm),
            ("--reject", args.reject),
            ("--supersede", args.supersede),
            ("--retract", args.retract),
        )
        if value
    ]
    if len(exclusive) > 1:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"cannot combine {' and '.join(exclusive)}",
            "run one delta move at a time",
        )
    if exclusive and args.kind:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"cannot combine {exclusive[0]} with record flags",
            "resolve/supersede/retract and record are separate moves",
        )
    if args.list and args.kind:
        raise DevagueError(
            EXIT_USER_ERROR,
            "cannot combine --list with record flags",
            "list and record are separate moves: run 'devague delta --list' "
            "or 'devague delta --kind <kind> --behavior \"<text>\" --caused-by <ref>'",
        )
    # Record-only flags with no --kind given must never fall through to
    # listing (the evidence/lapse-ledger precedent) — a silent no-op is the
    # worst failure available for a ledger whose premise is that filing is
    # cheap enough to do mid-flight.
    if not args.kind and not exclusive:
        given = [
            flag
            for flag, value in (
                ("--behavior", args.behavior),
                ("--caused-by", args.caused_by),
                ("--evidence", args.evidence),
            )
            if value
        ]
        if given:
            raise DevagueError(
                EXIT_USER_ERROR,
                f"{', '.join(given)} given without --kind to file",
                "file the delta in one move: devague delta --kind added|amended|removed "
                '--behavior "<text>" --caused-by <ref> , or drop the flags to list',
            )
    if args.supersede:
        return _supersede(args)
    if args.retract:
        return _retract(args)
    if args.confirm:
        return _resolve_status(args, args.confirm, "approved")
    if args.reject:
        return _resolve_status(args, args.reject, "rejected")
    if args.kind:
        return _record(args)
    return _list(args)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "delta", help="File, list, supersede, retract, or adjudicate a behavioral delta."
    )
    p.add_argument("--kind", choices=DELTA_KINDS, help="added, amended, or removed.")
    p.add_argument("--behavior", help="The behavior added, amended, or removed, in readable text.")
    p.add_argument(
        "--caused-by",
        action="append",
        default=None,
        metavar="REF",
        help="Backward provenance: the claim, approved deviation, or prior delta this "
        "delta traces to (repeatable, required to file).",
    )
    p.add_argument(
        "--evidence",
        action="append",
        default=None,
        metavar="REF",
        help="Forward provenance: an evidence record ref that validates this delta "
        "(repeatable, optional — evidence often lands later).",
    )
    # default=None (not "user") so an explicitly-passed --origin is
    # distinguishable from the default — cmd_delta needs that to tell
    # record/event intent from a bare list, mirroring evidence.py.
    p.add_argument("--origin", choices=ORIGINS, default=None, help="Who proposed it.")
    p.add_argument(
        "--supersede",
        metavar="REF",
        help="Mark an existing evidence/delta record superseded (appends a "
        "supersession event; never edits the target's content).",
    )
    p.add_argument(
        "--replacement",
        metavar="REF",
        help="With --supersede: the record that replaces the superseded one (optional).",
    )
    p.add_argument(
        "--retract",
        metavar="REF",
        help="Clear a record's superseded flag (appends a retraction event; "
        "the flag flips live again).",
    )
    resolution = p.add_mutually_exclusive_group()
    resolution.add_argument(
        "--confirm", metavar="ID", help="Approve a proposed delta id (user-only)."
    )
    resolution.add_argument("--reject", metavar="ID", help="Reject a delta id (user-only).")
    resolution.add_argument("--list", action="store_true", help="List filed deltas (default).")
    p.add_argument("--plan", help="Plan slug (default: current plan).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_delta)
