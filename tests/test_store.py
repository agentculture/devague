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
