"""Delivery persistence: JSON under .devague/deliveries/<plan-slug>.json.

The peer of :mod:`devague.plan_store` (itself the peer of :mod:`devague.store`).
Paths are cwd-relative so a delivery ledger lives alongside the plan it tracks
deviations for. A delivery's key is its source plan's slug verbatim — a
delivery has no independent identity, unlike a frame or plan, so there is no
separate "current delivery" pointer; the move that reads/writes one always
resolves the plan first (see :mod:`devague.cli._plans`).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from devague.delivery import DELIVERY_SCHEMA_VERSION, Delivery, from_dict, to_dict
from devague.store import validate_slug

DELIVERIES_DIR = Path(".devague/deliveries")


class IncompatibleDeliverySchemaError(ValueError):
    """A persisted delivery declares a schema_version this devague cannot read."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path_for(slug: str) -> Path:
    return DELIVERIES_DIR / f"{validate_slug(slug)}.json"


def save(delivery: Delivery) -> Path:
    DELIVERIES_DIR.mkdir(parents=True, exist_ok=True)
    # Stamp the version this binary actually writes: a delivery loaded under an
    # older label then mutated with newer fields must not be rewritten under that
    # older label, or the fail-closed load gate (schema_version >
    # DELIVERY_SCHEMA_VERSION) is defeated and an old binary silently drops the
    # newer payload (data loss) — the 0.17.0 frame/plan-store fix, applied here.
    delivery.schema_version = DELIVERY_SCHEMA_VERSION
    delivery.updated = _now()
    if not delivery.created:
        delivery.created = delivery.updated
    p = path_for(delivery.plan_slug)
    p.write_text(json.dumps(to_dict(delivery), indent=2) + "\n", encoding="utf-8")
    return p


def load(slug: str) -> Delivery:
    p = path_for(slug)
    if not p.exists():
        raise FileNotFoundError(slug)
    delivery = from_dict(json.loads(p.read_text(encoding="utf-8")))
    validate_slug(delivery.plan_slug)  # reject a tampered file whose internal slug escapes
    if delivery.plan_slug != slug:
        # The embedded plan_slug drives save(); a file whose internal slug disagrees
        # with its filename could silently redirect a later save onto a different
        # plan's ledger, so reject it.
        raise ValueError(
            f"delivery plan slug mismatch: file {slug!r} declares plan_slug "
            f"{delivery.plan_slug!r}"
        )
    if delivery.schema_version > DELIVERY_SCHEMA_VERSION:
        raise IncompatibleDeliverySchemaError(
            f"delivery {slug!r} uses schema_version {delivery.schema_version}, but this "
            f"devague supports up to {DELIVERY_SCHEMA_VERSION}; upgrade devague to read it"
        )
    return delivery


def load_or_new(slug: str) -> Delivery:
    """Load the delivery ledger for ``slug``, or a fresh empty one if none exists yet.

    A plan may never have had a deviation recorded against it, so "no file yet"
    is the normal starting state, not an error (unlike :func:`load`, which is
    for callers that require an existing ledger).
    """
    try:
        return load(slug)
    except FileNotFoundError:
        return Delivery(plan_slug=slug)
