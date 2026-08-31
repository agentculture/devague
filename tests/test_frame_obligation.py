"""Tests for the Obligation domain model on Frame (bvts t1, schema v6).

An Obligation records a behavioral commitment attached to a claim — the
*seam* it applies to, the *behavior* text describing what is owed, and a
verbatim *source_text* snapshot of the claim's text at filing time (so later
drift between the claim and what the obligation was filed against is
detectable, see ``obligation_drift`` below).

The record shape mirrors ``LapseRecord`` (issue #97 t1): prefix-generic id
minting via ``Frame._next``, origin-driven initial status
(``llm`` -> ``proposed``, ``user`` -> ``approved``), append-only with no
amend/delete path — only ``set_obligation_status`` mutates a filed record.
Unlike ``LapseRecord``, the field that needs cross-referencing validation
(``claim_id``) can only be checked against the live frame, so — exactly like
``add_lapse``'s ``code`` check and ``add_scope_entry``'s seed-id check — it
is validated at the *filing* path (``Frame.add_obligation``), never in
``Obligation.__post_init__``, which has no access to ``Frame.claims`` at
all.

Covers targets: c2, h4, c22, h18.
"""

from __future__ import annotations

import json

import pytest

from devague import store
from devague.frame import (
    OBLIGATION_STATUSES,
    SCHEMA_VERSION,
    Claim,
    Frame,
    Obligation,
    from_dict,
    obligation_drift,
    to_dict,
)

# ── AC1: Obligation shape, Frame.add_obligation fail-closed at filing path ────


def test_frame_obligations_defaults_empty() -> None:
    f = Frame(slug="s", title="t")
    assert f.obligations == []


def test_add_obligation_mints_sequential_ids() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "the API must validate input")
    o1 = f.add_obligation("c1", "input boundary", "reject malformed payloads")
    o2 = f.add_obligation("c1", "output boundary", "never leak stack traces")
    assert (o1.id, o2.id) == ("o1", "o2")
    assert f.obligations == [o1, o2]


def test_add_obligation_snapshots_source_claim_text() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "the API must validate input")
    o = f.add_obligation("c1", "input boundary", "reject malformed payloads")
    assert o.seam == "input boundary"
    assert o.behavior == "reject malformed payloads"
    assert o.source_text == "the API must validate input"
    assert o.claim_id == "c1"


def test_add_obligation_rejects_unknown_claim_id() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown claim id"):
        f.add_obligation("c99", "seam", "behavior")
    assert f.obligations == []


def test_add_obligation_user_origin_lands_approved() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "text")
    o = f.add_obligation("c1", "seam", "behavior", origin="user")
    assert o.status == "approved"


def test_add_obligation_llm_origin_lands_proposed() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "text")
    o = f.add_obligation("c1", "seam", "behavior", origin="llm")
    assert o.status == "proposed"


def test_add_obligation_defaults_origin_to_user_and_auto_approves() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "text")
    o = f.add_obligation("c1", "seam", "behavior")
    assert o.origin == "user"
    assert o.status == "approved"


def test_find_obligation() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "text")
    f.add_obligation("c1", "seam", "behavior")
    assert f.find_obligation("o1") is not None
    assert f.find_obligation("nope") is None


def test_roundtrip_obligations_via_dict_verbatim() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "the API must validate input")
    f.add_obligation("c1", "input boundary", "reject malformed payloads", origin="llm")
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.obligations == f.obligations
    o = f2.obligations[0]
    assert (o.id, o.claim_id, o.seam, o.behavior) == (
        "o1",
        "c1",
        "input boundary",
        "reject malformed payloads",
    )
    assert o.source_text == "the API must validate input"
    assert o.origin == "llm"
    assert o.status == "proposed"


def test_roundtrip_obligations_via_store(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_claim("requirement", "text")
    f.add_obligation("c1", "seam", "behavior", origin="user")
    store.save(f)
    loaded = store.load("demo")
    assert to_dict(loaded) == to_dict(f)
    assert loaded.obligations[0].seam == "seam"


# ── AC2: planting an obligation never demotes a confirmed claim ───────────────


def test_add_obligation_does_not_demote_confirmed_claim() -> None:
    """Pins the deliberate asymmetry with `interrogate --instruction`
    (cli/_commands/interrogate.py's `_apply_instruction`) and `amend_claim`,
    both of which flip a CONFIRMED claim back to `proposed`. Filing an
    obligation is not an edit to the claim itself -- it is a new record
    that snapshots the claim -- so the claim's own status must be untouched."""
    f = Frame(slug="s", title="t")
    claim = f.add_claim("requirement", "the API must validate input")
    assert claim.status == "confirmed"
    f.add_obligation("c1", "seam", "behavior")
    assert f.find_claim("c1").status == "confirmed"


def test_add_obligation_on_proposed_claim_leaves_it_proposed() -> None:
    f = Frame(slug="s", title="t")
    claim = f.add_claim("requirement", "text", origin="llm")
    assert claim.status == "proposed"
    f.add_obligation("c1", "seam", "behavior")
    assert f.find_claim("c1").status == "proposed"


# ── AC3: SCHEMA_VERSION == 6, fail-closed on 7, v5 frames load + re-save as v6 ─


def test_schema_version_is_6() -> None:
    assert SCHEMA_VERSION == 6


def test_load_rejects_newer_schema_version_before_parsing_malformed_obligations(
    tmp_path, monkeypatch
) -> None:
    """A frame declaring a newer schema (7) is refused fail-closed BEFORE
    from_dict attempts to parse it -- proven with an `obligations` entry
    missing required keys, which would otherwise raise a raw KeyError
    instead of the intended IncompatibleSchemaError."""
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    raw = {
        "slug": "demo",
        "title": "Demo",
        "schema_version": SCHEMA_VERSION + 1,
        "claims": [],
        "open_vagueness": [],
        "obligations": [{"id": "o1"}],  # missing seam/behavior/etc -- would KeyError
    }
    store.path_for("demo").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(store.IncompatibleSchemaError, match="schema_version"):
        store.load("demo")


def test_v5_frame_without_obligations_loads_clean_and_resaves_as_v6(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    legacy_v5 = {
        "slug": "demo",
        "title": "Demo",
        "schema_version": 5,
        "claims": [],
        "open_vagueness": [],
        "lapses": [],
    }
    store.path_for("demo").write_text(json.dumps(legacy_v5), encoding="utf-8")

    loaded = store.load("demo")
    assert loaded.schema_version == 5
    assert loaded.obligations == []

    store.save(loaded)
    reloaded_raw = json.loads(store.path_for("demo").read_text(encoding="utf-8"))
    assert reloaded_raw["schema_version"] == SCHEMA_VERSION == 6
    assert store.load("demo").obligations == []


def test_legacy_dict_without_obligations_key_loads_empty_list() -> None:
    f = from_dict(
        {"slug": "s", "title": "t", "schema_version": 5, "claims": [], "open_vagueness": []}
    )
    assert f.obligations == []


# ── AC4: pure drift function between an obligation snapshot and live claim ────


def test_obligation_drift_none_when_claim_text_unchanged() -> None:
    f = Frame(slug="s", title="t")
    claim = f.add_claim("requirement", "the API must validate input")
    o = f.add_obligation("c1", "seam", "behavior")
    assert obligation_drift(o, claim) is None


def test_obligation_drift_reports_when_claim_text_changed() -> None:
    f = Frame(slug="s", title="t")
    claim = f.add_claim("requirement", "the API must validate input")
    o = f.add_obligation("c1", "seam", "behavior")
    claim.text = "the API must validate and sanitize input"
    drift = obligation_drift(o, claim)
    assert drift is not None
    assert "o1" in drift
    assert "c1" in drift


def test_obligation_drift_rejects_mismatched_claim() -> None:
    o = Obligation(id="o1", claim_id="c1", seam="seam", behavior="behavior", source_text="x")
    other_claim = Claim(id="c2", kind="requirement", text="x")
    with pytest.raises(ValueError, match="not the source"):
        obligation_drift(o, other_claim)


# ── AC1/AC4 (chassis parity with LapseRecord): no amend/delete, status flips ──


def test_no_amend_or_delete_obligation_method_exists() -> None:
    for name in ("amend_obligation", "delete_obligation", "remove_obligation"):
        assert not hasattr(Frame, name), f"Frame must not expose {name}"


def test_set_obligation_status_transitions_and_reports_unknown() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "text")
    f.add_obligation("c1", "seam", "behavior", origin="llm")  # proposed
    assert f.set_obligation_status("o1", "approved") is True
    assert f.find_obligation("o1").status == "approved"
    assert f.set_obligation_status("oX", "rejected") is False


def test_set_obligation_status_rejects_unknown_status_without_mutating() -> None:
    f = Frame(slug="s", title="t")
    f.add_claim("requirement", "text")
    f.add_obligation("c1", "seam", "behavior", origin="llm")
    before = f.find_obligation("o1").status
    with pytest.raises(ValueError, match="unknown obligation status"):
        f.set_obligation_status("o1", "not-a-status")
    assert f.find_obligation("o1").status == before


def test_obligation_statuses_are_proposed_approved_rejected() -> None:
    assert set(OBLIGATION_STATUSES) == {"proposed", "approved", "rejected"}


def test_obligation_record_dataclass_validates_origin_and_status() -> None:
    with pytest.raises(ValueError, match="unknown obligation origin"):
        Obligation(
            id="o1",
            claim_id="c1",
            seam="seam",
            behavior="behavior",
            source_text="x",
            origin="alien",
        )
    with pytest.raises(ValueError, match="unknown obligation status"):
        Obligation(
            id="o1",
            claim_id="c1",
            seam="seam",
            behavior="behavior",
            source_text="x",
            status="weird",
        )
