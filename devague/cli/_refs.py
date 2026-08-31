"""Shared id-shaped ref validation, extracted from ``deviate`` (bvts t6).

``devague deviate`` and ``devague delta`` both need to tell a real,
resolvable id (``c14``, ``t3``, ``d2``, ``b7``, ...) apart from free-form
prose that merely happens not to be id-shaped, and both need a best-effort
load of a plan's source frame to validate against. Before this module
existed, ``deviate.py`` carried both pieces privately; ``delta.py`` needs the
same shape rule for its own ``--caused-by`` refs (claim ids, approved
deviation ids, delta ids), so the regex, the frame-loading fallback, and the
refuse-unless-known check now live in exactly one place rather than being
copied.

Extracting this changes no behavior: ``deviate.py``'s ``--affects`` checks
still raise the same errors on the same inputs, just via this shared helper.
"""

from __future__ import annotations

import re

from devague import store
from devague.cli._errors import EXIT_USER_ERROR, DevagueError

# An id-shaped ref: a single lowercase letter followed by digits — the shape
# every devague-generated id uses (t3 tasks, c14 claims, h5 honesty
# conditions, r1 plan risks, d1 deviations, b7 deltas, v/q/s ids elsewhere).
# Anything else is free-form prose and is never refused.
ID_SHAPED_RE = re.compile(r"^[a-z]\d+$")


def load_source_frame(frame_slug: str):
    """Best-effort load of a plan's source frame; ``None`` when it is gone or
    corrupt (mirrors ``cmd_summary``'s graceful degradation in
    :mod:`devague.cli._commands.summary`) — a missing frame narrows what an
    id-shaped ref can validate against, it never crashes the move."""
    try:
        return store.load(frame_slug)
    except (FileNotFoundError, ValueError):
        return None


def refuse_unless_known(ref: str, known: set[str], *, flag: str, what: str, hint: str) -> None:
    """Fail closed when ``ref`` is id-shaped but absent from ``known``.

    Free-form prose (anything not matching :data:`ID_SHAPED_RE`) is always
    allowed and never reaches the ``known`` check — a ref that merely looks
    like an id is the only thing this guards against silently drifting from
    something real.
    """
    if ID_SHAPED_RE.match(ref) and ref not in known:
        raise DevagueError(
            EXIT_USER_ERROR,
            f"{flag} {ref!r} does not resolve to {what}",
            hint,
        )
