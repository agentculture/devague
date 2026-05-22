"""Tests for the placeholder CLI verbs (learn / explain).

devague is greenfield — these verbs are honest stubs. The tests pin the
contract: each verb exits 0, prints a 'not yet implemented' signal, and
honours --json with a structured payload.
"""

from __future__ import annotations

import json

import pytest

from devague.cli import main


def test_learn_exits_zero_and_signals_greenfield(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "devague" in out
    assert "not yet implemented" in out.lower()


def test_learn_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "devague"
    assert payload["status"] == "greenfield"
    assert payload["verb"] == "learn"


def test_explain_exits_zero_and_signals_greenfield(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["explain"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "devague" in out
    assert "not yet implemented" in out.lower()


def test_explain_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verb"] == "explain"
    assert payload["status"] == "greenfield"
