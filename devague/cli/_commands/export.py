"""``devague export`` — write the buildable spec, only if the frame has converged."""

from __future__ import annotations

import argparse
from pathlib import Path

from devague import render, store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.cli._frames import resolve
from devague.cli._output import emit_result
from devague.convergence import evaluate

SPECS_DIR = Path("docs/specs")


def cmd_export(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    result = evaluate(frame)
    if not result.ready:
        raise DevagueError(
            EXIT_USER_ERROR,
            "frame has not converged; cannot export",
            "resolve: " + "; ".join(result.blockers),
        )
    text = render.render(frame, args.format)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SPECS_DIR / f"{frame.slug}.md"
    out_path.write_text(text, encoding="utf-8")
    frame.status = "exported"
    store.save(frame)
    if getattr(args, "json", False):
        emit_result({"path": str(out_path), "format": args.format}, json_mode=True)
    else:
        emit_result(f"exported spec to {out_path}", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("export", help="Export the buildable spec (requires convergence).")
    p.add_argument(
        "--format",
        default="spec-md",
        choices=("spec-md",),
        help="Renderer format (default: spec-md).",
    )
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.set_defaults(func=cmd_export)
