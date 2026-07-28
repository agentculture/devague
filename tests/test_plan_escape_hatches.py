"""Tests for #53-esd t1: plan-engine escape hatches and demotion visibility.

Covers ``depend <tN> --on <tM> --remove`` (cut one dependency edge without task
recreation), the new ``amend <tN>`` move (edit a task's summary and/or
replace/remove acceptance criteria by index), and the stdout hardening shared by
every demoting move (``instruct``, ``amend``, ``depend --remove``): a harness that
reads only stdout must still see the confirmed -> proposed flip, not just the
stderr diagnostic (issue #67).
"""

from __future__ import annotations

import json

from devague import plan_store, store
from devague.cli import main

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")


def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame that passes the frame gate; return its slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the escape hatches"])  # c1 announcement
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


# ── the stdout-only capture test (write this first, per the TDD instruction) ──
def test_all_demoting_moves_name_the_flip_on_stdout_alone(tmp_path, monkeypatch, capsys) -> None:
    """Issue #67 hardening: a harness that reads only stdout must still see the
    confirmed -> proposed demotion, exactly as spelled in the plan instruction:
    ``t1: instruction set (confirmed -> proposed; re-confirm)``.
    """
    _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "alpha"])  # t1, confirmed
    main(["plan", "task", "beta"])  # t2, confirmed
    main(["plan", "task", "gamma", "--dep", "t1"])  # t3, confirmed, depends on t1
    capsys.readouterr()  # drain the three 'added ...' lines before capturing below

    rc = main(["plan", "instruct", "t1", "how to verify"])
    assert rc == 0
    out = capsys.readouterr().out  # stdout ONLY — .err is never read in this test
    assert out.strip() == "t1: instruction set (confirmed -> proposed; re-confirm)"

    rc = main(["plan", "amend", "t2", "--summary", "beta, revised"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == "t2: amended (confirmed -> proposed; re-confirm)"

    rc = main(["plan", "depend", "t3", "--on", "t1", "--remove"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == "t3 no longer depends on t1 (confirmed -> proposed; re-confirm)"


# ── depend --remove ───────────────────────────────────────────────────────────
def test_depend_remove_round_trip_preserves_other_fields(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "root"])  # t1
    main(
        [
            "plan",
            "task",
            "core",
            "--origin",
            "llm",  # stays proposed, isolating this test from the flip rule
            "--dep",
            "t1",
            "--accept",
            "criterion one",
            "--covers",
            "c1",
            "--instruction",
            "verify via `pytest`",
        ]
    )  # t2
    capsys.readouterr()
    rc = main(["plan", "depend", "t2", "--on", "t1", "--remove", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["deps"] == []
    assert payload["flipped"] is False
    task = plan_store.load(slug).find_task("t2")
    assert task.deps == []
    assert task.summary == "core"
    assert task.acceptance_criteria == ["criterion one"]
    assert task.covers == ["c1"]
    assert task.instruction == "verify via `pytest`"
    assert task.status == "proposed"


def test_depend_remove_unknown_edge_errors_with_hint(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "a"])
    main(["plan", "task", "b"])
    capsys.readouterr()
    rc = main(["plan", "depend", "t2", "--on", "t1", "--remove"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "does not depend on" in err
    assert "hint:" in err
    assert plan_store.load(slug).find_task("t2").deps == []


def test_depend_remove_unknown_task_errors(tmp_path, monkeypatch, capsys) -> None:
    _seeded_plan(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "depend", "tX", "--on", "t1", "--remove"])
    assert rc == 1
    assert "no such task" in capsys.readouterr().err


def test_depend_remove_flips_confirmed_task_json(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "root"])  # t1, confirmed
    main(["plan", "task", "core", "--dep", "t1"])  # t2, confirmed, depends on t1
    capsys.readouterr()
    rc = main(["plan", "depend", "t2", "--on", "t1", "--remove", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "proposed"
    assert payload["flipped"] is True
    task = plan_store.load(slug).find_task("t2")
    assert task.status == "proposed"
    assert task.deps == []


def test_depend_remove_on_proposed_task_no_flip(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "root"])  # t1
    main(["plan", "task", "core", "--dep", "t1", "--origin", "llm"])  # t2, proposed
    capsys.readouterr()
    rc = main(["plan", "depend", "t2", "--on", "t1", "--remove", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "proposed"
    assert payload["flipped"] is False
    assert plan_store.load(slug).find_task("t2").status == "proposed"


def test_depend_remove_flip_emits_stderr_note_in_text_mode(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "root"])  # t1
    main(["plan", "task", "core", "--dep", "t1"])  # t2, confirmed
    capsys.readouterr()
    rc = main(["plan", "depend", "t2", "--on", "t1", "--remove"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "proposed" in err
    assert plan_store.load(slug).find_task("t2").status == "proposed"


def test_converge_stops_reporting_removed_edge(tmp_path, monkeypatch, capsys) -> None:
    """A dangling dep on an unknown task id used to be creatable through
    `plan task --dep` directly; issue #86 makes the CLI refuse that at
    creation time now, so the dangling dep is injected straight into the
    store here — simulating a plan that already carries this damage from
    before the fix (or from hand-edited JSON) — to verify `depend --remove`
    still repairs it."""
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "a"])  # t1
    main(["plan", "task", "b"])  # t2
    capsys.readouterr()
    plan = plan_store.load(slug)
    plan.find_task("t2").deps.append("ghost")  # simulate pre-existing damage
    plan_store.save(plan)

    rc = main(["plan", "converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert any("depends on unknown task ghost" in b for b in payload["blockers"])

    rc = main(["plan", "depend", "t2", "--on", "ghost", "--remove"])
    assert rc == 0
    capsys.readouterr()

    rc = main(["plan", "converge", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert not any("depends on unknown task ghost" in b for b in payload["blockers"])
    assert plan_store.load(slug).find_task("t2").deps == []


# ── amend ─────────────────────────────────────────────────────────────────────
def test_amend_does_not_touch_deps_covers_instruction(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "root"])  # t1
    main(
        [
            "plan",
            "task",
            "core",
            "--origin",
            "llm",
            "--dep",
            "t1",
            "--accept",
            "one",
            "--accept",
            "two",
            "--covers",
            "c1",
            "--instruction",
            "verify via `pytest`",
        ]
    )  # t2
    capsys.readouterr()
    rc = main(
        [
            "plan",
            "amend",
            "t2",
            "--summary",
            "core, revised",
            "--accept-replace",
            "2",
            "TWO",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"] == "core, revised"
    assert payload["acceptance_criteria"] == ["one", "TWO"]
    assert payload["flipped"] is False
    task = plan_store.load(slug).find_task("t2")
    assert task.summary == "core, revised"
    assert task.acceptance_criteria == ["one", "TWO"]
    assert task.deps == ["t1"]
    assert task.covers == ["c1"]
    assert task.instruction == "verify via `pytest`"


def test_amend_replace_and_remove_indices_refer_to_pre_call_list(
    tmp_path, monkeypatch, capsys
) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(
        [
            "plan",
            "task",
            "core",
            "--accept",
            "one",
            "--accept",
            "two",
            "--accept",
            "three",
        ]
    )  # t1, confirmed, 3 criteria
    capsys.readouterr()
    rc = main(
        [
            "plan",
            "amend",
            "t1",
            "--accept-replace",
            "2",
            "TWO",
            "--accept-remove",
            "1",
            "--accept-remove",
            "3",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["acceptance_criteria"] == ["TWO"]
    task = plan_store.load(slug).find_task("t1")
    assert task.acceptance_criteria == ["TWO"]


def test_amend_out_of_range_index_errors_without_mutating(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core", "--accept", "one"])  # t1
    capsys.readouterr()
    rc = main(["plan", "amend", "t1", "--accept-replace", "1", "ONE", "--accept-remove", "5"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "out of range" in err
    assert "hint:" in err
    task = plan_store.load(slug).find_task("t1")
    # Validation happens before any mutation — a bad index anywhere in the batch
    # leaves the whole call a no-op, including the otherwise-valid replace.
    assert task.acceptance_criteria == ["one"]


def test_amend_non_integer_index_errors_cleanly(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core", "--accept", "one"])  # t1
    capsys.readouterr()
    rc = main(["plan", "amend", "t1", "--accept-replace", "abc", "text"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "must be an integer" in err
    assert plan_store.load(slug).find_task("t1").acceptance_criteria == ["one"]


def test_amend_no_args_errors(tmp_path, monkeypatch, capsys) -> None:
    _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])
    capsys.readouterr()
    rc = main(["plan", "amend", "t1"])
    assert rc == 1
    assert "nothing to amend" in capsys.readouterr().err


def test_amend_unknown_task_errors(tmp_path, monkeypatch, capsys) -> None:
    _seeded_plan(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "amend", "tX", "--summary", "x"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no such task" in err
    assert "hint:" in err


def test_amend_refuses_on_rejected_task(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])  # t1, confirmed
    main(["plan", "reject", "t1"])
    capsys.readouterr()
    rc = main(["plan", "amend", "t1", "--summary", "new summary"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "rejected" in err
    assert "hint:" in err
    task = plan_store.load(slug).find_task("t1")
    assert task.summary == "core"  # untouched — refused, not silently applied


def test_amend_on_proposed_task_no_flip(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core", "--origin", "llm"])  # t1, proposed
    capsys.readouterr()
    rc = main(["plan", "amend", "t1", "--summary", "revised", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "proposed"
    assert payload["flipped"] is False
    assert plan_store.load(slug).find_task("t1").summary == "revised"


def test_amend_flips_confirmed_task_json(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])  # t1, confirmed
    capsys.readouterr()
    rc = main(["plan", "amend", "t1", "--summary", "revised", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "proposed"
    assert payload["flipped"] is True
    task = plan_store.load(slug).find_task("t1")
    assert task.status == "proposed"
    assert task.summary == "revised"


def test_amend_flip_emits_stderr_note_in_text_mode(tmp_path, monkeypatch, capsys) -> None:
    slug = _seeded_plan(monkeypatch, tmp_path, capsys)
    main(["plan", "task", "core"])  # t1, confirmed
    capsys.readouterr()
    rc = main(["plan", "amend", "t1", "--summary", "revised"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "proposed" in err
    assert plan_store.load(slug).find_task("t1").status == "proposed"


# ── discoverability ───────────────────────────────────────────────────────────
def test_amend_and_depend_remove_registered_in_learn_and_explain(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "learn", "--json"]) == 0
    moves = json.loads(capsys.readouterr().out)["moves"]
    assert "amend" in moves
    assert "depend" in moves

    assert main(["plan", "explain", "amend", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["move"] == "amend"
    assert "rejected" in payload["description"]

    assert main(["plan", "explain", "depend", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["move"] == "depend"
    assert "--remove" in payload["description"]
