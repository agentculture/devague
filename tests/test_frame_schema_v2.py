"""Schema v2: scope entries + per-item instruction fields (#53 t1).

Covers c10 (per-item instruction), h3 (instructions round-trip verbatim,
absent instruction renders nothing / defaults empty), c4 + h9 (a scope survey
stage exists as first-class state with provenance to claims).
"""

from __future__ import annotations

import json

import pytest

from devague import store
from devague.frame import (
    SCHEMA_VERSION,
    Claim,
    Frame,
    HonestyCondition,
    ScopeEntry,
    from_dict,
    to_dict,
)


def test_schema_version_bumped_exactly_once() -> None:
    # Pinned at 2 when this file was written (#53 t1); a later legitimate bump
    # (resolve-parked-vagueness t1, v3: Vagueness.resolved/resolution) moves
    # this pin forward rather than leaving a stale, now-false assertion.
    assert SCHEMA_VERSION == 3


def test_claim_and_honesty_instruction_default_empty() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("announcement", "we shipped X", origin="user")
    h = f.add_honesty(c, "must be measurable", origin="llm")
    assert c.instruction == ""
    assert h.instruction == ""


def test_claim_and_honesty_instruction_settable_verbatim() -> None:
    c = Claim(id="c1", kind="requirement", text="x", instruction="verify via `pytest -k x`")
    h = HonestyCondition(id="h1", text="y", instruction="check the CLI --json output")
    assert c.instruction == "verify via `pytest -k x`"
    assert h.instruction == "check the CLI --json output"


def test_add_scope_entry_ids_and_defaults() -> None:
    f = Frame(slug="s", title="t")
    e1 = f.add_scope_entry("existing frame.py", "no instruction field today")
    e2 = f.add_scope_entry("existing store.py", "schema_version fails closed already")
    assert isinstance(e1, ScopeEntry)
    assert (e1.id, e2.id) == ("s1", "s2")
    assert e1.seeds == []
    assert f.scope_entries == [e1, e2]


def test_add_scope_entry_with_seeds_referencing_existing_claims() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("requirement", "must persist instructions", origin="user")
    e = f.add_scope_entry("survey of store.py", "needs instruction field", seeds=[c.id])
    assert e.seeds == ["c1"]


def test_add_scope_entry_rejects_unknown_seed_id() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError):
        f.add_scope_entry("survey", "finding", seeds=["c999"])


def test_add_scope_entry_rejects_unknown_seed_id_among_valid_ones() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("requirement", "must persist instructions", origin="user")
    with pytest.raises(ValueError):
        f.add_scope_entry("survey", "finding", seeds=[c.id, "c999"])


def test_roundtrip_scope_entries_and_instructions_via_dict() -> None:
    f = Frame(slug="s", title="t")
    c = f.add_claim("requirement", "instructions round-trip", origin="user")
    c.instruction = "capture, store, export renders them verbatim"
    h = f.add_honesty(c, "cond", origin="user")
    h.instruction = "check export output contains the instruction text"
    f.add_scope_entry("existing frame.py", "no instruction field today", seeds=[c.id])

    f2 = from_dict(to_dict(f))

    assert to_dict(f2) == to_dict(f)
    assert f2.claims[0].instruction == "capture, store, export renders them verbatim"
    assert f2.claims[0].honesty_conditions[0].instruction == (
        "check export output contains the instruction text"
    )
    assert f2.scope_entries[0].surface == "existing frame.py"
    assert f2.scope_entries[0].finding == "no instruction field today"
    assert f2.scope_entries[0].seeds == [c.id]


def test_roundtrip_scope_entries_and_instructions_via_store(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    c = f.add_claim("requirement", "instructions round-trip", origin="user")
    c.instruction = "verify via the export renderer"
    f.add_scope_entry("survey", "finding", seeds=[c.id])
    store.save(f)
    assert to_dict(store.load("demo")) == to_dict(f)


def test_legacy_v1_dict_loads_with_empty_scope_and_instruction_defaults() -> None:
    legacy = {
        "slug": "s",
        "title": "t",
        "schema_version": 1,
        "claims": [
            {
                "id": "c1",
                "kind": "requirement",
                "text": "x",
                "origin": "user",
                "status": "confirmed",
            }
        ],
        "open_vagueness": [],
    }
    f = from_dict(legacy)
    assert f.claims[0].instruction == ""
    assert f.scope_entries == []


def test_legacy_v1_frame_without_schema_version_loads_via_store(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {"slug": "demo", "title": "Demo", "claims": [], "open_vagueness": []}
    store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    loaded = store.load("demo")
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded.scope_entries == []


def test_load_rejects_newer_schema_version_still_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.save(Frame(slug="demo", title="Demo"))
    p = store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = SCHEMA_VERSION + 1
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        store.load("demo")


def test_scope_entry_seeds_default_to_empty_list() -> None:
    e = ScopeEntry(id="s1", surface="a", finding="b")
    assert e.seeds == []
