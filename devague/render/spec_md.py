"""Renderer: the buildable spec as markdown, derived from a converged frame."""

from __future__ import annotations

from devague.frame import Frame


def _texts(frame: Frame, kind: str) -> list[str]:
    return [c.text for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def render_spec(frame: Frame) -> str:
    out: list[str] = [f"# {frame.title}", ""]
    ann = _texts(frame, "announcement")
    if ann:
        out += ["> " + ann[0], ""]
    aud = _texts(frame, "audience")
    if aud:
        out += ["## Audience", "", *[f"- {t}" for t in aud], ""]
    befores = _texts(frame, "before_state")
    afters = _texts(frame, "after_state")
    if befores or afters:
        out += ["## Before → After", ""]
        out += [f"- Before: {t}" for t in befores]
        out += [f"- After: {t}" for t in afters]
        out.append("")
    why = _texts(frame, "why_it_matters")
    if why:
        out += ["## Why it matters", "", *[f"- {t}" for t in why], ""]
    reqs = [h.text for c in frame.claims for h in c.honesty_conditions if h.status == "confirmed"]
    if reqs:
        out += ["## Requirements / honesty conditions", "", *[f"- {t}" for t in reqs], ""]
    succ = _texts(frame, "success_signal")
    if succ:
        out += ["## Success signals", "", *[f"- {t}" for t in succ], ""]
    bnd = _texts(frame, "boundary")
    if bnd:
        out += ["## Non-goals", "", *[f"- {t}" for t in bnd], ""]
    hqs = [q for c in frame.claims for q in c.hard_questions]
    if hqs:
        out += [
            "## Hard questions",
            "",
            *[f"- {q.text}" + (" (blocking)" if q.blocking else "") for q in hqs],
            "",
        ]
    follow = [v.text for v in frame.open_vagueness if v.kind in ("follow_up", "out_of_scope")]
    if follow:
        out += ["## Open / follow-up", "", *[f"- {t}" for t in follow], ""]
    return "\n".join(out).rstrip() + "\n"
