"""Tests for the internalised ``status`` verbs (``devague status`` / ``devague plan status``).

``status`` used to live as embedded Python inside the ``think`` / ``spec-to-plan``
skill wrappers; issue #30 moved it into the deterministic CLI. These tests pin the
in-CLI contract directly (no subprocess): the human/JSON output shape, that a bad
``--frame`` / ``--plan`` errors to stderr with no stdout, that the verb is
**read-only** (never flips ``drafting``↔``converged``), and that the plan verb
re-checks the live source frame for drift.
"""

from __future__ import annotations

import json

from devague import plan_store, store
from devague.cli import main

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")
_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame whose gate passes (but do NOT run ``converge``)."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the plan engine"])  # c1 announcement (auto-confirmed)
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def _converged_plan(monkeypatch, tmp_path) -> str:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    args = ["plan", "task", "Build everything", "--accept", "all targets satisfied"]
    for tid in _ALL_TARGETS:
        args += ["--covers", tid]
    main(args)
    return slug


# ── frame status ──────────────────────────────────────────────────────────────
def test_frame_status_no_frames_text(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "no frames yet" in out
    assert 'devague new "<announcement>"' in out


def test_frame_status_no_frames_json(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "frame": None,
        "total": 0,
        "ready_for_spec": False,
        "blockers": [],
        "warnings": [],
        "parked_items": [],
        "required_next_moves": [],
    }


def test_frame_status_names_gaps_and_first_move(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "Devague ships a documented spec contract"])
    capsys.readouterr()
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "frame: devague-ships-a-documented-spec-contract" in out
    assert "NOT passed" in out
    assert "missing confirmed 'audience' claim" in out
    assert "recommended next move (first gap):" in out
    assert "devague capture --kind audience" in out


def test_frame_status_json_shape_when_not_converged(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "An idea"])
    capsys.readouterr()
    assert main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["frame"] == store.current_slug()
    assert payload["total"] == 1
    assert payload["ready_for_spec"] is False
    assert payload["blockers"]
    assert len(payload["required_next_moves"]) == len(payload["blockers"])


def test_frame_status_passed(tmp_path, monkeypatch, capsys) -> None:
    _converged_frame(monkeypatch, tmp_path)
    capsys.readouterr()
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "PASSED" in out
    assert "devague export" in out


def test_frame_status_bad_frame_errors_to_stderr(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "A real frame"])
    capsys.readouterr()
    rc = main(["status", "--frame", "ghost"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no such frame" in captured.err
    assert captured.out == ""  # nothing leaks to stdout on the error path (#30)


def test_frame_status_is_read_only(tmp_path, monkeypatch) -> None:
    # The frame's gate passes, but `converge` was never run — status must not
    # silently flip drafting→converged the way the old wrapper's `converge` call did.
    slug = _converged_frame(monkeypatch, tmp_path)
    assert store.load(slug).status == "drafting"
    main(["status"])
    assert store.load(slug).status == "drafting"


# ── plan status ───────────────────────────────────────────────────────────────
def test_plan_status_no_plans_text(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "status"]) == 0
    out = capsys.readouterr().out
    assert "no plans yet" in out
    assert "devague plan new --frame" in out


def test_plan_status_no_plans_json(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "plan": None,
        "total": 0,
        "ready_for_plan": False,
        "blockers": [],
        "warnings": [],
        "parked_items": [],
        "required_next_moves": [],
    }


def test_plan_status_names_gaps(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    assert main(["plan", "status"]) == 0
    out = capsys.readouterr().out
    assert f"plan: {slug}" in out
    assert "NOT passed" in out
    assert "devague plan task" in out


def test_plan_status_passed(tmp_path, monkeypatch, capsys) -> None:
    _converged_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    assert main(["plan", "status"]) == 0
    out = capsys.readouterr().out
    assert "PASSED" in out
    assert "devague plan export" in out


def test_plan_status_json_passed_shape(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    assert main(["plan", "status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == slug
    assert payload["total"] == 1
    assert payload["ready_for_plan"] is True


def test_plan_status_bad_plan_errors_to_stderr(tmp_path, monkeypatch, capsys) -> None:
    _converged_plan(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["plan", "status", "--plan", "ghost"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no such plan" in captured.err
    assert captured.out == ""


def test_plan_status_is_read_only(tmp_path, monkeypatch) -> None:
    slug = _converged_plan(monkeypatch, tmp_path)
    assert plan_store.load(slug).status == "drafting"
    main(["plan", "status"])
    assert plan_store.load(slug).status == "drafting"


def test_plan_status_surfaces_frame_drift(tmp_path, monkeypatch, capsys) -> None:
    # Regress the source frame after the plan was seeded; plan status must
    # surface the drift as a real error (stderr), not a misleading verdict.
    slug = _converged_plan(monkeypatch, tmp_path)
    main(["reject", "c2"])  # drop a required confirmed claim → frame un-converges
    capsys.readouterr()
    rc = main(["plan", "status", "--plan", slug])
    captured = capsys.readouterr()
    assert rc != 0
    assert "regressed" in captured.err
    assert captured.out == ""
