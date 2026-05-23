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
            "run 'devague new \"<announcement>\"' or pass --frame <slug>",
        )
    try:
        store.validate_slug(slug)
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"invalid frame slug: {slug!r}",
            "slugs are lowercase letters, digits, and hyphens — no path separators",
        ) from exc
    try:
        return store.load(slug)
    except store.IncompatibleSchemaError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            str(exc),
            "this frame was written by a newer devague — upgrade: 'uv tool install -U devague'",
        ) from exc
    except FileNotFoundError:
        raise DevagueError(
            EXIT_USER_ERROR, f"no such frame: {slug}", "run 'devague list' to see frames"
        ) from None
    except ValueError as exc:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"frame {slug!r} is malformed: {exc}",
            "the frame file was hand-edited or corrupted — "
            "fix .devague/frames/<slug>.json or recreate the frame",
        ) from exc
