"""Staleness derivation (issue #97/bvts t8) — the second read-only join beside
:mod:`devague.contested`.

Two directions, both pure and read-only over recorded state:

1. **Stale deviations** — an approved ``devague deviate`` record whose
   ``--affects`` names a claim/honesty id that some (non-superseded) evidence
   record's contract side also covers, but only evidence *filed before* the
   deviation counts against it, and no evidence covering the same overlap was
   ever filed at or after the deviation. In plain terms: execution deviated
   from something evidence once backed, and nobody re-validated it afterward.
2. **Orphaned evidence** — a (non-superseded) evidence record whose
   obligation no longer resolves (the obligation was rejected, or the ref
   simply names nothing in either obligation store), or whose behavior was
   itself removed/superseded by a later delta that references it.

Neither direction does any semantic matching — both are pure joins over ids,
statuses, and list position. This module deliberately mirrors
:mod:`devague.contested`'s shape: a frozen finding dataclass per direction, a
``find_*`` entrypoint per frame, the same fail-open ``_load_*_safely`` helpers
(imported, not duplicated), a deterministic numeric-aware sort, and JSON-dict
helpers for ``--json`` callers. It is consumed the same way contested markers
are — ``devague show`` and ``devague status`` render its findings as visible
staleness lines; nothing here ever mutates a frame, a plan, or a delivery
ledger.

**Ordering convention (load-bearing, read this before touching the join):**
Delivery records carry no timestamp of their own — :class:`RunReference` is
the only clock in the whole model, and it is optional, per-evidence, and
about when a *test* ran, not when a *record was filed*. What *is* recorded,
always, is append order: :meth:`devague.delivery.Delivery._next` mints each
family's ids strictly increasing from 1, one family's ids are never reused
or renumbered, and nothing is ever deleted — so a record's numeric id suffix
(``d3`` -> ``3``, ``e7`` -> ``7``) is exactly its 1-based position in its own
family's append order. This module treats that per-family numeric position as a *single shared
timeline* across every family in one delivery ledger, comparing an
evidence record's position against a deviation's position directly as
integers: an evidence record at the SAME OR AN EARLIER position (``e5`` vs
``d5`` or ``d9``) counts as "filed before or alongside" the deviation, and
only a STRICTLY LATER position (``e10`` vs ``d5``) counts as a genuine
re-filing after it. The tie goes to "before" deliberately — the ordinary
real sequence is evidence filed first, then a deviation recorded against
what it covers, so two records that happen to mint the same per-family
numeral are far more likely to be "evidence, then deviation" than the
reverse. This is only ever an approximation of true chronology (two
families' ids can interleave in a specific way relative to real filing
order that this cannot see), but there is no sharper signal available
anywhere in the data model as it exists today, so this is the
deterministic, documented choice the design brief asks for rather than a
claim of exact simultaneity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from devague import plan_store
from devague.contested import _numeric_suffix, load_delivery_safely, load_plan_safely
from devague.delivery import Delivery
from devague.frame import Frame
from devague.plan import Plan

__all__ = [
    "StaleDeviationFinding",
    "OrphanedEvidenceFinding",
    "find_staleness",
    "stale_deviation_to_dict",
    "orphaned_evidence_to_dict",
    "stale_deviation_line",
    "orphaned_evidence_line",
]


@dataclass(frozen=True)
class StaleDeviationFinding:
    """An approved deviation whose overlap with once-filed evidence was
    never re-validated after the deviation landed.
    """

    deviation_id: str
    what: str
    reason: str
    classification: Optional[str]
    plan_slug: str
    claim_ids: tuple[str, ...]
    stale_evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class OrphanedEvidenceFinding:
    """A non-superseded evidence record whose contract side no longer holds:
    its obligation doesn't resolve/was rejected, or a delta that references
    it was superseded or itself removed the behavior.
    """

    evidence_id: str
    obligation_ref: str
    test_ref: str
    plan_slug: str
    reason: str


def _resolve_obligation(
    ref: str, frame: Optional[Frame], plan: Optional[Plan]
) -> tuple[frozenset, Optional[str]]:
    """Resolve an evidence ``obligation_ref`` to ``(claim_ids, status)``.

    Two obligation shapes exist on two different stores (t1's frame-side
    ``Obligation`` and t2's plan-side ``CriterionObligation``), and both mint
    ids from the same ``o``-prefix — so this tries the plan first (the
    delivery is scoped to one plan, and evidence obligations concern task
    work), then falls back to the plan's source frame:

    * a plan :class:`~devague.plan.CriterionObligation` names a task, not a
      claim directly — its "contract side" is the set of coverage-target ids
      (``c*``/``h*``) that task's ``covers`` names, since a
      :class:`~devague.plan.CoverageTarget` id mirrors the source frame id
      verbatim (the same convention :mod:`devague.contested` relies on);
    * a frame :class:`~devague.frame.Obligation` names its claim directly
      via ``claim_id``.

    Returns ``(frozenset(), None)`` when ``ref`` resolves in neither store —
    the "absent" case for :func:`find_orphaned_evidence`. Never raises.
    """
    if plan is not None:
        ob = plan.find_obligation(ref)
        if ob is not None:
            task = plan.find_task(ob.task_id)
            claims = frozenset(task.covers) if task is not None else frozenset()
            return claims, ob.status
    if frame is not None:
        ob = frame.find_obligation(ref)
        if ob is not None:
            return frozenset({ob.claim_id}), ob.status
    return frozenset(), None


def _filed_at_or_before(ev, dev) -> bool:
    """Was this evidence filed at or before this deviation, on the ledger?

    Records filed since the shared ``seq`` counter exists carry their true
    position on the delivery's one filing timeline — compare those directly.
    Legacy records (``seq == 0`` on either side) fall back to the numeric id
    suffix, where "<=" (not "<") reflects that each family mints ids
    independently from 1, so an id-1 evidence record and an id-1 deviation
    are treated as "at or before" (the common real sequence is evidence
    first, then the deviation). Only a strictly later position counts as a
    genuine re-filing.
    """
    if ev.seq and dev.seq:
        return ev.seq <= dev.seq
    return _numeric_suffix(ev.id) <= _numeric_suffix(dev.id)


def _scan_evidence_against(
    dev, affected: frozenset, frame: Frame, plan: Plan, delivery: Delivery
) -> tuple[list[str], set, bool]:
    """Scan the ledger's evidence against one approved deviation's affects.

    Returns ``(stale_refs, overlap_claims, refiled)`` — ordering per
    :func:`_filed_at_or_before`.
    """
    stale_refs: list[str] = []
    overlap_claims: set = set()
    refiled = False
    for ev in delivery.evidence:
        if ev.superseded:
            continue
        claims, _status = _resolve_obligation(ev.obligation_ref, frame, plan)
        shared = claims & affected
        if not shared:
            continue
        if _filed_at_or_before(ev, dev):
            stale_refs.append(ev.id)
            overlap_claims |= shared
        else:
            refiled = True
    return stale_refs, overlap_claims, refiled


def _stale_deviations_for(
    frame: Frame, plan: Plan, delivery: Delivery
) -> list[StaleDeviationFinding]:
    findings: list[StaleDeviationFinding] = []
    for dev in delivery.deviations:
        if dev.status != "approved":
            continue
        affected = frozenset(dev.affects)
        if not affected:
            continue
        stale_refs, overlap_claims, refiled = _scan_evidence_against(
            dev, affected, frame, plan, delivery
        )
        if stale_refs and not refiled:
            findings.append(
                StaleDeviationFinding(
                    deviation_id=dev.id,
                    what=dev.what,
                    reason=dev.reason,
                    classification=dev.classification,
                    plan_slug=plan.slug,
                    claim_ids=tuple(sorted(overlap_claims, key=_numeric_suffix)),
                    stale_evidence_refs=tuple(sorted(stale_refs, key=_numeric_suffix)),
                )
            )
    return findings


def _orphan_reasons(ev, frame: Frame, plan: Plan, delivery: Delivery) -> list[str]:
    reasons: list[str] = []
    _claims, status = _resolve_obligation(ev.obligation_ref, frame, plan)
    if status is None:
        reasons.append(f"obligation {ev.obligation_ref!r} does not resolve")
    elif status == "rejected":
        reasons.append(f"obligation {ev.obligation_ref!r} was rejected")
    for delta in delivery.deltas:
        if ev.id not in delta.evidence_refs:
            continue
        if delta.superseded:
            reasons.append(f"referencing delta {delta.id!r} is superseded")
        if delta.kind == "removed":
            reasons.append(f"referencing delta {delta.id!r} removed the behavior")
    return reasons


def _orphaned_evidence_for(
    frame: Frame, plan: Plan, delivery: Delivery
) -> list[OrphanedEvidenceFinding]:
    findings: list[OrphanedEvidenceFinding] = []
    for ev in delivery.evidence:
        if ev.superseded:
            continue
        reasons = _orphan_reasons(ev, frame, plan, delivery)
        if reasons:
            findings.append(
                OrphanedEvidenceFinding(
                    evidence_id=ev.id,
                    obligation_ref=ev.obligation_ref,
                    test_ref=ev.test_ref,
                    plan_slug=plan.slug,
                    reason="; ".join(reasons),
                )
            )
    return findings


def find_staleness(
    frame: Frame,
) -> tuple[list[StaleDeviationFinding], list[OrphanedEvidenceFinding], list[str]]:
    """Derive both staleness directions for ``frame``.

    Returns ``(stale_deviations, orphaned_evidence, diagnostics)``, both
    finding lists sorted deterministically (plan slug, then numeric-aware
    id). ``diagnostics`` is zero or more human-readable strings describing a
    plan or delivery ledger that could not be read — never fatal; the caller
    decides whether/where to surface them (typically stderr).

    Never raises (fail-open) and never mutates ``frame``, any plan, or any
    delivery ledger — a pure derivation over what is already on disk,
    exactly like :func:`devague.contested.find_contested_markers`.
    """
    stale_deviations: list[StaleDeviationFinding] = []
    orphaned_evidence: list[OrphanedEvidenceFinding] = []
    diagnostics: list[str] = []

    try:
        slugs = plan_store.list_slugs()
    except OSError as exc:
        diagnostics.append(f"staleness: could not list plans ({exc}); no findings derived")
        return stale_deviations, orphaned_evidence, diagnostics

    for slug in slugs:
        plan, plan_diag = load_plan_safely(slug, label="staleness")
        if plan_diag:
            diagnostics.append(plan_diag)
        if plan is None or plan.frame_slug != frame.slug:
            continue

        delivery, delivery_diag = load_delivery_safely(slug, label="staleness")
        if delivery_diag:
            diagnostics.append(delivery_diag)
        if delivery is None:
            continue

        stale_deviations.extend(_stale_deviations_for(frame, plan, delivery))
        orphaned_evidence.extend(_orphaned_evidence_for(frame, plan, delivery))

    stale_deviations.sort(key=lambda f: (f.plan_slug, _numeric_suffix(f.deviation_id)))
    orphaned_evidence.sort(key=lambda f: (f.plan_slug, _numeric_suffix(f.evidence_id)))
    return stale_deviations, orphaned_evidence, diagnostics


def stale_deviation_to_dict(finding: StaleDeviationFinding) -> dict:
    """The JSON-friendly shape of one stale-deviation finding."""
    return {
        "deviation": finding.deviation_id,
        "what": finding.what,
        "reason": finding.reason,
        "classification": finding.classification,
        "plan": finding.plan_slug,
        "claims": list(finding.claim_ids),
        "stale_evidence": list(finding.stale_evidence_refs),
    }


def orphaned_evidence_to_dict(finding: OrphanedEvidenceFinding) -> dict:
    """The JSON-friendly shape of one orphaned-evidence finding."""
    return {
        "evidence": finding.evidence_id,
        "obligation": finding.obligation_ref,
        "test": finding.test_ref,
        "plan": finding.plan_slug,
        "reason": finding.reason,
    }


def stale_deviation_line(finding: StaleDeviationFinding) -> str:
    """Render one stale-deviation finding as a single human-facing line."""
    line = f"stale: deviation {finding.deviation_id} affects {', '.join(finding.claim_ids)}"
    if finding.classification:
        line += f" ({finding.classification})"
    refs = ", ".join(finding.stale_evidence_refs)
    return f"{line} — evidence {refs} never re-filed since: {finding.reason}"


def orphaned_evidence_line(finding: OrphanedEvidenceFinding) -> str:
    """Render one orphaned-evidence finding as a single human-facing line."""
    return (
        f"stale: evidence {finding.evidence_id} ({finding.test_ref}) "
        f"in plan {finding.plan_slug}: {finding.reason}"
    )
