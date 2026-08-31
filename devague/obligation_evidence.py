"""Which obligations have approved evidence — the fail-open loading edge (bvts t7).

An obligation (:class:`devague.frame.Obligation` /
:class:`devague.plan.CriterionObligation`) is a behavioral commitment. The only
thing that discharges one is an :class:`~devague.delivery.EvidenceRecord` in
the delivery ledger that is **approved** (a human adjudicated it) and **not
superseded** (nothing has replaced it). Everything else — a ``proposed`` record
awaiting adjudication, a ``rejected`` one, a superseded one — leaves the
obligation untested.

This module is the *edge*: it does the I/O and nothing else. The predicate that
turns "which refs are met" into warning text lives in the two convergence
engines (:func:`devague.convergence.evaluate` /
:func:`devague.plan_convergence.evaluate`), which stay pure functions over
state they are handed — the same split
:func:`devague.plan_convergence.evaluate`'s ``targets`` parameter already uses
(the CLI re-derives live targets and passes them in) and the same one
:mod:`devague.contested` uses (markers are derived in the CLI layer and passed
to the renderers). Keeping the load out here is what makes the warnings
unit-testable without a filesystem, and what lets the CLI route this module's
diagnostics to stderr — something a convergence engine has no business doing.

**Fail-open is mandatory**, for exactly the reason spelled out in
:mod:`devague.contested`'s docstring: this is frame-side code reaching across
to the plan and delivery stores. A missing, truncated, or
newer-than-supported file degrades to "nothing known to be met from that
source" plus a human-readable diagnostic — never a crash, and never a blocker.
The three loaders in :mod:`devague.contested` are *reused* here (with an
``obligations:`` diagnostic label) rather than re-implemented, so the two
derivations cannot drift apart.

Two known imprecision modes, stated rather than hidden:

* **Ref ambiguity.** ``EvidenceRecord.obligation_ref`` is a bare id, and both
  ``Frame.obligations`` and ``Plan.obligations`` mint ``o1``, ``o2``, … So a
  plan's own ``o1`` and its source frame's ``o1`` are indistinguishable in a
  ledger. The consequence is a possible *false negative warning* (an
  obligation reported met by evidence filed against its namesake), never a
  false blocker — the warnings never gate. Disambiguating refs is a
  delivery-store change, out of this task's scope.
* **Outcome is not consulted.** An approved evidence record with
  ``outcome="fail"`` still counts as evidence *about* the obligation: the join
  is "is this obligation tested at all", not "does it pass". A failing test is
  a delivery-side signal (``devague summary``), not a convergence warning
  about missing coverage.
"""

from __future__ import annotations

from devague import plan_store
from devague.contested import delivery_for_frame, load_delivery_safely
from devague.delivery import Delivery

__all__ = [
    "approved_evidence_refs",
    "met_obligation_refs_for_frame",
    "met_obligation_refs_for_plan",
]

# Diagnostic prefix for this derivation, so a degraded read is attributable
# (contested.py's own reads say "contested:").
_LABEL = "obligations"


def approved_evidence_refs(delivery: Delivery) -> set[str]:
    """Every obligation ref discharged by ``delivery`` — pure, no I/O.

    Approved **and** not superseded: an approved record that something later
    replaced is history, not live evidence, and a proposed/rejected one was
    never accepted in the first place.
    """
    return {
        rec.obligation_ref
        for rec in delivery.evidence
        if rec.status == "approved" and not rec.superseded
    }


def met_obligation_refs_for_frame(frame_slug: str) -> tuple[set[str], list[str]]:
    """Obligation refs discharged anywhere downstream of ``frame_slug``.

    Returns ``(refs, diagnostics)``. A frame carries no reverse pointer to the
    plans seeded from it, so this walks every plan slug, keeps the ones whose
    ``frame_slug`` matches, and unions their ledgers' approved evidence —
    :func:`devague.contested.delivery_for_frame` is that walk, reused verbatim.

    Never raises: an unlistable plan directory, an unreadable plan, and an
    unreadable/newer-schema ledger each degrade to "nothing from that source"
    plus a diagnostic the caller routes to stderr.
    """
    refs: set[str] = set()
    diagnostics: list[str] = []
    try:
        slugs = plan_store.list_slugs()
    except OSError as exc:
        diagnostics.append(f"{_LABEL}: could not list plans ({exc}); no evidence read")
        return refs, diagnostics

    for slug in slugs:
        delivery, slug_diags = delivery_for_frame(slug, frame_slug, label=_LABEL)
        diagnostics.extend(slug_diags)
        if delivery is not None:
            refs |= approved_evidence_refs(delivery)
    return refs, diagnostics


def met_obligation_refs_for_plan(plan_slug: str) -> tuple[set[str], list[str]]:
    """Obligation refs discharged by ``plan_slug``'s own ledger.

    Returns ``(refs, diagnostics)``. A criterion obligation belongs to one
    plan, so — unlike the frame side — there is exactly one ledger to read and
    no walk to do. A plan with no ledger yet (the common case: nothing has been
    filed against it) is silent, not a diagnostic.
    """
    delivery, diag = load_delivery_safely(plan_slug, label=_LABEL)
    diagnostics = [diag] if diag else []
    if delivery is None:
        return set(), diagnostics
    return approved_evidence_refs(delivery), diagnostics
