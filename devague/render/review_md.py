"""Renderer: the human-review artifact — every *proposed* (unconfirmed) item.

Explicitly NON-authoritative and distinct from spec-md: it exists so a human can
review LLM proposals (in-terminal or out of band) before confirming any. Nothing
here is authoritative until the user runs ``devague confirm``. See issue #17.
"""

from __future__ import annotations

from devague.frame import Frame

_BANNER = (
    "> **Review artifact — nothing confirmed yet.** These are unconfirmed, "
    "LLM-proposed items; they are NOT authoritative and NOT a buildable spec. "
    "Confirm or reject each with `devague confirm <id>` / `devague reject <id>`."
)


def proposed_claims(frame: Frame) -> list:
    return [c for c in frame.claims if c.status == "proposed"]


def proposed_honesty(frame: Frame) -> list:
    return [(c, h) for c in frame.claims for h in c.honesty_conditions if h.status == "proposed"]


def render_review(frame: Frame) -> str:
    out: list[str] = [f"# Review — {frame.title}", "", _BANNER, ""]
    claims = proposed_claims(frame)
    pairs = proposed_honesty(frame)
    if not claims and not pairs:
        out += ["No proposed items — nothing awaiting review.", ""]
        return "\n".join(out).rstrip() + "\n"
    if claims:
        out += ["## Proposed claims", ""]
        out += [f"- `{c.id}` ({c.kind}): {c.text}" for c in claims]
        out += [""]
    if pairs:
        out += ["## Proposed honesty conditions", ""]
        out += [f"- `{h.id}` (on `{c.id}` {c.kind}): {h.text}" for c, h in pairs]
        out += [""]
    return "\n".join(out).rstrip() + "\n"
