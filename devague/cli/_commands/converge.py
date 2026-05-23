"""``devague converge`` — evaluate the convergence gate."""

from __future__ import annotations

import argparse

from devague import store
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.convergence import evaluate


def cmd_converge(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    result = evaluate(frame)
    if result.ready and frame.status == "drafting":
        frame.status = "converged"
        store.save(frame)
    elif not result.ready and frame.status == "converged":
        frame.status = "drafting"
        store.save(frame)
    if getattr(args, "json", False):
        emit_result(
            {
                "ready_for_spec": result.ready,
                "blockers": result.blockers,
                "warnings": result.warnings,
                "parked_items": result.parked_items,
                "required_next_moves": result.required_next_moves,
            },
            json_mode=True,
        )
    elif result.ready:
        msg = "converged ✓"
        if result.warnings:
            msg += "\nwarnings:\n" + "\n".join(f"  - {w}" for w in result.warnings)
        emit_result(msg, json_mode=False)
    else:
        lines = "\n".join(f"  - {b}" for b in result.blockers)
        emit_result("not converged:\n" + lines, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("converge", help="Check whether the frame can export a spec.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_converge)
