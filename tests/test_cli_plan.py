from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from devague import plan_store, store
from devague.cli import main

_KINDS = ("audience", "after_state", "before_state", "boundary", "success_signal")
# After a converged frame seeded below: claims c1..c6, honesty h1..h6 → 12 targets.
_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _converged_frame(monkeypatch, tmp_path) -> str:
    """Seed a frame that passes the frame gate; return its slug."""
    monkeypatch.chdir(tmp_path)
    main(["new", "Ship the plan engine"])  # c1 announcement
    for kind in _KINDS:
        main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"])
    f = store.load(store.current_slug())
    for c in f.claims:
        main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"])
    return store.current_slug()


def _converged_plan(monkeypatch, tmp_path, capsys) -> str:
    """Seed + converge a plan covering every target; return the plan slug."""
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    args = ["plan", "task", "Build everything", "--accept", "all targets satisfied"]
    for tid in _ALL_TARGETS:
        args += ["--covers", tid]
    main(args)
    capsys.readouterr()
    return slug


# ── group plumbing ────────────────────────────────────────────────────────────
def test_bare_plan_prints_help(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["plan"])
    assert rc == 0
    assert "plan" in capsys.readouterr().out


def test_unknown_plan_move_errors(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["plan", "frobnicate"])
    assert exc.value.code == 1
    assert "error:" in capsys.readouterr().err


# ── new ─────────────────────────────────────────────────────────────────────
def test_plan_new_refuses_unconverged_frame(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    main(["new", "just an idea"])
    rc = main(["plan", "new", "--frame", store.current_slug()])
    assert rc == 1
    assert "has not converged" in capsys.readouterr().err


def test_plan_new_missing_frame(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["plan", "new", "--frame", "ghost"])
    assert rc == 1
    assert "no such frame" in capsys.readouterr().err


def test_plan_new_happy_and_collision(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    capsys.readouterr()
    rc = main(["plan", "new", "--frame", slug, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["slug"] == slug and payload["targets"] == 12
    # second attempt refuses (1:1 link, no clobber)
    rc = main(["plan", "new", "--frame", slug])
    assert rc == 1
    assert "already exists" in capsys.readouterr().err


# ── task / accept / depend / cover ──────────────────────────────────────────
def test_task_inline_flags_and_json(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    rc = main(
        ["plan", "task", "core", "--accept", "works", "--covers", "c1", "--dep", "t9", "--json"]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "t1" and payload["covers"] == ["c1"] and payload["deps"] == ["t9"]


def test_task_unknown_cover_target_errors(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    rc = main(["plan", "task", "x", "--covers", "c99"])
    assert rc == 1
    assert "unknown coverage target" in capsys.readouterr().err


def test_accept_depend_cover_moves(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "a"])
    main(["plan", "task", "b"])
    capsys.readouterr()
    assert main(["plan", "accept", "t1", "criterion"]) == 0
    assert main(["plan", "depend", "t2", "--on", "t1"]) == 0
    capsys.readouterr()  # drain text output before the --json read
    assert main(["plan", "cover", "t1", "--target", "c1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["covers"] == ["c1"]


def test_moves_on_unknown_task_error(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    for argv in (
        ["plan", "accept", "tX", "c"],
        ["plan", "depend", "tX", "--on", "t1"],
        ["plan", "cover", "tX", "--target", "c1"],
        ["plan", "confirm", "tX"],
    ):
        assert main(argv) == 1
        assert "no such task" in capsys.readouterr().err


def test_cover_unknown_target_errors(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "a"])
    capsys.readouterr()
    assert main(["plan", "cover", "t1", "--target", "zzz"]) == 1
    assert "unknown coverage target" in capsys.readouterr().err


# ── confirm / reject (user-only) ────────────────────────────────────────────
def test_confirm_and_reject(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    main(["plan", "task", "speculative", "--origin", "llm"])  # proposed
    capsys.readouterr()
    assert main(["plan", "confirm", "t1", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "confirmed"
    assert main(["plan", "reject", "t1"]) == 0
    assert plan_store.load(slug).find_task("t1").status == "rejected"


# ── risk ────────────────────────────────────────────────────────────────────
def test_risk_recorded_and_unknown_task_errors(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    rc = main(["plan", "risk", "scaling unknown", "--kind", "unknown_blocking", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "unknown_blocking"
    assert main(["plan", "risk", "x", "--kind", "follow_up", "--task", "tX"]) == 1
    assert "no such task" in capsys.readouterr().err


# ── converge / export ───────────────────────────────────────────────────────
def test_converge_reports_then_passes(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    rc = main(["plan", "converge", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["ready_for_plan"] is False  # no tasks yet

    args = ["plan", "task", "all", "--accept", "ok"] + sum(
        (["--covers", t] for t in _ALL_TARGETS), []
    )
    main(args)
    capsys.readouterr()
    rc = main(["plan", "converge", "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["ready_for_plan"] is True
    assert plan_store.load(slug).status == "converged"


def test_export_blocked_until_converged(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    capsys.readouterr()
    rc = main(["plan", "export"])
    assert rc == 1
    assert "has not converged" in capsys.readouterr().err


def test_export_writes_plan_md(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path, capsys)
    rc = main(["plan", "export"])
    assert rc == 0
    plan = plan_store.load(slug)
    # #12: exported docs carry a YYYY-MM-DD prefix from the plan's creation date.
    out = Path("docs/plans") / f"{plan.created[:10]}-{slug}.md"
    assert out.exists()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-.+\.md", out.name)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Build Plan — Ship the plan engine")
    assert "status: `exported`" in text
    assert plan_store.load(slug).status == "exported"


def test_export_rejects_non_plan_format(tmp_path, monkeypatch, capsys) -> None:
    _converged_plan(monkeypatch, tmp_path, capsys)
    with pytest.raises(SystemExit) as exc:
        main(["plan", "export", "--format", "spec-md"])
    assert exc.value.code == 1


# ── frame drift ───────────────────────────────────────────────────────────────
def test_converge_errors_when_frame_deleted(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path, capsys)
    Path(".devague/frames").joinpath(f"{slug}.json").unlink()
    rc = main(["plan", "converge"])
    assert rc == 1
    assert "no longer exists" in capsys.readouterr().err


def test_converge_errors_when_frame_regressed(tmp_path, monkeypatch, capsys) -> None:
    _converged_plan(monkeypatch, tmp_path, capsys)
    # Regress the source frame below convergence.
    main(["park", "scale?", "--kind", "unknown_blocking"])
    capsys.readouterr()
    rc = main(["plan", "converge"])
    assert rc == 1
    assert "regressed below convergence" in capsys.readouterr().err


# ── show / list ───────────────────────────────────────────────────────────────
def test_show_text_and_json(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path, capsys)
    assert main(["plan", "show"]) == 0
    assert "# Build Plan" in capsys.readouterr().out
    assert main(["plan", "show", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["slug"] == slug


def test_show_degrades_without_frame(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path, capsys)
    Path(".devague/frames").joinpath(f"{slug}.json").unlink()
    assert main(["plan", "show"]) == 0  # no announcement, but renders
    assert "# Build Plan" in capsys.readouterr().out


def test_list_empty_and_populated(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "list"]) == 0
    assert "no plans yet" in capsys.readouterr().out
    _converged_plan(monkeypatch, tmp_path, capsys)
    assert main(["plan", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["plans"]


def test_resolve_plan_without_current(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["plan", "show"])
    assert rc == 1
    assert "no plan selected" in capsys.readouterr().err


def test_resolve_plan_missing_slug(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["plan", "show", "--plan", "ghost"])
    assert rc == 1
    assert "no such plan" in capsys.readouterr().err


def test_resolve_plan_invalid_slug(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["plan", "show", "--plan", "../evil"])
    assert rc == 1
    assert "invalid plan slug" in capsys.readouterr().err


def test_resolve_plan_rejects_newer_schema(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path, capsys)
    p = plan_store.path_for(slug)
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["schema_version"] = raw["schema_version"] + 99
    p.write_text(json.dumps(raw), encoding="utf-8")
    rc = main(["plan", "show", "--plan", slug])
    assert rc == 1
    err = capsys.readouterr().err
    assert "schema_version" in err and "upgrade" in err


def test_resolve_plan_rejects_malformed_value(tmp_path, monkeypatch, capsys) -> None:
    slug = _converged_plan(monkeypatch, tmp_path, capsys)
    p = plan_store.path_for(slug)
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["tasks"][0]["origin"] = "alien"
    p.write_text(json.dumps(raw), encoding="utf-8")
    rc = main(["plan", "show", "--plan", slug])
    assert rc == 1
    assert "malformed" in capsys.readouterr().err


# ── waves (#20) ───────────────────────────────────────────────────────────────
def _plan_with_deps(monkeypatch, tmp_path, capsys, deps: list[list[str]]) -> str:
    """Seed an in-progress plan whose task i depends on the ids in ``deps[i-1]``."""
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    for i, d in enumerate(deps, start=1):
        argv = ["plan", "task", f"task {i}"]
        for dep in d:
            argv += ["--dep", dep]
        main(argv)
    capsys.readouterr()
    return slug


def test_waves_json_linear(tmp_path, monkeypatch, capsys) -> None:
    slug = _plan_with_deps(monkeypatch, tmp_path, capsys, [[], ["t1"], ["t2"]])
    assert main(["plan", "waves", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["plan"] == slug
    assert payload["waves"] == [["t1"], ["t2"], ["t3"]]


def test_waves_text_mode_lists_each_wave(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_deps(monkeypatch, tmp_path, capsys, [[], ["t1"]])
    assert main(["plan", "waves"]) == 0
    out = capsys.readouterr().out
    assert "t1" in out and "t2" in out


def test_waves_emit_on_unconverged_plan(tmp_path, monkeypatch, capsys) -> None:
    # No coverage / acceptance => the plan has not converged, but waves still emit:
    # waves are scheduling metadata derived from the graph, not gated on convergence.
    _plan_with_deps(monkeypatch, tmp_path, capsys, [[], ["t1"]])
    assert main(["plan", "converge", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ready_for_plan"] is False
    assert main(["plan", "waves", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["waves"] == [["t1"], ["t2"]]


def test_waves_excludes_rejected_tasks(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_deps(monkeypatch, tmp_path, capsys, [[], [], ["t1"]])
    main(["plan", "reject", "t2"])
    capsys.readouterr()
    assert main(["plan", "waves", "--json"]) == 0
    flat = [tid for w in json.loads(capsys.readouterr().out)["waves"] for tid in w]
    assert "t2" not in flat and {"t1", "t3"} <= set(flat)


def test_waves_does_not_mutate_plan_state(tmp_path, monkeypatch, capsys) -> None:
    slug = _plan_with_deps(monkeypatch, tmp_path, capsys, [[], ["t1"]])
    before = plan_store.path_for(slug).read_text(encoding="utf-8")
    assert main(["plan", "waves", "--json"]) == 0
    assert plan_store.path_for(slug).read_text(encoding="utf-8") == before


def test_waves_dangling_dep_errors(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_deps(monkeypatch, tmp_path, capsys, [["t99"]])
    assert main(["plan", "waves", "--json"]) == 1
    assert "unknown task" in capsys.readouterr().err


def test_waves_cycle_errors(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_deps(monkeypatch, tmp_path, capsys, [[], ["t1"]])
    main(["plan", "depend", "t1", "--on", "t2"])  # t1 -> t2 -> t1
    capsys.readouterr()
    assert main(["plan", "waves"]) == 1
    assert "cycle" in capsys.readouterr().err


def test_waves_dep_on_rejected_errors(tmp_path, monkeypatch, capsys) -> None:
    _plan_with_deps(monkeypatch, tmp_path, capsys, [[], ["t1"]])
    main(["plan", "reject", "t1"])  # t2 still depends on the now-rejected t1
    capsys.readouterr()
    assert main(["plan", "waves"]) == 1
    assert "rejected task" in capsys.readouterr().err


# ── learn / explain ───────────────────────────────────────────────────────────
def test_learn_and_explain(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "learn"]) == 0
    assert "spec into a buildable plan" in capsys.readouterr().out
    assert main(["plan", "learn", "--json"]) == 0
    moves = json.loads(capsys.readouterr().out)["moves"]
    assert "converge" in moves and "waves" in moves
    assert main(["plan", "explain", "waves", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["move"] == "waves"
    assert main(["plan", "explain", "task", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["move"] == "task"
    assert main(["plan", "explain", "bogus"]) == 1
    assert "unknown plan move" in capsys.readouterr().err


# ── converge surfaces warnings in text mode (PR #29) ────────────────────────────
def test_plan_converge_text_surfaces_warnings(tmp_path, monkeypatch, capsys) -> None:
    """Text-mode `plan converge` must show non-blocking warnings, like frame converge."""
    slug = _converged_frame(monkeypatch, tmp_path)
    main(["plan", "new", "--frame", slug])
    # Three confirmed tasks in a serial chain (waves [[t1],[t2],[t3]]) that cover
    # every target → the plan converges, but the over-serialized graph trips the
    # non-blocking TDD-fitness warning.
    main(
        [
            "plan",
            "task",
            "A",
            "--accept",
            "a",
            "--covers",
            "c1",
            "--covers",
            "c2",
            "--covers",
            "c3",
            "--covers",
            "c4",
            "--covers",
            "h1",
            "--covers",
            "h2",
        ]
    )
    main(
        [
            "plan",
            "task",
            "B",
            "--accept",
            "b",
            "--dep",
            "t1",
            "--covers",
            "c5",
            "--covers",
            "c6",
            "--covers",
            "h3",
            "--covers",
            "h4",
        ]
    )
    main(["plan", "task", "C", "--accept", "c", "--dep", "t2", "--covers", "h5", "--covers", "h6"])
    capsys.readouterr()
    assert main(["plan", "converge"]) == 0
    out = capsys.readouterr().out
    assert "converged ✓" in out
    assert "warnings:" in out  # over-serialized chain → visible in default text output
