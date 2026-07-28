"""Contested-by-deviation derivation (#92, t14).

An approved ``devague deviate`` record can name a confirmed claim in its
``--affects`` list — the deviation ledger knows a claim has been contested by
execution, but until now nothing surfaced that back-reference: the exported
spec, ``devague show``, and ``devague status`` all rendered the claim as if
nothing had happened. The maintainer ruling on #92 is explicit: **the spec is
not editable to fix this** ("don't change the spec, this is part of the
ledger — deviate is the marking of the change"). So this module derives the
back-reference read-only, at render time, from state that already exists —
it never mutates a claim, a plan, or a delivery ledger, and it never invents
an id.

The join (decisions c24/c19, honesty conditions h14/h17/h27): a frame outlives
the plan(s) seeded from it and carries no reverse pointer to them, so finding
"every delivery ledger whose deviations might affect this frame's claims"
means enumerating :func:`devague.plan_store.list_slugs`, loading each plan,
keeping the ones whose ``frame_slug`` matches, and then loading
:mod:`devague.delivery_store` per matching plan slug — exactly the shape
:mod:`devague.cli._commands.deviate`'s own ``--affects`` validation already
established (loading a plan's live source frame to check a ref against it),
just walked in the opposite direction.

Fail-open is a hard requirement (claim c34/h27): this is the FIRST time
frame-side code (``export``/``show``/``status`` — the tool's core read paths)
reaches across to the plan/delivery stores at all. A plan file or delivery
ledger that is missing, truncated, or declares a schema newer than this
binary understands must never crash or block those commands — it degrades to
"no markers derived from that source" plus a human-readable diagnostic string
the caller is responsible for routing to stderr (typically via
:func:`devague.cli._output.emit_diagnostic`). A delivery ledger that simply
does not exist yet (a plan with no recorded deviations — the common case) is
not a diagnostic at all: :mod:`devague.delivery_store` itself treats that as
normal, and so does this module.

Pure and read-only throughout: every function here only ever calls ``load``/
``list_slugs`` on the plan and delivery stores, never ``save``. Nothing here
mutates ``frame`` either.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from devague import delivery_store, plan_store
from devague.delivery import Delivery
from devague.frame import Frame
from devague.plan import Plan

__all__ = [
    "ContestedMarker",
    "find_contested_markers",
    "sorted_markers",
    "marker_to_dict",
]


@dataclass(frozen=True)
class ContestedMarker:
    """One approved deviation naming a confirmed claim in its ``--affects``."""

    claim_id: str
    deviation_id: str
    what: str
    reason: str
    classification: Optional[str]
    plan_slug: str


def _numeric_suffix(item_id: str) -> int:
    """The trailing digits of an id (``c14`` -> 14), for a numeric-aware sort
    that orders ``c2`` before ``c10`` — a plain lexicographic sort would not.
    Non-numeric/empty input sorts as 0 rather than raising; this only ever
    feeds a display order, never an identity check.
    """
    digits = "".join(ch for ch in item_id if ch.isdigit())
    return int(digits) if digits else 0


def _load_plan_safely(slug: str) -> tuple[Optional[Plan], Optional[str]]:
    """Best-effort plan load: ``(plan, diagnostic)``, never raises.

    ``diagnostic`` is ``None`` on success. A plan that disappeared between
    ``list_slugs()`` and this load (a narrow race, not a corruption shape) is
    treated the same as "not found" and silently skipped — it is not one of
    the three corruption shapes the fail-open contract is about.
    """
    try:
        return plan_store.load(slug), None
    except FileNotFoundError:
        return None, None
    except plan_store.IncompatiblePlanSchemaError as exc:
        return (
            None,
            f"contested: plan {slug!r} uses a schema this devague can't read, skipped ({exc})",
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return None, f"contested: plan {slug!r} is unreadable, skipped ({exc})"


def _load_delivery_safely(slug: str) -> tuple[Optional[Delivery], Optional[str]]:
    """Best-effort delivery-ledger load: ``(delivery, diagnostic)``, never raises.

    A missing ledger (no deviation ever recorded against this plan) is the
    normal, silent case — mirrors :func:`devague.delivery_store.load_or_new`'s
    own treatment of "no file yet". A truncated/malformed file or a
    newer-than-supported ``schema_version`` is a real corruption shape (claim
    c34): both degrade to "no markers from this ledger" plus a diagnostic.
    """
    try:
        return delivery_store.load(slug), None
    except FileNotFoundError:
        return None, None
    except delivery_store.IncompatibleDeliverySchemaError as exc:
        return None, (
            f"contested: delivery ledger for plan {slug!r} uses a schema this "
            f"devague can't read, skipped ({exc})"
        )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return None, (
            f"contested: delivery ledger for plan {slug!r} is unreadable, skipped ({exc})"
        )


def find_contested_markers(
    frame: Frame,
) -> tuple[dict[str, list[ContestedMarker]], list[str]]:
    """Derive contested markers for ``frame``'s confirmed claims.

    Returns ``(markers, diagnostics)``. ``markers`` maps a confirmed claim id
    to every :class:`ContestedMarker` naming it, sorted deterministically
    (:func:`sorted_markers`'s order); a claim with nothing contesting it is
    simply absent from the dict (``markers.get(cid, [])`` is the intended
    read). ``diagnostics`` is zero or more human-readable strings describing
    a plan or delivery ledger that could not be read — never fatal, the
    caller decides whether/where to surface them.

    Never raises (fail-open, claim c34) and never mutates ``frame``, any
    plan, or any delivery ledger (pure derivation, claim c21/h17).
    """
    confirmed_ids = {c.id for c in frame.claims if c.status == "confirmed"}
    markers: dict[str, list[ContestedMarker]] = {}
    diagnostics: list[str] = []

    try:
        slugs = plan_store.list_slugs()
    except OSError as exc:
        diagnostics.append(f"contested: could not list plans ({exc}); no markers derived")
        return markers, diagnostics

    for slug in slugs:
        plan, plan_diag = _load_plan_safely(slug)
        if plan_diag:
            diagnostics.append(plan_diag)
        if plan is None or plan.frame_slug != frame.slug:
            continue

        delivery, delivery_diag = _load_delivery_safely(slug)
        if delivery_diag:
            diagnostics.append(delivery_diag)
        if delivery is None:
            continue

        for dev in delivery.deviations:
            if dev.status != "approved":
                continue
            for ref in dev.affects:
                if ref in confirmed_ids:
                    markers.setdefault(ref, []).append(
                        ContestedMarker(
                            claim_id=ref,
                            deviation_id=dev.id,
                            what=dev.what,
                            reason=dev.reason,
                            classification=dev.classification,
                            plan_slug=slug,
                        )
                    )

    for entries in markers.values():
        entries.sort(key=lambda m: (m.plan_slug, _numeric_suffix(m.deviation_id)))
    return markers, diagnostics


def sorted_markers(markers: dict[str, list[ContestedMarker]]) -> list[ContestedMarker]:
    """Flatten a claim-id-keyed marker map into one deterministically ordered
    list — claim id first (numeric-aware), then plan slug, then deviation id.
    """
    flat = [m for entries in markers.values() for m in entries]
    flat.sort(
        key=lambda m: (_numeric_suffix(m.claim_id), m.plan_slug, _numeric_suffix(m.deviation_id))
    )
    return flat


def marker_to_dict(marker: ContestedMarker) -> dict:
    """The JSON-friendly shape of one marker, for ``--json`` output."""
    return {
        "claim": marker.claim_id,
        "deviation": marker.deviation_id,
        "what": marker.what,
        "reason": marker.reason,
        "classification": marker.classification,
        "plan": marker.plan_slug,
    }
