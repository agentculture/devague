"""The convergence gate: is a frame solid enough to export a buildable spec?"""

from __future__ import annotations

from dataclasses import dataclass, field

from devague.frame import SPEC_AFFECTING_KINDS, Frame


@dataclass
class ConvergenceResult:
    passed: bool
    missing: list[str] = field(default_factory=list)


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


def evaluate(frame: Frame) -> ConvergenceResult:
    confirmed = [c for c in frame.claims if c.status == "confirmed"]
    confirmed_kinds = {c.kind for c in confirmed}
    missing = (
        _missing_required_kinds(confirmed_kinds)
        + _missing_claim_resolution(frame, confirmed)
        + _missing_open_uncertainty(frame)
    )
    return ConvergenceResult(passed=not missing, missing=missing)
