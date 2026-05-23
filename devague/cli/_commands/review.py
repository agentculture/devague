"""``devague review`` — surface every *proposed* (unconfirmed) item for human review.

Lists proposed claims and proposed honesty conditions with their ids. It is
deliberately NOT gated on convergence and never mutates state — it is a
read-only view of what is awaiting a user decision (issue #17). Confirm/reject
the listed ids with ``devague confirm`` / ``devague reject``.
"""

from __future__ import annotations

import argparse

from devague import render, store
from devague.cli._frames import resolve
from devague.cli._output import emit_diagnostic, emit_result
from devague.render.review_md import proposed_claims, proposed_honesty


def _json_payload(frame) -> dict:
    return {
        "slug": frame.slug,
        "proposed_claims": [
            {"id": c.id, "kind": c.kind, "text": c.text} for c in proposed_claims(frame)
        ],
        "proposed_honesty": [
            {"id": h.id, "claim_id": c.id, "claim_kind": c.kind, "text": h.text}
            for c, h in proposed_honesty(frame)
        ],
    }


def cmd_review(args: argparse.Namespace) -> int:
    frame = resolve(args.frame)  # read-only: the frame is never saved/converged
    artifact = render.render(frame, "review-md")
    path = None
    if not getattr(args, "no_write", False):
        # Persist a durable, NON-authoritative artifact to uncommitted working
        # state (.devague/reviews/<slug>.md) — distinct from docs/specs/.
        path = store.write_review(frame.slug, artifact)
    if getattr(args, "json", False):
        payload = _json_payload(frame)
        payload["path"] = str(path) if path else None
        emit_result(payload, json_mode=True)
    else:
        emit_result(artifact, json_mode=False)
        if path:
            emit_diagnostic(f"wrote review artifact to {path} (unconfirmed, not authoritative)")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "review",
        help="List proposed (unconfirmed) claims + honesty conditions for human review.",
    )
    p.add_argument("--frame", help="Frame slug (default: current).")
    p.add_argument("--json", action="store_true", help="Emit structured JSON.")
    p.add_argument(
        "--no-write",
        action="store_true",
        help="Print only; do not persist .devague/reviews/<slug>.md.",
    )
    p.set_defaults(func=cmd_review)
