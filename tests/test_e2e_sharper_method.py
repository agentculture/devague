"""t14: one real idea runs scope -> frame -> sharper spec -> plan -> fanout brief.

The dogfooded end-to-end run of the sharper method (#53) on the shipped surface
only. The idea is real: "devague ships an unpark move" (issue #57, found while
dogfooding the multi-repo frame — a parked blocking vagueness cannot be
resolved through moves today). Covers c1/h1 (the guided arc exists end to end),
c2/h7 (driven through the public CLI surface), c3/h8 (the sharper artifacts
render instructions + scope provenance).
"""

from __future__ import annotations

import json
from pathlib import Path

from devague import store
from devague.cli import main


def _json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_e2e_scope_frame_spec_plan_fanout(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    # --- scope -> frame -----------------------------------------------------
    assert (
        main(
            [
                "new",
                "devague ships an unpark move: a parked blocking vagueness "
                "can be resolved through a first-class move",
                "--title",
                "unpark move",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "scope",
                "devague/frame.py add_vagueness",
                "--finding",
                "park only appends; no move edits or removes a vagueness once parked",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "scope",
                "devague/convergence.py blocker hint",
                "--finding",
                "the resolve hint names moves that cannot clear a blocking park",
                "--seeds",
                "c1",
            ]
        )
        == 0
    )

    # user-origin captures auto-confirm; two carry per-item instructions
    assert main(["capture", "--kind", "audience", "operators driving frames through moves"]) == 0
    assert (
        main(
            [
                "capture",
                "--kind",
                "after_state",
                "a blocking park can be resolved via a move; the frame "
                "converges without hand-editing state",
                "--instruction",
                "park a blocking item, resolve it via the move, assert converge passes",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "capture",
                "--kind",
                "why_it_matters",
                "hand-editing .devague state is forbidden; a stale blocking "
                "park otherwise blocks forever",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "capture",
                "--kind",
                "boundary",
                "no bulk edit of vagueness text; only kind and resolution transitions",
                "--instruction",
                "attempt a text edit through the move and assert it is refused",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "capture",
                "--kind",
                "success_signal",
                "1 previously-blocked frame converges after the unpark move",
            ]
        )
        == 0
    )

    frame = store.load(store.current_slug())
    claim_ids = [c.id for c in frame.claims]
    for cid in claim_ids:
        assert main(["interrogate", cid, "--honesty", f"holds and is testable for {cid}"]) == 0
    frame = store.load(store.current_slug())
    honesty_ids = [h.id for c in frame.claims for h in c.honesty_conditions]
    assert main(["confirm", *honesty_ids]) == 0

    # --- converge: gate passes; sharpness warnings (t7) fire, never block ---
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is True
    assert any("instruction" in w for w in verdict["warnings"])  # S1 on instruction-less claims

    # --- sharper spec export (t6): instruction blocks + scope provenance ----
    assert main(["export"]) == 0
    spec_files = list(Path("docs/specs").glob("*-unpark-move.md"))
    assert len(spec_files) == 1
    spec_md = spec_files[0].read_text(encoding="utf-8")
    assert "instruction: park a blocking item" in spec_md  # verbatim, not paraphrased
    assert "Scope exploration" in spec_md
    assert "devague/frame.py add_vagueness" in spec_md  # provenance cites the surface

    # --- plan: tasks with instructions cover every target -------------------
    assert main(["plan", "new", "--frame", "unpark-move"]) == 0
    capsys.readouterr()
    assert main(["plan", "show", "--json"]) == 0
    targets = [t["id"] for t in _json_out(capsys)["targets"]]
    mid = len(targets) // 2
    assert (
        main(
            [
                "plan",
                "task",
                "add the unpark transition to the frame model",
                "--accept",
                "a blocking vagueness resolves and converge passes",
                "--instruction",
                "test-first against frame.py; keep the fail-closed schema",
                *[a for t in targets[:mid] for a in ("--covers", t)],
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "plan",
                "task",
                "expose the unpark move on the CLI with teaching",
                "--accept",
                "unpark appears in learn and explain output",
                "--dep",
                "t1",
                "--instruction",
                "register like scope; update learn MOVES",
                *[a for t in targets[mid:] for a in ("--covers", t)],
            ]
        )
        == 0
    )

    # the instruct move flips a confirmed task back to proposed (t5), then re-confirm
    assert main(["plan", "instruct", "t1", "sharper guidance, still verbatim"]) == 0
    plan_state = json.loads(Path(".devague/plans/unpark-move.json").read_text(encoding="utf-8"))
    t1 = next(t for t in plan_state["tasks"] if t["id"] == "t1")
    assert t1["status"] == "proposed"
    assert main(["plan", "confirm", "t1"]) == 0

    capsys.readouterr()
    assert main(["plan", "converge", "--json"]) == 0
    plan_verdict = _json_out(capsys)
    assert plan_verdict["ready_for_plan"] is True

    # --- sharper plan export (t9) -------------------------------------------
    assert main(["plan", "export"]) == 0
    plan_files = list(Path("docs/plans").glob("*-unpark-move.md"))
    assert len(plan_files) == 1
    plan_md = plan_files[0].read_text(encoding="utf-8")
    assert "- instruction: sharper guidance, still verbatim" in plan_md

    # --- fanout brief (t9 payload): self-contained, verbatim ----------------
    capsys.readouterr()
    assert main(["plan", "waves", "--json"]) == 0
    payload = _json_out(capsys)
    assert payload["waves"] == [["t1"], ["t2"]]
    brief = payload["tasks"]["t1"]
    assert brief["summary"] == "add the unpark transition to the frame model"
    assert brief["instruction"] == "sharper guidance, still verbatim"
    assert brief["acceptance_criteria"] == ["a blocking vagueness resolves and converge passes"]
    assert set(brief["covers"]) == set(targets[:mid])
