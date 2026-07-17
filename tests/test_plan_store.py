from __future__ import annotations

import json

import pytest

from devague import plan_store, store
from devague.frame import Frame
from devague.plan import PLAN_SCHEMA_VERSION, Plan


def _plan() -> Plan:
    p = Plan(slug="demo", title="Demo", frame_slug="demo")
    p.add_task("first task")
    return p


def test_save_load_roundtrip_and_current(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan())
    assert plan_store.current_slug() == "demo"
    assert plan_store.list_slugs() == ["demo"]
    loaded = plan_store.load("demo")
    assert loaded.title == "Demo" and loaded.frame_slug == "demo"
    assert loaded.created and loaded.updated


def test_load_missing_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        plan_store.load("nope")


def test_list_slugs_empty_without_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert plan_store.list_slugs() == []
    assert plan_store.current_slug() is None


def test_path_for_rejects_unsafe_slug() -> None:
    with pytest.raises(ValueError):
        plan_store.path_for("../../escape")


def test_load_rejects_tampered_internal_slug(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan())
    p = plan_store.path_for("demo")
    p.write_text(p.read_text().replace('"slug": "demo"', '"slug": "../../escape"', 1), "utf-8")
    with pytest.raises(ValueError):
        plan_store.load("demo")


def test_load_rejects_tampered_frame_slug(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan())
    p = plan_store.path_for("demo")
    p.write_text(p.read_text().replace('"frame_slug": "demo"', '"frame_slug": "../x"', 1), "utf-8")
    with pytest.raises(ValueError):
        plan_store.load("demo")


def test_plan_coexists_with_same_slug_frame(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.save(Frame(slug="demo", title="Demo"))
    plan_store.save(_plan())
    # Both persist independently in their own directories.
    assert store.list_slugs() == ["demo"]
    assert plan_store.list_slugs() == ["demo"]


def test_save_writes_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan())
    raw = json.loads(plan_store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == PLAN_SCHEMA_VERSION
    assert plan_store.load("demo").schema_version == PLAN_SCHEMA_VERSION


def test_load_rejects_newer_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan())
    p = plan_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = PLAN_SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(plan_store.IncompatiblePlanSchemaError, match="schema_version"):
        plan_store.load("demo")


def test_load_legacy_plan_without_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan_store.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {"slug": "demo", "title": "Demo", "frame_slug": "demo", "tasks": []}
    plan_store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    assert plan_store.load("demo").schema_version == PLAN_SCHEMA_VERSION


def test_load_v1_plan_with_tasks_but_no_instruction_field(tmp_path, monkeypatch) -> None:
    # #53 t2: a pre-existing (schema_version 1) plan predates the instruction field
    # on Task entirely — it must still load, with instruction defaulting to "".
    monkeypatch.chdir(tmp_path)
    plan_store.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {
        "slug": "demo",
        "title": "Demo",
        "frame_slug": "demo",
        "schema_version": 1,
        "tasks": [{"id": "t1", "summary": "first task"}],
    }
    plan_store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    loaded = plan_store.load("demo")
    # A declared v1 stays 1 (not silently upgraded); loading itself must not error,
    # and the new field defaults to "" for a task dict that predates it.
    assert loaded.schema_version == 1
    assert loaded.find_task("t1").instruction == ""


def test_save_load_roundtrips_task_instruction_verbatim(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = _plan()
    p.find_task("t1").instruction = "write the failing test before the fix"
    plan_store.save(p)
    loaded = plan_store.load("demo")
    assert loaded.find_task("t1").instruction == "write the failing test before the fix"


def test_save_load_roundtrips_resolved_risk(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = _plan()
    r = p.add_risk("scope?", "unknown_blocking")
    p.resolve_risk(r.id, "decided: proceed with option B")
    plan_store.save(p)
    loaded = plan_store.load("demo")
    loaded_risk = loaded.find_risk(r.id)
    assert loaded_risk.resolved is True
    assert loaded_risk.resolution == "decided: proceed with option B"


def test_load_v2_plan_with_risk_but_no_resolution_fields(tmp_path, monkeypatch) -> None:
    # resolve-parked-vagueness t2: a pre-existing (schema_version 2) plan predates
    # PlanRisk.resolved/resolution entirely — it must still load, defaulting both.
    monkeypatch.chdir(tmp_path)
    plan_store.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {
        "slug": "demo",
        "title": "Demo",
        "frame_slug": "demo",
        "schema_version": 2,
        "tasks": [],
        "risks": [{"id": "r1", "text": "scope?", "kind": "unknown_blocking", "task_id": None}],
    }
    plan_store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    loaded = plan_store.load("demo")
    assert loaded.schema_version == 2
    r = loaded.find_risk("r1")
    assert r.resolved is False
    assert r.resolution == ""


def test_load_rejects_slug_mismatch(tmp_path, monkeypatch) -> None:
    # A file under demo.json whose internal slug is a *different* valid slug must
    # be rejected, so a later save() can't be redirected onto another plan.
    monkeypatch.chdir(tmp_path)
    plan_store.save(_plan())
    p = plan_store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["slug"] = "other"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="slug mismatch"):
        plan_store.load("demo")


def test_save_upgrades_stale_schema_version_on_write(tmp_path, monkeypatch) -> None:
    # A plan loaded under an older label then mutated must be rewritten under the
    # version this binary writes, or the fail-closed load gate is defeated and an
    # old binary silently drops the newer payload (data loss). save() stamps the
    # current PLAN_SCHEMA_VERSION rather than re-emitting the loaded one.
    monkeypatch.chdir(tmp_path)
    p = _plan()
    p.schema_version = 1
    plan_store.save(p)
    assert plan_store.load("demo").schema_version == PLAN_SCHEMA_VERSION
    raw = json.loads(plan_store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == PLAN_SCHEMA_VERSION
