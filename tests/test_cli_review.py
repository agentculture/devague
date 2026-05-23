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
    assert {"slug", "proposed_claims", "proposed_honesty", "path"} <= payload.keys()
    assert payload["proposed_claims"][0]["id"] == "c2"
    assert payload["proposed_honesty"][0]["id"] == "h1"
    assert payload["proposed_honesty"][0]["claim_id"] == "c1"


def test_review_persists_artifact_to_devague_reviews(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    slug = store.current_slug()
    assert main(["review"]) == 0
    path = store.review_path(slug)
    assert path.exists()
    # Distinct from docs/specs/, and explicitly non-authoritative.
    assert ".devague/reviews/" in path.as_posix()
    assert "docs/specs/" not in path.as_posix()
    assert "nothing confirmed yet" in path.read_text().lower()


def test_review_manages_gitignore(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    main(["review"])
    gi = (tmp_path / ".gitignore").read_text()
    assert ".devague/reviews/" in gi


def test_review_gitignore_append_is_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text("*.pyc\n")
    store.ensure_ignored(".devague/reviews/")
    store.ensure_ignored(".devague/reviews/")  # second call must not duplicate
    gi = (tmp_path / ".gitignore").read_text()
    assert gi.count(".devague/reviews/") == 1
    assert "*.pyc" in gi  # pre-existing entries preserved


def test_review_no_write_skips_file(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    slug = store.current_slug()
    assert main(["review", "--no-write"]) == 0
    assert not store.review_path(slug).exists()


def test_from_review_round_trip(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)  # c2 proposed, h1 proposed
    slug = store.current_slug()
    main(["review"])
    path = store.review_path(slug)
    edited = (
        path.read_text()
        .replace("pending `c2`", "confirm `c2`")
        .replace("pending `h1`", "reject `h1`")
    )
    path.write_text(edited)
    assert main(["confirm", "--from-review", str(path)]) == 0
    f = store.load(slug)
    assert f.find_claim("c2").status == "confirmed"
    assert f.find_honesty("h1").status == "rejected"


def test_from_review_pending_is_never_auto_confirmed(tmp_path, monkeypatch, capsys) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["review"])  # leaves every line as `pending`
    rc = main(["confirm", "--from-review", str(store.review_path(slug))])
    assert rc == 1
    assert "no decisions" in capsys.readouterr().err
    f = store.load(slug)
    assert f.find_claim("c2").status == "proposed"
    assert f.find_honesty("h1").status == "proposed"


def test_from_review_applies_only_marked_lines(tmp_path, monkeypatch) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["review"])
    path = store.review_path(slug)
    # confirm c2 only; h1 stays `pending` and must be left untouched.
    path.write_text(path.read_text().replace("pending `c2`", "confirm `c2`"))
    assert main(["confirm", "--from-review", str(path)]) == 0
    f = store.load(slug)
    assert f.find_claim("c2").status == "confirmed"
    assert f.find_honesty("h1").status == "proposed"


def test_from_review_conflicting_decisions_error(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "X"])
    p = tmp_path / "r.md"
    p.write_text("- confirm `c1`\n- reject `c1`\n")
    assert main(["confirm", "--from-review", str(p)]) == 1
    assert "conflicting" in capsys.readouterr().err


def test_from_review_missing_file_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    assert main(["confirm", "--from-review", str(tmp_path / "nope.md")]) == 1
    assert "cannot read" in capsys.readouterr().err


def test_from_review_rejects_ids_and_file_together(tmp_path, monkeypatch, capsys) -> None:
    _seed_proposed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["review"])
    rc = main(["confirm", "c2", "--from-review", str(store.review_path(slug))])
    assert rc == 1
    assert "not both" in capsys.readouterr().err
