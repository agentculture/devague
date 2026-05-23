"""Filesystem naming for exported artifacts (specs and plans)."""

from __future__ import annotations

import time

# Stable, date-shaped sentinel used when ``created`` is absent or malformed. It must
# not vary by run (e.g. today's date) or idempotence would break for that edge — see
# the rationale in ``dated_name``.
UNDATED_PREFIX = "0000-00-00"


def dated_name(created: str, slug: str) -> str:
    """Return ``<YYYY-MM-DD>-<slug>.md`` — the export filename with a date prefix (#12).

    The date is taken from ``created`` (the object's persisted ISO timestamp,
    ``2026-05-23T…``) rather than today, so re-exporting an unchanged object is
    idempotent — it overwrites the same file instead of spawning a dated duplicate. An
    object is always saved (creation stamped) before it can converge and export, so a
    real date is the normal case.

    If ``created`` is somehow absent or malformed (only reachable via a hand-corrupted
    store file — ``store.save`` repopulates an *empty* stamp but not an *invalid* one),
    we fall back to the constant :data:`UNDATED_PREFIX` rather than today's date: a
    run-varying fallback would itself break the idempotence this prefix exists to
    provide.
    """
    date = (created or "")[:10]
    if not _is_iso_date(date):
        date = UNDATED_PREFIX
    return f"{date}-{slug}.md"


def _is_iso_date(value: str) -> bool:
    try:
        time.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False
