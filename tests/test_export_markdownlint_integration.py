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

import json
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


# ── issue-backlog-sweep t3 (#93, #49, #83, #87 c6/h6, c22/h18): a frame ──────
# mixing bare and already-backticked underscore identifiers, open parks of
# two kinds, and a rejected claim that also carried a hard question and
# seeded a scope entry — the real counter-evidence corpus shape ─────────────


def _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path) -> Path:
    monkeypatch.chdir(tmp_path)
    main(["new", "Sweep closes the issue backlog"])
    main(
        [
            "capture",
            "--kind",
            "audience",
            "operators driving _think and challenge",
            "--origin",
            "user",
        ]
    )
    main(
        [
            "capture",
            "--kind",
            "after_state",
            "specs escape `_read_file` and __init__.py safely",
            "--origin",
            "user",
        ]
    )
    main(
        [
            "capture",
            "--kind",
            "before_state",
            "exports failed markdownlint on _read_file identifiers",
            "--origin",
            "user",
        ]
    )
    main(["capture", "--kind", "boundary", "escaping never mutates frame JSON", "--origin", "user"])
    main(["capture", "--kind", "success_signal", "0 markdownlint-cli2 errors", "--origin", "user"])
    frame = store.load(store.current_slug())
    for c in frame.claims:
        main(["interrogate", c.id, "--honesty", "must hold.", "--origin", "user"])
    main(["park", "residual risk about scale", "--kind", "unknown_nonblocking"])
    main(["park", "later docs follow-up", "--kind", "follow_up"])

    # The #83 repro shape: capture (proposed), interrogate --risk, reject —
    # the hard question and the scope seed below must both vanish on export.
    main(
        [
            "capture",
            "--kind",
            "boundary",
            "the policy gate must receive rewritten args",
            "--origin",
            "llm",
        ]
    )
    frame = store.load(store.current_slug())
    contested = next(c for c in frame.claims if c.text.startswith("the policy gate"))
    main(["interrogate", contested.id, "--risk", "a hook could launder a denied command"])
    main(
        [
            "scope",
            "devague/render/spec_md.py",
            "--finding",
            "`_follow_up` no longer drops parks",
            "--seeds",
            contested.id,
        ]
    )
    main(["reject", contested.id])

    main(["converge"])
    main(["export"])
    frame = store.load(store.current_slug())
    return Path("docs/specs") / f"{frame.created[:10]}-{frame.slug}.md"


def test_mixed_identifier_export_passes_markdownlint_cli2(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    assert spec_path.exists()
    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_mixed_identifier_export_omits_rejected_content(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    out = spec_path.read_text(encoding="utf-8")
    assert "launder a denied command" not in out
    assert "policy gate must receive rewritten args" not in out
    assert "(rejected)" in out  # the dead scope seed is flagged, not silently dropped


def test_mixed_identifier_export_lists_both_open_park_kinds(tmp_path, monkeypatch) -> None:
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    out = spec_path.read_text(encoding="utf-8")
    assert "## Open parks" in out
    assert "[unknown_nonblocking] residual risk about scale" in out
    assert "[follow_up] later docs follow-up" in out


def _content_only(raw_json: str) -> dict:
    """Parse a frame JSON file, dropping the ``updated`` timestamp — the one
    field ``store.save`` always bumps on every write, unrelated to the
    escaping fix under test here.
    """
    d = json.loads(raw_json)
    d.pop("updated", None)
    return d


def test_repeated_export_is_byte_stable_and_frame_json_content_unchanged(
    tmp_path, monkeypatch
) -> None:
    # #87 acceptance (c6/h6, c22/h18): escaping is presentational only — the
    # rendered spec-md is byte-stable across repeated exports of the same
    # frame, and the frame JSON's content (everything `show --json` reads,
    # modulo the `updated` timestamp every save bumps) is untouched.
    spec_path = _build_and_export_mixed_identifier_frame(monkeypatch, tmp_path)
    frame_json_path = store.path_for(store.current_slug())
    first_spec = spec_path.read_text(encoding="utf-8")
    first_json = frame_json_path.read_text(encoding="utf-8")

    main(["export"])

    second_spec = spec_path.read_text(encoding="utf-8")
    second_json = frame_json_path.read_text(encoding="utf-8")
    assert first_spec == second_spec
    assert _content_only(first_json) == _content_only(second_json)

    result = _run_markdownlint(spec_path)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
