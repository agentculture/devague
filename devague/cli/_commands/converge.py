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
    if result.passed and frame.status == "drafting":
        frame.status = "converged"
        store.save(frame)
    if getattr(args, "json", False):
        emit_result({"passed": result.passed, "missing": result.missing}, json_mode=True)
    elif result.passed:
        emit_result("converged ✓", json_mode=False)
    else:
        emit_result(
            "not converged:\n" + "\n".join(f"  - {m}" for m in result.missing), json_mode=False
        )
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("converge", help="Check whether the frame can export a spec.")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_converge)
