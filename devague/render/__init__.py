"""Renderer registry: frame/spec → text, selected by --format.

New output modalities (NotebookLM, HTML, user stories) register here.
"""

from __future__ import annotations

from typing import Callable

from devague.cli._errors import EXIT_USER_ERROR, DevagueError
from devague.frame import Frame

_REGISTRY: dict[str, Callable[[Frame], str]] = {}


def register(name: str, fn: Callable[[Frame], str]) -> None:
    _REGISTRY[name] = fn


def formats() -> list[str]:
    return sorted(_REGISTRY)


def render(frame: Frame, fmt: str) -> str:
    if fmt not in _REGISTRY:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"unknown format: {fmt}",
            f"available formats: {', '.join(formats())}",
        )
    return _REGISTRY[fmt](frame)


# Register the built-in renderers (import-time side effect).
from devague.render import frame_md as _frame_md  # noqa: E402
from devague.render import review_md as _review_md  # noqa: E402
from devague.render import spec_md as _spec_md  # noqa: E402

register("frame-md", _frame_md.render_frame)
register("spec-md", _spec_md.render_spec)
register("review-md", _review_md.render_review)
