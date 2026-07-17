"""The convergence gate: is a frame solid enough to export a buildable spec?

Structural-sharpness rules (#53 t7)
-----------------------------------

Beyond the hard blockers, the gate emits **warning-only** structural-sharpness
signals. They never move ``ready_for_spec`` — the soft-rollout decision (the
resolved parked-v2 item): the tightened gate's structural checks land as
warnings first, so no frame that converges today is newly blocked. Each rule is
a **pure predicate over frame state** — never LLM text judgment (h6) — and is
enumerated here with its exact predicate and its known false-positive mode:

- **S1 — instruction present on spec-affecting claims.** For every *confirmed*
  claim whose ``kind`` is spec-affecting, warn if ``instruction`` is empty (after
  ``.strip()``). Predicate: ``kind in SPEC_AFFECTING_KINDS and status ==
  "confirmed" and not instruction.strip()``. Restricted to confirmed claims so a
  still-proposed claim (already a blocker) is not double-signalled. Known
  false positive: a self-evident claim that genuinely needs no separate
  verification instruction is still nudged for one — harmless, warning-only.

- **S2 — measurable success signal.** If the frame has at least one confirmed
  ``success_signal`` claim but **none** of them contains a measurable token,
  warn once. A claim text is "measurable" iff it contains a numeral, a ``%``, or
  a comparator (``<`` ``>`` ``≤`` ``≥``) — the ``_MEASURABLE_TOKEN`` regex. Gated
  on there being ≥1 confirmed success_signal so it never piles onto the existing
  "missing a 'success_signal' claim" blocker. Known false positive: a perfectly
  checkable *binary* success signal worded without a numeral (e.g. "the exported
  spec shows scope provenance") trips the warning even though it is verifiable —
  the operator can ignore it or add a count. It never *misses* a woolly numeric
  claim; it only over-fires on numeral-free-but-checkable prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from devague.frame import SPEC_AFFECTING_KINDS, Frame

# A success signal counts as measurable if its text carries any of: a numeral, a
# percent sign, or a comparison operator (ASCII ``<`` / ``>`` or their unicode
# ``≤`` / ``≥`` forms — ``<=`` / ``>=`` are covered by ``<`` / ``>``). Pure
# structure; no semantics, no LLM (h6, #53 t7 rule S2).
_MEASURABLE_TOKEN = re.compile(r"[0-9%<>≤≥]")


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
    """No blocking vagueness or unresolved blocking hard question remains.

    A blocking vagueness that has been closed via ``Frame.resolve_vagueness``
    (``v.resolved``) is no longer counted — it stays on record with its
    resolution text, but it has already been resolved through the ``park
    --resolve`` move, so it must not keep blocking convergence
    (resolve-parked-vagueness t3, #45/#55/#57).
    """
    missing = [
        f"blocking vagueness {v.id} unresolved"
        for v in frame.open_vagueness
        if v.kind == "unknown_blocking" and not v.resolved
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


def _sharpness_warnings(frame: Frame, confirmed: list) -> list[str]:
    """Deterministic structural-sharpness signals (see module docstring: S1, S2).

    Warning-only and never blocking (soft rollout per parked-v2). Pure predicates
    over frame state — no LLM judgment.
    """
    warnings = [
        # S1: a confirmed spec-affecting claim that ships into the spec without a
        # verification/implementation instruction is not directly actionable.
        f"claim {c.id} ({c.kind}) is confirmed but carries no instruction — add "
        f"one so the exported spec is directly actionable "
        f'(devague interrogate {c.id} --instruction "<how to verify or implement>")'
        for c in confirmed
        if c.kind in SPEC_AFFECTING_KINDS and not c.instruction.strip()
    ]
    # S2: at least one confirmed success_signal exists but none is measurable.
    signals = [c for c in confirmed if c.kind == "success_signal"]
    if signals and not any(_MEASURABLE_TOKEN.search(c.text) for c in signals):
        warnings.append(
            "no confirmed success_signal claim is measurable — none names a "
            "number, percentage, or comparator; add a measurable target "
            "(devague capture --kind success_signal "
            "\"<e.g. '95% of runs converge', 'under 3s'>\")"
        )
    return warnings


def _parked_items(frame: Frame) -> list[str]:
    """Tracked, non-blocking open vagueness (everything but unknown_blocking).

    A resolved item is closed, not open, so it drops out here too — otherwise
    ``converge``/``status`` would keep advertising a decided item as a live
    parked item (resolve-parked-vagueness t3).
    """
    return [
        f"[{v.kind}] {v.text}"
        for v in frame.open_vagueness
        if v.kind != "unknown_blocking" and not v.resolved
    ]


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
        vid = m.group(1)
        return f'devague park --resolve {vid} --decision "<the decision>"'
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
        warnings=_assumption_warnings(frame) + _sharpness_warnings(frame, confirmed),
        parked_items=_parked_items(frame),
        required_next_moves=[suggest_move(b) for b in blockers],
    )
