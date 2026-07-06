"""Tests for ``devague scope`` — records explored surfaces + findings (#53 t3)."""

from __future__ import annotations

import json

from devague import store
from devague.cli import main


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship sharper method", "--title", "sharper-method"])


def test_scope_records_entry_round_trip(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    rc = main(["scope", "devague/frame.py", "--finding", "claim model lives here"])
    assert rc == 0
    frame = store.load(slug)
    assert len(frame.scope_entries) == 1
    entry = frame.scope_entries[0]
    assert entry.id == "s1"
    assert entry.surface == "devague/frame.py"
    assert entry.finding == "claim model lives here"
    assert entry.seeds == []


def test_scope_records_entry_with_seeds(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["capture", "--kind", "requirement", "add a scope move"])
    rc = main(
        [
            "scope",
            "devague/cli/_commands/park.py",
            "--finding",
            "closest peer in shape",
            "--seeds",
            "c1",
        ]
    )
    assert rc == 0
    frame = store.load(slug)
    assert frame.scope_entries[0].seeds == ["c1"]


def test_scope_json_shape_on_record(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["scope", "docs/spec-contract.md", "--finding", "schema contract", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "id": "s1",
        "surface": "docs/spec-contract.md",
        "finding": "schema contract",
        "seeds": [],
    }


def test_scope_list_json_shape(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["scope", "a.py", "--finding", "first"])
    main(["scope", "b.py", "--finding", "second"])
    capsys.readouterr()
    rc = main(["scope", "--list", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope_entries"][0]["id"] == "s1"
    assert payload["scope_entries"][1]["id"] == "s2"
    assert [e["surface"] for e in payload["scope_entries"]] == ["a.py", "b.py"]


def test_scope_bare_invocation_lists(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["scope", "a.py", "--finding", "first"])
    capsys.readouterr()
    rc = main(["scope"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "s1" in out and "a.py" in out and "first" in out


def test_scope_bare_invocation_no_entries(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["scope"])
    assert rc == 0
    assert "no scope entries yet" in capsys.readouterr().out


def test_scope_unknown_seed_id_refused_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["scope", "devague/frame.py", "--finding", "bogus link", "--seeds", "c99"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown seed claim id" in err
    assert "hint:" in err
    # Transactional: nothing was recorded.
    frame = store.load(store.current_slug())
    assert frame.scope_entries == []


def test_scope_missing_finding_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["scope", "devague/frame.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--finding" in err
    frame = store.load(store.current_slug())
    assert frame.scope_entries == []


def test_scope_provenance_text_stored_verbatim(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    surface = "devague/cli/_commands/park.py + question.py"
    finding = "closest peers in shape — cite the file, not a generic disclaimer"
    main(["scope", surface, "--finding", finding])
    frame = store.load(slug)
    assert frame.scope_entries[0].surface == surface
    assert frame.scope_entries[0].finding == finding


def test_scope_frame_flag_targets_named_frame(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "First idea", "--title", "first-idea"])
    capsys.readouterr()
    main(["new", "Second idea", "--title", "second-idea"])
    capsys.readouterr()
    rc = main(["scope", "docs/", "--finding", "docs surface", "--frame", "first-idea"])
    assert rc == 0
    assert store.load("first-idea").scope_entries[0].surface == "docs/"
    assert store.load("second-idea").scope_entries == []


def test_scope_deterministic_no_subprocess_or_llm(tmp_path, monkeypatch) -> None:
    # Guard against accidental scope creep: recording must never shell out or
    # touch the filesystem beyond the frame store itself.
    import subprocess

    _seed(monkeypatch, tmp_path)
    called = {"n": 0}
    real_run = subprocess.run

    def _guard(*args, **kwargs):
        called["n"] += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _guard)
    main(["scope", "devague/frame.py", "--finding", "no subprocess used"])
    assert called["n"] == 0
