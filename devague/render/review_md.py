"""Renderer + parser for the human-review artifact — every *proposed* item.

Explicitly NON-authoritative and distinct from spec-md: it exists so a human can
review LLM proposals (in-terminal or out of band) before confirming any. Nothing
here is authoritative until the user runs ``devague confirm``. See issue #17.

The artifact is **round-trippable**: each proposed item is emitted with a leading
``pending`` marker. Edit a line's marker to ``confirm`` or ``reject``, then feed
the file to ``devague confirm --from-review <file>`` to apply exactly those
decisions (``render_review`` ⇄ :func:`parse_decisions`).
"""

from __future__ import annotations

import re

from devague.frame import Frame

# A decision line: "- <marker> `<id>` ...". The marker is the only editable part.
_DECISIONS = ("pending", "confirm", "reject")
_LINE = re.compile(r"^- (?P<decision>pending|confirm|reject)\s+`(?P<id>[ch]\d+)`")

_BANNER = (
    "> **Review artifact — nothing confirmed yet.** These are unconfirmed, "
    "LLM-proposed items; they are NOT authoritative and NOT a buildable spec. "
    "To apply, change a line's `pending` to `confirm` or `reject`, then run "
    "`devague confirm --from-review <file>` (or `devague confirm <id> ...`)."
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
        out += [f"- pending `{c.id}` ({c.kind}): {c.text}" for c in claims]
        out += [""]
    if pairs:
        out += ["## Proposed honesty conditions", ""]
        out += [f"- pending `{h.id}` (on `{c.id}` {c.kind}): {h.text}" for c, h in pairs]
        out += [""]
    return "\n".join(out).rstrip() + "\n"


def parse_decisions(text: str) -> dict[str, str]:
    """Parse a (possibly edited) review artifact into ``{id: "confirm"|"reject"}``.

    ``pending`` lines carry no decision and are skipped — applying a review file
    therefore touches only what the human explicitly marked (no auto-confirm).
    Raises ``ValueError`` on a duplicate, conflicting decision for one id.
    """
    decisions: dict[str, str] = {}
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        decision, item_id = m.group("decision"), m.group("id")
        if decision == "pending":
            continue
        if item_id in decisions and decisions[item_id] != decision:
            prior = decisions[item_id]
            raise ValueError(f"conflicting decisions for {item_id}: {prior} vs {decision}")
        decisions[item_id] = decision
    return decisions
