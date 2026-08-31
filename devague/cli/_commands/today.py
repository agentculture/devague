"""``devague today`` — project and write the current-spec artifact (t10).

Read-only over every store (frames, plans, delivery ledgers): the projection
walk in :mod:`devague.today` never saves anything. The **only** file this
command ever writes is ``docs/current-spec.md`` — undated, overwritten in
place on every run, unlike the dated ``docs/specs/*.md`` / ``docs/plans/*.md``
exports (those are process history; this is not, #92's ruling extended to a
whole document rather than one marker).

Bypasses the ``devague.render`` registry the same way ``devague export``
special-cases ``spec-md`` and ``devague plan deliverables`` calls
``render.deliverables_md`` directly: :func:`devague.render.today_md.
render_today` takes a :class:`~devague.today.ProjectionResult`, not a
``Frame``, so it does not fit that registry's ``Callable[[Frame], str]``
shape.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from devague.cli._output import emit_result
from devague.render import today_md
from devague.today import project_today, result_to_dict

CURRENT_SPEC_PATH = Path("docs/current-spec.md")


def cmd_today(args: argparse.Namespace) -> int:
    """Project the ledger and write ``docs/current-spec.md``, always.

    ``--json`` only changes what lands on stdout (the structured projection
    instead of a one-line confirmation) — the file write is unconditional, so
    a scripted ``devague today --json`` still refreshes the committed
    artifact rather than silently skipping it.
    """
    result = project_today()
    text = today_md.render_today(result)
    CURRENT_SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_SPEC_PATH.write_text(text, encoding="utf-8")
    if getattr(args, "json", False):
        emit_result(result_to_dict(result), json_mode=True)
    else:
        emit_result(f"wrote {CURRENT_SPEC_PATH}", json_mode=False)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "today",
        help="Project the current behavior of the app from the delivery ledger, read-only.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured projection on stdout (docs/current-spec.md is still written).",
    )
    p.set_defaults(func=cmd_today)
