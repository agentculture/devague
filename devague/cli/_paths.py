"""Filesystem naming for exported artifacts (specs and plans)."""

from __future__ import annotations

import time


def dated_name(created: str, slug: str) -> str:
    """Return ``<YYYY-MM-DD>-<slug>.md`` — the export filename with a date prefix (#12).

    The date is taken from ``created`` (the object's persisted ISO timestamp,
    ``2026-05-23T…``) rather than today, so re-exporting an unchanged object is
    idempotent — it overwrites the same file instead of spawning a dated duplicate. An
    object is always saved (creation stamped) before it can converge and export, but we
    fall back to today's UTC date if the stamp is somehow absent or malformed.
    """
    date = (created or "")[:10]
    if not _is_iso_date(date):
        date = time.strftime("%Y-%m-%d", time.gmtime())
    return f"{date}-{slug}.md"


def _is_iso_date(value: str) -> bool:
    try:
        time.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False
