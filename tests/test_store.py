from __future__ import annotations

import pytest

from devague import store
from devague.frame import Frame


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
