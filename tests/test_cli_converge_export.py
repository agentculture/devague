# tests/test_cli_converge_export.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_converge_demotes_converged_frame_when_gate_fails(tmp_path, monkeypatch, capsys) -> None:
    """Fix 1: converge must demote a converged frame back to drafting when gate fails."""
    _converged(monkeypatch, tmp_path)
    capsys.readouterr()  # drain setup output
    # Verify it converges first.
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert store.load(store.current_slug()).status == "converged"
    # Add a blocking vagueness item — gate now fails.
    main(["park", "scale?", "--kind", "unknown_blocking"])
    capsys.readouterr()  # drain park output
    # converge again: should fail AND demote back to drafting.
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert store.load(store.current_slug()).status == "drafting"


def test_export_rejects_non_spec_format(tmp_path, monkeypatch, capsys) -> None:
    """Fix 3: export --format frame-md must be rejected by argparse (choices guard)."""
    _converged(monkeypatch, tmp_path)
    capsys.readouterr()  # drain setup output
    with pytest.raises(SystemExit) as exc:
        main(["export", "--format", "frame-md"])
    assert exc.value.code == 1


def test_converge_llm_honesty_blocks_until_confirmed(tmp_path, monkeypatch, capsys) -> None:
    """Fix 5: an llm-origin honesty condition stays proposed and blocks convergence."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Specs in minutes"])  # c1 announcement (confirmed, user)
    # Add user honesty on c1 so it passes its own honesty check.
    main(["interrogate", "c1", "--honesty", "announcement is true", "--origin", "user"])
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    # Add user honesty on all claims except one — leave c2 (audience) with only an llm honesty.
    f = store.load(store.current_slug())
    for c in f.claims:
        origin = "llm" if c.id == "c2" else "user"
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", origin])
    capsys.readouterr()  # drain setup output

    # Gate should fail: c2 has no confirmed honesty condition (llm proposed one).
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert any("c2" in m and "honesty" in m for m in payload["missing"])

    # Discover the honesty id via show --json.
    main(["show", "--json"])
    frame_dict = json.loads(capsys.readouterr().out)
    c2 = next(c for c in frame_dict["claims"] if c["id"] == "c2")
    hid = c2["honesty_conditions"][0]["id"]

    # Confirm the honesty condition.
    main(["confirm", hid])
    capsys.readouterr()

    # Now the gate should pass.
    rc = main(["converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
