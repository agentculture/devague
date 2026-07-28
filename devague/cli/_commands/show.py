"""``devague show`` — render the current frame (markdown, or --json for raw state)."""

from __future__ import annotations

import argparse

from devague import render
from devague.cli._frames import resolve
from devague.cli._output import emit_diagnostic, emit_result
from devague.contested import find_contested_markers, marker_to_dict, sorted_markers
from devague.frame import to_dict


def _contested_line(m) -> str:
    line = f"contested: {m.claim_id} by {m.deviation_id}"
    if m.classification:
        line += f" ({m.classification})"
    return f"{line}: {m.reason}"


def cmd_show(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)
    # Contested-by-deviation derivation (#92): read-only, fails open — a
    # broken plan/delivery ledger anywhere in the join degrades to "no
    # markers from that source" plus a stderr diagnostic, never a crash.
    markers, diagnostics = find_contested_markers(frame)
    for diag in diagnostics:
        emit_diagnostic(diag)
    flat = sorted_markers(markers)
    if getattr(args, "json", False):
        payload = to_dict(frame)
        payload["contested"] = [marker_to_dict(m) for m in flat]
        emit_result(payload, json_mode=True)
    else:
        text = render.render(frame, args.format)
        if flat:
            text = text.rstrip("\n") + "\n\n" + "\n".join(_contested_line(m) for m in flat) + "\n"
        emit_result(text, json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("show", help="Render the current frame.")
    p.add_argument("--format", default="frame-md", help="Renderer format (default: frame-md).")
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit the raw frame as JSON, plus a derived 'contested' list (#92).",
    )
    p.set_defaults(func=cmd_show)
