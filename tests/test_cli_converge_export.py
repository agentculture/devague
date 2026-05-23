# tests/test_cli_converge_export.py
from __future__ import annotations

import json
from pathlib import Path

from devague import store
from devague.cli import main


def _converged(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])  # c1 announcement (confirmed)
    main(["interrogate", "c1", "--honesty", "announcement is true", "--origin", "user"])
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    # confirm an honesty condition on every confirmed spec-affecting claim
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])


def test_converge_reports_gaps_then_passes(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])
    capsys.readouterr()  # drain setup output
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False and payload["missing"]

    _converged(monkeypatch, tmp_path)
    capsys.readouterr()  # drain _converged output
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True


def test_export_blocked_until_converged(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])
    rc = main(["export"])
    assert rc == 1
    assert "has not converged" in capsys.readouterr().err


def test_export_writes_spec_when_converged(tmp_path, monkeypatch) -> None:
    _converged(monkeypatch, tmp_path)
    rc = main(["export"])
    assert rc == 0
    out = Path("docs/specs") / f"{store.current_slug()}.md"
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("# Specs in minutes")
    assert store.load(store.current_slug()).status == "exported"
