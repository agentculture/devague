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


# --- scope --amend (issue #84): replace a finding in place --------------------


def test_scope_amend_replaces_finding_in_place(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["capture", "--kind", "before_state", "count is 16", "--origin", "user"])  # c2
    main(
        [
            "scope",
            "colleague subprocess inventory",
            "--finding",
            "16 spawn literals",
            "--seeds",
            "c2",
        ]
    )  # s1
    rc = main(
        [
            "scope",
            "--amend",
            "s1",
            "--finding",
            "21 spawn literals across 15 modules",
        ]
    )
    assert rc == 0
    frame = store.load(slug)
    entry = frame.scope_entries[0]
    assert entry.id == "s1"  # no id churn
    assert entry.surface == "colleague subprocess inventory"  # untouched
    assert entry.finding == "21 spawn literals across 15 modules"
    assert entry.seeds == ["c2"]  # untouched


def test_scope_amend_json_shape(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["scope", "a.py", "--finding", "first"])
    capsys.readouterr()
    rc = main(["scope", "--amend", "s1", "--finding", "corrected", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "id": "s1",
        "surface": "a.py",
        "finding": "corrected",
        "seeds": [],
    }


def test_scope_amend_echoes_text_mode(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["scope", "a.py", "--finding", "first"])
    capsys.readouterr()
    rc = main(["scope", "--amend", "s1", "--finding", "corrected"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "amended s1 (a.py)"


def test_scope_amend_unknown_id_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["scope", "--amend", "s99", "--finding", "corrected"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown scope entry id" in err
    assert "hint:" in err


def test_scope_amend_missing_finding_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["scope", "a.py", "--finding", "first"])
    capsys.readouterr()
    rc = main(["scope", "--amend", "s1"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--finding" in err
    frame = store.load(store.current_slug())
    assert frame.scope_entries[0].finding == "first"  # untouched


def test_scope_amend_with_surface_positional_refused(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["scope", "a.py", "--finding", "first"])
    capsys.readouterr()
    rc = main(["scope", "stray-surface", "--amend", "s1", "--finding", "corrected"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not both" in err
    frame = store.load(store.current_slug())
    assert frame.scope_entries[0].finding == "first"  # untouched


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
