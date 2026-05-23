from __future__ import annotations

from devague.convergence import evaluate
from devague.frame import Frame

_REQUIRED_KINDS = (
    "announcement",
    "audience",
    "after_state",
    "before_state",
    "boundary",
    "success_signal",
)


def _full_frame() -> Frame:
    f = Frame(slug="s", title="t")
    for kind in _REQUIRED_KINDS:
        c = f.add_claim(kind, f"{kind} text", origin="user")  # user -> confirmed
        f.add_honesty(c, "must hold", origin="user")  # user -> confirmed
    return f


def test_full_frame_converges() -> None:
    res = evaluate(_full_frame())
    assert res.ready is True and res.blockers == []


def test_missing_required_kinds_reported() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")
    res = evaluate(f)
    assert res.ready is False
    assert any("audience" in m for m in res.blockers)
    assert any("after_state" in m for m in res.blockers)


def test_proposed_claim_blocks() -> None:
    f = _full_frame()
    f.add_claim("boundary", "maybe not this", origin="llm")  # proposed
    res = evaluate(f)
    assert res.ready is False
    assert any("still proposed" in m for m in res.blockers)


def test_confirmed_claim_without_honesty_blocks() -> None:
    f = _full_frame()
    c = f.add_claim("success_signal", "extra signal", origin="user")  # confirmed, no honesty
    res = evaluate(f)
    assert res.ready is False
    assert any(c.id in m and "honesty" in m for m in res.blockers)


def test_blocking_vagueness_and_hard_question_block() -> None:
    f = _full_frame()
    f.add_vagueness("scale?", "unknown_blocking")
    res = evaluate(f)
    assert any("blocking vagueness" in m for m in res.blockers)
    f2 = _full_frame()
    f2.add_hard_question(f2.claims[0], "what if zero?", blocking=True)
    res2 = evaluate(f2)
    assert any("blocking hard question" in m for m in res2.blockers)


# --- #5 spec contract: gate semantics for the new claim kinds (t4/t5) ---------


def test_unconfirmed_assumption_is_warning_not_blocker() -> None:
    f = _full_frame()
    f.add_claim("assumption", "frames stay small", origin="llm")  # proposed
    res = evaluate(f)
    assert res.ready is True  # an assumption never blocks
    assert any("assumption" in w for w in res.warnings)


def test_requirement_is_spec_affecting() -> None:
    f = _full_frame()
    r = f.add_claim("requirement", "must round-trip", origin="user")  # confirmed, no honesty
    res = evaluate(f)
    assert res.ready is False
    assert any(r.id in b and "honesty" in b for b in res.blockers)


def test_descriptive_kinds_do_not_block() -> None:
    f = _full_frame()
    f.add_claim("non_goal", "not a PRD generator", origin="user")
    f.add_claim("decision", "keep the shipped vocabulary", origin="user")
    assert evaluate(f).ready is True  # neither needs a honesty condition


def test_structured_result_lists_parked_items() -> None:
    f = _full_frame()
    f.add_vagueness("ship a JSON Schema file?", "follow_up")
    res = evaluate(f)
    assert res.ready is True
    assert any("follow_up" in p for p in res.parked_items)
    assert res.required_next_moves == []  # nothing left to do
