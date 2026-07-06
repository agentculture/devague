"""Deterministic structural-sharpness warnings on the frame gate (#53 t7).

These pin the two documented rules added in t7 — both **warning-only** (soft
rollout per the resolved parked-v2 decision: structural checks land as warnings
first, never as blockers). Nothing here may flip ``ready_for_spec``.

- S1 (instruction present): a *confirmed spec-affecting* claim whose
  ``instruction`` is empty draws a per-claim warning naming its id.
- S2 (measurable success signal): if a frame has at least one confirmed
  ``success_signal`` claim but none of them contains a measurable token
  (a numeral, ``%``, or a comparator ``<`` / ``>`` / ``≤`` / ``≥``), a single
  warning is drawn.

The rules are pure predicates over frame state — never LLM judgment (h6). The
false-positive edges each rule is known to over-fire on are pinned below so the
soft-rollout story stays honest.
"""

from __future__ import annotations

import pytest

from devague.convergence import evaluate
from devague.frame import SPEC_AFFECTING_KINDS, Frame

# The six kinds a bare `_full_frame` needs to clear every *blocker* (so any
# remaining signal in `.warnings` is a sharpness warning, not a gate gap).
_REQUIRED_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "boundary",
    "success_signal",
)


def _full_frame(
    *, success_text: str = "success_signal text", with_instructions: bool = False
) -> Frame:
    """A frame that clears every convergence blocker (mirrors test_convergence).

    ``success_text`` overrides the success_signal claim's text so S2's
    measurability predicate can be exercised. ``with_instructions`` attaches a
    verbatim instruction to every spec-affecting claim so S1 stays silent.
    """
    f = Frame(slug="s", title="t")
    for kind in _REQUIRED_KINDS:
        text = success_text if kind == "success_signal" else f"{kind} text"
        c = f.add_claim(kind, text, origin="user")  # user -> confirmed
        f.add_honesty(c, "must hold", origin="user")  # user -> confirmed
        if with_instructions:
            c.instruction = f"verify {kind}"
    return f


# --- baseline: warnings never move the gate ----------------------------------


def test_pre_change_converging_frame_still_converges_with_warnings() -> None:
    """A frame that converged before t7 still converges — the new signals are
    warnings, so ``ready`` stays True and blockers/next-moves are untouched."""
    res = evaluate(_full_frame())
    assert res.ready is True
    assert res.blockers == []
    assert res.required_next_moves == []  # derived from blockers only
    assert res.warnings  # but sharpness warnings are surfaced


# --- S1: instruction present on confirmed spec-affecting claims ---------------


def test_s1_confirmed_spec_affecting_claim_without_instruction_warns() -> None:
    res = evaluate(_full_frame())
    # Every required kind is spec-affecting and instruction-less → one warning each.
    for kind in _REQUIRED_KINDS:
        assert kind in SPEC_AFFECTING_KINDS
    instruction_warnings = [w for w in res.warnings if "instruction" in w]
    # One per spec-affecting confirmed claim (all six).
    assert len(instruction_warnings) == len(_REQUIRED_KINDS)
    # Each names its claim id and the fixing move.
    assert all("--instruction" in w for w in instruction_warnings)


def test_s1_names_the_claim_id() -> None:
    f = _full_frame()
    boundary = next(c for c in f.claims if c.kind == "boundary")
    res = evaluate(f)
    assert any(boundary.id in w and "instruction" in w for w in res.warnings)


def test_s1_silent_when_instruction_present() -> None:
    res = evaluate(_full_frame(with_instructions=True))
    assert res.ready is True
    assert not any("instruction" in w for w in res.warnings)


def test_s1_ignores_whitespace_only_instruction() -> None:
    """A whitespace-only instruction is 'no instruction' — the warning still fires."""
    f = _full_frame(with_instructions=True)
    boundary = next(c for c in f.claims if c.kind == "boundary")
    boundary.instruction = "   \n  "
    res = evaluate(f)
    assert any(boundary.id in w and "instruction" in w for w in res.warnings)


def test_s1_only_confirmed_claims_no_double_signal_on_proposed() -> None:
    """A still-*proposed* spec-affecting claim is already a blocker; S1 must not
    also warn on it (no double-signalling)."""
    f = _full_frame()
    proposed = f.add_claim("requirement", "must round-trip", origin="llm")  # proposed
    res = evaluate(f)
    # It IS a blocker...
    assert any(proposed.id in b and "proposed" in b for b in res.blockers)
    # ...but NOT an S1 instruction warning.
    assert not any(proposed.id in w and "instruction" in w for w in res.warnings)


def test_s1_ignores_descriptive_and_assumption_kinds() -> None:
    """Descriptive/soft kinds are not spec-affecting → no instruction warning,
    even when confirmed and instruction-less."""
    f = _full_frame(with_instructions=True)
    ng = f.add_claim("non_goal", "not a PRD generator", origin="user")
    dec = f.add_claim("decision", "keep the vocabulary", origin="user")
    asm = f.add_claim("assumption", "frames stay small", origin="user")
    res = evaluate(f)
    for c in (ng, dec, asm):
        assert not any(c.id in w and "instruction" in w for w in res.warnings)


# --- S2: measurable success signal -------------------------------------------


def test_s2_warns_when_no_success_signal_is_measurable() -> None:
    # Default success text "success_signal text" carries no measurable token.
    res = evaluate(_full_frame(with_instructions=True))
    assert res.ready is True
    assert any("measurable" in w and "success_signal" in w for w in res.warnings)


@pytest.mark.parametrize(
    "text",
    [
        "converge in under 3 seconds",  # numeral
        "95% of runs converge",  # percent (and numeral)
        "resolves in < 200 ms",  # comparator + numeral
        "at least 2 reviewers approve",  # numeral
        "latency ≤ 5s",  # unicode comparator
    ],
)
def test_s2_silent_for_measurable_signal(text: str) -> None:
    res = evaluate(_full_frame(success_text=text, with_instructions=True))
    assert not any("measurable" in w for w in res.warnings)


def test_s2_not_fired_when_no_success_signal_claim_exists() -> None:
    """When there's no confirmed success_signal at all, that's the existing
    *blocker*'s job — S2 must not pile on a measurability warning."""
    f = Frame(slug="s", title="t")
    for kind in ("announcement", "audience", "after_state", "before_state", "boundary"):
        c = f.add_claim(kind, f"{kind} text", origin="user")
        f.add_honesty(c, "must hold", origin="user")
        c.instruction = "verify"
    res = evaluate(f)
    assert not res.ready  # missing success_signal is a blocker
    assert any("success_signal" in b for b in res.blockers)
    assert not any("measurable" in w for w in res.warnings)


def test_s2_measurable_only_needs_one_of_several_success_signals() -> None:
    """A frame with several success_signal claims stays silent if *any* is measurable."""
    f = _full_frame(success_text="the spec reads clearly", with_instructions=True)
    c = f.add_claim("success_signal", "95% of exports pass lint", origin="user")
    f.add_honesty(c, "must hold", origin="user")
    c.instruction = "verify"
    res = evaluate(f)
    assert not any("measurable" in w for w in res.warnings)


# --- known false-positive edges (pinned to keep the soft-rollout honest) ------


def test_s2_false_positive_binary_checkable_signal_still_warns() -> None:
    """Documented S2 false positive: a perfectly checkable *binary* success
    signal worded without a numeral (e.g. 'the exported spec shows scope
    provenance') trips the warning. Warning-only, so harmless — pinned here so
    the false-positive story is visible in the suite."""
    res = evaluate(
        _full_frame(
            success_text="the exported spec shows scope provenance",
            with_instructions=True,
        )
    )
    assert any("measurable" in w for w in res.warnings)


def test_s1_false_positive_self_contained_claim_still_nudged() -> None:
    """Documented S1 false positive: a self-evident spec-affecting claim that
    needs no separate verification instruction is still nudged for one."""
    res = evaluate(_full_frame())  # no instructions anywhere
    assert any("instruction" in w for w in res.warnings)


# --- structural invariants ----------------------------------------------------


def test_sharpness_warnings_never_touch_blockers_or_next_moves() -> None:
    f = _full_frame()  # converges, but with both S1 and S2 warnings
    res = evaluate(f)
    assert res.warnings
    assert res.blockers == []
    assert res.required_next_moves == []
    # warnings and blockers are distinct list objects (no aliasing).
    assert res.warnings is not res.blockers


def test_assumption_and_sharpness_warnings_coexist() -> None:
    """The pre-existing unconfirmed-assumption warning still fires alongside the
    new sharpness warnings."""
    f = _full_frame()
    f.add_claim("assumption", "frames stay small", origin="llm")  # proposed
    res = evaluate(f)
    assert any("assumption" in w for w in res.warnings)
    assert any("instruction" in w for w in res.warnings)
    assert any("measurable" in w for w in res.warnings)
