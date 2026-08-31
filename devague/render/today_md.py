"""Renderer: the current spec — what the app does *today* — as markdown (t10).

``devague today`` bypasses the ``devague.render`` registry the way ``devague
export`` special-cases ``spec-md``: that registry is ``Callable[[Frame],
str]``, and a projection has no single source frame (:mod:`devague.today`
walks every frame/plan/delivery ledger). ``cli/_commands/today.py`` calls
:func:`render_today` directly, mirroring how ``render.deliverables_md`` is
called directly rather than registered.

The artifact opens with a **derived** coverage-boundary statement (claim c23 /
honesty condition h19) built only from :class:`~devague.today.CoverageSpan`
numbers — never hand-written prose implying completeness. Every current
behavior renders its backward provenance in words (not bare ids), its forward
evidence with strength *and* the run date beside it (never a bare "pass" —
honesty condition h1), and a behavior with failing or absent live evidence
renders visibly unproven, never smoothed over. Conflicts render as their own
section: explicit human-decision items, matching how :mod:`devague.today`
refuses to auto-resolve them. Proposed/rejected delta counts render as
visibly pending/excluded rather than silently folded into the behavior list.
Diagnostics from the fail-open walk render in a small trailing section —
visible, never hidden.

The file this renders into (``docs/current-spec.md``) is undated and
overwritten in place, so nothing here may vary run to run except the evidence
run dates/commits that are themselves part of the ledgered record — the same
``LoadedState``/``ProjectionResult`` in always yields the same bytes out.
"""

from __future__ import annotations

from devague.render._md_safety import autolink_urls, heading_safe, md_safe_text
from devague.today import (
    ConflictItem,
    ProjectedBehavior,
    ProjectedEvidence,
    ProjectionResult,
)

TITLE = "Current spec — what the app does today"


def _safe(text: str) -> str:
    """Compose both render-time verbatim-text passes (mirrors ``spec_md._safe``)."""
    return autolink_urls(md_safe_text(text))


def _safe_heading(text: str) -> str:
    return heading_safe(md_safe_text(text))


# ── the coverage-boundary statement ──────────────────────────────────────────


def _coverage_lines(result: ProjectionResult) -> list[str]:
    span = result.coverage
    out = ["## Coverage boundary", ""]
    if span.earliest is None or span.latest is None:
        out.append(
            f"No plan has a ledgered delivery yet — this projection is empty by "
            f"construction. 0 of {span.total_plans} plans and 0 of "
            f"{span.total_frames} frames are covered."
        )
        out.append("")
        return out
    plans_word = "plan" if len(span.ledgered_plan_slugs) == 1 else "plans"
    out.append(
        f"This projection is complete only over the behavior ledger: "
        f"{len(span.ledgered_plan_slugs)} of {span.total_plans} {plans_word} "
        f"have a ledgered delivery ({', '.join(f'`{s}`' for s in span.ledgered_plan_slugs)}), "
        f"spanning `{span.earliest.created}` (plan `{span.earliest.plan_slug}`) "
        f"through `{span.latest.created}` (plan `{span.latest.plan_slug}`)."
    )
    if span.frames_absent_from_ledger:
        frames_word = "frame" if len(span.frames_absent_from_ledger) == 1 else "frames"
        out.append(
            f"{len(span.frames_absent_from_ledger)} of {span.total_frames} "
            f"{frames_word} have no ledgered delivery at all "
            f"({', '.join(f'`{s}`' for s in span.frames_absent_from_ledger)}) — "
            f"nothing in this document reflects them."
        )
    out.append(
        "Anything predating this boundary, or belonging to an unledgered "
        "frame, is not reflected here by construction."
    )
    out.append("")
    return out


# ── evidence + provenance ────────────────────────────────────────────────────


def _evidence_status_marker(e: ProjectedEvidence) -> str:
    if e.superseded:
        return " [superseded]"
    if e.status != "approved":
        return f" [{e.status}]"
    return ""


def _evidence_line(e: ProjectedEvidence) -> str:
    """One evidence line: strength + run date beside it, never a bare outcome.

    ``execution``/``sensitivity`` strengths always carry a run reference
    (``devague.delivery.EvidenceRecord`` enforces this at filing); a
    ``coverage``/``fidelity`` record legitimately has none, and renders the
    strength alone rather than fabricating a date.
    """
    line = f"{e.evidence_type} — {e.strength}: {e.outcome}"
    if e.run_timestamp:
        date = e.run_timestamp[:10]
        commit = f" @ {e.run_commit}" if e.run_commit else ""
        line += f" (run {date}{commit})"
    line += _evidence_status_marker(e)
    return f"    - evidence: {_safe(line)}"


def _proof_marker(behavior: ProjectedBehavior) -> str:
    """Never smoothed (h1): failing or absent live evidence renders visibly."""
    if behavior.has_failing_evidence:
        return "  - ⚠ unproven: failing evidence on record"
    if behavior.best_strength is None:
        return "  - ⚠ unproven: no passing evidence on record"
    return f"  - proof: best strength `{behavior.best_strength}`"


def _behavior_lines(behavior: ProjectedBehavior) -> list[str]:
    out = [f"- {_safe(behavior.behavior_text)} (`{behavior.key}`, {behavior.kind})"]
    causes = ", ".join(f"`{ref}`" for ref in behavior.caused_by) or "none recorded"
    out.append(
        f"  - provenance: caused by {causes} — plan `{behavior.plan_slug}`, "
        f"frame `{behavior.frame_slug or 'unknown'}`"
    )
    out.append(_proof_marker(behavior))
    for e in behavior.evidence:
        out.append(_evidence_line(e))
    for ref in behavior.unresolved_evidence_refs:
        out.append(f"    - evidence: unresolved ref `{ref}`")
    if not behavior.evidence and not behavior.unresolved_evidence_refs:
        out.append("    - evidence: none on record")
    if len(behavior.lineage) > 1:
        out.append(f"  - lineage: {', '.join(f'`{k}`' for k in behavior.lineage)}")
    return out


def _behaviors_section(result: ProjectionResult) -> list[str]:
    out = ["## Current behavior", ""]
    if not result.behaviors:
        out.append("No behavior currently projects from the ledger.")
        out.append("")
        return out
    for behavior in result.behaviors:
        out.extend(_behavior_lines(behavior))
    out.append("")
    return out


# ── conflicts: human-decision items, never auto-resolved ────────────────────


def _conflict_lines(conflict: ConflictItem) -> list[str]:
    out = [f"- [{conflict.reason}] lineage `{conflict.lineage_key}` — human decision required"]
    for party in conflict.parties:
        causes = ", ".join(f"`{ref}`" for ref in party.caused_by) or "none recorded"
        out.append(
            f"  - `{party.key}` ({party.kind}, plan `{party.plan_slug}`): "
            f"{_safe(party.behavior_text)} — caused by {causes}"
        )
    return out


def _conflicts_section(result: ProjectionResult) -> list[str]:
    if not result.conflicts:
        return []
    out = ["## Conflicts", ""]
    for conflict in result.conflicts:
        out.extend(_conflict_lines(conflict))
    out.append("")
    return out


# ── ledger status: pending/excluded counts, visibly not folded in ───────────


def _ledger_status_section(result: ProjectionResult) -> list[str]:
    out = ["## Ledger status", ""]
    out.append(f"- proposed deltas awaiting adjudication: {result.proposed_delta_count}")
    out.append(f"- rejected deltas (excluded from this projection): {result.rejected_delta_count}")
    out.append(
        f"- retired lineages (superseded with no live replacement): {result.retired_lineage_count}"
    )
    out.append("")
    return out


# ── diagnostics: visible, never hidden ───────────────────────────────────────


def _diagnostics_section(result: ProjectionResult) -> list[str]:
    if not result.diagnostics:
        return []
    out = ["## Diagnostics", ""]
    out.extend(f"- {_safe(d)}" for d in result.diagnostics)
    out.append("")
    return out


def render_today(result: ProjectionResult) -> str:
    """Render the current-spec artifact. Standalone-readable: behaviors,
    provenance, and proof status are all legible with no other file open.
    """
    out = [f"# {_safe_heading(TITLE)}", ""]
    out += _coverage_lines(result)
    out += _behaviors_section(result)
    out += _conflicts_section(result)
    out += _ledger_status_section(result)
    out += _diagnostics_section(result)
    return "\n".join(out).rstrip() + "\n"
