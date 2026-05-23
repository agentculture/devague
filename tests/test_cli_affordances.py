"""Tests for the agent-affordance verbs: learn / explain."""

from __future__ import annotations

import json

import pytest

from devague.cli import main


def test_learn_describes_moves(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "working backwards" in out
    assert "capture" in out and "converge" in out


def test_learn_teaches_first_question_and_guided_stages(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    # Issue #4's mandated entry point and supporting framing.
    assert "what's the announcement?" in out
    assert "users, teammates, or yourself" in out
    # The canonical 10-step guided sequence is documented.
    for stage in (
        "announcement",
        "audience",
        "after",
        "matter",
        "before",
        "honest",
        "faq",
        "boundaries",
        "success",
        "spec",
    ):
        assert stage in out


def test_learn_json_lists_moves_and_stages(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "devague"
    assert "capture" in payload["moves"]
    assert len(payload["stages"]) == 10
    assert payload["first_question"] == "What's the announcement?"


def test_explain_a_move(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "converge"])
    assert rc == 0
    assert "converge" in capsys.readouterr().out.lower()


def test_explain_unknown_move_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "nope"])
    assert rc == 1
    assert "unknown" in capsys.readouterr().err.lower()
