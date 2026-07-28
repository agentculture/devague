from __future__ import annotations

import json

import pytest

from devague import store
from devague.frame import SCHEMA_VERSION, Frame, from_dict, to_dict


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


def test_save_upgrades_stale_schema_version_on_write(tmp_path, monkeypatch) -> None:
    # A frame loaded under an older label then mutated must be rewritten under the
    # version this binary writes, or the fail-closed load gate is defeated and an
    # old binary silently drops the newer payload (data loss). save() stamps the
    # current SCHEMA_VERSION rather than re-emitting the loaded one.
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.schema_version = 1
    store.save(f)
    assert store.load("demo").schema_version == SCHEMA_VERSION
    raw = json.loads(store.path_for("demo").read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION


# --- resolve-parked-vagueness t1: Vagueness resolution state (schema v3) ------


def test_save_load_roundtrip_resolved_vagueness_identical(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    f.add_vagueness("unsure about scale", "unknown_blocking")
    f.resolve_vagueness("v1", "decided: cap at 10k")
    store.save(f)
    loaded = store.load("demo")
    assert to_dict(loaded) == to_dict(f)
    assert loaded.open_vagueness[0].resolved is True
    assert loaded.open_vagueness[0].resolution == "decided: cap at 10k"


# --- issue-backlog-sweep t2: schema-gate-before-parse + nested tolerance -----


def test_load_rejects_newer_schema_before_parsing_nested_unknown_key(tmp_path, monkeypatch) -> None:
    # Before t2's load-order fix, from_dict ran BEFORE the schema_version gate, so
    # a genuinely newer-schema file whose nested hard_questions/open_vagueness
    # carried an unrecognised key crashed with a raw TypeError (HardQuestion(**q)
    # / Vagueness(**v) reject unexpected kwargs) instead of the intended
    # fail-closed IncompatibleSchemaError. The gate must now trip first.
    monkeypatch.chdir(tmp_path)
    f = Frame(slug="demo", title="Demo")
    c = f.add_claim("announcement", "shipped X")
    f.add_hard_question(c, "what if empty?", blocking=True)
    f.add_vagueness("unsure about scale", "unknown_blocking")
    store.save(f)
    p = store.path_for("demo")
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = SCHEMA_VERSION + 1
    raw["claims"][0]["hard_questions"][0]["from_a_future_devague"] = "unknown"
    raw["open_vagueness"][0]["from_a_future_devague"] = "unknown"
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(store.IncompatibleSchemaError, match="schema_version"):
        store.load("demo")


def test_hard_question_from_dict_tolerates_unknown_keys() -> None:
    # Mirrors Claim's existing tolerant construction (frame.py from_dict): a
    # nested hard_questions entry carrying a not-yet-recognised key must not
    # raw-TypeError, so the field t4 eventually adds can land safely.
    legacy = {
        "slug": "s",
        "title": "t",
        "claims": [
            {
                "id": "c1",
                "kind": "announcement",
                "text": "x",
                "hard_questions": [
                    {
                        "id": "q1",
                        "text": "what if empty?",
                        "blocking": True,
                        "resolution": "a future field this devague doesn't know yet",
                    }
                ],
            }
        ],
        "open_vagueness": [],
    }
    f = from_dict(legacy)
    q = f.claims[0].hard_questions[0]
    assert (q.id, q.text, q.blocking, q.resolved) == ("q1", "what if empty?", True, False)


def test_vagueness_from_dict_tolerates_unknown_keys() -> None:
    legacy = {
        "slug": "s",
        "title": "t",
        "claims": [],
        "open_vagueness": [
            {
                "id": "v1",
                "text": "unsure about scale",
                "kind": "unknown_blocking",
                "from_a_future_devague": "unknown",
            }
        ],
    }
    f = from_dict(legacy)
    v = f.open_vagueness[0]
    assert (v.id, v.text, v.kind, v.resolved, v.resolution) == (
        "v1",
        "unsure about scale",
        "unknown_blocking",
        False,
        "",
    )


def test_load_v3_frame_shape_loads_unchanged_under_v4(tmp_path, monkeypatch) -> None:
    # Acceptance criterion: existing v3 frames load unchanged after the v4 bump.
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    v3 = {
        "slug": "demo",
        "title": "Demo",
        "schema_version": 3,
        "status": "drafting",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-01-01T00:00:00Z",
        "claims": [
            {
                "id": "c1",
                "kind": "announcement",
                "text": "shipped X",
                "origin": "user",
                "status": "confirmed",
                "honesty_conditions": [],
                "hard_questions": [
                    {"id": "q1", "text": "what if empty?", "resolved": False, "blocking": True}
                ],
                "links": [],
                "instruction": "",
            }
        ],
        "open_vagueness": [
            {
                "id": "v1",
                "text": "unsure about scale",
                "kind": "unknown_blocking",
                "claim_id": None,
                "resolved": False,
                "resolution": "",
                "resolution_claim_id": None,
            }
        ],
        "scope_entries": [],
    }
    store.path_for("demo").write_text(json.dumps(v3), encoding="utf-8")
    loaded = store.load("demo")
    assert loaded.schema_version == 3  # a declared v3 stays 3, not silently upgraded
    assert loaded.claims[0].hard_questions[0].blocking is True
    assert loaded.open_vagueness[0].kind == "unknown_blocking"


def test_load_legacy_v2_vagueness_defaults_resolved_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    store.FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    legacy = {
        "slug": "demo",
        "title": "Demo",
        "schema_version": 2,
        "claims": [],
        "open_vagueness": [{"id": "v1", "text": "x", "kind": "follow_up", "claim_id": None}],
    }
    store.path_for("demo").write_text(json.dumps(legacy), encoding="utf-8")
    loaded = store.load("demo")
    assert loaded.open_vagueness[0].resolved is False
    assert loaded.open_vagueness[0].resolution == ""
