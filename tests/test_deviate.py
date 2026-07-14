"""Tests for the delivery store + ``devague deviate`` move (esd t3).

Covers three layers: the ``Delivery``/``DeviationRecord`` domain model
(:mod:`devague.delivery`), its persistence (:mod:`devague.delivery_store`,
the plan_store peer including the 0.17.0 upgrade-on-write fix), and the CLI
move itself (:mod:`devague.cli._commands.deviate`). Acceptance criteria:

1. a deviate record persists under ``.devague/deliveries/<plan-slug>.json``
   with its own schema_version, fail-closed load, and upgrade-on-write
2. llm-origin deviations land proposed; only user confirm marks them
   approved; user-origin records auto-approve; a record without a reason is
   refused with a hint
3. the plan JSON is byte-identical before and after every deviate operation
"""

from __future__ import annotations

import json

import pytest

from devague import delivery_store, plan_store
from devague.cli import main
from devague.delivery import (
    CLASSIFICATIONS,
    DELIVERY_SCHEMA_VERSION,
    Delivery,
    DeviationRecord,
    from_dict,
    to_dict,
)
from devague.plan import Plan


def _plan(slug: str = "demo") -> Plan:
    p = Plan(slug=slug, title="Demo", frame_slug=slug)
    p.add_task("first task")
    return p


def _seed_plan(monkeypatch, tmp_path, slug: str = "demo") -> Plan:
    monkeypatch.chdir(tmp_path)
    plan = _plan(slug)
    plan_store.save(plan)
    return plan


def _delivery() -> Delivery:
    d = Delivery(plan_slug="demo")
    d.add_deviation("skipped a step", "t1", "ran out of time", origin="user")
    return d


# ── domain model ─────────────────────────────────────────────────────────────


def test_next_allocates_sequential_ids() -> None:
    d = Delivery(plan_slug="demo")
    r1 = d.add_deviation("first", "t1", "reason one")
    r2 = d.add_deviation("second", "t1", "reason two")
    assert (r1.id, r2.id) == ("d1", "d2")


def test_user_origin_auto_approves() -> None:
    d = Delivery(plan_slug="demo")
    rec = d.add_deviation("did x instead", "t1", "reason", origin="user")
    assert rec.status == "approved"


def test_llm_origin_lands_proposed() -> None:
    d = Delivery(plan_slug="demo")
    rec = d.add_deviation("did x instead", "t1", "reason", origin="llm")
    assert rec.status == "proposed"


def test_add_deviation_without_reason_raises() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError):
        d.add_deviation("did x instead", "t1", "")


def test_add_deviation_affects_repeatable_and_defaults_empty() -> None:
    d = Delivery(plan_slug="demo")
    rec = d.add_deviation("x", "t1", "reason", affects=["t2", "c3"])
    assert rec.affects == ["t2", "c3"]
    rec2 = d.add_deviation("y", "t1", "reason")
    assert rec2.affects == []


def test_add_deviation_classification_optional() -> None:
    d = Delivery(plan_slug="demo")
    rec = d.add_deviation("x", "t1", "reason")
    assert rec.classification is None
    rec2 = d.add_deviation("y", "t1", "reason", classification="risky")
    assert rec2.classification == "risky"


def test_add_deviation_rejects_unknown_classification() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError):
        d.add_deviation("x", "t1", "reason", classification="not-a-kind")


def test_add_deviation_rejects_unknown_origin() -> None:
    d = Delivery(plan_slug="demo")
    with pytest.raises(ValueError):
        d.add_deviation("x", "t1", "reason", origin="robot")


def test_find_deviation() -> None:
    d = _delivery()
    assert d.find_deviation("d1") is not None
    assert d.find_deviation("nope") is None


def test_set_status_transitions_and_reports_unknown() -> None:
    d = _delivery()
    assert d.set_status("d1", "rejected") is True
    assert d.find_deviation("d1").status == "rejected"
    assert d.set_status("dX", "approved") is False


def test_classification_kinds_include_expected_values() -> None:
    assert set(CLASSIFICATIONS) == {"acceptable", "risky", "needs-follow-up"}


def test_delivery_carries_schema_version() -> None:
    d = Delivery(plan_slug="demo")
    assert d.schema_version == DELIVERY_SCHEMA_VERSION
    assert to_dict(d)["schema_version"] == DELIVERY_SCHEMA_VERSION


def test_to_dict_from_dict_roundtrip() -> None:
    d = _delivery()
    d.deviations[0].classification = "acceptable"
    restored = from_dict(to_dict(d))
    assert restored.plan_slug == d.plan_slug
    assert restored.deviations[0] == d.deviations[0]


def test_from_dict_defaults_missing_schema_version_to_current() -> None:
    restored = from_dict({"plan_slug": "demo", "deviations": []})
    assert restored.schema_version == DELIVERY_SCHEMA_VERSION


def test_from_dict_rebuilds_deviation_record_fields() -> None:
    raw = {
        "plan_slug": "demo",
        "schema_version": DELIVERY_SCHEMA_VERSION,
        "deviations": [
            {
                "id": "d1",
                "what": "swapped approach",
                "task_ref": "t1",
                "reason": "faster path",
                "affects": ["t2"],
                "origin": "llm",
                "status": "proposed",
                "classification": "needs-follow-up",
            }
        ],
    }
    restored = from_dict(raw)
    rec = restored.deviations[0]
    assert isinstance(rec, DeviationRecord)
    assert rec.what == "swapped approach"
    assert rec.task_ref == "t1"
    assert rec.affects == ["t2"]
    assert rec.classification == "needs-follow-up"


# ── delivery_store ───────────────────────────────────────────────────────────


def test_save_load_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    loaded = delivery_store.load("demo")
    assert loaded.plan_slug == "demo"
    assert loaded.deviations[0].what == "skipped a step"
    assert loaded.created and loaded.updated


def test_load_missing_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        delivery_store.load("nope")


def test_load_or_new_creates_empty_delivery_when_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    d = delivery_store.load_or_new("demo")
    assert d.plan_slug == "demo"
    assert d.deviations == []
    assert not delivery_store.path_for("demo").exists()


def test_load_or_new_loads_existing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    d = delivery_store.load_or_new("demo")
    assert len(d.deviations) == 1


def test_path_for_rejects_unsafe_slug() -> None:
    with pytest.raises(ValueError):
        delivery_store.path_for("../../escape")


def test_save_writes_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    raw = json.loads(delivery_store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == DELIVERY_SCHEMA_VERSION


def test_load_rejects_newer_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    p = delivery_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = DELIVERY_SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(delivery_store.IncompatibleDeliverySchemaError, match="schema_version"):
        delivery_store.load("demo")


def test_load_rejects_tampered_internal_plan_slug(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    p = delivery_store.path_for("demo")
    p.write_text(
        p.read_text().replace('"plan_slug": "demo"', '"plan_slug": "../../escape"', 1),
        "utf-8",
    )
    with pytest.raises(ValueError):
        delivery_store.load("demo")


def test_load_rejects_slug_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.save(_delivery())
    p = delivery_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["plan_slug"] = "other"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        delivery_store.load("demo")


def test_save_upgrades_stale_schema_version_on_write(tmp_path, monkeypatch) -> None:
    # The 0.17.0 fix pattern (frame/plan stores): save() must stamp the CURRENT
    # schema_version rather than re-emitting a loaded/older one, or the fail-closed
    # load gate (schema_version > DELIVERY_SCHEMA_VERSION) is defeated.
    monkeypatch.chdir(tmp_path)
    d = _delivery()
    d.schema_version = 0
    delivery_store.save(d)
    raw = json.loads(delivery_store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == DELIVERY_SCHEMA_VERSION
    assert delivery_store.load("demo").schema_version == DELIVERY_SCHEMA_VERSION


def test_load_legacy_delivery_without_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    delivery_store.DELIVERIES_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {"plan_slug": "demo", "deviations": []}
    delivery_store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    assert delivery_store.load("demo").schema_version == DELIVERY_SCHEMA_VERSION


# ── CLI: recording ───────────────────────────────────────────────────────────


def test_deviate_records_entry_round_trip(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["deviate", "used a different library", "--task", "t1", "--reason", "faster"])
    assert rc == 0
    delivery = delivery_store.load("demo")
    assert len(delivery.deviations) == 1
    rec = delivery.deviations[0]
    assert rec.id == "d1"
    assert rec.what == "used a different library"
    assert rec.task_ref == "t1"
    assert rec.reason == "faster"
    assert rec.affects == []
    assert rec.classification is None


def test_deviate_user_origin_auto_approves_end_to_end(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["deviate", "swap", "--task", "t1", "--reason", "why"])
    assert rc == 0
    assert delivery_store.load("demo").deviations[0].status == "approved"


def test_deviate_llm_origin_lands_proposed_end_to_end(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["deviate", "swap", "--task", "t1", "--reason", "why", "--origin", "llm"])
    assert rc == 0
    assert delivery_store.load("demo").deviations[0].status == "proposed"


def test_deviate_affects_repeatable(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(
        [
            "deviate",
            "swap",
            "--task",
            "t1",
            "--reason",
            "why",
            "--affects",
            "t2",
            "--affects",
            "c3",
        ]
    )
    assert rc == 0
    assert delivery_store.load("demo").deviations[0].affects == ["t2", "c3"]


def test_deviate_classification_flag(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(
        [
            "deviate",
            "swap",
            "--task",
            "t1",
            "--reason",
            "why",
            "--classification",
            "risky",
        ]
    )
    assert rc == 0
    assert delivery_store.load("demo").deviations[0].classification == "risky"


def test_deviate_missing_reason_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["deviate", "swap", "--task", "t1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--reason" in err
    assert "hint:" in err
    assert not delivery_store.path_for("demo").exists()


def test_deviate_missing_task_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["deviate", "swap", "--reason", "why"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--task" in err
    assert "hint:" in err


def test_deviate_json_shape_on_record(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["deviate", "swap", "--task", "t1", "--reason", "why", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "id": "d1",
        "what": "swap",
        "task": "t1",
        "reason": "why",
        "affects": [],
        "origin": "user",
        "status": "approved",
        "classification": None,
    }


# ── CLI: confirm / reject (user-only) ────────────────────────────────────────


def test_deviate_confirm_marks_approved(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    main(["deviate", "swap", "--task", "t1", "--reason", "why", "--origin", "llm"])
    assert delivery_store.load("demo").deviations[0].status == "proposed"
    rc = main(["deviate", "--confirm", "d1"])
    assert rc == 0
    assert delivery_store.load("demo").deviations[0].status == "approved"


def test_deviate_reject_marks_rejected(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    main(["deviate", "swap", "--task", "t1", "--reason", "why", "--origin", "llm"])
    rc = main(["deviate", "--reject", "d1"])
    assert rc == 0
    assert delivery_store.load("demo").deviations[0].status == "rejected"


def test_deviate_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    rc = main(["deviate", "--confirm", "d99"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such deviation" in err
    assert "hint:" in err


# ── CLI: list ────────────────────────────────────────────────────────────────


def test_deviate_list_text_output_empty(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["deviate", "--list"])
    assert rc == 0
    assert "no deviations recorded yet" in capsys.readouterr().out


def test_deviate_bare_invocation_lists(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    main(["deviate", "swap", "--task", "t1", "--reason", "why"])
    capsys.readouterr()
    rc = main(["deviate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "d1" in out and "swap" in out


def test_deviate_list_json_shape(tmp_path, monkeypatch, capsys) -> None:
    _seed_plan(monkeypatch, tmp_path)
    main(["deviate", "first", "--task", "t1", "--reason", "r1"])
    main(["deviate", "second", "--task", "t1", "--reason", "r2"])
    capsys.readouterr()
    rc = main(["deviate", "--list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == "demo"
    assert [d["id"] for d in payload["deviations"]] == ["d1", "d2"]


def test_deviate_plan_flag_targets_named_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan("first-plan"))
    plan_store.save(_plan("second-plan"))
    rc = main(
        [
            "deviate",
            "swap",
            "--task",
            "t1",
            "--reason",
            "why",
            "--plan",
            "first-plan",
        ]
    )
    assert rc == 0
    assert len(delivery_store.load("first-plan").deviations) == 1
    assert not delivery_store.path_for("second-plan").exists()


def test_deviate_no_plan_selected_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["deviate", "swap", "--task", "t1", "--reason", "why"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no plan selected" in err


# ── acceptance criterion 3: plan JSON is byte-identical ──────────────────────


def test_deviate_never_mutates_the_plan_json(tmp_path, monkeypatch) -> None:
    _seed_plan(monkeypatch, tmp_path)
    plan_path = plan_store.path_for("demo")
    before = plan_path.read_bytes()

    main(["deviate", "used a workaround", "--task", "t1", "--reason", "blocked upstream"])
    main(["deviate", "swap", "--task", "t1", "--reason", "why", "--origin", "llm"])
    main(["deviate", "--confirm", "d2"])
    main(["deviate", "--reject", "d1"])
    main(["deviate", "--list"])
    main(["deviate", "--list", "--json"])

    after = plan_path.read_bytes()
    assert before == after


def test_deviate_deterministic_no_subprocess_or_llm(tmp_path, monkeypatch) -> None:
    # Guard against scope creep: recording must never shell out.
    import subprocess

    _seed_plan(monkeypatch, tmp_path)
    called = {"n": 0}
    real_run = subprocess.run

    def _guard(*args, **kwargs):
        called["n"] += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _guard)
    main(["deviate", "no subprocess used", "--task", "t1", "--reason", "why"])
    assert called["n"] == 0
