"""The convergence gate: is a frame solid enough to export a buildable spec?"""

from __future__ import annotations

from dataclasses import dataclass, field

from devague.frame import SPEC_AFFECTING_KINDS, Frame


@dataclass
class ConvergenceResult:
    passed: bool
    missing: list[str] = field(default_factory=list)


def evaluate(frame: Frame) -> ConvergenceResult:
    missing: list[str] = []
    confirmed = [c for c in frame.claims if c.status == "confirmed"]
    confirmed_kinds = {c.kind for c in confirmed}

    for required in ("announcement", "audience", "after_state"):
        if required not in confirmed_kinds:
            missing.append(f"missing confirmed '{required}' claim")
    if "before_state" not in confirmed_kinds and "why_it_matters" not in confirmed_kinds:
        missing.append("missing 'before_state' or 'why_it_matters' claim")
    if "boundary" not in confirmed_kinds:
        missing.append("missing a 'boundary' / non-goal claim")
    if "success_signal" not in confirmed_kinds:
        missing.append("missing a 'success_signal' claim")

    for c in frame.claims:
        if c.kind in SPEC_AFFECTING_KINDS and c.status == "proposed":
            missing.append(f"claim {c.id} still proposed (confirm or reject it)")

    for c in confirmed:
        if c.kind in SPEC_AFFECTING_KINDS and not any(
            h.status == "confirmed" for h in c.honesty_conditions
        ):
            missing.append(f"claim {c.id} has no confirmed honesty condition")

    for v in frame.open_vagueness:
        if v.kind == "unknown_blocking":
            missing.append(f"blocking vagueness {v.id} unresolved")

    for c in frame.claims:
        for q in c.hard_questions:
            if q.blocking and not q.resolved:
                missing.append(f"blocking hard question {q.id} on {c.id} unresolved")

    return ConvergenceResult(passed=not missing, missing=missing)
