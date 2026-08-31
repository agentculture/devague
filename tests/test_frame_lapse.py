"""Tests for the Lapse domain model on Frame (issue-97 t1, schema v5).

The Reasoning Degradation Ledger's record shape mirrors ``DeviationRecord``
(``devague/delivery.py``) — prefix-generic id minting via ``Frame._next``,
origin-driven initial status, fail-closed ``__post_init__`` validation for
enum-like fields, append-only records with no delete path. It deliberately
refines that chassis in one place (c21): ``code`` is validated at the
*filing* path (``add_lapse``), not in ``__post_init__``, so retiring a code
after a dogfood cycle never bricks a frame that already filed it — a closed
load-time enum would refuse to load any frame carrying a retired code,
because ``from_dict`` constructs the dataclass directly.

Covers targets: c2, h2, c17, h12, c20, c21, h16.
"""

from __future__ import annotations

import json

import pytest

from devague import store
from devague.frame import (
    LAPSE_CODES,
    LAPSE_STATUSES,
    SCHEMA_VERSION,
    Frame,
    LapseRecord,
    from_dict,
    to_dict,
)

# ── AC1: Frame.lapses, add_lapse id minting, origin-driven status, round-trip ─


def test_frame_lapses_defaults_empty() -> None:
    f = Frame(slug="s", title="t")
    assert f.lapses == []


def test_add_lapse_mints_sequential_ids() -> None:
    f = Frame(slug="s", title="t")
    r1 = f.add_lapse("grader-unverified", "graded without a rubric")
    r2 = f.add_lapse("control-absent", "no control group used")
    assert (r1.id, r2.id) == ("l1", "l2")
    assert f.lapses == [r1, r2]


def test_add_lapse_user_origin_lands_approved() -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse("provenance-missing", "cited without a source", origin="user")
    assert rec.status == "approved"


def test_add_lapse_llm_origin_lands_proposed() -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse("provenance-missing", "cited without a source", origin="llm")
    assert rec.status == "proposed"


def test_add_lapse_defaults_origin_to_user_and_auto_approves() -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse("n-below-claim", "claimed generality from n=1")
    assert rec.origin == "user"
    assert rec.status == "approved"


def test_add_lapse_stores_skipped_check_and_refs() -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse(
        "instrument-changed-mid-series",
        "swapped grader mid-run",
        skipped_check="re-baseline after swap",
        refs=["t3", "c7"],
    )
    assert rec.skipped_check == "re-baseline after swap"
    assert rec.refs == ["t3", "c7"]


def test_add_lapse_skipped_check_and_refs_default_empty() -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse("assumption-for-measurement", "assumed the metric measured intent")
    assert rec.skipped_check == ""
    assert rec.refs == []


def test_find_lapse() -> None:
    f = Frame(slug="s", title="t")
    f.add_lapse("grader-unverified", "x")
    assert f.find_lapse("l1") is not None
    assert f.find_lapse("nope") is None


def test_roundtrip_lapses_via_dict_verbatim() -> None:
    f = Frame(slug="s", title="t")
    f.add_lapse(
        "control-absent",
        "no control group",
        skipped_check="ran an A/B check",
        refs=["c3"],
        origin="llm",
    )
    f2 = from_dict(to_dict(f))
    assert to_dict(f2) == to_dict(f)
    assert f2.lapses == f.lapses
    rec = f2.lapses[0]
    assert (rec.id, rec.code, rec.what) == ("l1", "control-absent", "no control group")
    assert rec.skipped_check == "ran an A/B check"
    assert rec.refs == ["c3"]
    assert rec.origin == "llm"
    assert rec.status == "proposed"


def test_roundtrip_lapses_via_store(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_lapse("grader-unverified", "no rubric applied", origin="user")
    store.save(f)
    loaded = store.load("demo")
    assert to_dict(loaded) == to_dict(f)
    assert loaded.lapses[0].code == "grader-unverified"


def test_lapse_codes_include_the_six_starting_codes() -> None:
    assert set(LAPSE_CODES) == {
        "assumption-for-measurement",
        "grader-unverified",
        "control-absent",
        "n-below-claim",
        "instrument-changed-mid-series",
        "provenance-missing",
    }


@pytest.mark.parametrize("code", list(LAPSE_CODES))
def test_add_lapse_accepts_every_starting_code(code: str) -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse(code, "some degradation")
    assert rec.code == code


# ── AC2: code validated at filing time only, tolerant at load time (c21/h16) ──


def test_add_lapse_rejects_unknown_code() -> None:
    f = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown lapse code"):
        f.add_lapse("not-a-real-code", "something")
    assert f.lapses == []


def test_lapse_record_constructed_directly_with_unknown_code_does_not_raise() -> None:
    # from_dict constructs LapseRecord directly (never through add_lapse), so
    # __post_init__ must NOT validate `code` — only `origin`/`status` do.
    rec = LapseRecord(id="l1", code="a-code-nobody-filed-through-add-lapse", what="x")
    assert rec.code == "a-code-nobody-filed-through-add-lapse"


def test_retired_code_still_loads_and_survives_roundtrip(monkeypatch) -> None:
    """Files a lapse, simulates the code's retirement, then round-trips the
    frame through to_dict/from_dict and asserts it loads cleanly and the
    record survives verbatim (h16's pinning test)."""
    f = Frame(slug="s", title="t")
    rec = f.add_lapse("grader-unverified", "no rubric applied")
    payload = to_dict(f)

    # Simulate the dogfood-cycle retirement of "grader-unverified": it is no
    # longer a filable code, but frames that already filed it must still load.
    retired_codes = tuple(c for c in LAPSE_CODES if c != "grader-unverified")
    monkeypatch.setattr("devague.frame.LAPSE_CODES", retired_codes)

    # Filing it now is refused...
    f2 = Frame(slug="s", title="t")
    with pytest.raises(ValueError, match="unknown lapse code"):
        f2.add_lapse("grader-unverified", "no rubric applied")

    # ...but loading the frame that filed it before retirement still works.
    reloaded = from_dict(payload)
    assert reloaded.lapses[0].code == "grader-unverified"
    assert reloaded.lapses[0].id == rec.id
    assert to_dict(reloaded) == payload


def test_retired_code_still_loads_via_store_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_lapse("n-below-claim", "generalized from n=1")
    store.save(f)

    retired_codes = tuple(c for c in LAPSE_CODES if c != "n-below-claim")
    monkeypatch.setattr("devague.frame.LAPSE_CODES", retired_codes)

    loaded = store.load("demo")
    assert loaded.lapses[0].code == "n-below-claim"


# ── AC3: SCHEMA_VERSION >= 5 (lapses landed at v5; a later bump, e.g. bvts
# t1's Frame.obligations at v6, only ever moves it forward), fail-closed on
# newer-than-supported, v4 frames load + re-save at the current version ─────


def test_schema_version_is_at_least_5() -> None:
    assert SCHEMA_VERSION >= 5


def test_load_rejects_newer_schema_version_before_parsing_malformed_lapses(
    tmp_path, monkeypatch
) -> None:
    """A frame declaring a newer schema (6) is refused fail-closed BEFORE
    from_dict attempts to parse it — proven here with a `lapses` entry
    missing required keys, which would otherwise raise a raw KeyError
    instead of the intended IncompatibleSchemaError (mirrors store.py's
    documented check-before-parse order, t2 of issue-backlog-sweep)."""
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    raw = {
        "slug": "demo",
        "title": "Demo",
        "schema_version": SCHEMA_VERSION + 1,
        "claims": [],
        "open_vagueness": [],
        "lapses": [{"id": "l1"}],  # missing code/what -- would KeyError if parsed
    }
    store.path_for("demo").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(store.IncompatibleSchemaError, match="schema_version"):
        store.load("demo")


def test_v4_frame_without_lapses_loads_clean_and_resaves_at_current_version(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    legacy_v4 = {
        "slug": "demo",
        "title": "Demo",
        "schema_version": 4,
        "claims": [],
        "open_vagueness": [],
    }
    store.path_for("demo").write_text(json.dumps(legacy_v4), encoding="utf-8")

    loaded = store.load("demo")
    assert loaded.schema_version == 4
    assert loaded.lapses == []

    store.save(loaded)
    reloaded_raw = json.loads(store.path_for("demo").read_text(encoding="utf-8"))
    assert reloaded_raw["schema_version"] == SCHEMA_VERSION
    assert store.load("demo").lapses == []


def test_legacy_dict_without_lapses_key_loads_empty_list() -> None:
    f = from_dict(
        {"slug": "s", "title": "t", "schema_version": 4, "claims": [], "open_vagueness": []}
    )
    assert f.lapses == []


# ── AC4: no amend/delete API; only set_lapse_status mutates; refs unvalidated ─


def test_no_amend_or_delete_lapse_method_exists() -> None:
    for name in ("amend_lapse", "delete_lapse", "remove_lapse"):
        assert not hasattr(Frame, name), f"Frame must not expose {name}"


def test_set_lapse_status_transitions_and_reports_unknown() -> None:
    f = Frame(slug="s", title="t")
    f.add_lapse("grader-unverified", "x", origin="llm")  # proposed
    assert f.set_lapse_status("l1", "approved") is True
    assert f.find_lapse("l1").status == "approved"
    assert f.set_lapse_status("lX", "rejected") is False


def test_set_lapse_status_rejects_unknown_status_without_mutating() -> None:
    f = Frame(slug="s", title="t")
    f.add_lapse("grader-unverified", "x", origin="llm")
    before = f.find_lapse("l1").status
    with pytest.raises(ValueError, match="unknown lapse status"):
        f.set_lapse_status("l1", "not-a-status")
    assert f.find_lapse("l1").status == before


def test_lapse_statuses_are_proposed_approved_rejected() -> None:
    assert set(LAPSE_STATUSES) == {"proposed", "approved", "rejected"}


def test_lapse_refs_stored_verbatim_never_validated() -> None:
    f = Frame(slug="s", title="t")
    rec = f.add_lapse(
        "provenance-missing",
        "x",
        refs=["not-a-real-id", "t99", "some free text", ""],
    )
    assert rec.refs == ["not-a-real-id", "t99", "some free text", ""]


def test_lapse_record_dataclass_validates_origin_and_status_but_not_code() -> None:
    with pytest.raises(ValueError, match="unknown lapse origin"):
        LapseRecord(id="l1", code="grader-unverified", what="x", origin="alien")
    with pytest.raises(ValueError, match="unknown lapse status"):
        LapseRecord(id="l1", code="grader-unverified", what="x", status="weird")
    # An unknown/retired code never raises at construction time.
    LapseRecord(id="l1", code="anything-goes-here", what="x")
