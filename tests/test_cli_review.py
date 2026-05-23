from __future__ import annotations

import json

from devague import store
from devague.cli import main


def _seed_proposed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship review loop"])  # c1 announcement (confirmed)
    main(["capture", "--kind", "audience", "devs", "--origin", "llm"])  # c2 proposed
    main(["interrogate", "c1", "--honesty", "must be true"])  # h1 proposed (origin llm)


def test_review_lists_proposed_with_ids(tmp_path, monkeypatch, capsys) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    capsys.readouterr()
    assert main(["review"]) == 0
    out = capsys.readouterr().out
    assert "c2" in out and "h1" in out
    assert "nothing confirmed yet" in out.lower()


def test_review_runs_on_non_converged_frame(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    # The frame is nowhere near converged; review must still succeed (un-gated).
    assert main(["review"]) == 0


def test_review_does_not_mutate_state(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    before = store.path_for(store.current_slug()).read_text()
    main(["review"])
    main(["review", "--json"])
    after = store.path_for(store.current_slug()).read_text()
    assert before == after  # byte-identical: review never saves
    f = store.load(store.current_slug())
    assert f.find_claim("c2").status == "proposed"
    assert f.find_honesty("h1").status == "proposed"


def test_review_json_shape(tmp_path, monkeypatch, capsys) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    capsys.readouterr()
    assert main(["review", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert {"slug", "proposed_claims", "proposed_honesty"} <= payload.keys()
    assert payload["proposed_claims"][0]["id"] == "c2"
    assert payload["proposed_honesty"][0]["id"] == "h1"
    assert payload["proposed_honesty"][0]["claim_id"] == "c1"
