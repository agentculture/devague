"""Tests for the teaching surface covering the scope stage + `question` move.

`devague learn` gains the scope-exploration lead-in (optional-but-recommended
— the recorded non-goal is that it never becomes a mandatory first stage), and
`devague explain` gains coverage for every frame-side move it was missing
(`scope`, `question`, `review`) — #53 t10, covers c9.
"""

from __future__ import annotations

import json

import pytest

from devague.cli import main


# ── learn: the scope stage is taught as optional-but-recommended ───────────
def test_learn_mentions_scope_stage(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "scope" in out
    # The real, shipped command syntax — not "planned" / "not yet" wording.
    assert "devague scope" in out
    assert "--finding" in out
    assert "--seeds" in out


def test_learn_presents_scope_as_optional_by_size(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    # Optional-but-recommended framing, citing the recorded non-goal (c7):
    # small ideas may skip it — never a mandatory first stage.
    assert "optional" in out
    assert "skip" in out
    assert "not a mandatory" in out


def test_learn_keeps_ten_stage_arc_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    # Scope is a lead-in, not one of the ten numbered stages — the existing
    # guided-arc contract (test_cli_affordances.py) must stay pinned.
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["stages"]) == 10
    assert payload["stages"][0]["name"] == "Announcement"


def test_learn_json_includes_scope_stage_section(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "scope_stage" in payload
    section = payload["scope_stage"]
    assert "scope" in json.dumps(section).lower()
    assert any("optional" in str(v).lower() for v in section.values())


def test_learn_mentions_instruction_flags_and_plan_handoff(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--instruction" in out
    # The plan-side handoff moves (#53 t5).
    assert "plan task" in out
    assert "plan instruct" in out


def test_learn_json_includes_instruction_flags_note(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "instruction_flags" in payload
    assert "--instruction" in payload["instruction_flags"]


def test_learn_existing_assertions_still_hold(capsys: pytest.CaptureFixture[str]) -> None:
    # Guard against regressing the pre-existing learn contract while adding
    # the scope lead-in (test_cli_affordances.py pins the rest).
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "what's the announcement?" in out
    assert "not a mandatory conversation order" in out


# ── explain: scope, question, and review now resolve ────────────────────────
def test_explain_scope_works(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "scope"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "scope" in out


def test_explain_question_works(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "question"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "question" in out


def test_explain_review_works(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "review"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "review" in out


def test_explain_scope_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "scope", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["move"] == "scope"
    assert payload["description"]


def test_explain_question_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "question", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["move"] == "question"
    assert payload["description"]


def test_explain_unknown_move_error_path_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "not-a-real-move"])
    assert rc == 1
    err = capsys.readouterr().err.lower()
    assert "unknown move" in err
    assert "hint:" in err
    assert "traceback" not in err


def test_learn_moves_list_now_includes_scope_question_review(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    for name in ("scope", "question", "review"):
        assert name in payload["moves"]
