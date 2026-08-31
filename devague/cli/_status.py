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
from typing import Optional

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


def _contested_line(entry: dict) -> str:
    """Render one derived contested-by-deviation entry (#92) as a single
    ``contested: <claim> by <deviation> (<classification>): <reason>`` line.
    Takes the plain JSON-shaped dict (:func:`devague.contested.marker_to_dict`)
    rather than the ``ContestedMarker`` dataclass itself, so this shared
    frame/plan status renderer stays decoupled from the contested module —
    it only needs to agree on a dict shape, not import a domain type.
    """
    line = f"contested: {entry['claim']} by {entry['deviation']}"
    if entry.get("classification"):
        line += f" ({entry['classification']})"
    return f"{line}: {entry['reason']}"


def _stale_deviation_line(entry: dict) -> str:
    """Render one derived stale-deviation entry (#97/bvts t8) — mirrors
    :func:`_contested_line`'s dict-shaped, decoupled-from-the-domain-module
    contract. Takes :func:`devague.staleness.stale_deviation_to_dict`-shaped
    dicts.
    """
    line = f"stale: deviation {entry['deviation']} affects {', '.join(entry['claims'])}"
    if entry.get("classification"):
        line += f" ({entry['classification']})"
    refs = ", ".join(entry["stale_evidence"])
    return f"{line} — evidence {refs} never re-filed since: {entry['reason']}"


def _orphaned_evidence_line(entry: dict) -> str:
    """Render one derived orphaned-evidence entry (#97/bvts t8). Takes
    :func:`devague.staleness.orphaned_evidence_to_dict`-shaped dicts.
    """
    return (
        f"stale: evidence {entry['evidence']} ({entry['test']}) "
        f"in plan {entry['plan']}: {entry['reason']}"
    )


def emit_status(
    labels: StatusLabels,
    *,
    selected: str,
    total: int,
    result: ConvergenceResult,
    json_mode: bool,
    contested: Optional[list[dict]] = None,
    stale_deviations: Optional[list[dict]] = None,
    orphaned_evidence: Optional[list[dict]] = None,
) -> None:
    """Render the convergence verdict + recommended next move for one artifact.

    ``contested`` (#92) is the frame engine's derived contested-by-deviation
    list (see :mod:`devague.contested`) — a list of
    :func:`devague.contested.marker_to_dict`-shaped dicts, or ``None`` when
    the caller has no notion of it (the plan engine's ``status`` never passes
    this; only the frame engine's does). ``None`` means "not applicable" and
    omits the JSON key entirely; an empty list means "checked, nothing
    contested" and still renders the key (JSON) but no lines (text) — the
    same never-fabricate-an-empty-section convention every other renderer
    here follows. ``stale_deviations``/``orphaned_evidence`` (#97/bvts t8)
    are the staleness join's two directions (see :mod:`devague.staleness`),
    following the exact same ``None`` vs ``[]`` contract and, like
    ``contested``, only ever passed by the frame engine's ``status``.
    """
    if json_mode:
        payload = {
            labels.noun: selected,
            "total": total,
            labels.ready_key: result.ready,
            "blockers": result.blockers,
            "warnings": result.warnings,
            "parked_items": result.parked_items,
            "required_next_moves": result.required_next_moves,
        }
        if contested is not None:
            payload["contested"] = contested
        if stale_deviations is not None:
            payload["stale_deviations"] = stale_deviations
        if orphaned_evidence is not None:
            payload["orphaned_evidence"] = orphaned_evidence
        emit_result(payload, json_mode=True)
        return

    plural = "s" if total != 1 else ""
    lines = [f"{labels.noun}: {selected}    ({total} {labels.noun}{plural} total)"]
    if contested:
        lines += [_contested_line(c) for c in contested]
    if stale_deviations:
        lines += [_stale_deviation_line(s) for s in stale_deviations]
    if orphaned_evidence:
        lines += [_orphaned_evidence_line(o) for o in orphaned_evidence]
    if result.ready:
        lines.append("convergence: PASSED ✓")
        lines += [f"  ⚠ {w}" for w in result.warnings]
        lines += [f"  ~ {p}" for p in result.parked_items]
        lines.append(f"next move: {labels.export_move}")
    else:
        lines.append(f"convergence: NOT passed — {len(result.blockers)} gap(s):")
        lines += [f"  - {b}" for b in result.blockers]
        lines += [f"  ⚠ {w}" for w in result.warnings]
        lines += [f"  ~ {p}" for p in result.parked_items]
        if result.required_next_moves:
            lines += [
                "",
                "recommended next move (first gap):",
                f"  {result.required_next_moves[0]}",
            ]
    emit_result("\n".join(lines), json_mode=False)
