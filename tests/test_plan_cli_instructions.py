"""Tests for #53 t5: instruction flags on plan moves.

Covers ``plan task --instruction`` (stores verbatim on a new task), the new
``plan instruct <tN> "<text>"`` move (adds/updates an instruction on an
existing task), the re-confirm rule (setting/changing an instruction on a
CONFIRMED task flips it back to 'proposed'), and that ``plan show --json``
carries each task's instruction.
"""

from __future__ import annotations

import json

from devague import plan_store, store
from devague.cli import main

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")


def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame that passes the frame gate; return its slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship instructions"])  # c1 announcement
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def _seeded_plan(monkeypatch, tmp_path, capsys) -> str:
    """A plan with no tasks yet, seeded from a converged frame."""
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    return slug


# ── plan task --instruction ──────────────────────────────────────────────────
def test_task_instruction_stored_verbatim(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "task", "core", "--instruction", "run the `pytest` suite", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["instruction"] == "run the `pytest` suite"
    task = plan_store.load(slug).find_task(payload["id"])
    assert task.instruction == "run the `pytest` suite"


def test_task_without_instruction_defaults_empty(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])
    capsys.readouterr()
    task = plan_store.load(slug).tasks[0]
    assert task.instruction == ""


# ── instruct: add / update on an existing task ───────────────────────────────
def test_instruct_adds_instruction_to_existing_proposed_task(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "speculative", "--origin", "llm"])  # proposed
    capsys.readouterr()
    rc = main(["plan", "instruct", "t1", "verify via `pytest`", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "t1"
    assert payload["instruction"] == "verify via `pytest`"
    assert payload["status"] == "proposed"  # was never confirmed, so unchanged
    assert payload["flipped"] is False
    task = plan_store.load(slug).find_task("t1")
    assert task.instruction == "verify via `pytest`"
    assert task.status == "proposed"


def test_instruct_updates_existing_instruction(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(
        [
            "plan",
            "task",
            "speculative",
            "--origin",
            "llm",
            "--instruction",
            "first draft",
        ]
    )
    capsys.readouterr()
    rc = main(["plan", "instruct", "t1", "second draft", "--json"])
    assert rc == 0
    task = plan_store.load(slug).find_task("t1")
    assert task.instruction == "second draft"


def test_instruct_unknown_task_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    _seeded_plan(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "instruct", "tX", "text"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such task" in err
    assert "hint:" in err


# ── re-confirm rule ───────────────────────────────────────────────────────────
def test_instruct_flips_confirmed_task_to_proposed(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])  # origin=user -> confirmed by default
    capsys.readouterr()
    assert plan_store.load(slug).find_task("t1").status == "confirmed"
    rc = main(["plan", "instruct", "t1", "how to verify", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "proposed"
    assert payload["flipped"] is True
    task = plan_store.load(slug).find_task("t1")
    assert task.status == "proposed"
    assert task.instruction == "how to verify"


def test_instruct_flip_emits_stderr_note_in_text_mode(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])  # confirmed
    capsys.readouterr()
    rc = main(["plan", "instruct", "t1", "how to verify"])  # text mode
    assert rc == 0
    err = capsys.readouterr().err
    assert "proposed" in err
    assert plan_store.load(slug).find_task("t1").status == "proposed"


def test_instruct_on_proposed_task_no_flip_note(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "speculative", "--origin", "llm"])  # proposed
    capsys.readouterr()
    rc = main(["plan", "instruct", "t1", "how to verify"])
    assert rc == 0
    out = capsys.readouterr()
    assert out.err == ""  # no flip note; status was already proposed
    assert plan_store.load(slug).find_task("t1").status == "proposed"


def test_instruct_flips_confirmed_task_json_note_only_relevant_fields(
    tmp_path, monkeypatch, capsys
) -> None:
    """A rejected task is untouched by the flip rule (only confirmed -> proposed)."""
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])  # confirmed
    main(["plan", "reject", "t1"])
    capsys.readouterr()
    rc = main(["plan", "instruct", "t1", "how to verify", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["flipped"] is False
    assert plan_store.load(slug).find_task("t1").status == "rejected"


# ── plan show --json carries instructions ────────────────────────────────────
def test_show_json_includes_task_instruction(tmp_path, monkeypatch, capsys) -> None:
    _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core", "--instruction", "do the thing"])
    capsys.readouterr()
    rc = main(["plan", "show", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tasks"][0]["instruction"] == "do the thing"


# ── discoverability ───────────────────────────────────────────────────────────
def test_instruct_registered_in_learn_and_explain(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "learn", "--json"]) == 0
    moves = json.loads(capsys.readouterr().out)["moves"]
    assert "instruct" in moves
    assert main(["plan", "explain", "instruct", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["move"] == "instruct"
