"""Renderer: the Announcement Frame as markdown."""

from __future__ import annotations

from devague.frame import Frame, Vagueness

_SECTIONS = [
    ("announcement", "Announcement"),
    ("audience", "Audience"),
    ("after_state", "After-state experience"),
    ("why_it_matters", "Why it matters"),
    ("before_state", "Before-state pain"),
    ("requirement", "Requirements"),
    ("assumption", "Assumptions"),
    ("success_signal", "Success signals"),
    ("boundary", "Boundaries"),
    ("non_goal", "Non-goals"),
    ("decision", "Decisions"),
    ("open_question", "Open questions"),
]


def _instruction_lines(instruction: str, indent: str = "  ") -> list[str]:
    """A nested ``- instruction: <verbatim text>`` bullet under an item, or nothing
    when the item carries no instruction — never fabricated filler (#53 t1/t6,
    c10/h3).
    """
    return [f"{indent}- instruction: {instruction}"] if instruction else []


def _claim_lines(claim) -> list[str]:
    mark = "" if claim.status == "confirmed" else f" _({claim.status})_"
    lines = [f"- {claim.text}{mark}"]
    lines += _instruction_lines(claim.instruction)
    for h in claim.honesty_conditions:
        hm = "" if h.status == "confirmed" else f" _({h.status})_"
        lines.append(f"  - honesty: {h.text}{hm}")
        lines += _instruction_lines(h.instruction, indent="    ")
    for q in claim.hard_questions:
        qm = "blocking" if q.blocking else "open"
        lines.append(f"  - Q ({qm}): {q.text}")
    return lines


def _section_lines(frame: Frame, kind: str, heading: str) -> list[str]:
    claims = [c for c in frame.claims if c.kind == kind and c.status != "rejected"]
    if not claims:
        return []
    lines = [f"## {heading}", ""]
    for c in claims:
        lines.extend(_claim_lines(c))
    lines.append("")
    return lines


def _vagueness_bullet(v: Vagueness) -> str:
    """A single ``open_vagueness`` bullet: plain for an item still open, or
    carrying its resolution text for a resolved one (resolve-parked-vagueness
    t7). The flat list stays a single section — resolved items are not split
    into their own heading here (spec_md's ``Resolved vagueness`` subsection is
    the polished-export treatment; frame_md is the working-state view). An
    already-resolved item with no resolution text renders the plain form —
    never a fabricated ``— resolved:`` with nothing after it.
    """
    base = f"- [{v.kind}] {v.text}"
    if v.resolved and v.resolution:
        return f"{base} — resolved: {v.resolution}"
    return base


def _vagueness_lines(frame: Frame) -> list[str]:
    if not frame.open_vagueness:
        return []
    lines = ["## Open vagueness", ""]
    lines.extend(_vagueness_bullet(v) for v in frame.open_vagueness)
    lines.append("")
    return lines


def _scope_lines(frame: Frame) -> list[str]:
    """Scope-exploration provenance, mirroring spec_md's scope section (#53 t6):
    each recorded surface + finding, with the claim ids it seeded. Empty
    ``scope_entries`` renders nothing.
    """
    if not frame.scope_entries:
        return []
    lines = ["## Scope exploration", ""]
    for e in frame.scope_entries:
        # A surface carrying its own code span cannot be wrapped again (MD038).
        span = e.surface if "`" in e.surface else f"`{e.surface}`"
        lines.append(f"- `{e.id}` — {span}: {e.finding}")
        if e.seeds:
            lines.append(f"  - seeds: {', '.join(f'`{s}`' for s in e.seeds)}")
    lines.append("")
    return lines


def render_frame(frame: Frame) -> str:
    out = [
        f"# Announcement Frame — {frame.title}",
        "",
        f"slug: `{frame.slug}` · status: `{frame.status}`",
        "",
    ]
    for kind, heading in _SECTIONS:
        out.extend(_section_lines(frame, kind, heading))
    out.extend(_scope_lines(frame))
    out.extend(_vagueness_lines(frame))
    return "\n".join(out).rstrip() + "\n"
