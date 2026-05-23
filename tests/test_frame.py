from __future__ import annotations

import pytest

from devague.frame import (
    CLAIM_KINDS,
    SCHEMA_VERSION,
    SPEC_AFFECTING_KINDS,
    Claim,
    Frame,
    HonestyCondition,
    Vagueness,
    from_dict,
    to_dict,
)


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


# --- #5 spec contract: enriched entity model ----------------------------------


def test_new_claim_kinds_present() -> None:
    for kind in ("non_goal", "requirement", "assumption", "decision"):
        assert kind in CLAIM_KINDS


def test_requirement_is_spec_affecting_descriptive_kinds_are_not() -> None:
    assert "requirement" in SPEC_AFFECTING_KINDS
    # Descriptive kinds (and the soft assumption kind) must not demand a honesty
    # condition / block convergence by being proposed.
    for kind in ("non_goal", "decision", "open_question", "assumption"):
        assert kind not in SPEC_AFFECTING_KINDS


def test_can_add_new_kind_claims() -> None:
    f = Frame(slug="s", title="t")
    r = f.add_claim("requirement", "must persist losslessly", origin="user")
    n = f.add_claim("non_goal", "not a PRD generator", origin="user")
    a = f.add_claim("assumption", "frames are small", origin="llm")
    d = f.add_claim("decision", "keep shipped vocabulary", origin="user")
    assert (r.kind, n.kind, a.kind, d.kind) == (
        "requirement",
        "non_goal",
        "assumption",
        "decision",
    )
    assert a.status == "proposed"  # llm origin still lands proposed


def test_frame_carries_schema_version() -> None:
    f = Frame(slug="s", title="t")
    assert f.schema_version == SCHEMA_VERSION
    assert to_dict(f)["schema_version"] == SCHEMA_VERSION
    assert from_dict(to_dict(f)).schema_version == SCHEMA_VERSION


def test_legacy_frame_without_schema_version_loads() -> None:
    # A 0.4.0 frame has no schema_version key — it must still load.
    f = from_dict({"slug": "s", "title": "t", "claims": [], "open_vagueness": []})
    assert f.schema_version == SCHEMA_VERSION


@pytest.mark.parametrize("bad", [1.9, True, "1", None])
def test_from_dict_rejects_non_integer_schema_version(bad) -> None:
    # int() would silently coerce 1.9->1 / True->1; a malformed type must raise.
    with pytest.raises(ValueError, match="schema_version"):
        from_dict({"slug": "s", "title": "t", "schema_version": bad})


def test_dataclasses_validate_enums() -> None:
    with pytest.raises(ValueError):
        Claim(id="c1", kind="bogus", text="x")
    with pytest.raises(ValueError):
        Claim(id="c1", kind="audience", text="x", origin="alien")
    with pytest.raises(ValueError):
        Claim(id="c1", kind="audience", text="x", status="weird")
    with pytest.raises(ValueError):
        Vagueness(id="v1", text="x", kind="nope")
    with pytest.raises(ValueError):
        HonestyCondition(id="h1", text="x", status="weird")
