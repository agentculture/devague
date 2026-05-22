from __future__ import annotations

from devague.frame import Frame, from_dict, to_dict


def test_add_claim_user_is_confirmed_llm_is_proposed() -> None:
    f = Frame(slug="s", title="t")
    a = f.add_claim("announcement", "we shipped X", origin="user")
    b = f.add_claim("audience", "devs", origin="llm")
    assert a.id == "c1" and a.status == "confirmed"
    assert b.id == "c2" and b.status == "proposed"


def test_add_honesty_and_hard_question_and_vagueness_ids() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x")
    h = f.add_honesty(c, "must be measurable", origin="llm")
    q = f.add_hard_question(c, "what if empty?", blocking=True)
    v = f.add_vagueness("unsure about scale", "unknown_blocking")
    assert h.id == "h1" and h.status == "proposed"
    assert q.id == "q1" and q.blocking is True and q.resolved is False
    assert v.id == "v1" and v.kind == "unknown_blocking"


def test_set_status_finds_claim_or_honesty() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("audience", "devs", origin="llm")
    h = f.add_honesty(c, "cond", origin="llm")
    assert f.set_status("c1", "confirmed") is True and c.status == "confirmed"
    assert f.set_status("h1", "confirmed") is True and h.status == "confirmed"
    assert f.set_status("nope", "confirmed") is False


def test_roundtrip_to_from_dict() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "x", origin="user")
    f.add_honesty(c, "cond")
    f.add_hard_question(c, "q?", blocking=True)
    f.add_vagueness("v", "follow_up", claim_id="c1")
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.claims[0].honesty_conditions[0].text == "cond"
