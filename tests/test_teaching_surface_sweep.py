"""Tests for the learn/explain documentation sweep (issues #48/#52/#84/#85/#86/#90).

A wave of code tasks shipped real surfaces (`interrogate --resolve`, `amend`,
`scope --amend` + `--seeds` accepting hard-question ids, `plan defer`,
`plan risk --amend`, transactional multi-id `plan confirm`/`plan reject`,
"live" `plan cover`, the reject cascade, and the scope subagent fan-out) ahead
of the docs catching up. This file is the docs-catch-up: it greps
`devague learn` / `devague explain` / `devague plan learn` /
`devague plan explain` output for each new verb and flag. Documentation-only
— the moves themselves are already covered by their own functional tests
elsewhere (test_cli_moves.py, test_plan_escape_hatches.py, test_cli_plan.py,
...); this file only pins that they are *taught*, closing the #52 acceptance
criterion ("learn/explain document the resolve path").
"""

from __future__ import annotations

import json

import pytest

from devague.cli import main


# ── 1. interrogate --resolve (issues #48/#52) — the criterion this task names directly
def test_learn_documents_interrogate_resolve(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "interrogate" in out
    assert "--resolve" in out
    assert "--decision" in out
    assert "USER decision" in out


def test_explain_interrogate_documents_resolve(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "interrogate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--resolve" in out
    assert "--decision" in out


def test_explain_interrogate_json_documents_resolve(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "interrogate", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "--resolve" in payload["description"]


def test_learn_operating_rules_name_interrogate_resolve_close_out(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Mirrors the existing `park --resolve` operating rule (issues #45/#55/#57/#60)
    — a blocking hard question must not read as a permanent dead end either.
    """
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "interrogate CID --resolve QID --decision TEXT" in out


# ── 2. amend (issue #84) — was entirely absent from MOVES/explain before this ──
def test_amend_is_registered_in_learn_moves(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "amend" in payload["moves"]


def test_amend_appears_in_bare_learn_moves_listing(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "\n  amend " in out


def test_explain_amend_works(capsys: pytest.CaptureFixture[str]) -> None:
    """Before this sweep, `devague explain amend` failed with 'unknown move: amend'."""
    rc = main(["explain", "amend"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "amend" in out
    assert "id churn" in out


def test_explain_amend_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "amend", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["move"] == "amend"
    assert payload["description"]


# ── 3. scope --amend + --seeds accepting hard-question (q*) ids (issue #84) ────
def test_learn_scope_seeds_mentions_claim_and_hard_question_ids(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "hard-question" in out
    assert "(q*)" in out


def test_explain_scope_mentions_amend(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "scope"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--amend" in out
    assert "SID" in out


def test_learn_json_scope_stage_mentions_hard_question_seeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    section = json.dumps(payload["scope_stage"]).lower()
    assert "hard-question" in section
    assert "q*" in section


# ── 4. plan defer (issue #85) ───────────────────────────────────────────────────
def test_plan_learn_documents_defer(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["plan", "learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "defer" in payload["moves"]


def test_plan_explain_defer_documents_reason_and_undo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["plan", "explain", "defer"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--reason" in out
    assert "--undo" in out


# ── 5. plan risk --amend (issue #84 comment) ────────────────────────────────────
def test_plan_explain_risk_documents_amend(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["plan", "explain", "risk"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--amend" in out
    assert "--text" in out
    assert "RID" in out


def test_plan_explain_risk_json_documents_amend(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["plan", "explain", "risk", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "--amend" in payload["description"]
    assert "--text" in payload["description"]


# ── 6. multi-id transactional plan confirm/reject (issue #86) ──────────────────
def test_plan_explain_confirm_documents_transactional_multi_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["plan", "explain", "confirm"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "one or more" in out
    assert "transactionally" in out


def test_plan_explain_reject_documents_transactional_multi_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["plan", "explain", "reject"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "one or more" in out
    assert "transactionally" in out


# ── 7. "live" plan cover / plan task --covers (issue #90) ──────────────────────
def test_plan_explain_cover_documents_live_frame_validation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["plan", "explain", "cover"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "live" in out


def test_plan_explain_cover_json_documents_live_frame_validation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["plan", "explain", "cover", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "live" in payload["description"].lower()


# ── 8. flat reject cascade + --json "cascaded" key ──────────────────────────────
def test_learn_documents_reject_cascade(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "cascad" in out
    assert "also rejected" in out


def test_explain_reject_json_documents_cascaded_key(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["explain", "reject", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "cascaded" in payload["description"]


# ── 9. the scope subagent fan-out (SCOPE_STAGE must not contradict SKILL.md) ───
def test_learn_documents_scope_fan_out_threshold(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "sonnet" in out
    assert "4 or fewer" in out
    assert "5 or more" in out
    assert "never run a devague move" in out


def test_learn_json_scope_stage_includes_fan_out_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "fan_out" in payload["scope_stage"]
    assert "sonnet" in payload["scope_stage"]["fan_out"].lower()


# ── 10. plan learn names all seven skills (stale "six"/missing "challenge") ────
def test_plan_learn_names_seven_skills_including_challenge(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["plan", "learn"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "seven operator skills" in out
    assert "challenge" in out
    assert "six operator skills" not in out
