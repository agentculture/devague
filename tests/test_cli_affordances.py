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


def test_learn_json_lists_moves(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "devague"
    assert "capture" in payload["moves"]


def test_explain_a_move(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "converge"])
    assert rc == 0
    assert "converge" in capsys.readouterr().out.lower()


def test_explain_unknown_move_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "nope"])
    assert rc == 1
    assert "unknown" in capsys.readouterr().err.lower()
