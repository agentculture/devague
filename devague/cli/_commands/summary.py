"""``devague summary`` — render a delivery-summary skeleton from state alone.

The execution-seam wrap-up leg (#53-esd t4): a render-only view over a plan, its
live source frame, and its delivery (deviation) store, producing the eight-section
skeleton the ``summarize-delivery`` skill starts from instead of hand-assembling
the baseline. See :mod:`devague.render.summary_md` for the rendering logic and the
no-overclaim rules it enforces.

Read-only: no store is ever saved here. ``--pr`` swaps in the condensed PR-body
skeleton (:func:`devague.render.summary_md.render_pr_summary`); ``--json`` emits
the structured equivalent of whichever mode is selected.
"""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._deliveries import resolve_delivery
from devague.cli._output import emit_diagnostic, emit_result
from devague.cli._plans import resolve_plan
from devague.frame import Frame
from devague.plan import Plan
from devague.render import summary_md
from devague.staleness import find_staleness


def _load_source_frame(frame_slug: str) -> Frame | None:
    """Best-effort load of the plan's source frame; degrade to ``None`` when it is
    gone or corrupt, mirroring ``cmd_plan_show``'s graceful degradation."""
    try:
        return store.load(frame_slug)
    except (FileNotFoundError, ValueError):
        return None


def cmd_summary(args: argparse.Namespace) -> int:
    plan: Plan = resolve_plan(args.plan)
    frame = _load_source_frame(plan.frame_slug)
    delivery = resolve_delivery(plan.slug)
    json_mode = getattr(args, "json", False)

    # Staleness derivation (#97/bvts t8), loaded at the edge exactly like
    # ``cli/_commands/status.py`` loads it: fails open, so a broken plan or
    # delivery ledger anywhere in the join degrades to "no findings from that
    # source" plus a stderr diagnostic, never a crash — and it needs a real
    # frame to join against (no frame, no staleness to derive).
    stale_devs: list = []
    orphaned: list = []
    if frame is not None:
        stale_devs, orphaned, staleness_diags = find_staleness(frame)
        for diag in staleness_diags:
            emit_diagnostic(diag)

    # A single return path (SonarCloud python:S3516 — a function with several
    # `return 0` branches always returning the same literal value): select
    # which payload to emit, then emit and return once. `_dispatch` treats a
    # `None` return as success (exit 0) exactly like an explicit `return 0`,
    # so the CLI contract is unchanged.
    if args.pr and json_mode:
        emit_result(summary_md.pr_data(plan, frame, delivery), json_mode=True)
    elif args.pr:
        emit_result(summary_md.render_pr_summary(plan, frame, delivery), json_mode=False)
    elif json_mode:
        emit_result(
            summary_md.summary_data(plan, frame, delivery, stale_devs, orphaned), json_mode=True
        )
    else:
        emit_result(
            summary_md.render_summary(plan, frame, delivery, stale_devs, orphaned), json_mode=False
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "summary",
        help="Render a delivery-summary skeleton from plan/frame/delivery state (read-only).",
    )
    p.add_argument("--plan", help="Plan slug (default: current plan).")
    p.add_argument("--pr", action="store_true", help="Emit the condensed PR-body skeleton instead.")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_summary)
