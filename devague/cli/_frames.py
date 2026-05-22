"""Resolve the target frame for a move: explicit --frame, else the current frame."""

from __future__ import annotations

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.frame import Frame


def resolve(slug: str | None) -> Frame:
    slug = slug or store.current_slug()
    if not slug:
        raise DevagueError(
            EXIT_USER_ERROR,
            "no frame selected",
            'run \'devague new "<announcement>"\' or pass --frame <slug>',
        )
    try:
        return store.load(slug)
    except FileNotFoundError:
        raise DevagueError(
            EXIT_USER_ERROR, f"no such frame: {slug}", "run 'devague list' to see frames"
        ) from None
