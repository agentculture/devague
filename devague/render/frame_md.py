"""Renderer: the Announcement Frame as markdown."""

from __future__ import annotations

from devague.frame import Frame

_SECTIONS = [
    ("announcement", "Announcement"),
    ("audience", "Audience"),
    ("after_state", "After-state experience"),
    ("why_it_matters", "Why it matters"),
    ("before_state", "Before-state pain"),
    ("boundary", "Boundaries / non-goals"),
    ("success_signal", "Success signals"),
    ("open_question", "Open questions"),
]


def _claim_lines(claim) -> list[str]:
    mark = "" if claim.status == "confirmed" else f" _({claim.status})_"
    lines = [f"- {claim.text}{mark}"]
    for h in claim.honesty_conditions:
        hm = "" if h.status == "confirmed" else f" _({h.status})_"
        lines.append(f"  - honesty: {h.text}{hm}")
    for q in claim.hard_questions:
        qm = "blocking" if q.blocking else "open"
        lines.append(f"  - Q ({qm}): {q.text}")
    return lines


def _section_lines(frame: Frame, kind: str, heading: str) -> list[str]:
    claims = [c for c in frame.claims if c.kind == kind and c.status != "rejected"]
    if not claims:
        return []
    lines = [f"## {heading}"]
    for c in claims:
        lines.extend(_claim_lines(c))
    lines.append("")
    return lines


def _vagueness_lines(frame: Frame) -> list[str]:
    if not frame.open_vagueness:
        return []
    lines = ["## Open vagueness"]
    lines.extend(f"- [{v.kind}] {v.text}" for v in frame.open_vagueness)
    lines.append("")
    return lines


def render_frame(frame: Frame) -> str:
    out = [
        f"# Announcement Frame — {frame.title}",
        "",
        f"_slug: {frame.slug} · status: {frame.status}_",
        "",
    ]
    for kind, heading in _SECTIONS:
        out.extend(_section_lines(frame, kind, heading))
    out.extend(_vagueness_lines(frame))
    return "\n".join(out).rstrip() + "\n"
