from __future__ import annotations

import json

import pytest

from devague import store
from devague.frame import SCHEMA_VERSION, Frame, to_dict


def test_slugify_caps_and_sanitises() -> None:
    assert store.slugify("Hello, World!") == "hello-world"
    assert store.slugify("   ") == "frame"
    assert len(store.slugify("x" * 200)) <= 50


def test_save_load_roundtrip_and_current(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "shipped X")
    store.save(f)
    assert store.current_slug() == "demo"
    assert store.list_slugs() == ["demo"]
    loaded = store.load("demo")
    assert loaded.title == "Demo"
    assert loaded.created and loaded.updated  # timestamps stamped on save


def test_load_missing_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load("nope")


@pytest.mark.parametrize("bad", ["../evil", "../../etc/passwd", "/abs", "a/b", "a.b", "", "-lead"])
def test_validate_slug_rejects_traversal_and_separators(bad) -> None:
    with pytest.raises(ValueError):
        store.validate_slug(bad)


def test_validate_slug_accepts_clean_slug() -> None:
    assert store.validate_slug("shipped-instant-specs") == "shipped-instant-specs"


def test_path_for_rejects_unsafe_slug() -> None:
    with pytest.raises(ValueError):
        store.path_for("../../escape")


def test_load_rejects_tampered_internal_slug(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "shipped X")
    store.save(f)
    # Tamper the persisted JSON so its internal slug escapes the frames dir.
    p = store.path_for("demo")
    p.write_text(p.read_text().replace('"demo"', '"../../escape"', 1), encoding="utf-8")
    with pytest.raises(ValueError):
        store.load("demo")


def test_unique_slug_avoids_collision(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert store.unique_slug("demo") == "demo"
    store.save(Frame(slug="demo", title="Demo"))
    assert store.unique_slug("demo") == "demo-2"
    store.save(Frame(slug="demo-2", title="Demo"))
    assert store.unique_slug("demo") == "demo-3"


# --- #5 spec contract: schema_version persistence -----------------------------


def test_save_writes_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.save(Frame(slug="demo", title="Demo"))
    raw = json.loads(store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION
    assert store.load("demo").schema_version == SCHEMA_VERSION


def test_lossless_roundtrip_with_new_kinds(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_claim("announcement", "shipped X", origin="user")
    f.add_claim("requirement", "must round-trip", origin="user")
    f.add_claim("assumption", "frames stay small", origin="llm")
    store.save(f)
    assert to_dict(store.load("demo")) == to_dict(f)


def test_load_rejects_newer_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.save(Frame(slug="demo", title="Demo"))
    p = store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = SCHEMA_VERSION + 99
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        store.load("demo")


def test_load_legacy_frame_without_schema_version(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {"slug": "demo", "title": "Demo", "claims": [], "open_vagueness": []}
    store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    assert store.load("demo").schema_version == SCHEMA_VERSION


def test_load_rejects_slug_mismatch(tmp_path, monkeypatch) -> None:
    # A file under demo.json whose internal slug is a *different* valid slug must
    # be rejected, so a later save() can't be redirected onto another frame.
    monkeypatch.chdir(tmp_path)
    store.save(Frame(slug="demo", title="Demo"))
    p = store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["slug"] = "other"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="slug mismatch"):
        store.load("demo")
