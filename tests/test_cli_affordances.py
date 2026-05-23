"""Tests for the agent-affordance verbs: learn / explain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devague.cli import main

_GUIDANCE_DOC = Path(__file__).resolve().parents[1] / "docs" / "llm-guidance.md"


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


def test_learn_surfaces_operating_rules(capsys: pytest.CaptureFixture[str]) -> None:
    # devague#19: the anti-fabrication contract is always-on in `learn` output.
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "operating rules" in out
    assert "anti-fabrication" in out
    # The core rules and the not-a framing.
    assert "stay proposed" in out and "user-only" in out
    assert "not a mandatory conversation order" in out  # order is adaptive
    assert "questionnaire" in out and "prd generator" in out
    # Agent-agnostic pointer — not hardcoded to one runtime.
    assert "agents.md" in out and "claude.md" in out
    assert "docs/llm-guidance.md" in out


def test_learn_json_exposes_operating_contract(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["guidance_doc"] == "docs/llm-guidance.md"
    assert len(payload["operating_rules"]) >= 4
    assert len(payload["not_a"]) == 3
    assert any("proposed" in r.lower() for r in payload["operating_rules"])


def test_guidance_doc_exists_and_documents_the_contract() -> None:
    # The CLI points agents at this doc, so it must exist and carry the contract.
    assert _GUIDANCE_DOC.is_file()
    text = _GUIDANCE_DOC.read_text(encoding="utf-8").lower()
    assert "anti-fabrication" in text
    assert "never `confirm` your own proposal" in text or "never confirm your own proposal" in text
    assert "not a mandatory" in text  # adaptive order
    # Agent-agnostic, not Claude-specific.
    assert "agents.md" in text


def test_explain_a_move(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "converge"])
    assert rc == 0
    assert "converge" in capsys.readouterr().out.lower()


def test_explain_unknown_move_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "nope"])
    assert rc == 1
    assert "unknown" in capsys.readouterr().err.lower()
