"""Renderer: the buildable spec as markdown, derived from a converged frame."""

from __future__ import annotations

from devague.frame import Frame


def _texts(frame: Frame, kind: str) -> list[str]:
    return [c.text for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def _section(heading: str, texts: list[str]) -> list[str]:
    """A standard ``## heading`` + bullet-list block, or nothing when empty."""
    if not texts:
        return []
    return [f"## {heading}", "", *[f"- {t}" for t in texts], ""]


def _before_after(frame: Frame) -> list[str]:
    befores = _texts(frame, "before_state")
    afters = _texts(frame, "after_state")
    if not (befores or afters):
        return []
    lines = ["## Before → After", ""]
    lines += [f"- Before: {t}" for t in befores]
    lines += [f"- After: {t}" for t in afters]
    return lines + [""]


def _confirmed_honesty(frame: Frame) -> list[str]:
    return [h.text for c in frame.claims for h in c.honesty_conditions if h.status == "confirmed"]


def _hard_questions(frame: Frame) -> list[str]:
    hqs = [q for c in frame.claims for q in c.hard_questions]
    bullets = [f"- {q.text}" + (" (blocking)" if q.blocking else "") for q in hqs]
    return ["## Hard questions", "", *bullets, ""] if hqs else []


def _follow_up(frame: Frame) -> list[str]:
    return [v.text for v in frame.open_vagueness if v.kind in ("follow_up", "out_of_scope")]


def render_spec(frame: Frame) -> str:
    out: list[str] = [f"# {frame.title}", ""]
    ann = _texts(frame, "announcement")
    if ann:
        out += ["> " + ann[0], ""]
    out += _section("Audience", _texts(frame, "audience"))
    out += _before_after(frame)
    out += _section("Why it matters", _texts(frame, "why_it_matters"))
    out += _section("Requirements / honesty conditions", _confirmed_honesty(frame))
    out += _section("Success signals", _texts(frame, "success_signal"))
    out += _section("Scope / boundaries", _texts(frame, "boundary"))
    out += _section("Non-goals", _texts(frame, "non_goal"))
    out += _section("Assumptions", _texts(frame, "assumption"))
    out += _section("Decisions", _texts(frame, "decision"))
    out += _hard_questions(frame)
    out += _section("Open questions", _texts(frame, "open_question"))
    out += _section("Open / follow-up", _follow_up(frame))
    return "\n".join(out).rstrip() + "\n"
