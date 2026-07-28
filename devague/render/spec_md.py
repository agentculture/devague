"""Renderer: the buildable spec as markdown, derived from a converged frame."""

from __future__ import annotations

from typing import Optional

from devague.contested import ContestedMarker
from devague.frame import (
    VAGUENESS_KINDS,
    Claim,
    Frame,
    HardQuestion,
    HonestyCondition,
    Vagueness,
)
from devague.render._md_safety import autolink_urls, heading_safe, md_safe_text

# Keyed by confirmed claim id -> the approved deviations naming it in their
# ``--affects`` (#92). Pure input data: this module never derives it itself
# (that would mean I/O inside a renderer) — the caller (``devague export``)
# computes it via ``devague.contested.find_contested_markers`` and passes it
# in, the same way ``render.deliverables_md`` takes a already-loaded ``Plan``
# rather than loading one itself.
ContestedMap = dict[str, list[ContestedMarker]]


def _safe(text: str) -> str:
    """Compose both render-time verbatim-text passes for one field (#64, #87):
    identifier/control-character escaping first, then bare-URL autolinking.

    Order matters: ``autolink_urls`` already treats a backtick-delimited code
    span as untouchable, so running ``md_safe_text`` first means any fresh
    code span it introduces (wrapping an underscore-bearing identifier) is
    then correctly skipped by the autolink pass. Running them in the other
    order risks an autolinked ``<...>`` URL being reopened by an identifier
    match landing inside it — ``md_safe_text`` has no notion of
    angle-bracket protection, only of existing backtick code spans.
    """
    return autolink_urls(md_safe_text(text))


def _safe_heading(text: str) -> str:
    """Like ``_safe`` but for heading text: composes with ``heading_safe``
    (MD026 trailing-punctuation stripping) instead of a bare ``autolink_urls``.
    """
    return heading_safe(md_safe_text(text))


def _claims(frame: Frame, kind: str) -> list[Claim]:
    return [c for c in frame.claims if c.kind == kind and c.status == "confirmed"]


def _instruction_lines(instruction: str, indent: str = "  ") -> list[str]:
    """A nested ``- instruction: <verbatim text>`` bullet under an item, or nothing
    when the item carries no instruction — never fabricated filler (#53 t1/t6,
    c10/h3).
    """
    return [f"{indent}- instruction: {_safe(instruction)}"] if instruction else []


def _contested_marker_text(m: ContestedMarker) -> str:
    """The shared ``contested by `dN` (classification): reason`` fragment —
    used both as a nested bullet under an affected claim and (prefixed with
    ``>``) under the announcement blockquote.
    """
    text = f"contested by `{m.deviation_id}`"
    if m.classification:
        text += f" ({m.classification})"
    return f"{text}: {_safe(m.reason)}"


def _contested_lines(
    claim_id: str, contested: Optional[ContestedMap], indent: str = "  "
) -> list[str]:
    """Nested ``- ⚠ contested by ...`` bullets for a confirmed claim named in an
    approved deviation's ``--affects`` (#92), or nothing when the claim isn't
    contested — never fabricated filler, mirrors ``_instruction_lines``. The
    spec is never rewritten to match what execution later learned (the #92
    maintainer ruling); this only ever adds a read-only pointer to the ledger
    entry that superseded the claim.
    """
    entries = (contested or {}).get(claim_id, [])
    return [f"{indent}- ⚠ {_contested_marker_text(m)}" for m in entries]


def _claim_bullets(
    claims: list[Claim], prefix: str = "", contested: Optional[ContestedMap] = None
) -> list[str]:
    out: list[str] = []
    for c in claims:
        out.append(f"- {prefix}{_safe(c.text)}")
        out += _instruction_lines(c.instruction)
        out += _contested_lines(c.id, contested)
    return out


def _claim_section(
    heading: str, claims: list[Claim], contested: Optional[ContestedMap] = None
) -> list[str]:
    """A ``## heading`` + bullet-list block of claims, each with its own nested
    instruction bullet when it carries one, or nothing when empty.
    """
    if not claims:
        return []
    return [f"## {heading}", "", *_claim_bullets(claims, contested=contested), ""]


def _before_after(frame: Frame, contested: Optional[ContestedMap] = None) -> list[str]:
    befores = _claims(frame, "before_state")
    afters = _claims(frame, "after_state")
    if not (befores or afters):
        return []
    lines = ["## Before → After", ""]
    lines += _claim_bullets(befores, prefix="Before: ", contested=contested)
    lines += _claim_bullets(afters, prefix="After: ", contested=contested)
    return lines + [""]


def _requirements_block(frame: Frame, contested: Optional[ContestedMap] = None) -> list[str]:
    """Requirement claims (confirmed) with their confirmed honesty conditions nested."""
    reqs = _claims(frame, "requirement")
    if not reqs:
        return []
    out = ["## Requirements", ""]
    for c in reqs:
        out.append(f"- {_safe(c.text)}")
        out += _instruction_lines(c.instruction)
        out += _contested_lines(c.id, contested)
        for h in c.honesty_conditions:
            if h.status != "confirmed":
                continue
            out.append(f"  - honesty: {_safe(h.text)}")
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
        out.append(f"- {_safe(h.text)}")
        out += _instruction_lines(h.instruction)
    return out + [""]


def _hard_question_marker(q: HardQuestion) -> str:
    """A trailing marker for one hard question: ``(resolved)`` once answered,
    else ``(blocking)`` while it still blocks convergence, else nothing.
    Resolved takes priority over blocking — an answered question is no longer
    an open blocker regardless of the flag it was created with (#49).
    """
    if q.resolved:
        return " (resolved)"
    if q.blocking:
        return " (blocking)"
    return ""


def _hard_questions(frame: Frame) -> list[str]:
    """Hard questions attached to non-rejected claims, each carrying a
    resolved/blocking marker.

    Two independent fidelity fixes (#49, #83): a resolved question no longer
    renders as if it were still an open blocker, and a question whose parent
    claim was rejected is dropped entirely — rejected content must never
    reach the exported spec, regardless of the question's own state.
    """
    bullets = [
        f"- {_safe(q.text)}{_hard_question_marker(q)}"
        for c in frame.claims
        if c.status != "rejected"
        for q in c.hard_questions
    ]
    return ["## Hard questions", "", *bullets, ""] if bullets else []


def _open_parks(frame: Frame) -> list[str]:
    """All still-open (unresolved) parked vagueness, of every kind, grouped by
    kind and labeled with it.

    Replaces the old filter that only ever surfaced ``follow_up``/
    ``out_of_scope`` and silently dropped every open ``unknown_nonblocking``/
    ``unknown_blocking`` park (#93, #49) — exactly ``unknown_nonblocking`` is
    the kind that legitimately coexists with a converged frame, which made it
    the kind most worth rendering. A resolved item moves into
    ``_resolved_vagueness_section`` instead (resolve-parked-vagueness t7);
    counting it here too would fabricate it as still open.
    """
    items = [v for v in frame.open_vagueness if not v.resolved]
    if not items:
        return []
    ordered = sorted(items, key=lambda v: VAGUENESS_KINDS.index(v.kind))
    out = ["## Open parks", ""]
    out.extend(f"- [{v.kind}] {_safe(v.text)}" for v in ordered)
    return out + [""]


def _resolved_vagueness(frame: Frame) -> list[Vagueness]:
    """Resolved open-vagueness items, of any kind.

    Unlike the old open-parks filter (which only ever surfaced follow_up/
    out_of_scope kinds), a decided item — including a resolved
    ``unknown_blocking`` or ``unknown_nonblocking`` park — belongs in the
    exported spec once it carries a resolution: the whole point of resolving
    a parked unknown is that the answer ships with the spec (issue 45's
    provenance ask). An item marked resolved with no resolution text renders
    nothing here — never fabricated filler (mirrors ``_instruction_lines``).
    """
    return [v for v in frame.open_vagueness if v.resolved and v.resolution]


def _resolved_vagueness_section(frame: Frame) -> list[str]:
    items = _resolved_vagueness(frame)
    if not items:
        return []
    out = ["## Resolved vagueness", ""]
    out.extend(f"- [{v.kind}] {_safe(v.text)} — resolved: {_safe(v.resolution)}" for v in items)
    return out + [""]


def _seed_label(frame: Frame, seed_id: str) -> str:
    """A scope-entry seed id, flagged when it cites a rejected claim (the
    fourth #84 acceptance criterion, c33/h26) instead of rendering a bare
    dead reference, or when it cites a claim-attached hard question rather
    than a claim (#84's "smaller, related gap" — a finding the ``/scope``
    routing table sent to the ``question`` move, not ``capture``). A
    question seed reads as ``(question)``, or ``(question, resolved)`` once
    it carries an answer — distinct from a claim seed, since a question is
    not a claim and a resolved one is worth telling apart from a still-open
    one. An id that resolves to neither a claim nor a hard question renders
    as the plain backticked id, unchanged.
    """
    claim = frame.find_claim(seed_id)
    if claim is not None:
        if claim.status == "rejected":
            return f"`{seed_id}` (rejected)"
        return f"`{seed_id}`"
    question = frame.find_hard_question(seed_id)
    if question is not None:
        if question.resolved:
            return f"`{seed_id}` (question, resolved)"
        return f"`{seed_id}` (question)"
    return f"`{seed_id}`"


def _scope_section(frame: Frame) -> list[str]:
    """Scope-exploration provenance: each recorded surface + finding, with the
    claim ids it seeded — citing what was actually explored, not a generic
    disclaimer (#53 t1/t6, c8/h12/h2). Empty ``scope_entries`` renders nothing.
    """
    if not frame.scope_entries:
        return []
    out = ["## Scope exploration", ""]
    for e in frame.scope_entries:
        out.append(f"- `{e.id}` — `{e.surface}`: {_safe(e.finding)}")
        if e.seeds:
            out.append(f"  - seeds: {', '.join(_seed_label(frame, s) for s in e.seeds)}")
    return out + [""]


def render_spec(frame: Frame, contested: Optional[ContestedMap] = None) -> str:
    """Render the buildable spec.

    ``contested`` (#92) maps a confirmed claim id to the approved deviations
    naming it — computed by the caller via
    :func:`devague.contested.find_contested_markers` and passed in verbatim;
    this function stays a pure function of its two inputs, no I/O of its own
    (the same layering ``render.deliverables_md`` uses for a ``Plan``).
    Omitted/``None`` means "no contested markers" — every existing caller
    that renders a frame with no notion of deviations is unaffected.
    """
    out: list[str] = [f"# {_safe_heading(frame.title)}", ""]
    ann_claims = _claims(frame, "announcement")
    if ann_claims:
        ann = ann_claims[0]
        out.append("> " + _safe(ann.text))
        if ann.instruction:
            out.append(f"> instruction: {_safe(ann.instruction)}")
        for m in (contested or {}).get(ann.id, []):
            out.append(f"> ⚠ {_contested_marker_text(m)}")
        out.append("")
    out += _claim_section("Audience", _claims(frame, "audience"), contested)
    out += _before_after(frame, contested)
    out += _claim_section("Why it matters", _claims(frame, "why_it_matters"), contested)
    out += _requirements_block(frame, contested)
    out += _honesty_section("Honesty conditions", _other_honesty(frame))
    out += _claim_section("Success signals", _claims(frame, "success_signal"), contested)
    out += _claim_section("Scope / boundaries", _claims(frame, "boundary"), contested)
    out += _claim_section("Non-goals", _claims(frame, "non_goal"), contested)
    out += _claim_section("Assumptions", _claims(frame, "assumption"), contested)
    out += _scope_section(frame)
    out += _claim_section("Decisions", _claims(frame, "decision"), contested)
    out += _hard_questions(frame)
    out += _claim_section("Open questions", _claims(frame, "open_question"), contested)
    out += _open_parks(frame)
    out += _resolved_vagueness_section(frame)
    return "\n".join(out).rstrip() + "\n"
