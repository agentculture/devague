"""The convergence gate: is a frame solid enough to export a buildable spec?"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from devague.frame import SPEC_AFFECTING_KINDS, Frame


@dataclass
class ConvergenceResult:
    """Structured convergence verdict, shared by the frame and plan engines.

    ``ready`` is the gate (no blockers). The CLI serializes it under an
    engine-specific key (``ready_for_spec`` for frames, ``ready_for_plan`` for
    plans). ``blockers`` hold convergence back; ``warnings`` do not;
    ``parked_items`` are tracked-but-non-blocking unknowns; ``required_next_moves``
    are derived from the blockers so an operator knows what to do next.
    """

    ready: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parked_items: list[str] = field(default_factory=list)
    required_next_moves: list[str] = field(default_factory=list)


def _missing_required_kinds(confirmed_kinds: set[str]) -> list[str]:
    """Required confirmed claims for an honest announcement frame."""
    missing = [
        f"missing confirmed '{required}' claim"
        for required in ("announcement", "audience", "after_state")
        if required not in confirmed_kinds
    ]
    if "before_state" not in confirmed_kinds and "why_it_matters" not in confirmed_kinds:
        missing.append("missing 'before_state' or 'why_it_matters' claim")
    if "boundary" not in confirmed_kinds:
        missing.append("missing a 'boundary' / non-goal claim")
    if "success_signal" not in confirmed_kinds:
        missing.append("missing a 'success_signal' claim")
    return missing


def _missing_claim_resolution(frame: Frame, confirmed: list) -> list[str]:
    """No spec-affecting claim left proposed; each confirmed one is pressure-tested."""
    missing = [
        f"claim {c.id} still proposed (confirm or reject it)"
        for c in frame.claims
        if c.kind in SPEC_AFFECTING_KINDS and c.status == "proposed"
    ]
    missing += [
        f"claim {c.id} has no confirmed honesty condition"
        for c in confirmed
        if c.kind in SPEC_AFFECTING_KINDS
        and not any(h.status == "confirmed" for h in c.honesty_conditions)
    ]
    return missing


def _missing_open_uncertainty(frame: Frame) -> list[str]:
    """No blocking vagueness or unresolved blocking hard question remains."""
    missing = [
        f"blocking vagueness {v.id} unresolved"
        for v in frame.open_vagueness
        if v.kind == "unknown_blocking"
    ]
    missing += [
        f"blocking hard question {q.id} on {c.id} unresolved"
        for c in frame.claims
        for q in c.hard_questions
        if q.blocking and not q.resolved
    ]
    return missing


def _assumption_warnings(frame: Frame) -> list[str]:
    """Unconfirmed assumptions are soft: a warning, never a blocker (#5, h14)."""
    return [
        f"assumption {c.id} is unconfirmed — confirm it or it ships as a stated assumption"
        for c in frame.claims
        if c.kind == "assumption" and c.status != "confirmed"
    ]


def _parked_items(frame: Frame) -> list[str]:
    """Tracked, non-blocking open vagueness (everything but unknown_blocking)."""
    return [f"[{v.kind}] {v.text}" for v in frame.open_vagueness if v.kind != "unknown_blocking"]


def suggest_move(blocker: str) -> str:
    """Map a single blocker to the recommended next devague move.

    Confirmation is a USER-only transition, so any confirm-related move spells
    out who confirms — the agent must never imply it should confirm its own work.
    """
    m = re.search(r"missing confirmed '([a-z_]+)' claim", blocker)
    if m:
        kind = m.group(1)
        return (
            f'devague capture --kind {kind} "<text>"   (a user capture '
            f"auto-confirms; an --origin llm capture then needs the USER to confirm it)"
        )
    if "before_state" in blocker and "why_it_matters" in blocker:
        return 'devague capture --kind why_it_matters "<text>"'
    if "boundary" in blocker:
        return 'devague capture --kind boundary "<text>"'
    if "success_signal" in blocker:
        return 'devague capture --kind success_signal "<text>"'
    m = re.search(r"claim (c\d+) still proposed", blocker)
    if m:
        cid = m.group(1)
        return (
            f"this is an LLM proposal — the USER decides: devague confirm {cid} (or reject {cid})"
        )
    m = re.search(r"claim (c\d+) has no confirmed honesty condition", blocker)
    if m:
        cid = m.group(1)
        return (
            f'devague interrogate {cid} --honesty "<what must be true>"'
            f"   then USER: devague confirm <hN>"
        )
    m = re.search(r"blocking vagueness (v\d+)", blocker)
    if m:
        return f"resolve {m.group(1)}: capture+confirm the answer, or re-park it as non-blocking"
    m = re.search(r"blocking hard question (q\d+) on (c\d+)", blocker)
    if m:
        return (
            f"resolve {m.group(1)} on {m.group(2)}: answer it, then "
            f"capture/confirm the resulting claim"
        )
    return "devague show     # inspect and decide"


def evaluate(frame: Frame) -> ConvergenceResult:
    confirmed = [c for c in frame.claims if c.status == "confirmed"]
    confirmed_kinds = {c.kind for c in confirmed}
    blockers = (
        _missing_required_kinds(confirmed_kinds)
        + _missing_claim_resolution(frame, confirmed)
        + _missing_open_uncertainty(frame)
    )
    return ConvergenceResult(
        ready=not blockers,
        blockers=blockers,
        warnings=_assumption_warnings(frame),
        parked_items=_parked_items(frame),
        required_next_moves=[suggest_move(b) for b in blockers],
    )
