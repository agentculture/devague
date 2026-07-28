"""t9/t4: E2E repro + quality-gate coverage for issue 57's and issues #48/#52's
fixes — the resolve lifecycle driven through the real CLI, both engines
(frame side and plan side), plus the frame-side hard-question resolve.

Before waves 1-2 landed, a parked ``unknown_blocking`` vagueness (frame side)
or risk (plan side) could **never** be closed out through a move — the frame
or plan could not converge again once one existed. ``park --resolve VID
--decision TEXT [--claim CN]`` and ``plan risk --resolve RID --decision
TEXT`` are the fix. This test drives ``devague.cli.main`` end to end (mirrors
the harness in ``tests/test_e2e_sharper_method.py`` and the converging-frame
helper in ``tests/test_cli_converge_export.py`` / ``tests/test_cli_plan.py``)
through issue 57's exact repro, asserting the gate blocks before the resolve
and passes after, with zero direct reads/writes of ``.devague/*.json`` —
state is only ever inspected via ``store.load`` / ``plan_store.load`` (module
functions over the JSON, never a raw ``Path(".devague/...")`` open) or CLI
``--json`` output, matching the "no hand-editing" contract the resolve moves
exist to uphold.

A parallel, permanent convergence deadlock existed for a claim's *blocking
hard question* (``interrogate --hard-question --blocking`` / ``--contradicts``):
nothing in the codebase ever set ``HardQuestion.resolved``. ``interrogate <cN>
--resolve <qN> [--decision TEXT]`` (decision c36) is the fix; the tests below
(t4, issues #48/#52) mirror the same block-resolve-converge shape through CLI
moves alone.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, not shipped code
from pathlib import Path

import pytest

from devague import plan_store, store
from devague.cli import main

_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.yaml"

_REQUIRED_KINDS = ("audience", "after_state", "why_it_matters", "boundary", "success_signal")
_PLAN_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def _converging_frame(monkeypatch, tmp_path) -> None:
    """Build a frame that satisfies every required-kind gate check, confirmed
    with a confirmed honesty condition on each spec-affecting claim — the
    minimum an issue-57 frame needs so that, once the blocking park is
    resolved, convergence is blocked by nothing else.
    """
    monkeypatch.chdir(tmp_path)
    assert main(["new", "x", "--title", "x"]) == 0  # c1 announcement, user-origin -> confirmed
    assert main(["interrogate", "c1", "--honesty", "announcement is true", "--origin", "user"]) == 0
    for kind in _REQUIRED_KINDS:
        assert main(["capture", "--kind", kind, f"{kind} text", "--origin", "user"]) == 0
    frame = store.load(store.current_slug())
    for c in frame.claims:
        if c.id == "c1":
            continue
        assert main(["interrogate", c.id, "--honesty", "must hold", "--origin", "user"]) == 0


def test_e2e_issue57_frame_park_resolve_lifecycle(tmp_path, monkeypatch, capsys) -> None:
    """Frame side: park a blocking unknown, capture the deciding claim,
    resolve the park with --decision/--claim, converge, export — the exact
    issue-57 repro quoted in the plan brief, driven only through moves.
    """
    _converging_frame(monkeypatch, tmp_path)

    # The frame would already converge but for the park below — prove the
    # park is what blocks it (not a hole in the fixture).
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    assert _json_out(capsys)["ready_for_spec"] is True

    # --- issue 57 repro -----------------------------------------------------
    assert main(["park", "temporarily unknown", "--kind", "unknown_blocking"]) == 0  # v1

    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is False
    assert any("v1" in b and "vagueness" in b for b in verdict["blockers"])

    assert (
        main(["capture", "--kind", "decision", "decided: the answer is 42", "--origin", "user"])
        == 0
    )
    frame = store.load(store.current_slug())
    decision_claim_id = next(c.id for c in frame.claims if c.kind == "decision")

    capsys.readouterr()
    assert (
        main(
            [
                "park",
                "--resolve",
                "v1",
                "--decision",
                "decided: the answer is 42",
                "--claim",
                decision_claim_id,
            ]
        )
        == 0
    )
    assert "v1 -> resolved" in capsys.readouterr().out

    # converge must now pass — the resolved park no longer blocks.
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is True

    # export writes the spec, which renders the resolved item verbatim.
    assert main(["export"]) == 0
    frame = store.load(store.current_slug())
    spec_path = Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"
    assert spec_path.exists()
    spec_md = spec_path.read_text(encoding="utf-8")
    assert "## Resolved vagueness" in spec_md
    assert (
        "- [unknown_blocking] temporarily unknown — resolved: decided: the answer is 42" in spec_md
    )


def test_e2e_issue57_frame_export_passes_markdownlint(tmp_path, monkeypatch, capsys) -> None:
    """The resolved-vagueness section renders through the same real
    markdownlint-cli2 gate the repo's own dev tooling uses (mirrors
    tests/test_export_markdownlint_integration.py); skips cleanly when the
    binary is absent from PATH, matching that test's pattern.
    """
    if _MARKDOWNLINT is None:
        pytest.skip("markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)")

    _converging_frame(monkeypatch, tmp_path)
    assert (
        main(
            ["park", "temporarily unknown, see https://example.com.", "--kind", "unknown_blocking"]
        )
        == 0
    )
    assert (
        main(["capture", "--kind", "decision", "decided: the answer is 42", "--origin", "user"])
        == 0
    )
    frame = store.load(store.current_slug())
    decision_claim_id = next(c.id for c in frame.claims if c.kind == "decision")
    assert (
        main(
            [
                "park",
                "--resolve",
                "v1",
                "--decision",
                "decided: the answer is 42, see https://example.com.",
                "--claim",
                decision_claim_id,
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    assert _json_out(capsys)["ready_for_spec"] is True

    assert main(["export"]) == 0
    frame = store.load(store.current_slug())
    spec_path = Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"
    assert spec_path.exists()

    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_CONFIG), str(spec_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_e2e_issue57_plan_risk_resolve_lifecycle(tmp_path, monkeypatch, capsys) -> None:
    """Plan side twin: an unknown_blocking risk blocks plan convergence until
    ``plan risk --resolve RID --decision TEXT`` closes it out — the same
    lifecycle as the frame side, on the plan engine's structural peer.
    """
    _converging_frame(monkeypatch, tmp_path)
    slug = store.current_slug()

    assert main(["plan", "new", "--frame", slug]) == 0
    args = ["plan", "task", "cover everything", "--accept", "all targets satisfied"]
    for target in _PLAN_TARGETS:
        args += ["--covers", target]
    assert main(args) == 0

    # plan would already converge but for the risk below.
    capsys.readouterr()
    assert main(["plan", "converge", "--json"]) == 0
    assert _json_out(capsys)["ready_for_plan"] is True

    assert main(["plan", "risk", "scope is unclear", "--kind", "unknown_blocking"]) == 0  # r1

    capsys.readouterr()
    assert main(["plan", "converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_plan"] is False
    assert any("r1" in b and "risk" in b for b in verdict["blockers"])

    capsys.readouterr()
    assert main(["plan", "risk", "--resolve", "r1", "--decision", "scope is the whole repo"]) == 0
    assert "r1 -> resolved" in capsys.readouterr().out

    capsys.readouterr()
    assert main(["plan", "converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_plan"] is True

    assert main(["plan", "export"]) == 0
    plan = plan_store.load(slug)
    plan_path = Path("docs/plans") / f"{plan.created[:10]}-{slug}.md"
    assert plan_path.exists()


def test_e2e_issue84_plan_risk_amend_after_task_recreation_still_converges(
    tmp_path, monkeypatch, capsys
) -> None:
    """The issue #84 comment repro: a plan risk's TEXT names a task id that
    later rotates (the referenced task was rejected and recreated during a
    scope change). ``plan risk --amend RID --text TEXT`` corrects the stale
    reference in place — same id, kind, and (once resolved) resolution state
    — instead of leaving misleading text in the ledger or resolving the risk
    just to record a corrected duplicate. The amend must not disturb an
    already-resolved risk's resolution, and the plan must still converge
    and export afterward.
    """
    _converging_frame(monkeypatch, tmp_path)
    slug = store.current_slug()

    assert main(["plan", "new", "--frame", slug]) == 0
    assert main(["plan", "task", "install the scanner"]) == 0  # t1
    args = ["plan", "task", "cover everything", "--accept", "all targets satisfied"]
    for target in _PLAN_TARGETS:
        args += ["--covers", target]
    assert main(args) == 0  # t2

    assert (
        main(
            [
                "plan",
                "risk",
                "t1 installs and reports the counter only",
                "--kind",
                "out_of_scope",
                "--task",
                "t1",
            ]
        )
        == 0
    )  # r1

    # simulate the scope-driven rebuild: t1 is rejected and recreated as t3,
    # which stops covering the risk's stale text (but not the risk record
    # itself) — the plan still converges (the risk is non-blocking).
    assert main(["plan", "reject", "t1"]) == 0
    assert (
        main(
            [
                "plan",
                "task",
                "install the scanner (rebuilt)",
                "--accept",
                "scanner installed and reporting",
            ]
        )
        == 0
    )  # t3

    capsys.readouterr()
    assert main(["plan", "converge", "--json"]) == 0
    assert _json_out(capsys)["ready_for_plan"] is True

    capsys.readouterr()
    rc = main(
        ["plan", "risk", "--amend", "r1", "--text", "t3 installs and reports the counter only"]
    )
    assert rc == 0
    assert "r1: amended" in capsys.readouterr().out
    risk = plan_store.load(slug).find_risk("r1")
    assert risk.text == "t3 installs and reports the counter only"
    assert (risk.id, risk.kind, risk.task_id) == ("r1", "out_of_scope", "t1")
    assert risk.resolved is False

    # now resolve it, and prove a subsequent amend leaves the resolution alone.
    capsys.readouterr()
    assert (
        main(["plan", "risk", "--resolve", "r1", "--decision", "confirmed still out of scope"]) == 0
    )
    capsys.readouterr()
    rc = main(
        ["plan", "risk", "--amend", "r1", "--text", "t3 installs and reports the counter only (v2)"]
    )
    assert rc == 0
    risk = plan_store.load(slug).find_risk("r1")
    assert risk.text == "t3 installs and reports the counter only (v2)"
    assert risk.resolved is True
    assert risk.resolution == "confirmed still out of scope"

    assert main(["plan", "converge", "--json"]) == 0
    assert main(["plan", "export"]) == 0
    plan = plan_store.load(slug)
    plan_path = Path("docs/plans") / f"{plan.created[:10]}-{slug}.md"
    assert plan_path.exists()


def test_e2e_issue48_52_hard_question_block_resolve_converge_lifecycle(
    tmp_path, monkeypatch, capsys
) -> None:
    """The exact #48/#52 repro: a blocking hard question deadlocks convergence
    until ``interrogate <cN> --resolve <qN> --decision TEXT`` clears it —
    driven only through CLI moves, with the resolved state and decision text
    verified via a real ``store.load`` (a save/load round-trip), not a raw
    JSON read.
    """
    _converging_frame(monkeypatch, tmp_path)

    # The frame would already converge but for the blocking hard question
    # raised below — prove that's what blocks it (not a fixture hole).
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    assert _json_out(capsys)["ready_for_spec"] is True

    # --- issues #48/#52 repro ------------------------------------------------
    assert main(["interrogate", "c1", "--hard-question", "is this real?", "--blocking"]) == 0  # q1

    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is False
    assert any(
        "q1" in b and "c1" in b and "blocking hard question" in b for b in verdict["blockers"]
    )
    # suggest_move names the real, shipped move — not the old dead-end hint.
    assert any("devague interrogate c1 --resolve q1" in m for m in verdict["required_next_moves"])

    capsys.readouterr()
    assert (
        main(["interrogate", "c1", "--resolve", "q1", "--decision", "yes, verified end to end"])
        == 0
    )
    assert "q1 on c1 -> resolved" in capsys.readouterr().out

    # converge must now pass — the resolved hard question no longer blocks.
    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is True

    # Save/load round-trip: resolved state and decision text survive a fresh
    # store.load, not just the in-memory object the CLI process already held.
    frame = store.load(store.current_slug())
    q = next(q for c in frame.claims for q in c.hard_questions if q.id == "q1")
    assert q.resolved is True
    assert q.resolution == "yes, verified end to end"

    # export still works with the resolved question on record.
    assert main(["export"]) == 0
    spec_path = Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"
    assert spec_path.exists()


def test_e2e_issue52_rejected_claim_unresolved_blocking_question_no_longer_blocks(
    tmp_path, monkeypatch, capsys
) -> None:
    """Issue #52's fix (3): rejecting the parent claim also clears its
    unresolved blocking hard question from the gate — driven through
    ``confirm``/``reject`` alone, no ``--resolve`` needed for this path.
    """
    _converging_frame(monkeypatch, tmp_path)

    assert (
        main(["capture", "--kind", "requirement", "an extra requirement", "--origin", "llm"]) == 0
    )
    frame = store.load(store.current_slug())
    extra_id = next(c.id for c in frame.claims if c.kind == "requirement")
    assert main(["interrogate", extra_id, "--hard-question", "needed?", "--blocking"]) == 0

    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is False
    assert any("blocking hard question" in b for b in verdict["blockers"])

    assert main(["reject", extra_id]) == 0

    capsys.readouterr()
    assert main(["converge", "--json"]) == 0
    verdict = _json_out(capsys)
    assert verdict["ready_for_spec"] is True
    assert not any("blocking hard question" in b for b in verdict["blockers"])
