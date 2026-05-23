"""Shared rendering for the ``status`` value-add verb (frame and plan engines).

``status`` composes ``list`` + ``converge`` into one human-facing summary — where
the artifact stands and the recommended next move (the first gap's
``required_next_moves`` entry). It lives in the deterministic CLI (issue #30)
rather than in the skill wrappers' embedded Python, so it is unit-testable and
free of the wrappers' temp-file and stdout-ordering hazards: there is no
subprocess and no ``mktemp``, and a bad ``--frame`` / ``--plan`` raises
:class:`~devague.cli._errors.DevagueError` (routed to stderr by the chassis)
*before* any result reaches stdout.

The frame and plan engines are structural peers, so both call through here with
engine-specific labels carried by :class:`StatusLabels`.
"""

from __future__ import annotations

from dataclasses import dataclass

from devague.cli._output import emit_result
from devague.convergence import ConvergenceResult


@dataclass(frozen=True)
class StatusLabels:
    """Engine-specific strings the shared renderer needs.

    ``noun`` is both the human label and the JSON key for the selected artifact
    ("frame" / "plan"). ``ready_key`` matches what ``converge --json`` emits
    ("ready_for_spec" / "ready_for_plan"). ``export_move`` is the suggestion shown
    when converged; ``empty_text`` is the multi-line guidance when nothing exists.
    """

    noun: str
    ready_key: str
    export_move: str
    empty_text: str


def emit_empty(labels: StatusLabels, *, json_mode: bool) -> None:
    """Render the no-artifacts state (consistent JSON shape; guidance text)."""
    if json_mode:
        emit_result(
            {
                labels.noun: None,
                "total": 0,
                labels.ready_key: False,
                "blockers": [],
                "warnings": [],
                "parked_items": [],
                "required_next_moves": [],
            },
            json_mode=True,
        )
    else:
        emit_result(labels.empty_text, json_mode=False)


def emit_status(
    labels: StatusLabels,
    *,
    selected: str,
    total: int,
    result: ConvergenceResult,
    json_mode: bool,
) -> None:
    """Render the convergence verdict + recommended next move for one artifact."""
    if json_mode:
        emit_result(
            {
                labels.noun: selected,
                "total": total,
                labels.ready_key: result.ready,
                "blockers": result.blockers,
                "warnings": result.warnings,
                "parked_items": result.parked_items,
                "required_next_moves": result.required_next_moves,
            },
            json_mode=True,
        )
        return

    plural = "s" if total != 1 else ""
    lines = [f"{labels.noun}: {selected}    ({total} {labels.noun}{plural} total)"]
    if result.ready:
        lines.append("convergence: PASSED ✓")
        lines += [f"  ⚠ {w}" for w in result.warnings]
        lines.append(f"next move: {labels.export_move}")
    else:
        lines.append(f"convergence: NOT passed — {len(result.blockers)} gap(s):")
        lines += [f"  - {b}" for b in result.blockers]
        lines += [f"  ⚠ {w}" for w in result.warnings]
        if result.required_next_moves:
            lines += [
                "",
                "recommended next move (first gap):",
                f"  {result.required_next_moves[0]}",
            ]
    emit_result("\n".join(lines), json_mode=False)
