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


def render_frame(frame: Frame) -> str:
    out = [
        f"# Announcement Frame — {frame.title}",
        "",
        f"_slug: {frame.slug} · status: {frame.status}_",
        "",
    ]
    for kind, heading in _SECTIONS:
        claims = [c for c in frame.claims if c.kind == kind and c.status != "rejected"]
        if not claims:
            continue
        out.append(f"## {heading}")
        for c in claims:
            mark = "" if c.status == "confirmed" else f" _({c.status})_"
            out.append(f"- {c.text}{mark}")
            for h in c.honesty_conditions:
                hm = "" if h.status == "confirmed" else f" _({h.status})_"
                out.append(f"  - honesty: {h.text}{hm}")
            for q in c.hard_questions:
                qm = "blocking" if q.blocking else "open"
                out.append(f"  - Q ({qm}): {q.text}")
        out.append("")
    if frame.open_vagueness:
        out.append("## Open vagueness")
        for v in frame.open_vagueness:
            out.append(f"- [{v.kind}] {v.text}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
