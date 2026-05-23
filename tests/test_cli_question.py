from __future__ import annotations

import json

from devague import questions_io, store
from devague.cli import main


def _seed(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship review loop"])


def test_question_records_pending_decision(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    assert main(["question", "batch atomicity?"]) == 0
    text = store.questions_path(slug).read_text()
    assert "q1" in text and "batch atomicity?" in text
    assert ".devague/questions/" in (tmp_path / ".gitignore").read_text()


def test_questions_persist_across_runs(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["question", "first?"])
    main(["question", "second?"])  # separate invocation — must not clobber q1
    items = questions_io.parse(store.questions_path(slug).read_text())
    assert [i["id"] for i in items] == ["q1", "q2"]
    assert [i["text"] for i in items] == ["first?", "second?"]


def test_question_list_json(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["question", "only?"])
    capsys.readouterr()
    assert main(["question", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["questions"][0]["id"] == "q1"
    assert payload["questions"][0]["resolved"] is False


def test_question_resolve_records_decision(tmp_path, monkeypatch) -> None:
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    main(["question", "atomicity?"])
    assert main(["question", "--resolve", "q1", "--decision", "transactional"]) == 0
    items = questions_io.parse(store.questions_path(slug).read_text())
    assert items[0]["resolved"] is True
    assert items[0]["decision"] == "transactional"


def test_question_text_containing_delimiter_round_trips(tmp_path, monkeypatch) -> None:
    # Regression (Qodo, PR #23): a question whose text contains " — decided: "
    # must not corrupt on resolve/parse — split from the right.
    _seed(monkeypatch, tmp_path)
    slug = store.current_slug()
    tricky = "Should we use — decided: as syntax?"
    main(["question", tricky])
    main(["question", "--resolve", "q1", "--decision", "no"])
    items = questions_io.parse(store.questions_path(slug).read_text())
    assert items[0]["text"] == tricky
    assert items[0]["decision"] == "no"


def test_question_resolve_unknown_id_errors(tmp_path, monkeypatch, capsys) -> None:
    _seed(monkeypatch, tmp_path)
    main(["question", "q?"])
    assert main(["question", "--resolve", "q9", "--decision", "x"]) == 1
    assert "no such question" in capsys.readouterr().err
