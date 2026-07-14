"""Resolve the delivery ledger for a move: `.devague/deliveries/<slug>.json`.

The delivery-store peer of :mod:`devague.cli._plans` (read that module for the
pattern this mirrors). :func:`devague.delivery_store.load_or_new` already treats
"no ledger yet" as the normal starting state (a plan may never have had a
deviation recorded against it) and returns a fresh :class:`Delivery` for a
missing file — that is not an error and stays untranslated here. What *is* an
error is an existing-but-broken ledger: a schema_version newer than this binary
understands, or a file that fails to parse/validate. Before this module existed,
those exceptions fell through to ``_dispatch``'s last-resort ``except Exception``
handler and were misreported as "unexpected: ..." (Q5, PR #72 review) instead of
a clear, actionable :class:`DevagueError`.
"""

from __future__ import annotations

from devague import delivery_store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.delivery import Delivery


def resolve_delivery(slug: str) -> Delivery:
    """Load-or-new the delivery ledger for ``slug``, translating store errors.

    Mirrors :func:`devague.cli._plans.resolve_plan`'s translation of
    :mod:`devague.plan_store` errors, applied to :mod:`devague.delivery_store`.
    """
    try:
        return delivery_store.load_or_new(slug)
    except delivery_store.IncompatibleDeliverySchemaError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "upgrade devague (uv tool install -U devague)",
        ) from exc
    except ValueError as exc:
        # Covers malformed JSON (json.JSONDecodeError is a ValueError subclass)
        # and the delivery_store slug-mismatch/tampered-slug ValueErrors.
        raise DevagueError(
            EXIT_USER_ERROR,
            f"delivery ledger {slug!r} is malformed: {exc}",
            f"repair or remove .devague/deliveries/{slug}.json",
        ) from exc
