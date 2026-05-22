from __future__ import annotations

from devague.convergence import evaluate
from devague.frame import Frame

_REQUIRED_KINDS = (
    "announcement", "audience", "after_state", "before_state", "boundary", "success_signal"
)


def _full_frame() -> Frame:
    f = Frame(slug="s", title="t")
    for kind in _REQUIRED_KINDS:
        c = f.add_claim(kind, f"{kind} text", origin="user")  # user -> confirmed
        f.add_honesty(c, "must hold", origin="user")  # user -> confirmed
    return f


def test_full_frame_converges() -> None:
    res = evaluate(_full_frame())
    assert res.passed is True and res.missing == []


def test_missing_required_kinds_reported() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("announcement", "x", origin="user")
    res = evaluate(f)
    assert res.passed is False
    assert any("audience" in m for m in res.missing)
    assert any("after_state" in m for m in res.missing)


def test_proposed_claim_blocks() -> None:
    f = _full_frame()
    f.add_claim("boundary", "maybe not this", origin="llm")  # proposed
    res = evaluate(f)
    assert res.passed is False
    assert any("still proposed" in m for m in res.missing)


def test_confirmed_claim_without_honesty_blocks() -> None:
    f = _full_frame()
    c = f.add_claim("success_signal", "extra signal", origin="user")  # confirmed, no honesty
    res = evaluate(f)
    assert res.passed is False
    assert any(c.id in m and "honesty" in m for m in res.missing)


def test_blocking_vagueness_and_hard_question_block() -> None:
    f = _full_frame()
    f.add_vagueness("scale?", "unknown_blocking")
    res = evaluate(f)
    assert any("blocking vagueness" in m for m in res.missing)
    f2 = _full_frame()
    f2.add_hard_question(f2.claims[0], "what if zero?", blocking=True)
    res2 = evaluate(f2)
    assert any("blocking hard question" in m for m in res2.missing)
