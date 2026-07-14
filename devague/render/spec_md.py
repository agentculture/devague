"""Renderer: the buildable spec as markdown, derived from a converged frame."""

from __future__ import annotations

from devague.frame import Claim, Frame, HonestyCondition
from devague.render._md_safety import autolink_urls, heading_safe


def _claims(frame: Frame, kind: str) -> list[Claim]:
    return [c for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def _instruction_lines(instruction: str, indent: str = "  ") -> list[str]:
    """A nested ``- instruction: <verbatim text>`` bullet under an item, or nothing
    when the item carries no instruction — never fabricated filler (#53 t1/t6,
    c10/h3).
    """
    return [f"{indent}- instruction: {autolink_urls(instruction)}"] if instruction else []


def _claim_bullets(claims: list[Claim], prefix: str = "") -> list[str]:
    out: list[str] = []
    for c in claims:
        out.append(f"- {prefix}{autolink_urls(c.text)}")
        out += _instruction_lines(c.instruction)
    return out


def _text_section(heading: str, texts: list[str]) -> list[str]:
    """A standard ``## heading`` + plain bullet-list block, or nothing when empty.

    For text-only items with no instruction field (e.g. open vagueness).
    """
    if not texts:
        return []
    return [f"## {heading}", "", *[f"- {autolink_urls(t)}" for t in texts], ""]


def _claim_section(heading: str, claims: list[Claim]) -> list[str]:
    """A ``## heading`` + bullet-list block of claims, each with its own nested
    instruction bullet when it carries one, or nothing when empty.
    """
    if not claims:
        return []
    return [f"## {heading}", "", *_claim_bullets(claims), ""]


def _before_after(frame: Frame) -> list[str]:
    befores = _claims(frame, "before_state")
    afters = _claims(frame, "after_state")
    if not (befores or afters):
        return []
    lines = ["## Before → After", ""]
    lines += _claim_bullets(befores, prefix="Before: ")
    lines += _claim_bullets(afters, prefix="After: ")
    return lines + [""]


def _requirements_block(frame: Frame) -> list[str]:
    """Requirement claims (confirmed) with their confirmed honesty conditions nested."""
    reqs = _claims(frame, "requirement")
    if not reqs:
        return []
    out = ["## Requirements", ""]
    for c in reqs:
        out.append(f"- {autolink_urls(c.text)}")
        out += _instruction_lines(c.instruction)
        for h in c.honesty_conditions:
            if h.status != "confirmed":
                continue
            out.append(f"  - honesty: {autolink_urls(h.text)}")
            out += _instruction_lines(h.instruction, indent="    ")
    return out + [""]


def _other_honesty(frame: Frame) -> list[HonestyCondition]:
    """Confirmed honesty conditions on **confirmed** non-requirement claims.

    The parent claim must be confirmed too: spec-md renders only confirmed claims
    (see ``_claims``), so emitting honesty for a proposed/rejected claim would
    leave an orphan bullet with no parent — inconsistent with the confirmed-only
    export contract.
    """
    return [
        h
        for c in frame.claims
        if c.kind != "requirement" and c.status == "confirmed"
        for h in c.honesty_conditions
        if h.status == "confirmed"
    ]


def _honesty_section(heading: str, honesties: list[HonestyCondition]) -> list[str]:
    """Like ``_claim_section`` but for a flat list of honesty conditions."""
    if not honesties:
        return []
    out = [f"## {heading}", ""]
    for h in honesties:
        out.append(f"- {autolink_urls(h.text)}")
        out += _instruction_lines(h.instruction)
    return out + [""]


def _hard_questions(frame: Frame) -> list[str]:
    hqs = [q for c in frame.claims for q in c.hard_questions]
    bullets = [f"- {autolink_urls(q.text)}" + (" (blocking)" if q.blocking else "") for q in hqs]
    return ["## Hard questions", "", *bullets, ""] if hqs else []


def _follow_up(frame: Frame) -> list[str]:
    return [v.text for v in frame.open_vagueness if v.kind in ("follow_up", "out_of_scope")]


def _scope_section(frame: Frame) -> list[str]:
    """Scope-exploration provenance: each recorded surface + finding, with the
    claim ids it seeded — citing what was actually explored, not a generic
    disclaimer (#53 t1/t6, c8/h12/h2). Empty ``scope_entries`` renders nothing.
    """
    if not frame.scope_entries:
        return []
    out = ["## Scope exploration", ""]
    for e in frame.scope_entries:
        out.append(f"- `{e.id}` — `{e.surface}`: {autolink_urls(e.finding)}")
        if e.seeds:
            out.append(f"  - seeds: {', '.join(f'`{s}`' for s in e.seeds)}")
    return out + [""]


def render_spec(frame: Frame) -> str:
    out: list[str] = [f"# {heading_safe(frame.title)}", ""]
    ann_claims = _claims(frame, "announcement")
    if ann_claims:
        ann = ann_claims[0]
        out.append("> " + autolink_urls(ann.text))
        if ann.instruction:
            out.append(f"> instruction: {autolink_urls(ann.instruction)}")
        out.append("")
    out += _claim_section("Audience", _claims(frame, "audience"))
    out += _before_after(frame)
    out += _claim_section("Why it matters", _claims(frame, "why_it_matters"))
    out += _requirements_block(frame)
    out += _honesty_section("Honesty conditions", _other_honesty(frame))
    out += _claim_section("Success signals", _claims(frame, "success_signal"))
    out += _claim_section("Scope / boundaries", _claims(frame, "boundary"))
    out += _claim_section("Non-goals", _claims(frame, "non_goal"))
    out += _claim_section("Assumptions", _claims(frame, "assumption"))
    out += _scope_section(frame)
    out += _claim_section("Decisions", _claims(frame, "decision"))
    out += _hard_questions(frame)
    out += _claim_section("Open questions", _claims(frame, "open_question"))
    out += _text_section("Open / follow-up", _follow_up(frame))
    return "\n".join(out).rstrip() + "\n"
