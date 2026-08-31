"""Tests for the plan-side CriterionObligation model (t2, plan-side twin of
Frame.LapseRecord / issue #97 t1).

Mirrors ``Frame.add_lapse``/``LapseRecord`` (``devague/frame.py``): id minting
via ``Plan._next``, origin-driven initial status, fail-closed validation at
the *filing* path (``Plan.add_obligation``), append-only-ish with only
``set_obligation_status`` as a mutator. Unlike a lapse's ``code`` (which is
validated at filing but not at load, because codes retire), an obligation's
structural link — which task, which acceptance criterion — is what has to be
validated fail-closed, since criteria have no ids of their own: obligations
key by ``(task_id, criterion_index)`` plus a text ``criterion_snapshot``
captured at filing time so the obligation stays meaningful even if the
criterion's wording is later amended.

Covers targets: c2, c22.
"""

from __future__ import annotations

import json

import pytest

from devague import plan_store
from devague.plan import (
    OBLIGATION_STATUSES,
    PLAN_SCHEMA_VERSION,
    CriterionObligation,
    Plan,
    criterion_obligation_drift,
    from_dict,
    to_dict,
)


def _plan_with_task() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    t = p.add_task("first task")
    p.add_acceptance(t, "criterion one")
    p.add_acceptance(t, "criterion two")
    return p


# ── AC1: obligations attach to a task's acceptance criterion, validated fail-closed ─


def test_plan_obligations_defaults_empty() -> None:
    p = Plan(slug="s", title="t", frame_slug="s")
    assert p.obligations == []


def test_add_obligation_mints_sequential_ids() -> None:
    p = _plan_with_task()
    o1 = p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input")
    o2 = p.add_obligation("t1", 2, seam="store", behavior="round-trips")
    assert (o1.id, o2.id) == ("o1", "o2")
    assert p.obligations == [o1, o2]


def test_add_obligation_snapshots_criterion_text() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input")
    assert o.criterion_snapshot == "criterion one"
    assert o.task_id == "t1"
    assert o.criterion_index == 1
    assert o.seam == "cli"
    assert o.behavior == "rejects bad input"


def test_add_obligation_user_origin_lands_approved() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="x", origin="user")
    assert o.status == "approved"


def test_add_obligation_llm_origin_lands_proposed() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="x", origin="llm")
    assert o.status == "proposed"


def test_add_obligation_defaults_origin_to_user_and_auto_approves() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="x")
    assert o.origin == "user"
    assert o.status == "approved"


def test_add_obligation_rejects_unknown_task_id() -> None:
    p = _plan_with_task()
    with pytest.raises(ValueError, match="unknown task id"):
        p.add_obligation("tX", 1, seam="cli", behavior="x")
    assert p.obligations == []


def test_add_obligation_rejects_out_of_range_criterion_index() -> None:
    p = _plan_with_task()
    with pytest.raises(ValueError, match="acceptance criterion index out of range"):
        p.add_obligation("t1", 3, seam="cli", behavior="x")
    with pytest.raises(ValueError, match="acceptance criterion index out of range"):
        p.add_obligation("t1", 0, seam="cli", behavior="x")
    assert p.obligations == []


def test_find_obligation() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="x")
    assert p.find_obligation("o1") is not None
    assert p.find_obligation("nope") is None


def test_roundtrip_obligations_via_dict_verbatim() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 2, seam="store", behavior="round-trips", origin="llm")
    p2 = from_dict(to_dict(p))
    assert to_dict(p2) == to_dict(p)
    assert p2.obligations == p.obligations
    rec = p2.obligations[0]
    assert (rec.id, rec.task_id, rec.criterion_index) == ("o1", "t1", 2)
    assert rec.criterion_snapshot == "criterion two"
    assert rec.seam == "store"
    assert rec.behavior == "round-trips"
    assert rec.origin == "llm"
    assert rec.status == "proposed"


def test_roundtrip_obligations_via_store(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input", origin="user")
    plan_store.save(p)
    loaded = plan_store.load("demo")
    assert to_dict(loaded) == to_dict(p)
    assert loaded.obligations[0].seam == "cli"


# ── AC2: model method validates fail-closed; only set_obligation_status mutates ─


def test_no_amend_or_delete_obligation_method_exists() -> None:
    for name in ("amend_obligation", "delete_obligation", "remove_obligation"):
        assert not hasattr(Plan, name), f"Plan must not expose {name}"


def test_set_obligation_status_transitions_and_reports_unknown() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="x", origin="llm")  # proposed
    assert p.set_obligation_status("o1", "approved") is True
    assert p.find_obligation("o1").status == "approved"
    assert p.set_obligation_status("oX", "rejected") is False


def test_set_obligation_status_rejects_unknown_status_without_mutating() -> None:
    p = _plan_with_task()
    p.add_obligation("t1", 1, seam="cli", behavior="x", origin="llm")
    before = p.find_obligation("o1").status
    with pytest.raises(ValueError, match="unknown obligation status"):
        p.set_obligation_status("o1", "not-a-status")
    assert p.find_obligation("o1").status == before


def test_obligation_statuses_are_proposed_approved_rejected() -> None:
    assert set(OBLIGATION_STATUSES) == {"proposed", "approved", "rejected"}


def test_criterion_obligation_dataclass_validates_origin_and_status() -> None:
    with pytest.raises(ValueError, match="unknown obligation origin"):
        CriterionObligation(
            id="o1",
            task_id="t1",
            criterion_index=1,
            criterion_snapshot="x",
            seam="cli",
            behavior="x",
            origin="alien",
        )
    with pytest.raises(ValueError, match="unknown obligation status"):
        CriterionObligation(
            id="o1",
            task_id="t1",
            criterion_index=1,
            criterion_snapshot="x",
            seam="cli",
            behavior="x",
            status="weird",
        )


# ── AC3: PLAN_SCHEMA_VERSION == 5, fail-closed on 6, v4 plans load + re-save as v5 ─


def test_plan_schema_version_is_5() -> None:
    assert PLAN_SCHEMA_VERSION == 5


def test_load_rejects_newer_plan_schema_version_before_parsing_malformed_obligations(
    tmp_path, monkeypatch
) -> None:
    """A plan declaring a newer schema (6) is refused fail-closed BEFORE
    from_dict attempts to parse it — proven with an `obligations` entry
    missing required keys, which would otherwise raise a raw KeyError
    instead of the intended IncompatiblePlanSchemaError."""
    monkeypatch.chdir(tmp_path)
    plan_store.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    raw = {
        "slug": "demo",
        "title": "Demo",
        "frame_slug": "demo",
        "schema_version": PLAN_SCHEMA_VERSION + 1,
        "tasks": [],
        "risks": [],
        "obligations": [{"id": "o1"}],  # missing task_id/etc -- would KeyError if parsed
    }
    plan_store.path_for("demo").write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(plan_store.IncompatiblePlanSchemaError, match="schema_version"):
        plan_store.load("demo")


def test_v4_plan_without_obligations_loads_clean_and_resaves_as_v5(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    legacy_v4 = {
        "slug": "demo",
        "title": "Demo",
        "frame_slug": "demo",
        "schema_version": 4,
        "tasks": [],
        "risks": [],
    }
    plan_store.path_for("demo").write_text(json.dumps(legacy_v4), encoding="utf-8")

    loaded = plan_store.load("demo")
    assert loaded.schema_version == 4
    assert loaded.obligations == []

    plan_store.save(loaded)
    reloaded_raw = json.loads(plan_store.path_for("demo").read_text(encoding="utf-8"))
    assert reloaded_raw["schema_version"] == PLAN_SCHEMA_VERSION == 5
    assert plan_store.load("demo").obligations == []


# ── criterion_obligation_drift (bvts t4, plan-side twin of obligation_drift) ──


def test_criterion_obligation_drift_none_when_criterion_text_unchanged() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input")
    task = p.find_task("t1")
    assert criterion_obligation_drift(o, task) is None


def test_criterion_obligation_drift_reports_when_criterion_text_changed() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="rejects bad input")
    task = p.find_task("t1")
    task.acceptance_criteria[0] = "criterion one, revised"
    drift = criterion_obligation_drift(o, task)
    assert drift is not None
    assert "o1" in drift
    assert "t1" in drift


def test_criterion_obligation_drift_reports_when_criterion_removed() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 2, seam="cli", behavior="rejects bad input")
    task = p.find_task("t1")
    del task.acceptance_criteria[1]  # the criterion the obligation named is gone
    drift = criterion_obligation_drift(o, task)
    assert drift is not None
    assert "no longer exists" in drift


def test_criterion_obligation_drift_rejects_mismatched_task() -> None:
    p = _plan_with_task()
    o = p.add_obligation("t1", 1, seam="cli", behavior="x")
    other = p.add_task("second task")
    p.add_acceptance(other, "criterion for the other task")
    with pytest.raises(ValueError, match="not the source"):
        criterion_obligation_drift(o, other)


def test_legacy_dict_without_obligations_key_loads_empty_list() -> None:
    p = from_dict(
        {
            "slug": "s",
            "title": "t",
            "frame_slug": "s",
            "schema_version": 4,
            "tasks": [],
            "risks": [],
        }
    )
    assert p.obligations == []
