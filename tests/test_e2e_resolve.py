"""t9: E2E repro + quality-gate coverage for issue 57's fix — the resolve
lifecycle driven through the real CLI, both engines (frame side and plan
side).

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
