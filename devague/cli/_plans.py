"""Resolve the target plan for a move: explicit --plan, else the current plan."""

from __future__ import annotations

from devague import plan_store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.plan import Plan


def resolve_plan(slug: str | None) -> Plan:
    slug = slug or plan_store.current_slug()
    if not slug:
        raise DevagueError(
            EXIT_USER_ERROR,
            "no plan selected",
            "run 'devague plan new --frame <slug>' or pass --plan <slug>",
        )
    try:
        return plan_store.load(slug)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"invalid plan slug: {slug!r}",
            "slugs are lowercase letters, digits, and hyphens — no path separators",
        ) from exc
    except FileNotFoundError:
        raise DevagueError(
            EXIT_USER_ERROR, f"no such plan: {slug}", "run 'devague plan list' to see plans"
        ) from None
