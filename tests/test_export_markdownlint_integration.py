"""#64 integration test: real markdownlint-cli2 against a hostile-input export.

Unit tests (``tests/test_md_safety.py``, ``tests/test_render.py``,
``tests/test_render_plan.py``) pin the renderer behavior against a hand-rolled
check and hard-coded expected strings. This test instead drives the actual CLI
end to end (``devague new`` … ``devague export``; ``devague plan new`` …
``devague plan export``) against a frame whose announcement ends in '.' and
whose claims/tasks/risks carry bare URLs, then shells out to the real
``markdownlint-cli2`` binary — the same dev tool this repo's own ``CLAUDE.md``
documents (``markdownlint-cli2 "**/*.md"``) and the one league-of-agents-platform's
CI gates on — and asserts zero errors, with no hand-editing.

``markdownlint-cli2`` is dev tooling here, not installed by this repo's own CI
(``tests.yml`` / ``security-checks.yml`` run neither Node nor markdownlint), so
this test skips cleanly when the binary is not on PATH rather than failing the
suite.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404 - dev-tooling integration check, not shipped code
from pathlib import Path

import pytest

from devague import plan_store, store
from devague.cli import main

_MARKDOWNLINT = shutil.which("markdownlint-cli2")
_CONFIG = Path(__file__).resolve().parent.parent / ".markdownlint-cli2.yaml"

pytestmark = pytest.mark.skipif(
    _MARKDOWNLINT is None,
    reason="markdownlint-cli2 not on PATH (dev tooling; not installed by this repo's CI)",
)

_ALL_TARGETS = [f"c{i}" for i in range(1, 7)] + [f"h{i}" for i in range(1, 7)]


def _run_markdownlint(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, test-only
        [_MARKDOWNLINT, "--config", str(_CONFIG), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        check=False,
    )


def _export_hostile_spec(monkeypatch, tmp_path) -> Path:
    monkeypatch.chdir(tmp_path)
    main(["new", "League of Agents is live at https://league-of-agents.ai."])
    main(
        [
            "interrogate",
            "c1",
            "--honesty",
            "announcement is true, verified at http://status.league-of-agents.ai.",
            "--origin",
            "user",
        ]
    )
    for kind in ("audience", "after_state", "before_state", "boundary", "success_signal"):
        main(
            [
                "capture",
                "--kind",
                kind,
                f"{kind} text ends in a period, see https://league-of-agents.ai.",
                "--origin",
                "user",
            ]
        )
    frame = store.load(store.current_slug())
    for c in frame.claims:
        if c.id == "c1":
            continue
        main(["interrogate", c.id, "--honesty", "must hold.", "--origin", "user"])
    main(["export"])
    frame = store.load(store.current_slug())
    return Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"


def _export_hostile_plan(monkeypatch, tmp_path) -> Path:
    spec_path = _export_hostile_spec(monkeypatch, tmp_path)
    frame = store.load(store.current_slug())
    main(["plan", "new", "--frame", frame.slug])
    main(
        [
            "plan",
            "task",
            "Ship the beautiful, welcoming home page.",
            "--accept",
            "page is live, verified at https://league-of-agents.ai.",
            *[flag for tid in _ALL_TARGETS for flag in ("--covers", tid)],
        ]
    )
    main(
        [
            "plan",
            "risk",
            "traffic spike risk, see http://status.league-of-agents.ai for load.",
            "--kind",
            "unknown_nonblocking",
            "--task",
            "t1",
        ]
    )
    main(["plan", "export"])
    plan = plan_store.load(plan_store.current_slug())
    plan_path = Path("docs/plans") / f"{plan.created[:10]}-{plan.slug}.md"
    return spec_path, plan_path


def test_hostile_spec_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path = _export_hostile_spec(monkeypatch, tmp_path)
    assert spec_path.exists()
    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_hostile_plan_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path, plan_path = _export_hostile_plan(monkeypatch, tmp_path)
    assert plan_path.exists()
    result = _run_markdownlint(spec_path, plan_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
