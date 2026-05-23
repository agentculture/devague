from __future__ import annotations

import json

from devague import store
from devague.cli import main


def test_new_creates_frame_with_announcement(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["new", "Shipped instant specs", "--json"])
    assert rc == 0
    f = store.load(store.current_slug())
    assert f.claims[0].kind == "announcement"
    assert f.claims[0].status == "confirmed"


def test_capture_adds_classified_claim(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])
    capsys.readouterr()  # drain the "new" output before capture
    rc = main(["capture", "--kind", "audience", "developers", "--origin", "llm", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "audience"
    assert payload["status"] == "proposed"


def test_capture_without_frame_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["capture", "--kind", "audience", "devs"])
    assert rc == 1
    assert "no frame selected" in capsys.readouterr().err


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Shipped instant specs"])  # announcement = c1


def test_interrogate_adds_proposed_honesty(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["interrogate", "c1", "--honesty", "must be measurable", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["added"][0]["kind"] == "honesty"
    assert payload["added"][0]["status"] == "proposed"


def test_confirm_and_reject_transition_status(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    assert main(["confirm", "c2"]) == 0
    assert store.load(store.current_slug()).find_claim("c2").status == "confirmed"
    assert main(["reject", "c2"]) == 0
    assert store.load(store.current_slug()).find_claim("c2").status == "rejected"


def test_confirm_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    rc = main(["confirm", "zzz"])
    assert rc == 1
    assert "no such" in capsys.readouterr().err


def test_park_adds_vagueness(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    capsys.readouterr()  # drain the "new" output
    rc = main(["park", "scale is unclear", "--kind", "unknown_blocking", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "unknown_blocking"
    assert payload["id"] == "v1"
