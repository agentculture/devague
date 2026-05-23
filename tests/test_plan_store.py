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
